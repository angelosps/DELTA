from common import (
    AtomicConcept,
    JunctionConcept,
    RestrictionConcept,
    TBoxAxiom,
    ConceptAssertion,
    RoleAssertion,
)


def parse_abox_assertion(text):
    """Parses text into an ABox Assertion (Concept / Role Assertion).

    Args:
        text (str): Text representing an ABox assertion.

    Returns:
        ConceptAssertion or RoleAssertion: Parsed ABox assertion.

    Raises:
        ValueError: If the text is None.
    """

    if text is None:
        raise ValueError("Empty Assertion!")

    text = text.split()

    if len(text) == 6:  # Role Assertion
        role_name = text[0]
        individual_name1 = text[2]
        individual_name2 = text[4]
        return RoleAssertion(role_name, individual_name1, individual_name2)
    else:  # Concept Assertion
        concept = parse_concept(" ".join(text[1:-4]))  # remove the outer parentheses
        individual_name = text[-2]
        return ConceptAssertion(concept, individual_name)


def is_junction_concept(text, connective):
    """Checks if the text represents a junction concept.

    Args:
        text (str): Text that may representing a junction concept.
        connective (str): Junction connective.

    Returns:
        int: Index of the connective if the text is a junction concept, -1 otherwise.
    """
    connective_idx = text.find(connective)
    if connective_idx == -1:
        return -1

    indexes = [i for i, char in enumerate(text) if char == connective]

    for i in indexes:
        if text.count("(", 0, i) == text.count(")", 0, i) and text.count(
            "(", i + 1, len(text)
        ) == text.count(")", i + 1, len(text)):
            return i

    return -1


def parse_atomic_concept(text_list):
    polarity = text_list[0]
    concept_name = text_list[1]
    return AtomicConcept(polarity, concept_name)


def parse_junction_concept(text, connective):
    lhs_text, rhs_text = text.split(connective)

    lhs_text = lhs_text[lhs_text.find("(") + 1 : lhs_text.rfind(")")]
    rhs_text = rhs_text[rhs_text.find("(") + 1 : rhs_text.rfind(")")]

    lhs_concept = parse_concept(lhs_text.strip())
    rhs_concept = parse_concept(rhs_text.strip())

    atomic_in_lhs = isinstance(lhs_concept, AtomicConcept) or (
        isinstance(lhs_concept, JunctionConcept) and lhs_concept.has_atomic
    )

    atomic_in_rhs = isinstance(rhs_concept, AtomicConcept) or (
        isinstance(rhs_concept, JunctionConcept) and rhs_concept.has_atomic
    )

    return JunctionConcept(
        lhs_concept, connective, rhs_concept, atomic_in_lhs, atomic_in_rhs
    )


def parse_restriction_concept(text, restriction, role_idx=1):
    text_list = text.split()
    role_name = text_list[role_idx]
    inner_concept = ""

    left_parentheses = 1
    right_parentheses = 0
    start_idx = text.find("(") + 1

    for x in text[start_idx:]:
        if x == "(":
            left_parentheses += 1
        elif x == ")":
            right_parentheses += 1

        if left_parentheses == right_parentheses:
            break
        inner_concept += x

    return RestrictionConcept(
        restriction, role_name, parse_concept(inner_concept.strip())
    )


def parse_concept(text):
    """Parses DL text into a Concept"""

    text = text.strip()
    text_list = text.replace("(", "").replace(")", "").split()

    if len(text_list) == 2:
        return parse_atomic_concept(text_list)

    if "⊓" in text:
        return parse_junction_concept(text, "⊓")

    if "⊔" in text:
        return parse_junction_concept(text, "⊔")

    if text_list[0] in {"∀", "∃"}:
        return parse_restriction_concept(text, restriction=text_list[0])

    if text_list[0] in {">", "<", "=", ">=", "<="}:
        restriction = " ".join(text_list[0:2])
        return parse_restriction_concept(text, restriction=restriction, role_idx=2)

    raise ValueError(f"Unexpected text in concept parser: {text}")


