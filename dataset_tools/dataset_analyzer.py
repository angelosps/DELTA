import json
import argparse
import matplotlib.pyplot as plt

symbols_count = {
    '⊓' : 0, '⊔' : 0, '∀' : 0, '∃' : 0,
    '>' : 0, '>=': 0, '<' : 0, '<=' : 0,
    '=' : 0, '⊤' : 0, '⊥' : 0, '⊑' : 0
}

def barplot_data(labels, percentages, bar_colors, title, filename):
    plt.bar(labels, percentages, color=bar_colors)
    plt.title(title)
    plt.ylabel("Percentage %")
    plt.savefig(filename, bbox_inches='tight')
    plt.close()

def main():
    parser = argparse.ArgumentParser(description="Dataset Analyzer.")
    parser.add_argument("--file-path", required=True,
                        help="Path to JSONL file.")
    args = parser.parse_args()

    with open(args.file_path, 'r') as json_file:
        json_list = list(json_file)

    n_true_questions = 0
    n_false_questions = 0
    n_unknown_questions = 0
    not_in_true_questions = 0
    not_in_false_questions = 0
    not_in_unknown_questions = 0
    
    TRUE_W_NOT = 0
    FALSE_W_NOT = 1
    UNKNOWN_W_NOT = 2
    
    stats_per_type = {
        "ConceptAssertion" : [0,0,0],
        "TBoxAxiom" : [0,0,0],
        "RoleAssertion" : [0,0,0]
    }

    n_true_concept_assertions = 0
    n_false_concept_assertions = 0
    n_unknown_concept_assertions = 0
    n_true_tbox_axioms = 0
    n_false_tbox_axioms = 0
    n_unknown_tbox_axioms = 0
    n_true_role_assertions = 0
    n_false_role_assertions = 0
    n_unknown_role_assertions = 0

    for json_line in json_list:
        data = json.loads(json_line)
        context_logical_form = data['context_logical_form']

        for logical_form in context_logical_form:
            for symbol in symbols_count.keys():
                symbols_count[symbol] += logical_form.count(symbol)

        questions = data['questions']
        
        for question_dict in questions:
            question_text = question_dict['text']
            question_label = question_dict['label']
            question_type = question_dict['meta']

            if question_label == "True":
                n_true_questions += 1

                if "ConceptAssertion" in question_type:
                    n_true_concept_assertions += 1
                elif "TBoxAxiom" in question_type:
                    n_true_tbox_axioms += 1
                elif "RoleAssertion" in question_type:
                    n_true_role_assertions += 1

                if "not" in question_text:
                    if "ConceptAssertion" in question_type:
                        stats_per_type["ConceptAssertion"][TRUE_W_NOT] += 1
                    elif "TBoxAxiom" in question_type:
                        stats_per_type["TBoxAxiom"][TRUE_W_NOT] += 1
                    elif "RoleAssertion" in question_type:
                        stats_per_type["RoleAssertion"][TRUE_W_NOT] += 1
                    else:
                        print(f"WHAT IS THIS TYPE? {question_type}")

                    not_in_true_questions += 1
            elif question_label == "False":
                n_false_questions += 1

                if "ConceptAssertion" in question_type:
                    n_false_concept_assertions += 1
                elif "TBoxAxiom" in question_type:
                    n_false_tbox_axioms += 1

                if "not" in question_text:
                    if "ConceptAssertion" in question_type:
                        stats_per_type["ConceptAssertion"][FALSE_W_NOT] += 1
                    elif "TBoxAxiom" in question_type:
                        stats_per_type["TBoxAxiom"][FALSE_W_NOT] += 1
                    elif "RoleAssertion" in question_type:
                        stats_per_type["RoleAssertion"][FALSE_W_NOT] += 1
                    else:
                        print(f"WHAT IS THIS TYPE? {question_type}")
                    not_in_false_questions += 1
            else:
                n_unknown_questions += 1

                if "ConceptAssertion" in question_type:
                    n_unknown_concept_assertions += 1
                elif "TBoxAxiom" in question_type:
                    n_unknown_tbox_axioms += 1
                elif "RoleAssertion" in question_type:
                    n_unknown_role_assertions += 1

                if "not" in question_text:
                    if "ConceptAssertion" in question_type:
                        stats_per_type["ConceptAssertion"][UNKNOWN_W_NOT] += 1
                    elif "TBoxAxiom" in question_type:
                        stats_per_type["TBoxAxiom"][UNKNOWN_W_NOT] += 1
                    elif "RoleAssertion" in question_type:
                        stats_per_type["RoleAssertion"][UNKNOWN_W_NOT] += 1
                    else:
                        print(f"WHAT IS THIS TYPE? {question_type}")
                    not_in_unknown_questions += 1
    
    # Closing file
    json_file.close()

    # Print some statistics 
    print(f"Questions Analyzed: {n_true_questions + n_false_questions + n_unknown_questions}")
    print("{0:.2f} % of True questions contain 'not'.".format(not_in_true_questions / n_true_questions * 100))
    print("{0:.2f} % of False questions contain 'not'.".format(not_in_false_questions / n_false_questions * 100))
    if n_unknown_questions > 0:
        print("{0:.2f} % of Unknown questions contain 'not'.".format(not_in_unknown_questions / n_unknown_questions * 100))

    print(f"Number of True Concept Assertions: {n_true_concept_assertions}")
    print(f"Number of False Concept Assertions: {n_false_concept_assertions}")
    print(f"Number of Unknown Concept Assertions: {n_unknown_concept_assertions}")

    print(f"Number of True Role Assertions: {n_true_role_assertions}")
    print(f"Number of Unknown Role Assertions: {n_unknown_role_assertions}")

    print(f"Number of True TBox Axioms: {n_true_tbox_axioms}")
    print(f"Number of False TBox Axioms: {n_false_tbox_axioms}")
    print(f"Number of Unknown TBox Axioms: {n_unknown_tbox_axioms}")




    print("\n========== SYMBOL STATISTICS ==========")
    for key in symbols_count.keys():
        print(f"{key} : {symbols_count[key]/10}")


    labels = ["True Q with 'not'", "False Q with 'not'", "Unknown Q with 'not'"] # x - axis labels
    bar_colors = ["tab:green", "tab:red", "tab:blue"]

    n_concept_assertions = n_true_concept_assertions + n_false_concept_assertions + n_unknown_concept_assertions
    n_role_assertions = n_true_role_assertions + n_false_role_assertions + n_unknown_role_assertions
    n_tbox_axioms = n_true_tbox_axioms + n_false_tbox_axioms + n_unknown_tbox_axioms
    n_questions = n_concept_assertions + n_role_assertions + n_tbox_axioms
    type_of_q_labels = ["Concept Questions", "Role Questions", "TBox Questions"]
    question_types_percentages = [
        n_concept_assertions / n_questions * 100,
        n_role_assertions / n_questions * 100,
        n_tbox_axioms / n_questions * 100
    ]

    barplot_data(type_of_q_labels,
                 question_types_percentages, 
                 bar_colors,
                 "Question types", 
                 "types_stats.png")


    concept_assertion_percentages = [
        stats_per_type["ConceptAssertion"][TRUE_W_NOT] / n_true_concept_assertions * 100,
        stats_per_type["ConceptAssertion"][FALSE_W_NOT] / n_false_concept_assertions * 100,
        stats_per_type["ConceptAssertion"][UNKNOWN_W_NOT] / n_unknown_concept_assertions * 100
    ]

    barplot_data(labels,
                 concept_assertion_percentages, 
                 bar_colors,
                 "Concept Assertion Questions per label with 'not'",
                 "ca_stats.png")

    if all(i > 0 for i in[n_true_tbox_axioms, n_false_tbox_axioms, n_unknown_tbox_axioms]):
        tbox_axiom_percentages = [
            stats_per_type["TBoxAxiom"][TRUE_W_NOT] / n_true_tbox_axioms * 100,
            stats_per_type["TBoxAxiom"][FALSE_W_NOT] / n_false_tbox_axioms * 100,
            stats_per_type["TBoxAxiom"][UNKNOWN_W_NOT] / n_unknown_tbox_axioms * 100
        ]

        barplot_data(labels,
                    tbox_axiom_percentages,
                    bar_colors,
                    "TBox Axiom Questions per label with 'not'",
                    "ta_stats.png")
        
    

if __name__ == "__main__":
    main()