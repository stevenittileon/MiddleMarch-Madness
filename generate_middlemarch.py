import argparse
import csv
import io
import json
import random
import urllib.error
import urllib.request
import zipfile
from collections import Counter
from typing import List, Sequence, Tuple


# This script generates "MiddleMatch" examples:
# given a sequence and two anchor names (left/right),
# the model must output the single name between them.
#
# Example pattern in sequence:
#   ... left, answer, right ...
# Question:
#   "What name appears right between left and right?"

COMMON_FIRST_NAMES = [
    "Carlos", "Dale", "Stephen", "Finnian", "Gregory", "Leonard", "Bruce",
    "Raymond", "James", "Avery", "Harper", "Jordan", "Noah", "Ethan", "Liam",
    "Olivia", "Emma", "Sophia", "Mason", "Logan", "Caleb", "Wyatt", "Lucas",
    "Amelia", "Henry", "Benjamin", "Aiden", "Elijah", "Daniel", "Jackson",
    "Isaac", "Levi", "Mateo", "Julian", "Nora", "Mila", "Aria", "Hazel",
    "Stella", "Zoe", "Ivy", "Quinn", "Ezra", "Hudson", "Owen", "Asher",
    "Maya", "Riley", "Carter", "Jaxon", "Adrian", "Roman", "Elliot", "Declan",
]

COMMON_LAST_NAMES = [
    "Davis", "Sims", "Cruz", "Ross", "Collins", "Kalman", "Phillips", "Roberts",
    "Wright", "White", "Turner", "Brooks", "Parker", "Campbell", "Stewart",
    "Bennett", "Reed", "Morgan", "Cook", "Howard", "Foster", "Myers", "Ward",
    "Sanders", "Patel", "Nguyen", "Flores", "Kim", "Torres", "Murphy",
    "Alvarez", "Price", "Hughes", "Sanchez", "Ramirez", "Gray", "Wood",
    "Watson", "Hill", "Peterson", "Kelly", "Cooper", "Evans", "Rivera",
    "Diaz", "Gomez", "Edwards", "Ortiz", "Reyes", "Mendoza", "Carter",
]

SSA_NAMES_ZIP_URL = "https://www.ssa.gov/oact/babynames/names.zip"


def clean_name(value: str) -> str:
    """Normalize raw name strings from external sources."""
    cleaned = value.strip().replace("\ufeff", "")
    # Drop obvious decode artifacts from mixed encodings.
    if "�" in cleaned:
        return ""
    return cleaned


def fetch_ssa_top_first_names(limit: int, sex: str = "all") -> List[str]:
    """
    Download SSA baby-name data and return top first names by total count.
    sex can be: 'all', 'M', or 'F'.
    """
    if limit <= 0:
        raise ValueError("limit must be > 0")
    normalized_sex = sex.upper()
    if normalized_sex not in {"ALL", "M", "F"}:
        raise ValueError("sex must be one of: all, M, F")

    request = urllib.request.Request(
        SSA_NAMES_ZIP_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            )
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            "Could not download SSA names (HTTP error). "
            "Try --first-names-source local or rerun later."
        ) from exc

    # Aggregate counts across all years before ranking.
    counts: Counter[str] = Counter()
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        for info in zf.infolist():
            if not info.filename.startswith("yob") or not info.filename.endswith(".txt"):
                continue
            with zf.open(info.filename) as f:
                for line in f:
                    name, row_sex, count = line.decode("utf-8").strip().split(",")
                    if normalized_sex != "ALL" and row_sex != normalized_sex:
                        continue
                    cleaned = clean_name(name)
                    if cleaned:
                        counts[cleaned] += int(count)

    # Return names sorted by popularity (highest total count first).
    return [name for name, _ in counts.most_common(limit)]


