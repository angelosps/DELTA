import signal
from argparse import ArgumentParser
from json import load, dump
from subprocess import Popen, PIPE, TimeoutExpired
from os import setsid, killpg, remove
from signal import SIGTERM
from random import choice, randint
from tqdm.auto import tqdm
from nltk import Nonterminal, PCFG
from owl_2_nl import get_inferred_axioms_with_explanations
from utils import *
from common import *
from nl_2_owl import create_ontology
from grammar_utils import *
from question_generation import *

### Some global data ###
individual_names = list()
all_statements_NL = dict()
context_statements_NL = dict()

TBoxAxiomQuestions = 0
RoleAssertionQuestions = 0
ConceptAssertionQuestions = 0


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


def handle_abox_assertion_case(
    generated_statement,
    generated_abox,
    generated_role_names,
    generated_abox_concepts,
    generated_statements,
    context_statements_NL,
):
    generated_abox_assertion = parse_abox_assertion(generated_statement)
    concept_assertion_constraint_satisfied = True

    if isinstance(generated_abox_assertion, ConceptAssertion):
        concept_assertion_constraint_satisfied = concept_assertion_constrain_check(
            generated_abox_assertion, generated_abox
        )
        if concept_assertion_constraint_satisfied:
            generated_abox.add(generated_abox_assertion)
            generated_abox_concepts.add(generated_abox_assertion.concept)
            generated_statements.add(generated_statement)
            context_statements_NL[
                generated_abox_assertion
            ] = generated_abox_assertion.nl()
            generated_abox_concepts = extend_with_all_conjunction_sides(
                generated_abox_assertion.concept,
                generated_abox_concepts,
            )
            return True
    else:  # RoleAssertion
        generated_abox.add(generated_abox_assertion)
        generated_role_names.add(generated_abox_assertion.RoleName)
        generated_statements.add(generated_statement)
        context_statements_NL[generated_abox_assertion] = generated_abox_assertion.nl()
        return True

    return False


def handle_tbox_axiom_case(
    generated_statement,
    generated_abox_concepts,
    generated_tbox,
    lhs_pool,
    generated_statements,
    context_statements_NL,
):
    generated_tbox_axiom = parse_tbox_axiom(generated_statement)

    if len(lhs_pool) == 0:
        generated_tbox_axiom.LHS_concept = choice(list(generated_abox_concepts))
    else:  # The LHS will be sampled from the lhs_pool #
        generated_tbox_axiom.LHS_concept = choice(tuple(lhs_pool))

    tbox_axiom_constraint_satisfied = tbox_axiom_constrain_check(generated_tbox_axiom)

    if tbox_axiom_constraint_satisfied:
        generated_tbox.add(generated_tbox_axiom)
        generated_statements.add(generated_statement)
        context_statements_NL[generated_tbox_axiom] = generated_tbox_axiom.nl()
        lhs_pool = extend_with_all_conjunction_sides(
            generated_tbox_axiom.RHS_concept, lhs_pool
        )
        lhs_pool.add(generated_tbox_axiom.RHS_concept)
        return True
    else:
        return False


def generate_KB(
    statement_types,
    grammar,
    generated_statements,
    generated_abox,
    generated_abox_concepts,
    generated_role_names,
    generated_tbox,
    lhs_pool,
    context_statements_NL,
):
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
                    if len(generated_abox_concepts) == 0:
                        break
                    if handle_tbox_axiom_case(
                        generated_statement,
                        generated_abox_concepts,
                        generated_tbox,
                        lhs_pool,
                        generated_statements,
                        context_statements_NL,
                    ):
                        num_generated_statements += 1
                        num_generation_attempts = 0
                    else:
                        num_generation_attempts += 1

                elif start_symbol == "ABoxAssertion":
                    if handle_abox_assertion_case(
                        generated_statement,
                        generated_abox,
                        generated_role_names,
                        generated_abox_concepts,
                        generated_statements,
                        context_statements_NL,
                    ):
                        num_generated_statements += 1
                        num_generation_attempts = 0
                    else:
                        num_generation_attempts += 1


def process_ontology_and_inferred_axioms(
    example_id, generated_abox, generated_tbox, context_statements_NL, max_depth
):
    try:
        # Set up the signal handler
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(1)  # Set a 1-second timeout
        if create_ontology(example_id, generated_abox, generated_tbox) == False:
            print("Couldn't create ontology.")
            return None, None
        # Disable the signal alarm
        signal.alarm(0)
    except Exception as ex:
        # If the code times out, catch the exception and return None
        if str(ex) == "Timed out":
            print("Owlready2 Timed out!")
        print("Owlready exception!")
        return None, None

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
            return None, None

    if INCONSISTENCY_MSG in owlapi_output:
        print("Inconsistent ontology!")
        return None, None

    global all_statements_NL
    all_statements_NL = context_statements_NL.copy()  # Shallow copy!

    theory = Theory(
        list(generated_abox),
        list(generated_tbox),
        list(context_statements_NL.values())
        + ["All individuals are different from each other."],
    )

    inferred_axioms = get_inferred_axioms_with_explanations(
        owlapi_output, all_statements_NL
    )

    if inferred_axioms == None:
        print("No inferred axioms!")
        return None, None

    # Keep only useful inferred axiom instances from all that owlapi has produced
    useful_inferred_axioms = inferred_axioms_constrain_check(inferred_axioms, max_depth)

    if useful_inferred_axioms == None:  # no inferred axiom reached the max depth
        print("No useful inferred!")
        return None, None

    return theory, useful_inferred_axioms


