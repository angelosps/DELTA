""" A script that tests if all lookup questions are presented in the text and
    all unknown questions are not. """

import json
import argparse


def main():
    parser = argparse.ArgumentParser(description="Question tester.")
    parser.add_argument("--file-path", required=True, help="Path to JSONL file.")
    args = parser.parse_args()

    with open(args.file_path, "r") as json_file:
        json_list = list(json_file)
    json_file.close()
    cnt = 0
    for json_line in json_list:
        data = json.loads(json_line)
        context = data["context"]
        questions = data["questions"]

        for question in questions:
            if (
                question["depth"] == 0
                and question["label"] == "True"
                and question["text"] not in context
            ):
                print("True lookup question not in the context, skipping this theory!")
            elif (
                question["depth"] >= 1
                or (question["depth"] == 0 and question["label"] != "True")
            ) and question["text"] in context:
                # print("Found question of depth > 0 in context, skipping this theory!")
                print(data["context_logical_form"])
                print(question)
                print(data["id"])
                cnt += 1
    print(cnt)


if __name__ == "__main__":
    main()