def fetch_first_names_from_url(url: str, limit: int) -> List[str]:
    """
    Download first names from a public URL.
    Supported formats:
    - .txt: one name per line
    - .csv: uses 'name' column if present, otherwise first column
    """
    if limit <= 0:
        raise ValueError("limit must be > 0")
    if not url:
        raise ValueError("url must be non-empty")

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
    text = raw.decode("utf-8", errors="replace")

    # Parse names from either plain text or CSV.
    names: List[str] = []
    if url.lower().endswith(".txt"):
        for line in text.splitlines():
            name = clean_name(line)
            if name:
                names.append(name)
    else:
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames:
            lowered = {name.lower(): name for name in reader.fieldnames}
            if "name" in lowered:
                key = lowered["name"]
                for row in reader:
                    value = clean_name(row.get(key) or "")
                    if value:
                        names.append(value)
            else:
                first_col = reader.fieldnames[0]
                for row in reader:
                    value = clean_name(row.get(first_col) or "")
                    if value:
                        names.append(value)
        else:
            # Fallback: treat as plain lines if CSV headers are missing.
            for line in text.splitlines():
                value = clean_name(line.split(",")[0])
                if value:
                    names.append(value)

    # Preserve source order while removing duplicates.
    deduped = list(dict.fromkeys(names))
    return deduped[:limit]


def fetch_first_names_from_files(file_paths: Sequence[str], limit: int) -> List[str]:
    """Load first names from local .txt/.csv files."""
    if limit <= 0:
        raise ValueError("limit must be > 0")
    if not file_paths:
        raise ValueError("Provide at least one local file path.")

    # Merge all names from all provided local files.
    names: List[str] = []
    for path in file_paths:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()

        # Handle simple one-name-per-line files (your Ontario files match this).
        if "," not in text:
            for line in text.splitlines():
                value = clean_name(line)
                if value:
                    names.append(value)
            continue

        # CSV parsing path.
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames:
            lowered = {name.lower(): name for name in reader.fieldnames}
            if "name" in lowered:
                key = lowered["name"]
                for row in reader:
                    value = clean_name(row.get(key) or "")
                    if value:
                        names.append(value)
            else:
                first_col = reader.fieldnames[0]
                for row in reader:
                    value = clean_name(row.get(first_col) or "")
                    if value:
                        names.append(value)
        else:
            for line in text.splitlines():
                value = clean_name(line.split(",")[0])
                if value:
                    names.append(value)

    # Preserve source order while removing duplicates.
    deduped = list(dict.fromkeys(names))
    return deduped[:limit]


def build_name_pool(
    pool_size: int, rng: random.Random, first_names: Sequence[str]
) -> List[str]:
    """Create a pool of unique full names."""
    if pool_size <= 0:
        raise ValueError("pool_size must be > 0")
    max_unique = len(first_names) * len(COMMON_LAST_NAMES)
    if pool_size > max_unique:
        raise ValueError(f"pool_size too large; max unique names is {max_unique}")

    # Build all possible "First Last" combinations, then sample K of them.
    # This ensures each generated pool has unique names.
    all_combinations = [
        f"{first} {last}"
        for first in first_names
        for last in COMMON_LAST_NAMES
    ]
    return rng.sample(all_combinations, pool_size)


def parse_between(sequence: Sequence[str], left: str, right: str) -> str:
    """
    Return the single item found directly between left and right.
    Expects exactly one unique in-between value across all left ? right matches.
    """
    # Find all names that appear in the middle of left ? right.
    candidates = {
        sequence[i + 1]
        for i in range(len(sequence) - 2)
        if sequence[i] == left and sequence[i + 2] == right
    }
    if not candidates:
        raise ValueError("No match found for left ? right pattern.")
    if len(candidates) != 1:
        raise ValueError("Ambiguous pattern: more than one middle candidate.")
    return next(iter(candidates))


def build_middlematch_example(
    n: int, name_pool: Sequence[str], rng: random.Random
) -> Tuple[List[str], str, str, str]:
    """Generate one N-length example with a guaranteed single answer."""
    if n < 3:
        raise ValueError("n must be at least 3")
    if len(name_pool) < 3:
        raise ValueError("name_pool must contain at least 3 names")

    # Retry a bounded number of times until we find a unique-answer row.
    for _ in range(2000):
        # Start with a random length-N sequence drawn from the K-name pool.
        seq = [rng.choice(name_pool) for _ in range(n)]
        left, middle, right = rng.sample(name_pool, 3)
        idx = rng.randint(0, n - 3)

        # Force at least one left-middle-right occurrence.
        seq[idx] = left
        seq[idx + 1] = middle
        seq[idx + 2] = right

        # Ensure the question has exactly one valid answer.
        answers = {
            seq[i + 1]
            for i in range(n - 2)
            if seq[i] == left and seq[i + 2] == right
        }
        if answers == {middle}:
            return seq, left, right, middle
    raise RuntimeError("Failed to generate a unique MiddleMatch example.")


