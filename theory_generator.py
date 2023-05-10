import signal
from argparse import ArgumentParser
from json import load, dump
from subprocess import Popen, PIPE, TimeoutExpired
from os import setsid, killpg, remove
from signal import SIGTERM
from random import choice, randint
from tqdm.auto import tqdm
from numpy.random import choice
from nltk import Nonterminal, PCFG
from owl_2_nl import get_inferred_axioms_with_explanations
from utils import *
from common import *
from nl_2_owl import create_ontology
from K_union_a_consistency import KB_union_unknown_axiom

INCONSISTENCY_MSG = "INCONSISTENT ONTOLOGY!"

### Some global data ###
individual_names = list()
all_statements_NL = dict()
context_statements_NL = dict()

TBoxAxiomQuestions = 0
RoleAssertionQuestions = 0
ConceptAssertionQuestions = 0


def choose_production(grammar, nonterminal):
    """Choose a production with specified nonterminal as LHS based on the probability distribution
    of the grammar."""
    productions = [
        item for item in grammar.productions() if item.lhs().symbol() == nonterminal
    ]
    if len(productions) == 0:
        raise ValueError(f"Nonterminal {nonterminal} not found in the grammar!")
    probabilities = [production.prob() for production in productions]
    chosen_production = choice(productions, p=probabilities)
    return chosen_production


def generate_random_statement(grammar, nonterminal):
    """Generate a random statement from the given nonterminal LHS in the grammar."""
    chosen_production = choose_production(grammar, nonterminal)
    rhs = chosen_production.rhs()
    sentence = ""

    for item in rhs:
        if isinstance(item, Nonterminal):
            item_generated_statement = generate_random_statement(grammar, item.symbol())
        else:
            item_generated_statement = item

        if len(sentence) > 0:
            sentence += " "
        sentence += item_generated_statement

    return sentence


def find_inferred_axiom_depth_expl(inferred_axioms, axiom):
    for ia in inferred_axioms:
        if ia["axiom"] == axiom:
            return ia["depth"], ia["explanation"]
    assert False


def get_subclass_false_questions(theory, inferred_axioms):
    subclass_false_questions_dict = dict()
    inferred_axioms_list = [ia["axiom"] for ia in inferred_axioms]
    inferred_tbox_axioms_list = [
        ia["axiom"] for ia in inferred_axioms if isinstance(ia["axiom"], TBoxAxiom)
    ]

    for assertion in theory.ABoxAssertions + inferred_axioms_list:
        if not isinstance(assertion, ConceptAssertion):
            continue

        lhs = assertion.concept
        TBOX_POOL = 0
        INFERRED_POOL = 1
        pool_found, rhs = issubclassof(
            lhs, theory.TBoxAxioms, inferred_tbox_axioms_list
        )

        if rhs != None:
            rhs_neg = alcq_negate(rhs)
            negated_axiom = TBoxAxiom(lhs, "⊑", rhs_neg)

            if assertion in theory.ABoxAssertions:  # and rhs in theory.TBoxAxioms:
                assertion_depth = 1
                assertion_expl = [assertion]
            elif assertion in inferred_axioms_list:
                assertion_depth, assertion_expl = find_inferred_axiom_depth_expl(
                    inferred_axioms, assertion
                )
            else:
                assert False

            subclass_axiom = TBoxAxiom(lhs, "⊑", rhs)
            if pool_found == TBOX_POOL:
                subclass_axiom_depth = 1
                subclass_axiom_expl = [subclass_axiom]
            elif pool_found == INFERRED_POOL:
                (
                    subclass_axiom_depth,
                    subclass_axiom_expl,
                ) = find_inferred_axiom_depth_expl(inferred_axioms, subclass_axiom)
            else:
                assert False

            depth = assertion_depth + subclass_axiom_depth + 1
            explanation = assertion_expl + subclass_axiom_expl + [negated_axiom]

            false_question = {
                "axiom": negated_axiom,
                "depth": depth,
                "explanation": explanation,
            }

            if depth not in subclass_false_questions_dict:
                subclass_false_questions_dict[depth] = list()
            subclass_false_questions_dict[depth].append(false_question)

    return subclass_false_questions_dict


