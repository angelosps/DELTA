from re import finditer, DOTALL
from utils import parse_concept
from common import *

NOT_SUPPORTED_CLASS = -1


def skip_url(text, start_from=0):
    if in_left_half(text[start_from:], "owl:Thing"):
        return "Thing", text.index("owl:Thing") + len("owl:Thing") - 1
    if in_left_half(text[start_from:], "owl:Nothing"):
        return "Nothing", text.index("owl:Nothing") + len("owl:Nothing") - 1

    # Catch owlapi incomplete axioms (objectintersectionof(A))
    if "#" not in text[start_from:]:
        return None, None

    start_index = text.index("#", start_from) + 1
    end_index = text.index(">", start_index)
    return text[start_index:end_index], end_index


def skip_double_url(text):
    # Clean 1st URL #
    clean1, end_index1 = skip_url(text)
    # Clean 2nd URL #
    clean2, _ = skip_url(text, end_index1)
    return clean1, clean2


def in_left_half(text, pattern):
    idx = text.find(pattern)
    if idx == -1 or (idx >= len(text) / 2):
        return False
    return True


def in_right_half(text, pattern):
    idx = text.find(pattern)
    if idx == -1 or (idx < len(text) / 2):
        return False
    return True


def decode_owl_axiom(axiom_text):
    axiom_text = axiom_text.replace("_", " ")
    axiom_text = axiom_text.replace(" L ", " ( ")
    axiom_text = axiom_text.replace("L ", "( ")
    axiom_text = axiom_text.replace(" R ", " ) ")
    axiom_text = axiom_text.replace(" R", " )")
    axiom_text = axiom_text.replace(" d ", " . ")
    axiom_text = axiom_text.replace("MT", "> ")
    axiom_text = axiom_text.replace("LT", "< ")
    axiom_text = axiom_text.replace("EQ", "= ")
    axiom_text = axiom_text.replace("AL", ">= ")
    axiom_text = axiom_text.replace("AM", "<= ")
    axiom_text = axiom_text.replace("exists", "∃")
    axiom_text = axiom_text.replace("only", "∀")
    axiom_text = axiom_text.replace("pos", "+")
    axiom_text = axiom_text.replace("neg", "¬")
    axiom_text = axiom_text.replace(" and ", "⊓")
    axiom_text = axiom_text.replace(" or ", "⊔")
    axiom_text = axiom_text.replace("Thing", "⊤")
    axiom_text = axiom_text.replace("Nothing", "⊥")

    # Atomic Concept from OWLAPI (i.e., "nice", "white")
    if len(axiom_text.split()) == 1:
        return AtomicConcept("+", axiom_text)

    concept = parse_concept(axiom_text)
    return concept


def ClassAssertionClass(text, all2NL=None):
    """Returns the owl axiom as ConceptAssertion python class."""
    ConceptText, Individual = skip_double_url(text)
    concept = decode_owl_axiom(ConceptText)
    concept_assertion = ConceptAssertion(concept, individual=Individual)
    if all2NL is not None and concept_assertion not in all2NL:
        all2NL[concept_assertion] = concept_assertion.nl()
    return concept_assertion


def SubClassOfClass(text, statements_NL=None):
    """Returns the the owl axiom as TBoxAxiom python class."""
    LHS_text, after_LHS_idx = skip_url(text)
    if LHS_text is None or after_LHS_idx is None:
        return None
    RHS_text, _ = skip_url(text, after_LHS_idx)

    LHS_concept = decode_owl_axiom(LHS_text)
    RHS_concept = decode_owl_axiom(RHS_text)
    concept_inclusion = TBoxAxiom(LHS_concept, "⊑", RHS_concept)
    if statements_NL is not None and concept_inclusion not in statements_NL:
        statements_NL[concept_inclusion] = concept_inclusion.nl()
    return concept_inclusion


