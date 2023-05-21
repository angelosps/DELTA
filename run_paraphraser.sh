#!/bin/bash

# define the base directory
base_dir="DATA_TEST"

# Initialize counters
total_sentences=0
total_questions=0
paraphrased_sentences=0
paraphrased_questions=0

# traverse through each file in each sub-directory
for file in $(find $base_dir -type f -name "*.jsonl"); do
  # get file name without extension
  filename=$(basename "$file" .jsonl)
  # get directory path
  dirpath=$(dirname "$file")
  # define output file name
  output_file="${dirpath}/${filename}_para.jsonl"
  # call python script and capture the output
  output=$(python3 dataset_tools/paraphraser.py --input-file $file --output-file $output_file)
  # parse and accumulate counts
  paraphrased_sentences=$(($paraphrased_sentences + $(echo "$output" | grep "Sentences paraphrased:" | awk '{print $3}')))
  total_sentences=$(($total_sentences + $(echo "$output" | grep "Total sentences:" | awk '{print $3}')))
  paraphrased_questions=$(($paraphrased_questions + $(echo "$output" | grep "Questions paraphrased:" | awk '{print $3}')))
  total_questions=$(($total_questions + $(echo "$output" | grep "Total questions:" | awk '{print $3}')))
done

# calculate percentages
percent_sentences=$(bc -l <<< "($paraphrased_sentences/$total_sentences)*100")
percent_questions=$(bc -l <<< "($paraphrased_questions/$total_questions)*100")

# print percentages
echo "Percentage of sentences paraphrased: $percent_sentences%"
echo "Percentage of questions paraphrased: $percent_questions%"