def make_true_questions(lookup_pool, inferred_axioms, max_depth, model_format):
    """Given the inferred axioms, pick one axiom from each depth [0, max_depth]
    as a true question and its negation as a false question."""

    def make_true_question(qID, axiom, depth, expl):
        if not model_format:
            true_question_dict = {
                "id": qID,
                "text": axiom.nl(),
                "label": "True",
                "proof": expl,
                "proof_depth": depth,
            }
        else:
            true_question_dict = {
                "id": qID,
                "text": axiom.nl(),
                "label": "True",
                "depth": depth,
                "explanation": expl,
                "meta": {"DL": str(axiom), "type": str(type(axiom))},
            }

        return true_question_dict

    # Initially, make the True Questions of Depth 0 (Lookup True Question)
    qID = 1
    questions = list()

    random_true_question = choice(lookup_pool)
    random_true_question_NL = context_statements_NL[random_true_question]

    if not model_format:
        lookup_true_question = {
            "id": qID,
            "text": random_true_question_NL,
            "label": "True",
            "proof": [],
            "proof_depth": 0,
        }
    else:
        lookup_true_question = {
            "id": qID,
            "text": random_true_question_NL,
            "label": "True",
            "depth": 0,
            "explanation": [],
            "meta": {
                "DL": str(random_true_question),
                "type": str(type(random_true_question)),
            },
        }

    qID += 1
    questions.append(lookup_true_question)

    ### Map inferred axioms according to (Depth, Type) ##
    mapped_axioms = dict()
    for ia in inferred_axioms:
        key = (ia["depth"], type(ia["axiom"]))
        if not key in mapped_axioms:
            mapped_axioms[key] = list()
        mapped_axioms[key].append(ia)

    for depth in list(range(1, max_depth + 1)):
        # Pick either Concept or Role Assertion
        concept_key = (depth, ConceptAssertion)
        role_key = (depth, RoleAssertion)
        tbox_key = (depth, TBoxAxiom)

        if role_key in mapped_axioms:  # Prioritize Role Assertions
            true_question = choice(mapped_axioms[role_key])
            mapped_axioms[role_key].remove(true_question)

            if len(mapped_axioms[role_key]) == 0:
                _ = mapped_axioms.pop(role_key)
        # With probability prioritize Concept Assertions or TBox Axioms
        elif choice([0, 1]):
            if concept_key in mapped_axioms:  # Concept Assertions
                true_question = choice(mapped_axioms[concept_key])
                mapped_axioms[concept_key].remove(true_question)
                if len(mapped_axioms[concept_key]) == 0:
                    _ = mapped_axioms.pop(concept_key)
            elif tbox_key in mapped_axioms:  # Finally TBox Axioms
                true_question = choice(mapped_axioms[tbox_key])
                mapped_axioms[tbox_key].remove(true_question)
                if len(mapped_axioms[tbox_key]) == 0:
                    _ = mapped_axioms.pop(tbox_key)
            else:  # True questions did not reach the desired target depth
                return None
        else:
            if tbox_key in mapped_axioms:  # TBox Axioms
                true_question = choice(mapped_axioms[tbox_key])
                mapped_axioms[tbox_key].remove(true_question)
                if len(mapped_axioms[tbox_key]) == 0:
                    _ = mapped_axioms.pop(tbox_key)
            elif concept_key in mapped_axioms:  # Finally Concept Assertions
                true_question = choice(mapped_axioms[concept_key])
                mapped_axioms[concept_key].remove(true_question)
                if len(mapped_axioms[concept_key]) == 0:
                    _ = mapped_axioms.pop(concept_key)
            else:  # True questions did not reach the desired target depth
                return None

        true_question = make_true_question(
            qID,
            true_question["axiom"],
            true_question["depth"],
            [e.__repr__() for e in true_question["explanation"]],
        )
        questions.append(true_question)
        qID += 1

    return questions


