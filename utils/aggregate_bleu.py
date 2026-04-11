"""
Corpus-level BLEU aggregator for the k6net6lke MT benchmark.

Reads pairs of (reference, hypothesis) text files — already normalized by
``normalize_asr_text.py`` — and reports per-file BLEU plus corpus-level
BLEU and chrF. The corpus-level number is what sacreBLEU and every
public MT leaderboard report; the per-file macro average used by the
legacy ``MTeval --simple`` pipeline is inappropriate for small test
sets with heterogeneous file lengths.

Each file's lines are joined with a space and passed to sacreBLEU as a
single "sentence". ``sacrebleu.corpus_bleu`` is then called with the
collected system and reference lists. This deliberately bypasses
segment-level alignment via mwerSegmenter: BLEU is an n-gram overlap
metric, so concatenating segments loses no information as long as the
concatenation is consistent across system and reference.

Usage:
    python3 aggregate_bleu.py \
        --ref data/et/foo.en.OSt --hyp outputs/et/mt/baz/foo.et.en.mt \
        --ref data/et/bar.en.OSt --hyp outputs/et/mt/baz/bar.et.en.mt \
        ...
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import sacrebleu  # type: ignore
except ImportError as e:  # pragma: no cover
    sys.stderr.write(
        "aggregate_bleu.py requires sacrebleu. Install with: pip install sacrebleu\n"
    )
    raise SystemExit(2) from e


def _load(path: Path) -> str:
    with open(path, encoding="utf-8") as f:
        return " ".join(line.strip() for line in f if line.strip())


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Corpus-level BLEU over pairs of reference/hypothesis files."
    )
    parser.add_argument(
        "--ref", action="append", required=True,
        help="Reference file path (repeatable).",
    )
    parser.add_argument(
        "--hyp", action="append", required=True,
        help="Hypothesis file path (repeatable, must match --ref order).",
    )
    parser.add_argument(
        "--tokenizer", default="13a",
        help="sacreBLEU tokenizer (default: 13a, matches SLTev legacy mode).",
    )
    parser.add_argument(
        "--lowercase", action="store_true",
        help="Pass lowercase=True to sacreBLEU in addition to any lowercasing done by the normalizer.",
    )
    args = parser.parse_args(argv)

    if len(args.ref) != len(args.hyp):
        sys.stderr.write(
            f"--ref ({len(args.ref)}) and --hyp ({len(args.hyp)}) count mismatch\n"
        )
        return 2

    hyps: list[str] = []
    refs: list[str] = []
    print("file\thyp_words\tref_words\tBLEU")
    per_file_bleu: list[float] = []
    for ref_s, hyp_s in zip(args.ref, args.hyp):
        ref_p = Path(ref_s)
        hyp_p = Path(hyp_s)
        ref_text = _load(ref_p)
        hyp_text = _load(hyp_p)
        refs.append(ref_text)
        hyps.append(hyp_text)
        # Per-file BLEU for diagnostics only.
        per = sacrebleu.corpus_bleu(
            [hyp_text], [[ref_text]],
            tokenize=args.tokenizer, lowercase=args.lowercase, force=True,
        )
        per_file_bleu.append(per.score)
        print(f"{ref_p.name}\t{len(hyp_text.split())}\t{len(ref_text.split())}\t{per.score:.2f}")

    bleu = sacrebleu.corpus_bleu(
        hyps, [refs], tokenize=args.tokenizer, lowercase=args.lowercase, force=True,
    )
    chrf = sacrebleu.corpus_chrf(hyps, [refs])

    macro = sum(per_file_bleu) / len(per_file_bleu) if per_file_bleu else 0.0

    print()
    print(f"files          : {len(args.ref)}")
    print(f"tokenizer      : {args.tokenizer}  lowercase={args.lowercase}")
    print(f"macro BLEU     : {macro:.2f}   (unweighted mean of per-file BLEU)")
    print(f"corpus BLEU    : {bleu.score:.2f}   (sacreBLEU standard)")
    print(f"corpus chrF    : {chrf.score:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
