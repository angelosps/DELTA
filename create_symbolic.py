import json
import argparse

def read_dataset(file_path):
    SoftDataset = list()
    HardDataset = list()
    with open(file_path, 'r') as json_file:
        json_list = list(json_file)
    json_file.close()

    for json_line in json_list:
        data = json.loads(json_line)
        context = data['context']
        context_logical_form = data['context_logical_form']
        questions = data['questions']
        for question in questions:
            SoftDataset.append({'context' : ' '.join([f"{prepare_soft_symbolic_form(sentence[:-1])}." for sentence in context]),
                        'question' : prepare_soft_symbolic_form(question['text']),
                        'label' : question['label']})
            HardDataset.append({'context' : ' '.join([prepare_hard_symbolic_form(dl) for dl in context_logical_form]),
                        'question' : prepare_hard_symbolic_form(question['meta']['DL']),
                        'label' : question['label']})
    return SoftDataset, HardDataset

def write_symbolic_datasets(soft_dataset, hard_dataset, soft_output_file, hard_output_file):
    with open(soft_output_file, 'w') as file:
        for data in soft_dataset:
            json_line = json.dumps(data)
            file.write(json_line + '\n')
    with open(hard_output_file, 'w') as file:
        for data in hard_dataset:
            json_line = json.dumps(data)
            file.write(json_line + '\n')


individual_names = {
    'ioanna': 'a1', 
    'dimitrios': 'a2', 
    'eleni': 'a3', 
    'maria': 'a4',
    'manolis': 'a5', 
    'angelos': 'a6', 
    'panos': 'a7',
    'anne': 'a8', 
    'bob': 'a9', 
    'charlie': 'a10', 
    'dave': 'a11', 
    'erin': 'a12', 
    'fiona': 'a13', 
    'gary': 'a14', 
    'harry': 'a15'
}

concept_names = {
    'ambitious': 'C1', 
    'confident': 'C2', 
    'creative': 'C3', 
    'determined': 'C4',
    'enthusiastic': 'C5', 
    'innovative': 'C6', 
    'logical': 'C7', 
    'persevering': 'C8',
    'red': 'C9', 
    'blue': 'C10', 
    'green': 'C11', 
    'kind': 'C12', 
    'nice': 'C13', 
    'big': 'C14',
    'cold': 'C15', 
    'young': 'C16', 
    'round': 'C17', 
    'rough': 'C18', 
    'orange': 'C19', 
    'smart': 'C20', 
    'quiet': 'C21', 
    'furry': 'C22',
}

role_names = {
    'admires': 'R1', 
    'admire': 'R1', 

    'consults': 'R2', 
    'consult': 'R2',

    'guides': 'R3', 
    'guide': 'R3', 

    'instructs': 'R4',
    'instruct': 'R4',

    'leads': 'R5', 
    'lead': 'R5', 

    'mentors': 'R6', 
    'mentor': 'R6', 

    'supervises': 'R7', 
    'supervise': 'R7',

    'supports': 'R8',
    'support': 'R8',

    'likes': 'R9', 
    'like': 'R9',

    'loves': 'R10', 
    'love': 'R10',

    'eats': 'R11', 
    'eat': 'R11',

    'chases': 'R12',
    'chase': 'R12',
}

# Merge all dictionaries
all_mappings = {**individual_names, **concept_names, **role_names}

def prepare_soft_symbolic_form(text):
    # Replace words in the text
    words = text.split()
    replaced_text = ' '.join([all_mappings.get(word.lower(), word) for word in words])
    replaced_text = ""
    for word in words:
        if word[-1] == ',' and (word[:-1] in all_mappings):
            replaced_text += f"{all_mappings.get(word[:-1].lower(), word)},"
        else:
            replaced_text += all_mappings.get(word.lower(), word)
        replaced_text += " "
    
    return replaced_text[:-1]


def prepare_hard_symbolic_form(text):
    text = text.replace('\u2203', 'exists')
    text = text.replace('\u2200', 'only')
    text = text.replace('\u00ac', 'not')
    text = text.replace('+', '')
    text = text.replace('  ', ' ')
    text = text.replace('\u22a4', 'top')
    text = text.replace('\u22a5', 'bottom')
    text = text.replace('\u2293', 'and')
    text = text.replace('\u2294', 'or')
    text = text.replace('\u2291', 'is subsumed by')

    # Replace words in the text
    words = text.split()
    replaced_text = ' '.join([all_mappings.get(word.lower(), word) for word in words])

    return replaced_text

def main(args):
    soft_dataset, hard_dataset = read_dataset(args.file_path)
    write_symbolic_datasets(soft_dataset, hard_dataset, args.soft_output_file, args.hard_output_file)
    print(f"SoftSymbolic dataset written to {args.soft_output_file}.")
    print(f"HardSymbolic dataset written to {args.hard_output_file}.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Read a DELTA dataset and transform it into SoftSymbolic form.')
    parser.add_argument('--file-path', type=str, help='path to DELTA dataset to transform.')
    parser.add_argument('--soft-output-file', type=str, help='path to store the SoftSymbolic dataset.')
    parser.add_argument('--hard-output-file', type=str, help='path to store the HardSymbolic dataset.')
    args = parser.parse_args()
    main(args)