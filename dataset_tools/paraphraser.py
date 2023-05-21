import argparse
import json
import openai
from sentence_transformers import SentenceTransformer, util

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


model = SentenceTransformer("paraphrase-distilroberta-base-v1")


def calculate_similarity(sentence1, sentence2):
    embeddings = model.encode([sentence1, sentence2], convert_to_tensor=True)
    similarity = util.pytorch_cos_sim(embeddings[0], embeddings[1])
    return similarity.item()


from tqdm import tqdm


def main():
    parser = argparse.ArgumentParser(description="Dataset fixer")
    parser.add_argument(
        "--input-file", required=True, help="Path to dataset JSONL file."
    )
    parser.add_argument(
        "--output-file", required=True, help="Path to dataset JSONL file."
    )
    args = parser.parse_args()
    input_file = args.input_file
    output_file = args.output_file

    print(f"I got '{args.input_file}' and I will produce '{output_file}'")
    threshold = 0.85
    sentences_rephrased = 0  # number of sentences rephrased
    n_sentences = 0
    questions_rephrased = 0  # number of questions rephrased
    n_questions = 0

    with open(input_file, "r") as infile:
        infile_list = list(infile)

    with open(output_file, "w") as outfile:
        progress_tracker = tqdm(total=len(infile_list))
        progress_tracker.set_description(desc="Parapharsing data...")
        for line in infile_list:
            data = json.loads(line)
            rephrased_context = []
            for sentence in data["context"]:
                n_sentences += 1
                rephrased_sentence = paraphrase(sentence)
                similarity_score = calculate_similarity(sentence, rephrased_sentence)
                if similarity_score >= threshold:
                    sentences_rephrased += 1
                    # print(
                    #     f"Keeping the rephrasing '{sentence}' -> '{rephrased_sentence}'"
                    # )
                    # print(f"with score: {similarity_score}\n")
                    rephrased_context.append(rephrased_sentence)
                else:
                    rephrased_context.append(sentence)

            rephrased_questions = []
            for question in data["questions"]:
                n_questions += 1
                rephrased_text = paraphrase(question["text"])
                similarity_score = calculate_similarity(
                    question["text"], rephrased_text
                )
                if similarity_score >= threshold:
                    questions_rephrased += 1
                    question["text"] = rephrased_text
                rephrased_questions.append(question)

            data["paraphrased"] = {
                "context": rephrased_context,
                "questions": rephrased_questions,
            }

            outfile.write(json.dumps(data, ensure_ascii=False) + "\n")
            progress_tracker.update()
        progress_tracker.close()

    print(f"Sentences paraphrased: {sentences_rephrased}")
    print(f"Total sentences: {n_sentences}")
    print(f"Questions paraphrased: {questions_rephrased}")
    print(f"Total questions: {n_questions}")


if __name__ == "__main__":
    main()