def make_false_questions(
    qID, theory, concept_assertions, inferred_axioms, max_depth, model_format
):
    def make_false_question(qID, axiom, depth, expl, model_format):
        if not model_format:
            false_question_dict = {
                "id": qID,
                "text": axiom.nl(),
                "label": "False",
                "proof": expl,
                "proof_depth": depth,
            }
        else:
            false_question_dict = {
                "id": qID,
                "text": axiom.nl(),
                "label": "False",
                "depth": depth,
                "explanation": expl,
                "meta": {
                    "DL": str(axiom),
                    "type": str(type(axiom)),
                },
            }

        return false_question_dict

    questions = list()

    ###### MAKE THE FALSE LOOKUP QUESTION ########
    random_false_question = choice(concept_assertions)

    individual = random_false_question.individual
    negated_concept = alcq_negate(random_false_question.concept)
    random_false_question = ConceptAssertion(negated_concept, individual)

    random_false_question = make_false_question(
        qID, random_false_question, 0, [], model_format
    )

    qID += 1
    questions.append(random_false_question)
    ##############################################

    ### Map inferred axioms according to (Depth, Type) ##
    mapped_axioms = dict()
    for ia in inferred_axioms:
        key = (ia["depth"], type(ia["axiom"]))
        if not key in mapped_axioms:
            mapped_axioms[key] = list()
        mapped_axioms[key].append(ia)

    ## Make False Questions for each depth ##
    tbox_false_questions = get_subclass_false_questions(theory, inferred_axioms)

    for depth in list(range(1, max_depth + 1)):
        if depth in tbox_false_questions:  # Prioritize TBox False Questions
            false_question = choice(tbox_false_questions[depth])
            tbox_false_questions[depth].remove(false_question)
            if len(tbox_false_questions[depth]) == 0:
                _ = tbox_false_questions.pop(depth)
        else:
            concept_key = (depth, ConceptAssertion)
            if concept_key in mapped_axioms:
                false_question = choice(mapped_axioms[concept_key])
                mapped_axioms[concept_key].remove(false_question)
                if len(mapped_axioms[concept_key]) == 0:
                    _ = mapped_axioms.pop(concept_key)
                negated_concept = alcq_negate(
                    false_question["axiom"].concept
                )  # Negate it
                individual = false_question["axiom"].individual
                false_question["axiom"] = ConceptAssertion(negated_concept, individual)
            else:  # False questions did not reach the desired target depth
                return None

        false_question = make_false_question(
            qID,
            false_question["axiom"],
            false_question["depth"],
            [e.__repr__() for e in false_question["explanation"]],
            model_format,
        )
        questions.append(false_question)
        qID += 1
    return questions


def is_unknown(random_unknown_axiom, all_statements_NL):
    # Check if unknown is in inferred axioms
    if random_unknown_axiom in all_statements_NL:
        return False

    neg_random_unknown_axiom = None

    if isinstance(random_unknown_axiom, ConceptAssertion):
        individual = random_unknown_axiom.individual
        negated_concept = alcq_negate(random_unknown_axiom.concept)
        neg_random_unknown_axiom = ConceptAssertion(negated_concept, individual)

    if (neg_random_unknown_axiom is not None) and (
        neg_random_unknown_axiom in all_statements_NL
    ):  # If \not(UnknownAxiom) in inferred -> False Question
        return False

    # Otherwise, we have to make the consistency check
    try:
        KB_union_unknown_axiom(random_unknown_axiom)
    except:
        return False

    owlapi_output = str()
    with Popen(
        ["java", "-jar", "./ConsistencyChecker.jar"],
        stdout=PIPE,
        universal_newlines=True,
        preexec_fn=setsid,
    ) as process:
        try:
            owlapi_output = process.communicate(timeout=1.5)[0]
        except TimeoutExpired:
            killpg(process.pid, SIGTERM)
            return False

    if INCONSISTENCY_MSG in owlapi_output:
        return False
    return True


