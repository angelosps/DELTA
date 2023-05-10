import json
import argparse

def main():
    parser = argparse.ArgumentParser(description="Dataset corrector")
    parser.add_argument("--file-path", required=True,
                        help="Path to dataset JSONL file.")
    args = parser.parse_args()
    extension_offset = len('jsonl') + 1
    new_file_path = f"{args.file_path[:-extension_offset]}_correct.jsonl"
   
    with open(args.file_path, 'r') as json_file:
        json_list = list(json_file)

    with open(new_file_path, 'w') as out_file:
        id = 1
        for json_line in json_list:
            skip = False
            data = json.loads(json_line)
            new_id = f"{'-'.join(data['id'].split('-')[:-1])}-{id}"
            
            context = data['context']
            questions = data['questions']

            # Check that the true lookup questions are present in the context
            if questions[0]['text'] not in context:
                print("True lookup question not in the context, skipping this theory!")
                continue

            # No other question should be present in the context
            for q in questions[1:]:
                if q['text'] in context:
                    print("Found question of depth > 0 in context, skipping this theory!")
                    skip = True
                    break
            if skip:
                continue
            
            new_data = {"id" : new_id, "context": context, "questions" : questions}
            json_object = json.dumps(new_data)
            # Write this line to new dataset with the updated ID ...
            out_file.write(json_object)
            out_file.write('\n')
            id += 1
        
    # Closing file
    json_file.close()
    out_file.close()

if __name__ == "__main__":
    main()