def EquivalentClassesClass(text, statements_NL=None):
    """Returns the the owl axiom as TBoxAxiom python class."""
    LHS_text, after_LHS_idx = skip_url(text)
    if LHS_text is None or after_LHS_idx is None:
        return None
    LHS_concept = decode_owl_axiom(LHS_text)

    # Make the check here to save the cardinality num
    if "cardinality" in text[after_LHS_idx:].lower():
        cardinality = int(text[text.find("Cardinality") + len("Cardinality") + 1])

    RHS_text, after_RHS_idx = skip_url(text, after_LHS_idx)
    if RHS_text is None or after_RHS_idx is None:
        return None
    if "objectcomplementof" in text[after_LHS_idx:].lower():
        RHS_text = f"neg_{RHS_text}"
    elif "objectunionof" in text[after_LHS_idx:].lower():
        union_lhs = RHS_text
        union_rhs, _ = skip_url(text, after_RHS_idx)
        if union_rhs is None:
            return None
        RHS_text = f"L_{union_lhs}_R_or_L_{union_rhs}_R"
    elif "objectintersectionof" in text[after_LHS_idx:].lower():
        intersection_lhs = RHS_text
        intersection_rhs, _ = skip_url(text, after_RHS_idx)
        if intersection_rhs is None:
            return None
        RHS_text = f"L_{intersection_lhs}_R_and_L_{intersection_rhs}_R"
    elif "objectsomevaluesfrom" in text[after_LHS_idx:].lower():
        role_name = RHS_text
        range, _ = skip_url(text, after_RHS_idx)
        if range is None:
            return None
        if range == "Thing" or range == "Nothing":
            range = f"pos_{range}"
        RHS_text = f"exists_{role_name}_d_L_{range}_R"
    elif "objectallvaluesfrom" in text[after_LHS_idx:].lower():
        role_name = RHS_text
        range, _ = skip_url(text, after_RHS_idx)
        if range is None:
            return None
        if range == "Thing" or range == "Nothing":
            range = f"pos_{range}"
        RHS_text = f"only_{role_name}_d_L_{range}_R"
    elif "objectexactcardinality" in text[after_LHS_idx:].lower():
        role_name = RHS_text
        range, _ = skip_url(text, after_RHS_idx)
        if range is None:
            return None
        if range == "Thing" or range == "Nothing":
            range = f"pos_{range}"
        RHS_text = f"EQ{cardinality}_{role_name}_d_L_{range}_R"
    elif "objectmincardinality" in text[after_LHS_idx:].lower():
        role_name = RHS_text
        range, _ = skip_url(text, after_RHS_idx)
        if range is None:
            return None
        if range == "Thing" or range == "Nothing":
            range = f"pos_{range}"
        RHS_text = f"AL{cardinality}_{role_name}_d_L_{range}_R"
    elif "objectmaxcardinality" in text[after_LHS_idx:].lower():
        role_name = RHS_text
        range, _ = skip_url(text, after_RHS_idx)
        if range is None:
            return None
        if range == "Thing" or range == "Nothing":
            range = f"pos_{range}"
        RHS_text = f"AM{cardinality}_{role_name}_d_L_{range}_R"

    RHS_concept = decode_owl_axiom(RHS_text)
    concept_equivalence = TBoxAxiom(LHS_concept, "≡", RHS_concept)

    if statements_NL is not None and concept_equivalence not in statements_NL:
        statements_NL[concept_equivalence] = concept_equivalence.nl()
    return concept_equivalence


def ObjectPropertyAssertionClass(text, statements_NL=None):
    RoleName, after_RoleName_idx = skip_url(text)
    Ind1, after_Ind1_idx = skip_url(text, after_RoleName_idx)
    Ind2, _ = skip_url(text, after_Ind1_idx)
    role_assertion = RoleAssertion(RoleName, Ind1, Ind2)

    if statements_NL is not None and role_assertion not in statements_NL:
        statements_NL[role_assertion] = role_assertion.nl()

    return role_assertion


