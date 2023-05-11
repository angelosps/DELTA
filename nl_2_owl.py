from owlready2 import *
from types import new_class
from common import AtomicConcept, ConceptAssertion, JunctionConcept, RestrictionConcept


def restriction_concept_2_owl(onto, restr_concept):
    """Given a restriction complex concept in nl, creates its corresponding
        owl class using owlready2.

    Args:
        arguments_list (list): the restriction concept arguments splitted in a list
        polarity (str): polarity of the concept

    Returns:
        Class:  the owlready class representing the concept
        str:    the name given of the owlready class
    """
    with onto:
        restriction = restr_concept.restriction
        role_name = restr_concept.role_name
        inner_concept, inner_concept_name = make_concept(onto, restr_concept.concept)

        if restriction == "∀":
            complex_concept_name = f"only_{role_name}_d_L_{inner_concept_name}_R"
            complex_concept = new_class(complex_concept_name, (Thing,))
            role = new_class(str(role_name), (ObjectProperty,))
            role.domain = role.range = [Thing]
            complex_concept.equivalent_to.append(role.only(inner_concept))
            return complex_concept, complex_concept_name
        elif restriction == "∃":
            complex_concept_name = f"exists_{role_name}_d_L_{inner_concept_name}_R"
            complex_concept = new_class(complex_concept_name, (Thing,))
            role = new_class(str(role_name), (ObjectProperty,))
            role.domain = role.range = [Thing]
            complex_concept.equivalent_to.append(role.some(inner_concept))
            return complex_concept, complex_concept_name
        else:
            quantifier = restr_concept.restriction.split()[0]
            quantity = restr_concept.restriction.split()[1]
            role_name = restr_concept.role_name

            if quantifier == ">":
                complex_concept_name = (
                    f"MT{quantity}_{role_name}_d_L_{inner_concept_name}_R"
                )
                complex_concept = new_class(str(complex_concept_name), (Thing,))
                role = new_class(str(role_name), (ObjectProperty,))
                role.domain = role.range = [Thing]
                complex_concept.equivalent_to.append(
                    role.min(int(quantity) + 1, inner_concept)
                )
                return complex_concept, complex_concept_name
            elif quantifier == "<":
                complex_concept_name = (
                    f"LT{quantity}_{role_name}_d_L_{inner_concept_name}_R"
                )
                complex_concept = new_class(str(complex_concept_name), (Thing,))
                role = new_class(str(role_name), (ObjectProperty,))
                role.domain = role.range = [Thing]
                complex_concept.equivalent_to.append(
                    role.max(int(quantity) - 1, inner_concept)
                )
                return complex_concept, complex_concept_name
            elif quantifier == ">=":
                complex_concept_name = (
                    f"AL{quantity}_{role_name}_d_L_{inner_concept_name}_R"
                )
                complex_concept = new_class(complex_concept_name, (Thing,))
                role = new_class(str(role_name), (ObjectProperty,))
                role.domain = role.range = [Thing]
                complex_concept.equivalent_to.append(
                    role.min(int(quantity), inner_concept)
                )
                return complex_concept, complex_concept_name
            elif quantifier == "<=":
                complex_concept_name = (
                    f"AM{quantity}_{role_name}_d_L_{inner_concept_name}_R"
                )
                complex_concept = new_class(complex_concept_name, (Thing,))
                role = new_class(str(role_name), (ObjectProperty,))
                role.domain = role.range = [Thing]
                complex_concept.equivalent_to.append(
                    role.max(int(quantity), inner_concept)
                )
                return complex_concept, complex_concept_name

            elif quantifier == "=":
                complex_concept_name = (
                    f"EQ{quantity}_{role_name}_d_L_{inner_concept_name}_R"
                )
                complex_concept = new_class(complex_concept_name, (Thing,))
                role = new_class(str(role_name), (ObjectProperty,))
                role.domain = role.range = [Thing]
                complex_concept.equivalent_to.append(
                    role.exactly(int(quantity), inner_concept)
                )
                return complex_concept, complex_concept_name


def AtomicConcept_2_Owl(onto, concept):
    with onto:
        polarity = concept.polarity
        concept_name = concept.concept_name
        concept = None
        if concept_name == "⊤":
            if polarity != "+":
                concept_name = "neg_Thing"
                concept = Nothing
            else:
                concept_name = "pos_Thing"
                concept = Thing
        elif concept_name == "⊥":
            if polarity != "+":
                concept_name = "neg_Nothing"
                concept = Thing
            else:
                concept_name = "pos_Nothing"
                concept = Nothing
        else:
            if polarity != "+":
                concept = new_class(f"pos_{concept_name}", (Thing,))
                concept_name = f"neg_{concept_name}"
                neg_complex_concept = new_class(concept_name, (Thing,))
                neg_complex_concept.equivalent_to.append(Not(concept))
                concept = neg_complex_concept
            else:
                concept_name = f"pos_{concept_name}"
                concept = new_class(concept_name, (Thing,))

    return concept, concept_name