def generate_example_questions(
    example_id,
    example_id_prefix,
    theory,
    useful_inferred,
    max_depth,
    grammar,
    context_statements_NL,
):
    qID = 2 * (max_depth + 1) + 1
    n_unknown_questions = max_depth + 1

    unknown_questions = generate_unknown_questions(
        qID,
        n_unknown_questions,
        grammar,
        all_statements_NL,
    )

    if unknown_questions == None:
        print("No unknown questions!")
        return None

    questions = list()
    concept_assertions = [
        assertion
        for assertion in theory.ABoxAssertions
        if isinstance(assertion, ConceptAssertion)
    ]

    lookup_questions_pool = [
        a
        for a in (theory.ABoxAssertions + theory.TBoxAxioms)
        if type(a) in {ConceptAssertion, RoleAssertion, TBoxAxiom}
    ]

    if len(concept_assertions) == 0 or len(lookup_questions_pool) == 0:
        print("Lookup questions pool is empty!")
        return None

    true_questions = make_true_questions(
        lookup_questions_pool, useful_inferred, max_depth, context_statements_NL
    )
    questions.extend(true_questions)

    qID = len(questions) + 1
    false_questions = make_false_questions(
        qID, theory, concept_assertions, useful_inferred, max_depth
    )

    if false_questions == None:
        print("No false questions!")
        return None

    questions.extend(false_questions)
    questions.extend(unknown_questions)

    example_id = str(example_id)
    if len(example_id_prefix) > 0:
        example_id = f"{example_id_prefix}-{example_id}"

    context = [f"{sentence}." for sentence in context_statements_NL.values()] + [
        "All individuals are different from each other."
    ]

    random.shuffle(context)

    example = Example(
        example_id,
        TheoryAssertionInstance(theory=theory, questions=questions),
        english=context,
    )

    if example_is_valid(context, questions) == False:
        print("Example is not valid!")
        return None

    return example


def generate_random_example(
    example_id, example_id_prefix, grammar, statement_types, max_depth
):
    example = None

    generated_statements = set()
    generated_abox = set()
    generated_abox_concepts = set()
    generated_role_names = set()
    generated_tbox = set()
    lhs_pool = set()

    generate_KB(
        statement_types,
        grammar,
        generated_statements,
        generated_abox,
        generated_abox_concepts,
        generated_role_names,
        generated_tbox,
        lhs_pool,
        context_statements_NL,
    )

    theory, useful_inferred = process_ontology_and_inferred_axioms(
        example_id, generated_abox, generated_tbox, context_statements_NL, max_depth
    )

    if theory == None or useful_inferred == None:
        return None

    example = generate_example_questions(
        example_id,
        example_id_prefix,
        theory,
        useful_inferred,
        max_depth,
        grammar,
        context_statements_NL,
    )

    if example != None:
        print(example.english)
        print(example.logical_forms)

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


def generate_theory(grammar, config, theory_op_file, num_of_examples, max_depth):
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


def parse_args():
    parser = ArgumentParser(description="Theory Generator.")
    parser.add_argument("--grammar", required=True, help="ALCQ Grammar (PCFG)")
    parser.add_argument(
        "--config-json",
        required=True,
        help="Json format config file with parameters to generate theory",
    )
    parser.add_argument(
        "--output-jsonl",
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
    return parser.parse_args()


def run(args):
    with open(args.grammar, "r") as grammar_file, open(
        args.config_json, "r"
    ) as config_json_file, open(args.output_jsonl, "w") as theory_op_file:
        config = load(config_json_file)
        production_strs = preprocess_pcfg(grammar_file)
        grammar_str = "\n".join(production_strs)
        grammar = PCFG.fromstring(grammar_str)
        global individual_names
        individual_names = [
            i.rhs()[0] for i in grammar.productions(lhs=Nonterminal("IndividualName"))
        ]

        print(
            f"\n\nStarting data generation with grammar: '{args.grammar}', number of examples: {args.num_of_examples}, max depth: {args.max_depth}.\n"
        )

        generate_theory(
            grammar,
            config,
            theory_op_file,
            int(args.num_of_examples),
            int(args.max_depth),
        )


def main():
    args = parse_args()
    run(args)


if __name__ == "__main__":
    main()
