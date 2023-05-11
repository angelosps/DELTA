from random import choice
from common import *
from utils import alcq_negate, parse_abox_assertion, parse_tbox_axiom
from add_ontology_axiom import KB_union_unknown_axiom
from subprocess import Popen, PIPE, TimeoutExpired
from grammar_utils import generate_random_statement
from os import setsid, killpg
from signal import SIGTERM


def make_true_questions(lookup_pool, inferred_axioms, max_depth, context_statements_NL):
    """Given the inferred axioms, pick one axiom from each depth [0, max_depth]
    as a true question and its negation as a false question."""

    def make_true_question(qID, axiom, depth, expl):
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

    random_false_question = make_false_question(qID, random_false_question, 0, [])

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
            "depth": 0,
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
