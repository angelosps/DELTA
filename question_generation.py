from random import choice
from common import *
from utils import alcq_negate, parse_abox_assertion, parse_tbox_axiom
from add_ontology_axiom import KB_union_unknown_axiom
from subprocess import Popen, PIPE, TimeoutExpired
from grammar_utils import generate_random_statement
from os import setsid, killpg
from signal import SIGTERM
from global_variables import INCONSISTENCY_MSG


def make_true_question(question_ID, axiom, depth, explanation, axiom_nl=None):
    """Helper function to create a true question."""
    true_question_dict = {
        "id": question_ID,
        "text": axiom_nl if axiom_nl is not None else axiom.nl(),
        "label": "True",
        "depth": depth,
        "explanation": explanation,
        "meta": {"DL": str(axiom), "type": str(type(axiom))},
    }

    return true_question_dict


def select_assertion(mapped_axioms, keys, concept_bias=0.5):
    """Helper function to select an assertion from mapped axioms."""
    for key in keys:
        if key in mapped_axioms:
            if (
                isinstance(key, tuple)
                and key[1] == ConceptAssertion
                and random.random() > concept_bias
            ):
                # Check if a TBoxAxiom is available
                tbox_key = (key[0], TBoxAxiom)
                if tbox_key in mapped_axioms:
                    continue  # Skip to the TBoxAxiom
                # If no TBoxAxiom available, don't skip the ConceptAssertion

            selected_assertion = choice(mapped_axioms[key])
            mapped_axioms[key].remove(selected_assertion)

            if len(mapped_axioms[key]) == 0:
                _ = mapped_axioms.pop(key)

            return selected_assertion

    return None


from collections import defaultdict


def make_true_questions(lookup_pool, inferred_axioms, max_depth, context2NL):
    qID = 1
    questions = list()

    # Create a lookup true question
    random_true_question = choice(lookup_pool)
    # Get it's NL representation from the dict of NL
    random_true_question_NL = context2NL[random_true_question]

    lookup_true_question = make_true_question(
        question_ID=qID,
        axiom=random_true_question,
        depth=0,
        explanation=[],
        axiom_nl=random_true_question_NL,
    )
    questions.append(lookup_true_question)

    if max_depth == 0:
        return questions

    qID += 1
    # Map inferred axioms according to (Depth, Type)
    mapped_axioms = defaultdict(list)
    for ia in inferred_axioms:
        mapped_axioms[(ia["depth"], type(ia["axiom"]))].append(ia)

    # Create questions for each depth
    for depth in list(range(1, max_depth + 1)):
        # Prioritize Role Assertions
        true_question = select_assertion(
            mapped_axioms,
            [(depth, RoleAssertion), (depth, ConceptAssertion), (depth, TBoxAxiom)],
        )

        # No true questions found for this depth
        if true_question is None:
            print("IMPOSSIBLEE ")
            return []

        # Create a question for the selected assertion
        true_question = make_true_question(
            qID,
            true_question["axiom"],
            true_question["depth"],
            [str(e) for e in true_question["explanation"]],
        )
        questions.append(true_question)
        qID += 1

    return questions


def find_inferred_axiom_depth_expl(inferred_axioms, axiom):
    for ia in inferred_axioms:
        if ia["axiom"] == axiom:
            return ia["depth"], ia["explanation"]
    assert False


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


def make_false_questions(qID, theory, concept_assertions, inferred_axioms, max_depth):
    def make_false_question(qID, axiom, depth, expl):
        return {
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

    def choose_and_remove(list):
        chosen_element = choice(list)
        list.remove(chosen_element)
        return chosen_element

    # Create false lookup question
    false_lookup_question = choice(concept_assertions)
    negated_concept = alcq_negate(false_lookup_question.concept)
    false_lookup_question = ConceptAssertion(
        negated_concept, false_lookup_question.individual
    )
    questions = [make_false_question(qID, false_lookup_question, 0, [])]

    if max_depth == 0:
        return questions

    qID += 1

    # Map inferred axioms according to (Depth, Type)
    mapped_axioms = defaultdict(list)
    for ia in inferred_axioms:
        mapped_axioms[(ia["depth"], type(ia["axiom"]))].append(ia)

    # Get false questions for TBox axioms
    tbox_false_questions = get_subclass_false_questions(theory, inferred_axioms)

    # Make False Questions for each depth
    for depth in range(1, max_depth + 1):
        if depth in tbox_false_questions:
            false_question = choose_and_remove(tbox_false_questions[depth])
            if not tbox_false_questions[depth]:
                del tbox_false_questions[depth]
        else:
            if (depth, ConceptAssertion) not in mapped_axioms:
                return []
            false_question = choose_and_remove(mapped_axioms[(depth, ConceptAssertion)])
            if not mapped_axioms[(depth, ConceptAssertion)]:
                del mapped_axioms[(depth, ConceptAssertion)]

            negated_concept = alcq_negate(false_question["axiom"].concept)
            false_question["axiom"] = ConceptAssertion(
                negated_concept, false_question["axiom"].individual
            )

        if false_question is None:
            return []

        false_question = make_false_question(
            qID,
            false_question["axiom"],
            false_question["depth"],
            [str(e) for e in false_question["explanation"]],
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
            owlapi_output = process.communicate(timeout=3)[0]
        except TimeoutExpired:
            killpg(process.pid, SIGTERM)
            return False

    if INCONSISTENCY_MSG in owlapi_output:
        return False
    return True


def generate_unknown_questions(qID, num_of_unknown_questions, grammar, all2NL):
    """Generate questions with "Unknown" label.
    Generates a random statement, and if it doesn't appear in any inferred axiom,
    or in the context, then it is valid."""
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
        if is_unknown(random_unknown_axiom, all2NL) == False:
            tries += 1
            continue

        tries = 0
        # valid unknown question
        random_unknown_axiom_nl = random_unknown_axiom.nl()
        unknown_questions_counter += 1

        unk_q_dict = {
            "id": qID,
            "text": random_unknown_axiom_nl,
            "label": "Unknown",
            "depth": "na",
            "meta": {
                "DL": str(random_unknown_axiom),
                "type": str(type(random_unknown_axiom)),
            },
        }

        qID += 1
        unknown_questions.append(unk_q_dict)
        all2NL[random_unknown_axiom] = random_unknown_axiom_nl  # Don't repeat it!

    if tries > max_tries:
        return None

    return unknown_questions
