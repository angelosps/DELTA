import inflect
from global_variables import GRAMMAR_ROLE_NAMES


def pluralize(restr_concept, whole=False):
    p = inflect.engine()
    pluralized = str()
    change = True
    for word in restr_concept.split():
        if (change is True) and (word in GRAMMAR_ROLE_NAMES):
            pluralized += f"{p.plural_verb(word)} "
            if not whole:
                change = False
        else:
            pluralized += f"{word} "

    pluralized = pluralized.strip()
    return pluralized


def restriction_concept_nl(restriction_concept):
    """
    Given a restriction concept, returns it's natural language representation.
    Args:
        arguments_list (list): List of concept's arguments

    Returns:
        str: the restriction concept in nl
    """
    restriction_concept_nl = str()
    restriction = restriction_concept.restriction.split()
    role_name = restriction_concept.role_name
    concept_nl = restriction_concept.concept.nl()

    if restriction[0] == "∀":
        restriction_concept_nl = (
            f"{role_name.replace('_',' ')} only {concept_nl} things"
        )
    elif restriction[0] == "∃":
        restriction_concept_nl = (
            f"exists something {concept_nl} that it {role_name.replace('_',' ')}"
        )
    else:
        quantity = restriction[0]
        quantifier = restriction[1]

        if quantifier == ">":
            restriction_concept_nl = (
                f"{role_name.replace('_',' ')} more than {quantity} {concept_nl} things"
            )
        elif quantifier == "<":
            restriction_concept_nl = (
                f"{role_name.replace('_',' ')} less than {quantity} {concept_nl} things"
            )
        elif quantifier == ">=":
            restriction_concept_nl = (
                f"{role_name.replace('_',' ')} at least {quantity} {concept_nl} things"
            )
        elif quantifier == "<=":
            restriction_concept_nl = (
                f"{role_name.replace('_',' ')} at most {quantity} {concept_nl} things"
            )
        elif quantifier == "=":
            restriction_concept_nl = (
                f"{role_name.replace('_',' ')} exactly {quantity} {concept_nl} things"
            )
        else:
            raise ValueError(
                f"Got unexpected restriction concept: '{restriction_concept}'"
            )

    return restriction_concept_nl