def generate_unknown_questions(qID, num_of_unknown_questions, grammar, model_format):
    """Generate questions with "Unknown" label.
    Generates a random statement, and if it doesn't appear in any inferred axiom,
    or in the context, then it is valid."""
    global all_statements_NL
    unknown_questions = list()
    unknown_questions_counter = 0
    tries = 0
    max_tries = 20
    while (unknown_questions_counter < num_of_unknown_questions) and (
        tries <= max_tries
    ):
        if choice([0, 1]) % 2:  # Random ABox Assertion
            random_unknown_statement = generate_random_statement(
                grammar, "ABoxAssertion"
            )
            random_unknown_axiom = parse_abox_assertion(random_unknown_statement)
        else:  # Random TBox Axiom
            random_unknown_statement = generate_random_statement(grammar, "TBoxAxiom")
            random_unknown_axiom = parse_tbox_axiom(random_unknown_statement)

        ## Unknownment Check! ##
        if is_unknown(random_unknown_axiom, all_statements_NL) == False:
            tries += 1
            continue

        tries = 0
        # valid unknown question
        UnkAxiom = random_unknown_axiom.nl()
        unknown_questions_counter += 1

        if not model_format:
            # Unknown Question #
            unk_q_dict = {
                "id": qID,
                "text": UnkAxiom,
                "label": "Unknown",
                "proof": [],
                "proof_depth": 0,
            }
        else:
            unk_q_dict = {
                "id": qID,
                "text": UnkAxiom,
                "label": "Unknown",
                "depth": 0,
                "meta": {
                    "DL": str(random_unknown_axiom),
                    "type": str(type(random_unknown_axiom)),
                },
            }

        qID += 1
        unknown_questions.append(unk_q_dict)
        all_statements_NL[random_unknown_axiom] = UnkAxiom  # Don't repeat it!

    if tries > max_tries:
        # print("Max tries in unknown reached!")
        return None

    return unknown_questions


def extend_with_all_conjunction_sides(concept, generated_concepts):
    if isinstance(concept, AtomicConcept) and concept.concept_name == "⊤":
        return set()
    if isinstance(concept, JunctionConcept) and concept.relationship == "⊓":
        LHS_set = extend_with_all_conjunction_sides(
            concept.lhs_concept, generated_concepts
        )
        RHS_set = extend_with_all_conjunction_sides(
            concept.rhs_concept, generated_concepts
        )
        return LHS_set.union(RHS_set)
    return generated_concepts.union({concept})


def issubclassof(C, TBoxPool, InferredPool):
    TBOX_POOL = 0
    INFERRED_POOL = 1
    NONE_POOL = -1
    for axiom in TBoxPool:
        if axiom.LHS_concept == C and axiom.Relationship == "⊑":
            return TBOX_POOL, axiom.RHS_concept
    for axiom in InferredPool:
        if axiom.LHS_concept == C and axiom.Relationship == "⊑":
            return INFERRED_POOL, axiom.RHS_concept
    return NONE_POOL, None


def inconceptassertion(C, ABoxAssertions):
    for assertion in ABoxAssertions:
        if not isinstance(assertion, ConceptAssertion):
            continue
        if assertion.concept == C:
            return True
    return False


def handler(signum, frame):
    raise Exception("Timed out")


