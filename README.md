# DELTA: Description Logics with Transformers

Code to produce ALCQ-based Knowledge Bases (KBs) in natural language. 

## Knowledge Base generation

Given an `ALCQ Probabilistic Context Free Grammar (PCFG)` the `data_generator.py` will produce `num_of_examples` KBs with questions within the target reasoning depth (`max_depth`).

## Usage

```
python3 data_generator.py --grammar grammars_and_config/ALCQ_grammarsV1/ALCQGrammarL<0/1/2/3>.txt 
                          --config-json grammars_and_config/config/D<1/2/3/5>_config.json 
                          --num-of-examples <integer> --max-depth <1/2/3/4/5> 
                          --output-jsonl <output-file-name>.jsonl
```
