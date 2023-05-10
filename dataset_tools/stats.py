import argparse
import json


def main():
    parser = argparse.ArgumentParser(description="Dataset Analyzer.")
    parser.add_argument("--file-path", required=True,
                        help="Path to JSONL file.")
    args = parser.parse_args()

    with open(args.file_path, 'r') as json_file:
        json_list = list(json_file)

    max_len = 0
    total_tokens = 0
    n_questions = 0

    for json_line in json_list:
        data = json.loads(json_line)
        context = ''.join(sentence for sentence in data['context'])

        questions = data['questions']

        for question_dict in questions:
            question_text = question_dict['text']
            total_tokens += len(context.split()) + len(question_text.split())
            max_len = max(max_len, len(context.split()) +
                          len(question_text.split()))
            n_questions += 1

    print(f"Average num of tokens = {total_tokens / n_questions}")
    print(f"Maximum num of tokens in pair = {max_len}")


if __name__ == "__main__":
    main()
