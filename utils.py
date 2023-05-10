from re import search
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
    E.g.:
        + blue ( Bob )
        ( - red and + white ) ( Dave )
        likes ( Bob , Fiona ) // Role Assertion
    """

    if text is None:
        raise ValueError("Empty Assertion!")

    text = text.split()

    if len(text) == 6:  # RoleAssertion
        RoleName = text[0]
        IndividualName1 = text[2]
        IndividualName2 = text[4]
        return RoleAssertion(RoleName, IndividualName1, IndividualName2)
    else:  # ConceptAssertion
        # remove the outer parentheses
        concept = parse_concept(" ".join(text[1:-4]))
        IndividualName = text[-2]
        return ConceptAssertion(concept, IndividualName)


def is_junction_concept(text, connective):
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


def parse_concept(text):
    """Parses text into a Concept"""

    text = text.strip()
    text_list = text.replace("(", "").replace(")", "").split()

    if len(text_list) == 2:
        polarity = text_list[0]
        concept_name = text_list[1]
        return AtomicConcept(polarity, concept_name)

    connective_idx = is_junction_concept(text, connective="⊓")
    if connective_idx != -1:
        lhs_text = str()
        rhs_text = str()

        atomic_in_lhs = False
        atomic_in_rhs = False

        lhs_text = text[0:connective_idx]
        rhs_text = text[connective_idx + 1 :]

        lhs_first_par_idx = lhs_text.find("(")
        lhs_last_par_idx = lhs_text.rfind(")")
        lhs_concept = parse_concept(
            lhs_text[lhs_first_par_idx + 1 : lhs_last_par_idx].strip()
        )
        if isinstance(lhs_concept, AtomicConcept) or (
            isinstance(lhs_concept, JunctionConcept) and lhs_concept.has_atomic
        ):
            atomic_in_lhs = True
        rhs_first_par_idx = rhs_text.find("(")
        rhs_last_par_idx = rhs_text.rfind(")")
        rhs_concept = parse_concept(
            rhs_text[rhs_first_par_idx + 1 : rhs_last_par_idx].strip()
        )
        if isinstance(rhs_concept, AtomicConcept) or (
            isinstance(rhs_concept, JunctionConcept) and rhs_concept.has_atomic
        ):
            atomic_in_rhs = True
        return JunctionConcept(
            lhs_concept, "⊓", rhs_concept, atomic_in_lhs, atomic_in_rhs
        )

    connective_idx = is_junction_concept(text, connective="⊔")
    if connective_idx != -1:
        lhs_text = str()
        rhs_text = str()
        atomic_in_lhs = False
        atomic_in_rhs = False

        lhs_text = text[0:connective_idx]
        rhs_text = text[connective_idx + 1 :]

        lhs_first_par_idx = lhs_text.find("(")
        lhs_last_par_idx = lhs_text.rfind(")")
        lhs_concept = parse_concept(
            lhs_text[lhs_first_par_idx + 1 : lhs_last_par_idx].strip()
        )
        if isinstance(lhs_concept, AtomicConcept) or (
            isinstance(lhs_concept, JunctionConcept) and lhs_concept.has_atomic
        ):
            atomic_in_lhs = True
        rhs_first_par_idx = rhs_text.find("(")
        rhs_last_par_idx = rhs_text.rfind(")")
        rhs_concept = parse_concept(
            rhs_text[rhs_first_par_idx + 1 : rhs_last_par_idx].strip()
        )
        if isinstance(rhs_concept, AtomicConcept) or (
            isinstance(rhs_concept, JunctionConcept) and rhs_concept.has_atomic
        ):
            atomic_in_rhs = True
        return JunctionConcept(
            lhs_concept, "⊔", rhs_concept, atomic_in_lhs, atomic_in_rhs
        )

    if text_list[0] in {"∀", "∃"}:
        inner_concept = str()
        restriction = text_list[0]
        role_name = text_list[1]
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
    elif text_list[0] in {">", "<", "=", ">=", "<="}:
        inner_concept = str()
        restriction = " ".join(text_list[0:2])
        role_name = text_list[2]
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
    else:
        print(f"Unexpected text in parser: '{text}'")
        assert False


def parse_tbox_axiom(statement_txt):
    """
    Parses text into a TBox Axiom (Subsumption/Equivalence).
    E.g.:
        + male ⊑ + person
    """
    lhs_txt = str()
    rhs_txt = str()
    reached_rel = False

    for x in statement_txt:
        if x == "⊑" or x == "≡":
            relation = x
            reached_rel = True
            continue
        if not reached_rel:
            lhs_txt += x
        else:
            rhs_txt += x

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


def is_tautology(LHS):
    if isinstance(LHS, AtomicConcept):
        return LHS.concept_name == "⊥"
    return False


def isSubClassOfThing(RHS):
    if isinstance(RHS, AtomicConcept):
        return RHS.concept_name == "⊤"
    return False


def tbox_axiom_constrain_check(generated_tbox_axiom, current_tbox):
    """Checks whether a generated TBox Axiom is valid according to the following rules:
    1. Don't allow A and/or A on each side concepts
    2. No tautologies (\Bottom \isSubClassOf Concept)
    3. Don't allow A \isSubClassOf A
    """

    lhs = generated_tbox_axiom.LHS_concept
    rhs = generated_tbox_axiom.RHS_concept

    if contains_same_sides(lhs) or contains_same_sides(rhs):
        return False

    if is_tautology(lhs):
        return False

    # TBox Axiom with LHS Concept = RHS Concept is not useful
    if generated_tbox_axiom.LHS_concept == generated_tbox_axiom.RHS_concept:
        return False

    graph = build_graph(list(current_tbox) + [generated_tbox_axiom])

    if has_cycle(graph):
        print("Cycle catched!")
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

    for node in list(graph.keys()):  # Use list() to avoid RuntimeError
        if node not in visited:
            if has_cycle_util(graph, node, visited, rec_stack):
                return True

    return False


def concept_assertion_constrain_check(
    generated_abox_assertion, generated_abox_assertions
):
    """Checks whether a generated A Box assertion is valid according to some rules."""

    if contains_same_sides(generated_abox_assertion.concept):
        return False

    negated_concept = alcq_negate(generated_abox_assertion.concept)
    if (
        ConceptAssertion(negated_concept, generated_abox_assertion.individual)
        in generated_abox_assertions
    ):
        print("Negation of the concept is in context!")
        return False

    return True


def inferred_axioms_constrain_check(inferred_instances, max_depth):
    """Given the inferred axioms in tuples of (axiom, depth, explanation),
    returns which of them are valid to be used as questions.
    i.e., they have to be within the max depth, do not contain Thing or Nothing, ...
    returns None if no axiom reached the desired max depth"""

    useful_inferred = list()
    proof_depths = set()
    maxd = -1
    for axiom, depth, expl in inferred_instances:
        if isinstance(axiom, TBoxAxiom) and axiom.LHS_concept == axiom.RHS_concept:
            continue

        # Don't take tautologies as questions
        if search(r"(?:[^a-zA-Z]|^)thing(?:[^a-zA-Z]|$)", axiom.nl()) != None:
            continue

        maxd = max(maxd, depth)
        if (
            (depth > 0)
            and (depth <= max_depth)
            and (axiom.nl().lower().find("is thing") == -1)
        ):
            dic = {"axiom": axiom, "depth": depth, "explanation": expl}
            proof_depths.add(depth)
            useful_inferred.append(dic)

    if useful_inferred == None:
        return None

    depths_seq_list = list(range(1, max_depth + 1))

    if any([d not in proof_depths for d in depths_seq_list]):
        print(f"Proof depths: {proof_depths}")
        return None

    return useful_inferred


def chaining_question(expl):
    def dfs(e, edges, vis):
        vis[e] = 1
        neighbors = edges[e]
        for n in neighbors:
            if vis[n] == 0:
                dfs(n, edges, vis)

    nodes = set()
    for e in expl:
        if isinstance(e, TBoxAxiom):
            lhs = e.LHS_concept
            rhs = e.RHS_concept
            nodes.add(lhs)
            nodes.add(rhs)
        elif isinstance(e, ConceptAssertion):
            nodes.add(e.concept)

    edges = {}
    for n in nodes:
        edges[n] = list()

    for e in expl:
        if isinstance(e, TBoxAxiom):
            lhs = e.LHS_concept
            rhs = e.RHS_concept

            edges[lhs].append(rhs)

            if e.Relationship != "⊑":  # Equivalence
                edges[rhs].append(lhs)

    for n in nodes:
        vis = {key: 0 for key in nodes}
        dfs(n, edges, vis)
        if sum(vis.values()) == len(nodes):
            return True
    return False


def opposite_polarity(polarity):
    return "¬" if polarity != "¬" else "+"


def opposite_connective(connective):
    return "⊓" if connective != "⊓" else "⊓"


def opposite_restriction(restriction):
    if restriction in {"∀", "∃"}:  # Existential
        if restriction == "∀":
            return "∃"
        else:
            return "∀"
    else:  # Quantification
        splitted_restriction = restriction.split()
        quantifier = splitted_restriction[0]
        quantity = splitted_restriction[1]

        if quantifier == ">":
            opposite_quant = "<="
        elif quantifier == "<":
            opposite_quant = ">="
        elif quantifier == "<=":
            opposite_quant = ">"
        elif quantifier == ">=":
            opposite_quant = "<"
        elif quantifier == "=":
            opposite_quant = "!="

        return f"{opposite_quant} {quantity}"


def alcq_negate(concept):
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
        else:  # Do not negate the filler !
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
        print(f"ALCQ-NEGATE ERROR! GOT: {concept}")
        assert False

    return negated_concept
