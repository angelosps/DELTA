import argparse
import json
import openai

openai.api_key = "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"


def paraphrase(sentence):
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=f"Rephrase the following without affecting its meaning:\n\n{sentence}.",
        temperature=0,
        max_tokens=60,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
    )

    output = response.choices[0].text.strip()
    return output


from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("paraphrase-distilroberta-base-v1")


def calculate_similarity(sentence1, sentence2):
    embeddings = model.encode([sentence1, sentence2], convert_to_tensor=True)
    similarity = util.pytorch_cos_sim(embeddings[0], embeddings[1])
    return similarity.item()


def main():
    parser = argparse.ArgumentParser(description="Dataset fixer")
    parser.add_argument(
        "--input-file", required=True, help="Path to dataset JSONL file."
    )
    args = parser.parse_args()
    input_file = args.input_file
    output_file = f"{args.input_file.split('.')[0]}_para.jsonl"

    print(f"I got '{args.input_file}' and I will produce '{output_file}'")
    threshold = 0.8
    with open(input_file, "r") as infile, open(output_file, "w") as outfile:
        for line in list(infile)[:100]:
            data = json.loads(line)
            rephrased_context = []
            for sentence in data["context"]:
                rephrased_sentence = paraphrase(sentence)
                similarity_score = calculate_similarity(sentence, rephrased_sentence)
                if similarity_score >= threshold:
                    print(
                        f"Keeping the rephrasing '{sentence}' -> '{rephrased_sentence}'"
                    )
                    print(f"with score: {similarity_score}\n")
                    rephrased_context.append(rephrased_sentence)
                else:
                    rephrased_context.append(sentence)

            print("-- NEW CONTEXT ---")
            print(rephrased_context)
            print()
            rephrased_questions = []

            for question in data["questions"]:
                rephrased_text = paraphrase(question["text"])

                similarity_score = calculate_similarity(
                    question["text"], rephrased_text
                )

                if similarity_score >= threshold:
                    print(
                        f"Keeping the rephrasing '{question['text']}' -> '{rephrased_text}'"
                    )
                    print(f"with score: {similarity_score}\n")
                    question["text"] = rephrased_text
                rephrased_questions.append(question)

            data["context"] = rephrased_context
            data["questions"] = rephrased_questions

            outfile.write(json.dumps(data) + "\n")


if __name__ == "__main__":
    main()