def owl_axiom_class(axiom_owl, all2NL=None):
    """Returns the axiom class of the given axiom in owl."""
    axiom_owl = axiom_owl.replace("Explanation ", "")

    if (
        "Entailment" in axiom_owl
    ):  # Remove <Entailment1680334193807> in some axioms (maybe caused by owlready)
        axiom_owl = " ".join(
            s for s in axiom_owl.split() if not any(c.isdigit() for c in s)
        )

    axiom_class = str()

    # Check axiom type #
    if axiom_owl.find("ClassAssertion") != -1:
        axiom_class = ClassAssertionClass(axiom_owl, all2NL)
    elif axiom_owl.find("SubClassOf") != -1:
        axiom_class = SubClassOfClass(axiom_owl, all2NL)
    elif axiom_owl.find("EquivalentClasses") != -1:
        axiom_class = EquivalentClassesClass(axiom_owl, all2NL)
    elif axiom_owl.find("ObjectPropertyAssertion") != -1:
        axiom_class = ObjectPropertyAssertionClass(axiom_owl, all2NL)
    else:
        return NOT_SUPPORTED_CLASS
    return axiom_class


def construct_owl_concept(owl_text):
    if owl_text.lower().find("objectintersectionof") != -1:
        lhs_concept_text, after_lhs_idx = skip_url(owl_text)
        if lhs_concept_text is None:
            return None
        rhs_concept_text, _ = skip_url(owl_text, after_lhs_idx)
        if rhs_concept_text is None:
            return None
        lhs_concept = decode_owl_axiom(lhs_concept_text)
        rhs_concept = decode_owl_axiom(rhs_concept_text)
        return JunctionConcept(lhs_concept, "⊓", rhs_concept, False, False)
    elif owl_text.lower().find("objectunionof") != -1:
        lhs_concept_text, after_lhs_idx = skip_url(owl_text)
        if lhs_concept_text is None:
            return None
        rhs_concept_text, _ = skip_url(owl_text, after_lhs_idx)
        if rhs_concept_text is None:
            return None
        lhs_concept = decode_owl_axiom(lhs_concept_text)
        rhs_concept = decode_owl_axiom(rhs_concept_text)
        return JunctionConcept(lhs_concept, "⊔", rhs_concept, False, False)
    elif owl_text.lower().find("objectsomevaluesfrom") != -1:
        restriction = "∃"
        role_name, after_role_name_idx = skip_url(owl_text)
        if role_name is None:
            return None
        inner_concept_text, _ = skip_url(owl_text, after_role_name_idx)
        if inner_concept_text is None:
            return None
        inner_concept = decode_owl_axiom(inner_concept_text)
        return RestrictionConcept(restriction, role_name, inner_concept)
    elif owl_text.lower().find("objectallvaluesfrom") != -1:
        restriction = "∀"
        role_name, after_role_name_idx = skip_url(owl_text)
        if role_name is None:
            return None
        inner_concept_text, _ = skip_url(owl_text, after_role_name_idx)
        if inner_concept_text is None:
            return None
        inner_concept = decode_owl_axiom(inner_concept_text)
        return RestrictionConcept(restriction, role_name, inner_concept)
    elif owl_text.lower().find("objectmincardinality") != -1:
        cardinality_idx = (
            owl_text.lower().find("objectmincardinality")
            + len("objectmincardinality")
            + 1
        )
        cardinality = owl_text[cardinality_idx]
        restriction = f">= {cardinality}"
        role_name, after_role_name_idx = skip_url(owl_text)
        if role_name is None:
            return None
        inner_concept_text, _ = skip_url(owl_text, after_role_name_idx)
        if inner_concept_text is None:
            return None
        inner_concept = decode_owl_axiom(inner_concept_text)
        return RestrictionConcept(restriction, role_name, inner_concept)
    elif owl_text.lower().find("objectmaxcardinality") != -1:
        cardinality_idx = (
            owl_text.lower().index("objectmaxcardinality")
            + len("objectmaxcardinality")
            + 1
        )
        cardinality = owl_text[cardinality_idx]
        restriction = f"<= {cardinality}"
        role_name, after_role_name_idx = skip_url(owl_text)
        if role_name is None:
            return None
        inner_concept_text, _ = skip_url(owl_text, after_role_name_idx)
        if inner_concept_text is None:
            return None
        inner_concept = decode_owl_axiom(inner_concept_text)
        return RestrictionConcept(restriction, role_name, inner_concept)
    elif owl_text.lower().find("objectexactcardinality") != -1:
        cardinality_idx = (
            owl_text.lower().find("objectexactcardinality")
            + len("objectexactcardinality")
            + 1
        )
        cardinality = owl_text[cardinality_idx]
        restriction = f"= {cardinality}"
        role_name, after_role_name_idx = skip_url(owl_text)
        if role_name is None:
            return None
        inner_concept_text, _ = skip_url(owl_text, after_role_name_idx)
        if inner_concept_text is None:
            return None
        inner_concept = decode_owl_axiom(inner_concept_text)
        return RestrictionConcept(restriction, role_name, inner_concept)
    elif owl_text.lower().find("objectcomplementof") != -1:
        concept_text, _ = skip_url(owl_text)
        if concept_text is None:
            return None
        concept = decode_owl_axiom(concept_text)
        concept.polarity = "¬"
        return concept
    else:
        concept_text, _ = skip_url(owl_text)
        if concept_text is None:
            return None
        return decode_owl_axiom(concept_text)


