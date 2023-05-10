from owlready2 import *
from common import ConceptAssertion, RoleAssertion, TBoxAxiom
from nl_2_owl import make_concept, special_axiom, make_special_axiom
from types import new_class


def KB_union_unknown_axiom(axiom):
    # The axiom would be a false question if KB U {Axiom} -> Inconsistent KB
    # Load the current ontology
    onto = get_ontology("./ALCQtesting.owl").load()
    # print(f"\nAdding axiom: {axiom}", flush=True)

    # Add the "unknown" question axiom to it
    with onto:
        if isinstance(axiom, ConceptAssertion):  # Class Assertion ##
            assertion_concept = axiom.concept
            indName = axiom.individual
            concept, _ = make_concept(onto, assertion_concept)
            ind = Thing(str(indName))
            ind.is_a.append(concept)
        elif isinstance(axiom, RoleAssertion):  # Role Assertion ##
            role_name = axiom.RoleName
            leftIndName = axiom.Individual_l
            rightIndName = axiom.Individual_r

            role = new_class(str(role_name), (ObjectProperty,))
            role.domain = [Thing]
            role.range = [Thing]

            leftInd = Thing(str(leftIndName))
            rightInd = Thing(str(rightIndName))
            leftInd.role_name.append(rightInd)
        elif isinstance(axiom, TBoxAxiom):
            # CLASS INCLUSION #
            special_check, special_type = special_axiom(axiom)
            if special_check:
                make_special_axiom(onto, axiom, special_type)
            else:
                lhs_concept, _ = make_concept(onto, axiom.LHS_concept)
                rhs_concept, _ = make_concept(onto, axiom.RHS_concept)
                lhs_concept.is_a.append(rhs_concept)

        AllDifferent(list(onto.individuals()))

        # individualset = set([str(i).split(".")[1] for i in list(onto.individuals())])
        # print(f"\nCONSISTENCY Individuals: {individualset}", flush=True)

        onto.save(f"./ALCQCC.owl", "rdfxml")
        onto.destroy(update_is_a=True, update_relation=True)
