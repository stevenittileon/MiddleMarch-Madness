# Building Middlemarch: A Small Reasoning Benchmark for LLMs

I started this project to test a very specific reasoning skill in language models: can a model reliably identify an item *between* two anchor items in a noisy sequence?

That idea became **MiddleMatch**.

## The Core Task

Each example gives the model:

- A list of length `N` (for example, `N=40`)
- Items sampled from a smaller pool of size `K` (for example, `K=10`)
- A question like:  
  "What is the single name that appears right between `X` and `Y`?"

Because `K` can be much smaller than `N`, the list contains repetitions. This makes the task less like simple lookup and more like pattern-based scanning under distraction.

## Why This Is Interesting

This benchmark sits in a useful middle ground:

- It is simple to explain
- It has deterministic, checkable answers
- It still stresses attention, positional reasoning, and robustness to repeated tokens

In other words, it is a lightweight way to probe whether a model can track local structure inside longer contexts.

## How the Generator Works

The script (`generate_middlemarch.py`) creates examples that are guaranteed to have a **single correct answer**.

For each row it:

1. Builds a random name pool of size `K`
2. Generates a random sequence of length `N`
3. Injects at least one `left, middle, right` pattern
4. Verifies that all `left ? right` matches point to exactly one unique middle value
5. Exports the result to JSONL with both a prompt and answer

This guarantees clean supervision data for training and reliable evaluation for testing.

## Name Sources

I also made the first-name source flexible so the benchmark can be grounded in real-world data:

- Built-in local names
- SSA baby-name source (when accessible)
- Public URL (`.txt` / `.csv`)
- Local files (including large baby-name CSVs)

That makes it easy to scale diversity without changing the core task definition.

## Where This Can Go Next

Some extensions I want to explore:

- Number-based MiddleMatch in addition to names
- Harder variants with punctuation/noise tokens
- Split datasets by difficulty (short/long context, low/high repetition)
- Evaluation scripts that compare model accuracy by `N`, `K`, and prompt style

Middlemarch is intentionally small and focused: one clear task, one clear answer, and a clean signal on whether an LLM is truly tracking sequence structure.
