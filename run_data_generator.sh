#!/bin/bash

config_dir="grammars_and_config/config"
num_examples=1000
data_dir="DATA"
depth=5
level=3

# Create the data directory if it doesn't exist
mkdir -p "${data_dir}"

depth_dir="${data_dir}/Depth${depth}"

# Create the depth directory if it doesn't exist
mkdir -p "${depth_dir}"

for vocab in 1 2; do
  grammar_dir="grammars_and_config/ALCQ_grammarsV${vocab}"
  grammar_file="${grammar_dir}/ALCQGrammarL${level}.txt"
  config_file="${config_dir}/D${depth}_config.json"
  output_file="${depth_dir}/V${vocab}-L${level}-D${depth}-1K.jsonl"

  echo "Running data_generator.py with grammar ${grammar_file} and depth ${depth}"
  python3 data_generator.py --grammar "${grammar_file}" --config-json "${config_file}" --num-of-examples "${num_examples}" --max-depth "${depth}" --output-jsonl "${output_file}"
done

echo "All iterations completed!"
