# Middlemarch Madness

`middlemarch` is a **MiddleMatch** dataset generator.

Each example gives a list of names and asks:
"What is the single name that appears right between X and Y?"

The script guarantees a unique answer for every generated row.

## N and K

- `N` = length of each list in an example
- `K` = number of possible names used to build that list

Example:
- `N=40, K=10` means each row has 40 positions, drawn from a 10-name pool (so repeats are expected).

## Quick start

```powershell
python .\generate_middlemarch.py --count 1000 --n 40 --k 10 --out middlemarch.jsonl
```

## Name sources

### 1) Built-in local names (default)

```powershell
python .\generate_middlemarch.py --count 1000 --n 40 --k 10 --first-names-source local --out middlemarch_local.jsonl
```

### 2) SSA popular baby names

```powershell
python .\generate_middlemarch.py --count 1000 --n 40 --k 10 --first-names-source ssa --ssa-sex all --ssa-limit 500 --out middlemarch_ssa.jsonl
```

Note: in some environments, the SSA endpoint may return HTTP 403. If that happens, use `local`, `url`, or `files`.

### 3) Public URL (`.txt` or `.csv`)

```powershell
python .\generate_middlemarch.py --count 1000 --n 40 --k 10 --first-names-source url --first-names-url "https://example.com/top_names.csv" --ssa-limit 500 --out middlemarch_websource.jsonl
```

- `.txt`: one name per line
- `.csv`: uses `name` column if present, otherwise first column

### 4) Local files (`.txt` or `.csv`)

```powershell
python .\generate_middlemarch.py --count 1000 --n 40 --k 10 --first-names-source files --first-names-files ".\ontario_baby_names_male_1917-2022.csv" ".\ontario_baby_names_female_1917-2022.csv" --ssa-limit 5000 --out middlemarch_ontario.jsonl
```

## Common options

- `--count`: number of examples (default `1000`)
- `--n`: sequence length `N` (default `40`)
- `--k`: pool size `K` (default `10`)
- `--seed`: random seed (default `42`)
- `--out`: output file (default `middlemarch.jsonl`)
- `--first-names-source`: `local | ssa | url | files`
- `--ssa-sex`: `all | M | F` (SSA only)
- `--ssa-limit`: max number of first names to keep from external sources (default `300`)
- `--first-names-url`: URL for `url` source
- `--first-names-files`: one or more local files for `files` source

## Output format (JSONL)

Each line includes:

- `id`
- `task` (`middlematch`)
- `n`, `k`
- `name_pool`
- `sequence`
- `left`, `right`
- `prompt`
- `answer`

## Parser helper

`parse_between(sequence, left, right)` returns the unique middle value for `left ? right`.
It raises an error when no match exists or when the match is ambiguous.
