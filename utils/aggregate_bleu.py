"""
Corpus-level BLEU aggregator for the k6net6lke MT benchmark.

Reads pairs of (reference, hypothesis) text files — already normalized by
``normalize_asr_text.py`` — and reports per-file BLEU plus corpus-level
BLEU and chrF.

Two things matter for the corpus number to be comparable to published
scores, and this script does both:

1. **Pool, don't average.** BLEU is a ratio of summed clipped n-gram
   matches to summed candidate n-grams, with a corpus-level brevity
   penalty. It is not linear in the per-file scores, so the unweighted
   mean of per-file BLEU is not a BLEU of anything. The macro average is
   still printed, but only as a diagnostic, and it is labelled as such.

2. **Score segments, not documents.** Every file is scored as a list of
   sentence-level segments aligned to the reference segmentation via
   mwerSegmenter (see ``mwer_align.py``), which is exactly what
   ``aggregate_bleurt.py`` already does.

On (2): an earlier version of this script joined each file's lines into a
single string and handed sacreBLEU one "sentence" per document, on the
reasoning that BLEU is an n-gram overlap metric and consistent
concatenation therefore loses no information. That reasoning does not
hold. Modified n-gram precision clips each candidate n-gram count by the
maximum count of that n-gram *in its own reference segment*. Concatenating
a document raises every clip ceiling to the document-wide count, so a
hypothesis n-gram produced in one part of the document can be paid for by
an occurrence anywhere else in the reference. Function words and common
collocations stop being constrained by position at all.

The effect is not academic. Measured on EN→ET over the six baseline
systems in this repo, document-level scoring inflates corpus BLEU by
+4.05 to +4.87 points. The inflation is systematic but not uniform: the
0.8-point spread between systems is larger than the gap that separates
several adjacent entries on this benchmark, so document-level scoring can
reorder systems that segment-level scoring separates (it does not happen
to reorder these six). chrF degrades far more sharply than BLEU — deepl
EN→ET reads 72.43 concatenated versus 50.14 segmented — because character
n-grams over a single document-length string match almost everything.

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mwer_align import align_with_mwersegmenter, load_lines  # noqa: E402

try:
    import sacrebleu  # type: ignore
except ImportError as e:  # pragma: no cover
    sys.stderr.write(
        "aggregate_bleu.py requires sacrebleu. Install with: pip install sacrebleu\n"
    )
    raise SystemExit(2) from e


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

    # Pooled across all documents; one entry per reference segment.
    all_hyps: list[str] = []
    all_refs: list[str] = []

    print("file\tsegments\thyp_lines\thyp_words\tref_words\tBLEU")
    per_file_bleu: list[float] = []
    for ref_s, hyp_s in zip(args.ref, args.hyp):
        ref_p = Path(ref_s)
        hyp_p = Path(hyp_s)
        ref_lines = load_lines(ref_p)
        hyp_lines = load_lines(hyp_p)
        # Re-flow the hypothesis onto the reference's segment boundaries so
        # the two sides are segment-parallel regardless of how the system
        # chose to break sentences.
        segs = align_with_mwersegmenter(ref_lines, hyp_lines)

        all_refs.extend(ref_lines)
        all_hyps.extend(segs)

        # Per-file BLEU for diagnostics only — still segment-level.
        per = sacrebleu.corpus_bleu(
            segs, [ref_lines],
            tokenize=args.tokenizer, lowercase=args.lowercase, force=True,
        )
        per_file_bleu.append(per.score)
        ref_words = sum(len(s.split()) for s in ref_lines)
        hyp_words = sum(len(s.split()) for s in segs)
        print(
            f"{ref_p.name}\t{len(ref_lines)}\t{len(hyp_lines)}\t"
            f"{hyp_words}\t{ref_words}\t{per.score:.2f}"
        )

    metric = sacrebleu.metrics.BLEU(
        tokenize=args.tokenizer, lowercase=args.lowercase, force=True
    )
    bleu = metric.corpus_score(all_hyps, [all_refs])
    chrf = sacrebleu.corpus_chrf(all_hyps, [all_refs])

    macro = sum(per_file_bleu) / len(per_file_bleu) if per_file_bleu else 0.0

    print()
    print(f"files          : {len(args.ref)}")
    print(f"segments       : {len(all_refs)}")
    print(f"tokenizer      : {args.tokenizer}  lowercase={args.lowercase}")
    print(f"corpus BLEU    : {bleu.score:.2f}   (sacreBLEU standard, segment-level)")
    print(f"corpus chrF    : {chrf.score:.2f}")
    print(f"macro BLEU     : {macro:.2f}   (unweighted mean of per-file BLEU; diagnostic only, not a corpus statistic)")
    print(f"BLEU signature : {metric.get_signature()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
