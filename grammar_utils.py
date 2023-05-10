from nltk import Nonterminal
from numpy.random import choice


def preprocess_pcfg(grammar_file):
    """Preprocesses given PCFG grammar file to return a collection of strings representing
    all the productions in the grammar. Expected grammar file format: NLTK PCFG format,
    for e.g.:
        Statement -> Fact
        Fact -> Polarity '(' Attribute Entity ')'
        Entity -> 'cat' | 'dog' | 'bald eagle' | 'rabbit' | 'mouse'
        Attribute -> 'red' | 'blue' | 'green' | 'kind' | 'nice' | 'big'
        Polarity -> '+' [0.8] | '-' [0.2]
    """
    # Iterate through the lines and collect productions in a dictionary, keyed by
    # the nonterminals. So if there are two lines, one with S -> NP VP | VP and another
    # with S -> NP VP PP on two different lines, the dictionary will contain a key 'S'
    # with value 'NP VP | VP | NP VP PP'.
    productions = []
    nonterminal_dict = {}
    for line in grammar_file.readlines():
        production_parts = line.strip().split("->", 1)
        if len(production_parts) == 2:
            lhs = production_parts[0].strip()
            rhs = production_parts[1]
            if lhs not in nonterminal_dict:
                nonterminal_dict[lhs] = rhs
            else:
                nonterminal_dict[lhs] += " | " + rhs

    # Iterate through the productions and check if each possible RHS has a probability
    # associated with it, expected to be specified like [0.5].
    productions = []
    for nonterminal in nonterminal_dict:
        rhs = nonterminal_dict[nonterminal]
        rhs_parts = [rhs_part.strip() for rhs_part in rhs.split("|")]
        num_parts = len(rhs_parts)
        found_probs = True
        for rhs_part in rhs_parts:
            rhs_part_items = rhs_part.split(" ")
            rhs_part_last_item = rhs_part_items[-1]
            if not (
                rhs_part_last_item.startswith("[") and rhs_part_last_item.endswith("]")
            ):
                found_probs = False
                break
        # If any of the RHS part items did not have an associated probability, assign all of them equal
        # probability.
        if not found_probs:
            prob = 1.0 / num_parts
            rhs_parts_with_probs = []
            for rhs_part in rhs_parts:
                rhs_part_mod = rhs_part + " " + "[" + str(prob) + "]"
                rhs_parts_with_probs.append(rhs_part_mod)
            rhs_parts = rhs_parts_with_probs
        final_rhs = " | ".join(rhs_parts)
        production = f"{nonterminal} -> {final_rhs}"
        productions.append(production)
    return productions


def choose_production(grammar, nonterminal):
    """Choose a production with specified nonterminal as LHS based on the probability distribution
    of the grammar."""
    productions = [
        item for item in grammar.productions() if item.lhs().symbol() == nonterminal
    ]
    if len(productions) == 0:
        raise ValueError(f"Nonterminal {nonterminal} not found in the grammar!")
    probabilities = [production.prob() for production in productions]
    chosen_production = choice(productions, p=probabilities)
    return chosen_production


def generate_random_statement(grammar, nonterminal):
    """Generate a random statement from the given nonterminal LHS in the grammar."""
    chosen_production = choose_production(grammar, nonterminal)
    rhs = chosen_production.rhs()
    sentence = ""

    for item in rhs:
        if isinstance(item, Nonterminal):
            item_generated_statement = generate_random_statement(grammar, item.symbol())
        else:
            item_generated_statement = item

        if len(sentence) > 0:
            sentence += " "
        sentence += item_generated_statement

    return sentence
