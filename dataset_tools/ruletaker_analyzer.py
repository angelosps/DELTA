import json
import argparse

def main():
    parser = argparse.ArgumentParser(description="Dataset Analyzer.")
    parser.add_argument("--file-path", required=True,
                        help="Path to JSONL file.")
    args = parser.parse_args()

    with open(args.file_path, 'r') as json_file:
        json_list = list(json_file)

    n_true_questions = 0
    n_false_questions = 0

    not_in_true_questions = 0
    not_in_false_questions = 0
    n_role_questions = 0
    n_concept_questions = 0
    n_tbox_questions = 0

    n_true_role_questions = 0
    n_false_role_questions = 0
    true_role_q_with_not = 0
    false_role_q_with_not = 0

    rolenames = ["likes", 'chases', 'eats' , 'sees' , 'visits' , 'needs']
    
    for json_line in json_list:
        data = json.loads(json_line)
        questions = data['questions']

        for q in questions:
            if " is " in q['text']:
                n_concept_questions += 1
            elif any(r[:-1] in q['text'] for r in rolenames) or \
                any(r in q['text'] for r in rolenames):
                n_role_questions += 1
                if q['label'] == True:
                    n_true_role_questions += 1
                    if "not" in q['text']:
                        true_role_q_with_not += 1
                else:
                    n_false_role_questions += 1
                    if "not" in q['text']:
                        false_role_q_with_not += 1
            else:
                n_tbox_questions += 1

            if q['label'] == True:
                n_true_questions += 1
            else:
                n_false_questions += 1

            if "not" in q['text']:
                if q['label'] == True:
                    not_in_true_questions += 1
                else:
                    not_in_false_questions += 1

    print("{0:.2f} % of True questions contain 'not'.".format(not_in_true_questions / n_true_questions * 100))
    print("{0:.2f} % of False questions contain 'not'.".format(not_in_false_questions / n_false_questions * 100))
    print("{0:.2f} % are Role questions.".format(n_role_questions / (n_true_questions + n_false_questions) * 100))
    print("{0:.2f} % are Concept questions.".format(n_concept_questions / (n_true_questions + n_false_questions) * 100))
    print("{0:.2f} % are TBox questions.".format(n_tbox_questions / (n_true_questions + n_false_questions) * 100))
    print("{0:.2f} % of True Role questions contain 'not'.".format(true_role_q_with_not / n_true_role_questions * 100))
    print("{0:.2f} % of False Role questions contain 'not'.".format(false_role_q_with_not / n_false_role_questions * 100))


if __name__ == "__main__":
    main()