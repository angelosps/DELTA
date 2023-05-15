import argparse
import json
import language_tool_python
from tqdm import tqdm

tool = language_tool_python.LanguageTool("en-US")
is_bad_rule = (
    lambda rule: rule.message
    == "The pronoun ‘someone’ is usually used with a third-person or a past tense verb."
    or rule.message == "Possible spelling mistake found."
    or rule.ruleId == "COLD_COULD"
    or rule.ruleId == "COMMA_COMPOUND_SENTENCE"
    or rule.ruleId == "COMMA_COMPOUND_SENTENCE_2"
    or rule.ruleId == "ADVERB_VERB_ADVERB_REPETITION"
    or rule.ruleId == "PHRASE_REPETITION"
)


def correct_sentence(text):
    matches = tool.check(text)
    matches = [rule for rule in matches if not is_bad_rule(rule)]

    corrected_text = language_tool_python.utils.correct(text, matches)
    if len(matches) != 0:
        for m in matches:
            if m.ruleId != "NON3PRS_VERB":
                print(m)
    return corrected_text


def fix_numbering_and_shuffle(input_file, output_file):
    with open(input_file, mode="r") as f:
        json_lines = list(f)
    f.close()
    id = 1
    with open(output_file, mode="w") as fout:
        progress_tracker = tqdm(total=len(json_lines))
        progress_tracker.set_description(desc="Correcting data...")
        for line in json_lines:
            skip = False
            data = json.loads(line)
            new_id = f"{'-'.join(data['id'].split('-')[:-1])}-{id}"
            new_context = list()
            for sentence in data["context"]:
                if "  " in sentence:
                    skip = True
                    break
                new_sentence = (
                    sentence.replace(" 1 ", " one ")
                    .replace(" 2 ", " two ")
                    .replace(" 3 ", " three ")
                    .replace("something", "someone")
                    .replace("things", "people")
                    .replace("Something", "Someone")
                    .replace("Things", "People")
                    .replace(" it is ", " they are ")
                )

                corr_sentence = correct_sentence(new_sentence)
                if new_sentence != corr_sentence:
                    # print(f"Old sentence: {new_sentence}")
                    # print(f"Corrected sentence: {corr_sentence}")
                    new_sentence = corr_sentence
                new_context.append(new_sentence)
            new_questions = list()
            qID = 1
            for question in data["questions"]:
                if "  " in question["text"]:
                    skip = True
                    break
                new_question_text = (
                    question["text"]
                    .replace(" 1 ", " one ")
                    .replace(" 2 ", " two ")
                    .replace(" 3 ", " three ")
                    .replace("something", "someone")
                    .replace("things", "people")
                    .replace("Something", "Someone")
                    .replace("Things", "People")
                    .replace(" it is ", " they are ")
                )

                corr_question = correct_sentence(new_question_text)
                if new_question_text != corr_question:
                    # print(f"Old question: {new_question_text}")
                    # print(f"Corrected question: {corr_question}")
                    new_question_text = corr_question

                new_question = {
                    "id": qID,
                    "text": new_question_text,
                    "label": question["label"],
                    "depth": question["depth"],
                    "explanation": question["explanation"]
                    if "explanation" in question
                    else [],
                    "meta": question["meta"],
                }
                new_questions.append(new_question)
                qID += 1

            assert len(data["questions"]) == qID - 1

            if skip:
                print("Invalid example, skipping ..")
                continue

            data2dump = {
                "id": new_id,
                "context": new_context,
                "questions": new_questions,
                "context_logical_form": data["context_logical_form"],
            }

            json_object = json.dumps(data2dump, ensure_ascii=False)
            fout.write(json_object)
            fout.write("\n")
            id += 1

            progress_tracker.update()

    progress_tracker.close()
    fout.close()
    tool.close()


def main():
    parser = argparse.ArgumentParser(description="Dataset fixer")
    parser.add_argument(
        "--input-file", required=True, help="Path to dataset JSONL file."
    )
    parser.add_argument(
        "--output-file", required=True, help="Path to save the result JSONL file."
    )
    args = parser.parse_args()
    input_file = args.input_file
    output_file = args.output_file

    print(f"I got '{args.input_file}' and I will produce '{output_file}'")

    ## Fix numbering in sentences --> Use words instead of numbers (1->"one", ..) ##
    fix_numbering_and_shuffle(input_file, output_file)


if __name__ == "__main__":
    main()
