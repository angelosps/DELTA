import inflect

all_role_names = {
    "likes",
    "loves",
    "admires",
    "eats",
    "chases",
    "values",
    "appreciates",
    "hires",
    "manages",
    "mentors",
    "teaches",
    "respects",
    "challenges",
    "trusts",
    "supports",
    "collaborates",
    "consults",
    "guides",
    "instructs",
    "leads",
    "supervises",
}


def pluralize(restr_concept, whole=False):
    p = inflect.engine()

    pluralized = str()
    change = True
    for word in restr_concept.split():
        if (change is True) and (word in all_role_names):
            pluralized += f"{p.plural_verb(word)} "
            if not whole:
                change = False
        else:
            pluralized += f"{word} "

    pluralized = pluralized.strip()
    return pluralized


def restriction_concept_nl(restr_concept):
    """
    Given a restriction concept, returns it's natural language representation.
    Args:
        arguments_list (list): List of concept's arguments

    Returns:
        str: the restriction concept in nl
    """

    restr_concept_nl = str()
    restriction = restr_concept.restriction.split()
    role_name = restr_concept.role_name
    concept_nl = restr_concept.concept.nl()

    if restriction[0] == "∀":
        restr_concept_nl = f"{role_name.replace('_',' ')} only {concept_nl} things"
    elif restriction[0] == "∃":
        restr_concept_nl = (
            f"exists something {concept_nl} that it {role_name.replace('_',' ')}"
        )
    else:
        quantity = restriction[0]
        quantifier = restriction[1]

        if quantifier == ">":
            restr_concept_nl = (
                f"{role_name.replace('_',' ')} more than {quantity} {concept_nl} things"
            )
        elif quantifier == "<":
            restr_concept_nl = (
                f"{role_name.replace('_',' ')} less than {quantity} {concept_nl} things"
            )
        elif quantifier == ">=":
            restr_concept_nl = (
                f"{role_name.replace('_',' ')} at least {quantity} {concept_nl} things"
            )
        elif quantifier == "<=":
            restr_concept_nl = (
                f"{role_name.replace('_',' ')} at most {quantity} {concept_nl} things"
            )
        elif quantifier == "=":
            restr_concept_nl = (
                f"{role_name.replace('_',' ')} exactly {quantity} {concept_nl} things"
            )

    return restr_concept_nl