def example_is_valid(context, questions):
    for x in context:
        if isinstance(x, ConceptAssertion):
            neg_x = Concept(x.individual, alcq_negate(x.concept))
            if neg_x in context:
                print(
                    f"INCONSISTENT ONTOLOGY!\nFound: '{x}', '{neg_x}' both in the same context!"
                )
                print(f"CONTEXT: {context}")
                return False
    for question in questions:
        if (
            question["depth"] == 0
            and question["label"] == "True"
            and f"{question['text']}." not in context
        ):
            print("True lookup question not in the context, skipping this theory!")
            print(f"CONTEXT: {context}")
            print(f"QUESTIONS: {questions}")
            return False
        elif (
            question["depth"] >= 1
            or (question["depth"] == 0 and question["label"] != "True")
        ) and f"{question['text']}." in context:
            print("Found question of depth > 0 in context, skipping this theory!")
            print(f"CONTEXT: {context}")
            print(f"QUESTIONS: {questions}")
            return False
    return True


def generate_random_example(
    example_id,
    example_id_prefix,
    grammar,
    statement_types,
    max_depth,
    model_format,
    grammar_level,
):
    example = None

    LHS_pool = set()
    generated_statements = set()
    generated_abox_assertions = set()
    generated_tbox_axioms = set()
    generated_assertion_concepts = set()
    generated_role_names = set()
    print("LETS GO NEW EXAMPLE")
    # Generate examples for every required type of statement (Start Symbol type)
    for statement_type in statement_types:
        start_symbol = statement_type["start_symbol"]
        num_statements_range = statement_type["num_statements_range"]
        req_num_statements = randint(num_statements_range[0], num_statements_range[1])

        num_generated_statements = 0
        max_generation_attempts = 20
        num_generation_attempts = 0

        while num_generated_statements < req_num_statements:
            if num_generation_attempts == max_generation_attempts:
                break

            # Generate random statement for current start_symbol
            generated_statement = generate_random_statement(grammar, start_symbol)

            if generated_statement in generated_statements:
                num_generation_attempts += 1
            else:
                if start_symbol == "TBoxAxiom":
                    if len(generated_assertion_concepts) == 0:
                        break

                    generated_tbox_axiom = parse_tbox_axiom(generated_statement)

                    if len(LHS_pool) == 0:
                        generated_tbox_axiom.LHS_concept = choice(
                            list(generated_assertion_concepts)
                        )
                    else:  # The LHS will be sampled from the LHS_pool #
                        generated_tbox_axiom.LHS_concept = choice(tuple(LHS_pool))

                    tbox_axiom_constraint_satisfied = tbox_axiom_constrain_check(
                        generated_tbox_axiom
                    )

                    if tbox_axiom_constraint_satisfied:
                        generated_tbox_axioms.add(generated_tbox_axiom)
                        generated_statements.add(generated_statement)
                        context_statements_NL[
                            generated_tbox_axiom
                        ] = generated_tbox_axiom.nl()
                        LHS_pool = extend_with_all_conjunction_sides(
                            generated_tbox_axiom.RHS_concept, LHS_pool
                        )
                        LHS_pool.add(generated_tbox_axiom.RHS_concept)
                        num_generated_statements += 1
                        num_generation_attempts = 0
                    else:
                        num_generation_attempts += 1
                elif start_symbol == "ABoxAssertion":
                    generated_abox_assertion = parse_abox_assertion(generated_statement)
                    concept_assertion_constraint_satisfied = True

                    if isinstance(generated_abox_assertion, ConceptAssertion):
                        concept_assertion_constraint_satisfied = (
                            concept_assertion_constrain_check(
                                generated_abox_assertion, generated_abox_assertions
                            )
                        )
                        if concept_assertion_constraint_satisfied:
                            generated_abox_assertions.add(generated_abox_assertion)
                            generated_assertion_concepts.add(
                                generated_abox_assertion.concept
                            )
                            generated_statements.add(generated_statement)
                            context_statements_NL[
                                generated_abox_assertion
                            ] = generated_abox_assertion.nl()
                            generated_assertion_concepts = (
                                extend_with_all_conjunction_sides(
                                    generated_abox_assertion.concept,
                                    generated_assertion_concepts,
                                )
                            )
                            num_generated_statements += 1
                            num_generation_attempts = 0
                        else:
                            num_generation_attempts += 1
                    else:  # RoleAssertion
                        generated_abox_assertions.add(generated_abox_assertion)
                        generated_role_names.add(generated_abox_assertion.RoleName)
                        generated_statements.add(generated_statement)
                        context_statements_NL[
                            generated_abox_assertion
                        ] = generated_abox_assertion.nl()
                        num_generated_statements += 1
                        num_generation_attempts = 0

    try:
        # Set up the signal handler
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(1)  # Set a 1-second timeout
        if (
            create_ontology(
                example_id, generated_abox_assertions, generated_tbox_axioms
            )
            == False
        ):
            print("Couldnt create ontology.")
            return None
        # Disable the signal alarm
        signal.alarm(0)
    except Exception as ex:
        # If the code times out, catch the exception and return None
        if str(ex) == "Timed out":
            print("Owlready2 Timed out!")
        print("Owlready exception!")
        return None

    owlapi_output = str()
    with Popen(
        ["java", "-jar", "./Explainer.jar"],
        stdout=PIPE,
        universal_newlines=True,
        preexec_fn=setsid,
    ) as process:
        try:
            owlapi_output = process.communicate(timeout=4.5)[0]
        except TimeoutExpired:
            killpg(process.pid, SIGTERM)
            print("Owlapi timeout!")
            return None

    if INCONSISTENCY_MSG in owlapi_output:
        print("Inconsistent ontology!")
        return None

    global all_statements_NL
    all_statements_NL = context_statements_NL.copy()  # Shallow copy!

    theory = Theory(
        list(generated_abox_assertions),
        list(generated_tbox_axioms),
        list(context_statements_NL.values())
        + ["All individuals are different from each other."],
    )

    sz_before = len(all_statements_NL)

    clean_inferred = get_inferred_axioms_with_explanations(
        owlapi_output, all_statements_NL
    )
    sz_after = len(all_statements_NL)

    assert sz_after >= sz_before

    if clean_inferred == None:
        print("No clean inferred!")
        return None

    # Keep only useful inferred axiom instances from all that owlapi has produced
    useful_inferred = inferred_axioms_constrain_check(clean_inferred, max_depth)

    if useful_inferred == None:  # no inferred axiom reached the max depth
        print("No useful inferred!")
        return None

    ## Make the UNKNOWN QUESTIONS first in order to fail early ##
    qID_pred = 2 * (max_depth + 1) + 1
    n_unknown_questions_pred = max_depth + 1

    unknown_questions = generate_unknown_questions(
        qID_pred, n_unknown_questions_pred, grammar, model_format
    )

    if unknown_questions == None:
        print("No unknown questions!")
        return None

    questions = list()
    concept_assertions = [
        a for a in theory.ABoxAssertions if isinstance(a, ConceptAssertion)
    ]
    lookup_pool = [
        a
        for a in (theory.ABoxAssertions + theory.TBoxAxioms)
        if type(a) in {ConceptAssertion, RoleAssertion, TBoxAxiom}
    ]

    if (len(concept_assertions) == 0) or (len(lookup_pool) == 0):
        print("No lookup pool!")
        return None

    ## Make the TRUE QUESTIONS ##
    true_questions = make_true_questions(
        lookup_pool, useful_inferred, max_depth, model_format
    )
    questions.extend(true_questions)

    ## Make the FALSE QUESTIONS ##
    qID = len(questions) + 1
    false_questions = make_false_questions(
        qID, theory, concept_assertions, useful_inferred, max_depth, model_format
    )

    if false_questions == None:
        print("No false questions!")
        return None

    questions.extend(false_questions)
    num_of_unknown_questions = len(questions) / 2
    qID = len(questions) + 1
    assert num_of_unknown_questions == n_unknown_questions_pred
    assert qID == qID_pred

    questions.extend(unknown_questions)

    ## Return the Generated Example ##
    example_id = str(example_id)
    if len(example_id_prefix) > 0:
        example_id = f"{example_id_prefix}-{example_id}"

    context = [f"{s}." for s in context_statements_NL.values()] + [
        "All individuals are different from each other."
    ]
    random.shuffle(context)
    example = Example(
        example_id,
        TheoryAssertionInstance(theory=theory, questions=questions),
        english=context,
        for_model=model_format,
    )

    if example_is_valid(context, questions) == False:
        print("Example non valid!")
        return None

    return example