def parse_tbox_axiom(statement_txt):
    """
    Parses text into a TBox Axiom (Subsumption / Equivalence).
    E.g.:
        + male ⊑ + person
    """
    if "⊑" in statement_txt:
        lhs_txt, rhs_txt = statement_txt.split("⊑", 1)
        relation = "⊑"
    elif "≡" in statement_txt:
        lhs_txt, rhs_txt = statement_txt.split("≡", 1)
        relation = "≡"
    else:
        raise ValueError("Invalid TBox Axiom!")

    lhs = parse_concept(lhs_txt.strip())
    rhs = parse_concept(rhs_txt.strip())
    return TBoxAxiom(lhs, relation, rhs)


def contains_same_sides(concept):
    if isinstance(concept, AtomicConcept):
        return False
    elif isinstance(concept, RestrictionConcept):
        return contains_same_sides(concept.concept)
    else:  # Junction Concept
        rhs = concept.rhs_concept
        lhs = concept.lhs_concept

        if isinstance(lhs, AtomicConcept) and isinstance(rhs, AtomicConcept):
            return lhs.concept_name == rhs.concept_name  # ignore the polarity

        if isinstance(lhs, RestrictionConcept) and isinstance(rhs, RestrictionConcept):
            return (
                lhs == rhs
                or contains_same_sides(lhs.concept)
                or contains_same_sides(rhs.concept)
            )

        lhs_result = False
        rhs_result = False

        if isinstance(lhs, JunctionConcept):
            lhs_result = contains_same_sides(lhs)

        if isinstance(rhs, JunctionConcept):
            rhs_result = contains_same_sides(rhs)

        return lhs_result or rhs_result


def is_tautology(axiom):
    """Checks if a given axiom is a tautology:
            1. ( + ⊤ ) ( individual )
            2. ( + ⊥ ) ⊑ RHS
            3. LHS ⊑ ( + ⊤ )
    Args:
        axiom (str): text representing an axiom

    Returns:
        bool: True if and only if the axiom is a tautology
    """
    if isinstance(axiom, ConceptAssertion):
        return axiom.concept == "⊤"
    elif isinstance(axiom, TBoxAxiom):
        if (
            isinstance(axiom.LHS_concept, AtomicConcept)
            and axiom.LHS_concept.concept_name == "⊥"
        ):
            return True
        elif (
            isinstance(axiom.RHS_concept, AtomicConcept)
            and axiom.RHS_concept.concept_name == "⊤"
        ):
            return True
    return False


def tbox_axiom_constrain_check(generated_tbox_axiom, current_tbox):
    """
    Checks whether a generated TBox Axiom is valid according to the following rules:
        1. TBox axioms with the same sides, applied recursively
        2. Tautologies
    """

    lhs = generated_tbox_axiom.LHS_concept
    rhs = generated_tbox_axiom.RHS_concept

    if contains_same_sides(lhs) or contains_same_sides(rhs):
        return False

    if isinstance(lhs, AtomicConcept) and lhs.concept_name == "⊥":
        return False

    # TBox Axiom with LHS Concept = RHS Concept is not useful
    if generated_tbox_axiom.LHS_concept == generated_tbox_axiom.RHS_concept:
        return False

    graph = build_graph(list(current_tbox) + [generated_tbox_axiom])

    if has_cycle(graph):
        return False
    return True


def build_graph(tbox_axioms):
    graph = {}
    for axiom in tbox_axioms:
        lhs = axiom.LHS_concept
        rhs = axiom.RHS_concept

        if lhs not in graph:
            graph[lhs] = []

        if rhs not in graph:
            graph[rhs] = []

        graph[lhs].append(rhs)

    return graph


def has_cycle_util(graph, node, visited, rec_stack):
    visited.add(node)
    rec_stack.add(node)

    for neighbor in graph[node]:
        if neighbor not in visited:
            if has_cycle_util(graph, neighbor, visited, rec_stack):
                return True
        elif neighbor in rec_stack:
            return True

    rec_stack.remove(node)
    return False


def has_cycle(graph):
    visited = set()
    rec_stack = set()

    for node in list(graph.keys()):
        if node not in visited:
            if has_cycle_util(graph, node, visited, rec_stack):
                return True

    return False


