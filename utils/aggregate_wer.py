"""
Micro-averaged WER aggregator for the k6net6lke ASR benchmark.

Reads pairs of (reference, hypothesis) text files — already normalized by
``normalize_asr_text.py`` — and reports per-file WER plus the corpus-level
macro- and micro-averages. The micro-average is what Whisper, Kaldi, and
ESPnet leaderboards use by default and is the number you should cite when
comparing systems.

Inputs are whitespace-joined line-by-line (no segment alignment via
mwerSegmenter), then passed to ``jiwer.process_words`` which computes a
word-level Levenshtein alignment over the whole document. This finds the
optimal global alignment, so ASR outputs that differ from the reference's
sentence boundaries are not penalised.

Usage:
    python3 aggregate_wer.py \
        --ref data/et/foo.et.OSt --hyp outputs/et/asr/baz/foo.et.asr \
        --ref data/et/bar.et.OSt --hyp outputs/et/asr/baz/bar.et.asr \
        ...
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import jiwer  # type: ignore
except ImportError as e:  # pragma: no cover
    sys.stderr.write(
        "aggregate_wer.py requires jiwer. Install with: pip install jiwer\n"
    )
    raise SystemExit(2) from e


def _load(path: Path) -> str:
    with open(path, encoding="utf-8") as f:
        return " ".join(line.strip() for line in f if line.strip())


def _score_pair(ref_path: Path, hyp_path: Path) -> tuple[int, int, int, int, int]:
    """Return (ref_words, substitutions, deletions, insertions, hits)."""
    ref = _load(ref_path)
    hyp = _load(hyp_path)
    # jiwer needs at least one word on the reference side.
    if not ref:
        return (0, 0, 0, len(hyp.split()), 0)
    out = jiwer.process_words(ref, hyp)
    ref_words = out.hits + out.substitutions + out.deletions
    return (ref_words, out.substitutions, out.deletions, out.insertions, out.hits)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Micro-averaged WER over pairs of reference/hypothesis files."
    )
    parser.add_argument(
        "--ref", action="append", required=True,
        help="Reference file path (repeatable).",
    )
    parser.add_argument(
        "--hyp", action="append", required=True,
        help="Hypothesis file path (repeatable, must match --ref order).",
    )
    args = parser.parse_args(argv)

    if len(args.ref) != len(args.hyp):
        sys.stderr.write(
            f"--ref ({len(args.ref)}) and --hyp ({len(args.hyp)}) count mismatch\n"
        )
        return 2

    total_ref = 0
    total_sub = 0
    total_del = 0
    total_ins = 0
    per_file_wers: list[float] = []

    print("file\tref_words\tS\tD\tI\tWER")
    for ref_s, hyp_s in zip(args.ref, args.hyp):
        ref_p = Path(ref_s)
        hyp_p = Path(hyp_s)
        ref_words, s, d, i, h = _score_pair(ref_p, hyp_p)
        edits = s + d + i
        wer = edits / ref_words if ref_words else float("inf")
        per_file_wers.append(wer)
        total_ref += ref_words
        total_sub += s
        total_del += d
        total_ins += i
        print(f"{ref_p.name}\t{ref_words}\t{s}\t{d}\t{i}\t{wer:.4f}")

    total_edits = total_sub + total_del + total_ins
    micro = total_edits / total_ref if total_ref else float("inf")
    macro = sum(per_file_wers) / len(per_file_wers) if per_file_wers else float("inf")

    print()
    print(f"files          : {len(args.ref)}")
    print(f"total ref words: {total_ref}")
    print(f"total S/D/I    : {total_sub}/{total_del}/{total_ins}  "
          f"(edits={total_edits})")
    print(f"macro WER      : {macro * 100:.2f}   (unweighted mean of per-file WER)")
    print(f"micro WER      : {micro * 100:.2f}   (sum edits / sum ref words)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