def throw_dumb_explanations(axiom_expl):
    """Eliminate dumb explanations:
    E.g. "A_intersection_B is equivalent to the intersection of A and B"
    a problem caused by the owlready complex classes representation"""

    explanations = list()
    for e in axiom_expl:
        if e.strip() == "":
            continue

        # Some explanations contain entailment axioms in owlapi
        if "entailment" in e:
            explanations.append(e)
            continue

        # Throw some explanations caused due to owlready's classes representation
        if e.lower().find("equivalentclasses") != -1:
            # break two sides, construct them and check if they are the same
            split_idx = e.find(" ")
            LHS_text = e[:split_idx]
            RHS_text = e[split_idx + 1 :]
            LHS_concept = construct_owl_concept(LHS_text)
            RHS_concept = construct_owl_concept(RHS_text)
            if LHS_concept is None or RHS_concept is None:
                return None
            if LHS_concept == RHS_concept:
                continue
            if (
                isinstance(LHS_concept, JunctionConcept)
                and isinstance(RHS_concept, JunctionConcept)
                and {LHS_concept.lhs_concept, LHS_concept.rhs_concept}
                == {RHS_concept.lhs_concept, RHS_concept.rhs_concept}
            ):
                continue  # A and B isEquivalentTo B and A

        explanations.append(e)

    return explanations


def get_inferred_axioms_with_explanations(data, all2NL):
    """Given the OWLAPI output (inferred axioms with their explanations in owl format)
    return each inferred axiom in nl, with its reasoning depth,
    and its explanation as a list of owl axioms"""

    clean_instances = list()

    regex = r"Explanation(.*?)EndOfExplanation"
    matches = finditer(regex, data, DOTALL)

    for match in matches:
        owlapi_instance = match.group()

        if (owlapi_instance == "") or (
            owlapi_instance.find("Explanation\nEndOfExplanation") != -1
        ):
            continue

        # First line will be the inferred axiom and remaining lines the explanation of it
        splitted_instance = [s.strip() for s in owlapi_instance.splitlines()]

        # Remove empty instances of InferredAxiom/Explanation got from owlapi
        if "Explanation" in splitted_instance:
            splitted_instance.remove("Explanation")

        splitted_instance.remove("EndOfExplanation")
        splitted_instance.remove("")

        if len(splitted_instance) == 0 or "rdfs:comment" in splitted_instance[0]:
            print("Found rdfs:comment")
            return None

        axiom_class = owl_axiom_class(splitted_instance[0], all2NL)

        if axiom_class == NOT_SUPPORTED_CLASS:
            print(f"Not-supported class.")
            continue

        if axiom_class is None:
            continue

        if len(splitted_instance) == 1:
            explanation = []
        else:
            explanation = splitted_instance[1:]
            explanation = throw_dumb_explanations(splitted_instance[1:])
            if explanation is None:
                print(f"Explanation is none!")
                return None
            explanation = [owl_axiom_class(axiom) for axiom in explanation]

        proof_depth = len(explanation)
        clean_instances.append((axiom_class, proof_depth, explanation))

    return clean_instances