def concept_assertion_constrain_check(
    generated_abox_assertion, generated_abox_assertions
):
    """
    Checks whether a generated ABox assertion is valid according to some rules.
    """
    concept = generated_abox_assertion.concept
    individual = generated_abox_assertion.individual

    if contains_same_sides(concept):
        return False

    # Check if the negated concept is in the generated ABox
    if ConceptAssertion(alcq_negate(concept), individual) in generated_abox_assertions:
        return False

    return True


def is_valid_axiom(axiom, depth, max_depth):
    """
    Check if an axiom is valid to be used as question.
    """
    if isinstance(axiom, TBoxAxiom) and axiom.LHS_concept == axiom.RHS_concept:
        return False

    if is_tautology(axiom):
        return False

    if depth <= 0 or depth > max_depth:
        return False

    return True


def missing_depths(proof_depths_found, max_depth):
    """
    Check if there are any missing depths in the proof
    """
    expected_depths = set(range(1, max_depth + 1))
    return any([depth not in proof_depths_found for depth in expected_depths])


def inferred_axioms_constrain_check(inferred_instances, max_depth):
    """
    Given the inferred axioms in tuples of (axiom, depth, explanation),
    returns which of them are valid to be used as questions.
    """

    useful_inferred = []
    proof_depths = set()

    for axiom, depth, explanation in inferred_instances:
        if not is_valid_axiom(axiom, depth, max_depth):
            continue

        axiom_dictionary = {
            "axiom": axiom,
            "depth": depth,
            "explanation": explanation,
        }
        proof_depths.add(depth)
        useful_inferred.append(axiom_dictionary)

    if not useful_inferred or missing_depths(proof_depths, max_depth):
        return None

    return useful_inferred


def opposite_polarity(polarity: str) -> str:
    """
    Returns the opposite polarity.
    """
    return "¬" if polarity != "¬" else "+"


def opposite_connective(connective: str) -> str:
    """
    Returns the opposite logical connective.
    """
    return "⊔" if connective == "⊓" else "⊔"


def opposite_restriction(restriction: str) -> str:
    """
    Returns the opposite restriction.
    """
    if restriction == "∀":
        return "∃"
    elif restriction == "∃":
        return "∀"

    quantifier, quantity = restriction.split()

    if quantifier == ">":
        return f"<= {quantity}"
    elif quantifier == "<":
        return f">= {quantity}"
    elif quantifier == "<=":
        return f"> {quantity}"
    elif quantifier == ">=":
        return f"< {quantity}"
    elif quantifier == "=":
        return f"!= {quantity}"
    else:
        raise ValueError(f"Unrecognized restriction: {restriction}")


def alcq_negate(concept):
    """
    Negates an ALCQ concept.

    Parameters:
    concept: The ALCQ concept to negate.

    Returns:
    A new ALCQ concept that represents the negation of the input.

    Raises:
    TypeError: If the concept is not an instance of a recognized ALCQ concept type.
    """
    negated_concept = None
    if isinstance(concept, AtomicConcept):
        if concept.concept_name == "⊤":
            negated_concept = AtomicConcept(concept.polarity, "⊥")
        elif concept.concept_name == "⊥":
            negated_concept = AtomicConcept(concept.polarity, "⊤")
        else:
            negated_concept = AtomicConcept(
                opposite_polarity(concept.polarity), concept.concept_name
            )

    elif isinstance(concept, RestrictionConcept):
        if concept.restriction in {"∀", "∃"}:
            negated_concept = RestrictionConcept(
                opposite_restriction(concept.restriction),
                concept.role_name,
                alcq_negate(concept.concept),
            )
        else:  # Do not negate the filler!
            negated_concept = RestrictionConcept(
                opposite_restriction(concept.restriction),
                concept.role_name,
                concept.concept,
            )

    elif isinstance(concept, JunctionConcept):  # De Morgan's Law
        negated_concept = JunctionConcept(
            alcq_negate(concept.lhs_concept),
            opposite_connective(concept.relationship),
            alcq_negate(concept.rhs_concept),
            concept.atomic_in_lhs,
            concept.atomic_in_rhs,
        )
    else:
        raise TypeError(f"Unexpected concept type: {type(concept)}")

    return negated_concept