def count_question_types(example):
    global ConceptAssertionQuestions, TBoxAxiomQuestions, RoleAssertionQuestions

    for q in example.theory_assertion_instance.questions:
        if "ConceptAssertion" in q["meta"]["type"]:
            ConceptAssertionQuestions += 1
        elif "TBoxAxiom" in q["meta"]["type"]:
            TBoxAxiomQuestions += 1
        elif "RoleAssertion" in q["meta"]["type"]:
            RoleAssertionQuestions += 1
        else:
            print(f"Unknown type of question found! {q['meta']}")
            assert False


def generate_theory(
    grammar,
    config,
    theory_op_file,
    num_of_examples,
    max_depth,
    model_format,
    grammar_level,
):
    """
    Generate a theory with specified properties per config file specifications,
    using the specified grammar.
    Arguments:
    theory_op_file: Output jsonl file containing the generated examples.
    """

    statement_types = config["theory"]["statement_types_per_example"]
    example_id_prefix = config.get("example_id_prefix", "")

    # Generate examples for every required type of statement (Start Symbol type)
    num_true_labels = 0
    num_false_labels = 0
    num_unknown_labels = 0
    curr_num_examples = 0
    progress_tracker = tqdm(total=num_of_examples)
    progress_tracker.set_description(desc="Generating Examples...")
    global all_statements_NL
    global context_statements_NL

    while curr_num_examples < num_of_examples:
        all_statements_NL.clear()
        context_statements_NL.clear()

        example = generate_random_example(
            curr_num_examples + 1,
            example_id_prefix,
            grammar,
            statement_types,
            max_depth,
            model_format,
            grammar_level,
        )
        if example is not None:
            for q in example.theory_assertion_instance.questions:
                if q["label"] == "True":
                    num_true_labels += 1
                elif q["label"] == "False":
                    num_false_labels += 1
                else:
                    num_unknown_labels += 1

            count_question_types(example)

            dump(example.to_json(), theory_op_file, ensure_ascii=False)
            theory_op_file.write("\n")

            ## Delete .owl files ##
            remove("ALCQCC.owl")
            remove("ALCQtesting.owl")
            curr_num_examples += 1
            progress_tracker.update()

    progress_tracker.close()

    print(f"Generated {curr_num_examples} examples.")
    print(f"  No. of True labels: {num_true_labels}")
    print(f"  No. of False labels: {num_false_labels}")
    print(f"  No. of Unknown labels: {num_unknown_labels}")
    print(f"  No. of ClassAssertion questions: {ConceptAssertionQuestions}")
    print(f"  No. of RoleAssertion questions: {RoleAssertionQuestions}")
    print(f"  No. of TBoxAxiom questions: {TBoxAxiomQuestions}")