def generate_dataset(
    count: int,
    n: int,
    k: int,
    seed: int,
    first_names: Sequence[str],
) -> List[dict]:
    # Seeded RNG makes runs reproducible.
    rng = random.Random(seed)
    rows: List[dict] = []

    for example_id in range(1, count + 1):
        # Use a fresh K-sized pool per row to increase diversity.
        pool = build_name_pool(k, rng, first_names)
        seq, left, right, answer = build_middlematch_example(n, pool, rng)
        list_text = ", ".join(seq)
        prompt = (
            f"Here is a list of names: {list_text}\n\n"
            f"What is the single name that appears right between {left} and {right}?"
        )
        # Store both structured fields and a ready-to-use natural-language prompt.
        rows.append(
            {
                "id": example_id,
                "task": "middlematch",
                "n": n,
                "k": k,
                "name_pool": pool,
                "sequence": seq,
                "left": left,
                "right": right,
                "prompt": prompt,
                "answer": answer,
            }
        )
    return rows


def write_jsonl(path: str, rows: List[dict]) -> None:
    """Write one JSON object per line (JSONL format)."""
    # JSONL = one JSON object per line, easy for training/eval pipelines.
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    # CLI entrypoint: parse args, choose name source, generate rows, write file.
    parser = argparse.ArgumentParser(
        description="Generate MiddleMatch dataset (find item between two names)."
    )
    parser.add_argument("--count", type=int, default=1000, help="Number of rows.")
    parser.add_argument("--n", type=int, default=40, help="Sequence length N.")
    parser.add_argument("--k", type=int, default=10, help="Pool size K.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument("--out", default="middlemarch.jsonl", help="Output JSONL path.")
    parser.add_argument(
        "--first-names-source",
        choices=["local", "ssa", "url", "files"],
        default="local",
        help="Source for first names: local list, SSA, URL file, or local files.",
    )
    parser.add_argument(
        "--ssa-sex",
        choices=["all", "M", "F"],
        default="all",
        help="When using SSA source, filter by sex bucket.",
    )
    parser.add_argument(
        "--ssa-limit",
        type=int,
        default=300,
        help="How many top SSA first names to pull before random pairing.",
    )
    parser.add_argument(
        "--first-names-url",
        default="",
        help="Public URL to a .txt or .csv file of first names (used when source=url).",
    )
    parser.add_argument(
        "--first-names-files",
        nargs="+",
        default=[],
        help="One or more local .txt/.csv files (used when source=files).",
    )
    args = parser.parse_args()

    if args.count <= 0:
        raise ValueError("--count must be > 0")
    if args.n < 3:
        raise ValueError("--n must be at least 3")
    if args.k < 3:
        raise ValueError("--k must be at least 3")

    # Select where first names come from.
    first_names = list(COMMON_FIRST_NAMES)
    if args.first_names_source == "ssa":
        first_names = fetch_ssa_top_first_names(args.ssa_limit, args.ssa_sex)
        if len(first_names) < 3:
            raise RuntimeError("SSA source returned too few first names.")
    if args.first_names_source == "url":
        first_names = fetch_first_names_from_url(args.first_names_url, args.ssa_limit)
        if len(first_names) < 3:
            raise RuntimeError("URL source returned too few first names.")
    if args.first_names_source == "files":
        first_names = fetch_first_names_from_files(args.first_names_files, args.ssa_limit)
        if len(first_names) < 3:
            raise RuntimeError("Local files source returned too few first names.")

    # Build dataset and save it.
    rows = generate_dataset(args.count, args.n, args.k, args.seed, first_names)
    write_jsonl(args.out, rows)
    print(f"Wrote {len(rows)} rows to {args.out} with N={args.n}, K={args.k}")
    print(f"Sample row name pool ({len(rows[0]['name_pool'])}): {', '.join(rows[0]['name_pool'])}")

    sample = rows[0]
    parsed = parse_between(sample["sequence"], sample["left"], sample["right"])
    print(
        f"Parser check: between '{sample['left']}' and '{sample['right']}' -> "
        f"'{parsed}' (expected '{sample['answer']}')"
    )


if __name__ == "__main__":
    main()