def junction_concept_2_owl(onto, concept2make):
    with onto:
        relationship = concept2make.relationship
        lhs_concept, lhs_concept_name = make_concept(onto, concept2make.lhs_concept)
        rhs_concept, rhs_concept_name = make_concept(onto, concept2make.rhs_concept)

        owl_concept_name = str()
        if relationship == "⊓":
            owl_concept_name = f"L_{lhs_concept_name}_R_and_L_{rhs_concept_name}_R"
            owl_concept = new_class(owl_concept_name, (Thing,))
            owl_concept.equivalent_to.append(lhs_concept & rhs_concept)
        else:
            owl_concept_name = f"L_{lhs_concept_name}_R_or_L_{rhs_concept_name}_R"
            owl_concept = new_class(owl_concept_name, (Thing,))
            owl_concept.equivalent_to.append(lhs_concept | rhs_concept)
    return owl_concept, owl_concept_name


def make_concept(onto, concept2make):
    """Given a concept, create it's owl class usign owlready.

    Args:
        onto (owlready ontology):   The ontology to which this concept will be added
        concept2make (Concept):     A concept to create it's owl representation using owlready.

    Returns:
        Class: the owlready class corresponding to the concept
    """
    with onto:
        if isinstance(concept2make, AtomicConcept):
            owl_concept, owl_concept_name = AtomicConcept_2_Owl(onto, concept2make)
        elif isinstance(concept2make, JunctionConcept):
            owl_concept, owl_concept_name = junction_concept_2_owl(onto, concept2make)
        elif isinstance(concept2make, RestrictionConcept):  # Restriction concept
            owl_concept, owl_concept_name = restriction_concept_2_owl(
                onto, concept2make
            )
        else:
            raise TypeError(
                "Unexpected type for concept2make: {}".format(type(concept2make))
            )

    return owl_concept, owl_concept_name


SPECIAL_RANGE = 0
SPECIAL_DOMAIN = 1


def special_axiom(axiom):
    if (
        isinstance(axiom.LHS_concept, AtomicConcept)
        and axiom.LHS_concept.concept_name == "⊤"
    ):
        return True, SPECIAL_RANGE

    if (
        isinstance(axiom.LHS_concept, RestrictionConcept)
        and axiom.LHS_concept.concept == "⊤"
    ):
        return True, SPECIAL_DOMAIN

    return False, None


def make_special_axiom(onto, special_axiom, special_type):
    LHS_concept = special_axiom.LHS_concept
    RHS_concept = special_axiom.RHS_concept
    with onto:
        if special_type == SPECIAL_RANGE:
            role_name = RHS_concept.role_name
            range_concept, _ = make_concept(onto, RHS_concept.concept)
            role = new_class(str(role_name), (ObjectProperty,))
            role.domain = [Thing]
            role.range = [range_concept]
        elif special_type == SPECIAL_DOMAIN:
            role_name = LHS_concept.role_name
            domain_concept, _ = make_concept(onto, RHS_concept)
            role = new_class(str(role_name), (ObjectProperty,))
            role.domain = [domain_concept]
            role.range = [Thing]


def create_ontology(id, ABoxAssertions, TBoxAxioms):
    """Given the ABox & the TBox, create the corresponding ontology using owlready.
    Args:
        ABoxAssertions (list):  List with the ABox assertions
        TBoxAxioms (list):      List with the TBox axioms
    """

    onto = get_ontology("http://alcq.org/onto.owl")
    onto.destroy(update_is_a=True, update_relation=True)
    onto = get_ontology("http://alcq.org/onto.owl")

    inds = set()

    with onto:
        ### A B O X  A S S E R T I O N S ###
        for assertion in ABoxAssertions:
            if isinstance(assertion, ConceptAssertion):  # Class Assertion ##
                assertion_concept = assertion.concept
                indName = assertion.individual
                inds.add(indName)
                concept, _ = make_concept(onto, assertion_concept)
                ind = Thing(str(indName))
                ind.is_a.append(concept)
            else:  # Role Assertion ##
                role_name = assertion.RoleName
                leftIndName = assertion.Individual_l
                rightIndName = assertion.Individual_r

                inds.add(leftIndName)
                inds.add(rightIndName)

                role = new_class(str(role_name), (ObjectProperty,))
                role.domain = [Thing]
                role.range = [Thing]

                leftInd = Thing(str(leftIndName))
                rightInd = Thing(str(rightIndName))
                role[leftInd].append(rightInd)

        ### T B O X  A X I O M S ###
        for axiom in TBoxAxioms:
            special_check, special_type = special_axiom(axiom)
            if special_check:
                make_special_axiom(onto, axiom, special_type)
                continue
            lhs_concept, _ = make_concept(onto, axiom.LHS_concept)
            rhs_concept, _ = make_concept(onto, axiom.RHS_concept)
            lhs_concept.is_a.append(rhs_concept)

        # We need to state this in OWA #
        individuals = list(onto.individuals())
        individualset = set([str(i).split(".")[1] for i in individuals])

        if inds != individualset:
            print("DIFFERENT INDIVIDUALS!!!\n\n")
            print(inds)
            print(individualset)
            while 1:
                pass

        if len(individuals) >= 2:
            AllDifferent(individuals)

        onto.save(f"./ALCQtesting.owl", "rdfxml")
        onto.save(f"./Generated-Ontologies/ALCQ-Ontology-{id}.owl", "rdfxml")
        onto.destroy(update_relation=True, update_is_a=True)