def preprocess_pcfg(grammar_file):
    """Preprocesses given PCFG grammar file to return a collection of strings representing
    all the productions in the grammar. Expected grammar file format: NLTK PCFG format,
    for e.g.:
        Statement -> Fact
        Fact -> Polarity '(' Attribute Entity ')'
        Entity -> 'cat' | 'dog' | 'bald eagle' | 'rabbit' | 'mouse'
        Attribute -> 'red' | 'blue' | 'green' | 'kind' | 'nice' | 'big'
        Polarity -> '+' [0.8] | '-' [0.2]
    """
    # Iterate through the lines and collect productions in a dictionary, keyed by
    # the nonterminals. So if there are two lines, one with S -> NP VP | VP and another
    # with S -> NP VP PP on two different lines, the dictionary will contain a key 'S'
    # with value 'NP VP | VP | NP VP PP'.
    productions = []
    nonterminal_dict = {}
    for line in grammar_file.readlines():
        production_parts = line.strip().split("->", 1)
        if len(production_parts) == 2:
            lhs = production_parts[0].strip()
            rhs = production_parts[1]
            if lhs not in nonterminal_dict:
                nonterminal_dict[lhs] = rhs
            else:
                nonterminal_dict[lhs] += " | " + rhs

    # Iterate through the productions and check if each possible RHS has a probability
    # associated with it, expected to be specified like [0.5].
    productions = []
    for nonterminal in nonterminal_dict:
        rhs = nonterminal_dict[nonterminal]
        rhs_parts = [rhs_part.strip() for rhs_part in rhs.split("|")]
        num_parts = len(rhs_parts)
        found_probs = True
        for rhs_part in rhs_parts:
            rhs_part_items = rhs_part.split(" ")
            rhs_part_last_item = rhs_part_items[-1]
            if not (
                rhs_part_last_item.startswith("[") and rhs_part_last_item.endswith("]")
            ):
                found_probs = False
                break
        # If any of the RHS part items did not have an associated probability, assign all of them equal
        # probability.
        if not found_probs:
            prob = 1.0 / num_parts
            rhs_parts_with_probs = []
            for rhs_part in rhs_parts:
                rhs_part_mod = rhs_part + " " + "[" + str(prob) + "]"
                rhs_parts_with_probs.append(rhs_part_mod)
            rhs_parts = rhs_parts_with_probs
        final_rhs = " | ".join(rhs_parts)
        production = f"{nonterminal} -> {final_rhs}"
        productions.append(production)
    return productions


