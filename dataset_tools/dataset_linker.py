import json
import argparse


def main():
    parser = argparse.ArgumentParser(description="Dataset linker")
    parser.add_argument("--i1", required=True, help="Path to first dataset JSONL file.")
    parser.add_argument(
        "--i2", required=True, help="Path to second dataset JSONL file."
    )
    parser.add_argument(
        "--output-file", required=True, help="Path to output dataset JSONL file."
    )
    args = parser.parse_args()

    out_file_path = args.output_file

    with open(args.i1, "r") as in_file1:
        json_list1 = list(in_file1)

    with open(args.i2, "r") as in_file2:
        json_list2 = list(in_file2)

    with open(out_file_path, "w") as out_file:
        id = 1
        for json_line in json_list1:
            skip = False
            data = json.loads(json_line)
            new_id = f"{'-'.join(data['id'].split('-')[:-1])}-{id}"

            context = data["context"]
            questions = data["questions"]

            for question in questions:
                if (
                    question["depth"] == 0
                    and question["label"] == "True"
                    and f"{question['text']}." not in context
                ):
                    # Check that the true lookup questions are present in the context
                    print(
                        "True lookup question not in the context, skipping this theory!"
                    )
                    continue
                elif (
                    question["depth"] == "na"
                    or question["depth"] > 1
                    or (question["depth"] == 0 and question["label"] != "True")
                ) and question["text"] in context:
                    print(
                        "Found question of depth > 0 in context, skipping this theory!"
                    )
                    skip = True
                    break
            if skip:
                continue

            new_data = {
                "id": new_id,
                "context": context,
                "questions": questions,
                "context_logical_form": data["context_logical_form"],
            }
            json_object = json.dumps(new_data, ensure_ascii=False)
            # Write this line to new dataset with the updated ID ...
            out_file.write(json_object)
            out_file.write("\n")
            id += 1

        # Continue by writing the second one
        for json_line in json_list2:
            skip = False
            data = json.loads(json_line)
            new_id = f"{'-'.join(data['id'].split('-')[:-1])}-{id}"

            context = data["context"]
            questions = data["questions"]

            for question in questions:
                if (
                    question["depth"] == 0
                    and question["label"] == "True"
                    and f"{question['text']}." not in context
                ):
                    # Check that the true lookup questions are present in the context
                    print(
                        "True lookup question not in the context, skipping this theory!"
                    )
                    continue
                elif (
                    question["depth"] == "na"
                    or question["depth"] > 1
                    or (question["depth"] == 0 and question["label"] != "True")
                ) and question["text"] in context:
                    print(
                        "Found question of depth > 0 in context, skipping this theory!"
                    )
                    skip = True
                    break
            if skip:
                continue

            new_data = {
                "id": new_id,
                "context": context,
                "questions": questions,
                "context_logical_form": data["context_logical_form"],
            }

            json_object = json.dumps(new_data, ensure_ascii=False)
            # Write this line to new dataset with the updated ID ...
            out_file.write(json_object)
            out_file.write("\n")
            id += 1

    # Closing file
    in_file1.close()
    in_file2.close()
    out_file.close()


if __name__ == "__main__":
    main()