def parse_args():
    parser = ArgumentParser(description="Theory Generator.")
    parser.add_argument("--grammar", required=True, help="Grammar (CFG) for theory")
    parser.add_argument(
        "--config-json",
        required=True,
        help="Json format config file with parameters to generate theory",
    )
    parser.add_argument(
        "--op-theory-jsonl",
        required=True,
        help="Output Jsonl file containing an example json object per line. Json object has the format of the TheoryAssertionInstance class",
    )
    parser.add_argument(
        "--num-of-examples",
        required=True,
        help="Total number of examples to generate.",
    )
    parser.add_argument(
        "--max-depth",
        required=True,
        help="Maximum reasoning depth for example questions.",
    )
    parser.add_argument(
        "--model-format",
        default=True,
        help="Make the dataset in a format for the model.",
    )
    parser.add_argument(
        "--grammar-level",
        required=True,
        help="Grammar level of expressiveness",
    )
    return parser.parse_args()


def run(args):
    with open(args.grammar, "r") as grammar_file, open(
        args.config_json, "r"
    ) as config_json_file, open(args.op_theory_jsonl, "w") as theory_op_file:
        grammar_level = int(args.grammar_level)
        config = load(config_json_file)
        production_strs = preprocess_pcfg(grammar_file)
        grammar_str = "\n".join(production_strs)
        grammar = PCFG.fromstring(grammar_str)
        model_format = True if args.model_format == "True" else False
        global individual_names
        individual_names = [
            i.rhs()[0] for i in grammar.productions(lhs=Nonterminal("IndividualName"))
        ]

        generate_theory(
            grammar,
            config,
            theory_op_file,
            int(args.num_of_examples),
            int(args.max_depth),
            model_format,
            grammar_level,
        )


def main():
    args = parse_args()
    run(args)


if __name__ == "__main__":
    main()
