"""
BLEURT-20 aggregator for the k6net6lke MT benchmark.

Reads pairs of pre-normalized (reference, hypothesis) text files and
reports per-file and corpus-level BLEURT-20 means. Both files must have
one sentence per line; the hypothesis is re-segmented to the reference's
sentence boundaries via mwerSegmenter (the same aligner used internally
by SLTev's `calc_bleu_score_segmenterlevel`) so per-pair BLEURT is
meaningful even when systems use different segmentations.

Requires a Python environment with:
    - torch
    - transformers>=4.40,<5   (bleurt-pytorch is incompatible with 5.x)
    - bleurt-pytorch

Point at a venv with those installed via BLEURT_PYTHON=/path/to/python.
The repo conventionally uses ~/.venvs/bleurt — see README.md for setup.

mwerSegmenter is located automatically from the SLTev package install.

Usage (called from run-mt-eval.sh):
    python3 aggregate_bleurt.py \
        --ref <normalized_ref_1> --hyp <normalized_hyp_1> \
        --ref <normalized_ref_2> --hyp <normalized_hyp_2> \
        ...
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mwer_align import align_with_mwersegmenter, load_lines  # noqa: E402


# -------- BLEURT imports (lazy-loaded so --help doesn't pay the cost) -------


def _load_bleurt(model_name: str = "lucadiliello/BLEURT-20"):
    import torch  # type: ignore
    from bleurt_pytorch import BleurtForSequenceClassification  # type: ignore
    from bleurt_pytorch.bleurt.tokenization_bleurt_sp import BleurtSPTokenizer  # type: ignore

    tok = BleurtSPTokenizer.from_pretrained(model_name)
    model = BleurtForSequenceClassification.from_pretrained(model_name).eval()
    if torch.cuda.is_available():
        model = model.cuda()
    return model, tok, torch


# --------------------------- BLEURT scoring core ---------------------------


def _score_all(
    model,
    tok,
    torch_mod,
    ref_lines: list[str],
    hyp_lines: list[str],
    batch_size: int,
    max_length: int,
) -> list[float]:
    """Score ref-hyp pairs in batches, GPU-accelerated."""
    scores: list[float] = []
    for start in range(0, len(ref_lines), batch_size):
        batch_refs = ref_lines[start : start + batch_size]
        batch_hyps = hyp_lines[start : start + batch_size]
        enc = tok(
            batch_refs,
            batch_hyps,
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt",
        )
        if torch_mod.cuda.is_available():
            enc = {k: v.cuda() for k, v in enc.items()}
        with torch_mod.no_grad():
            out = model(**enc).logits.flatten().tolist()
        scores.extend(out)
    return scores


# ------------------------------- CLI ---------------------------------------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Corpus-level BLEURT-20 over pairs of reference/hypothesis files."
    )
    parser.add_argument(
        "--ref", action="append", required=True,
        help="Normalized reference file path (repeatable).",
    )
    parser.add_argument(
        "--hyp", action="append", required=True,
        help="Normalized hypothesis file path (repeatable, must match --ref order).",
    )
    parser.add_argument(
        "--model", default="lucadiliello/BLEURT-20",
        help="HuggingFace BLEURT checkpoint (default: full BLEURT-20).",
    )
    parser.add_argument(
        "--batch-size", type=int, default=32,
        help="Batch size per forward pass.",
    )
    parser.add_argument(
        "--max-length", type=int, default=512,
        help="Maximum token length for each ref/hyp pair.",
    )
    args = parser.parse_args(argv)

    if len(args.ref) != len(args.hyp):
        sys.stderr.write(
            f"--ref ({len(args.ref)}) and --hyp ({len(args.hyp)}) count mismatch\n"
        )
        return 2

    model, tok, torch_mod = _load_bleurt(args.model)

    all_scores: list[float] = []
    print("file\tn_pairs\tmean_bleurt")
    for ref_s, hyp_s in zip(args.ref, args.hyp):
        ref_path = Path(ref_s)
        hyp_path = Path(hyp_s)
        ref_lines = load_lines(ref_path)
        hyp_lines = load_lines(hyp_path)
        # Align hypothesis to reference sentence boundaries.
        aligned_hyp = align_with_mwersegmenter(ref_lines, hyp_lines)
        # Drop pairs where either side is empty post-alignment.
        pairs = [
            (r, h) for r, h in zip(ref_lines, aligned_hyp) if r.strip() and h.strip()
        ]
        if not pairs:
            print(f"{ref_path.name}\t0\tnan")
            continue
        ref_batch = [p[0] for p in pairs]
        hyp_batch = [p[1] for p in pairs]
        scores = _score_all(
            model, tok, torch_mod, ref_batch, hyp_batch,
            args.batch_size, args.max_length,
        )
        mean = sum(scores) / len(scores)
        print(f"{ref_path.name}\t{len(pairs)}\t{mean:.4f}")
        all_scores.extend(scores)

    if not all_scores:
        print("\nNo sentence pairs scored.")
        return 1

    corpus_mean = sum(all_scores) / len(all_scores)
    print()
    print(f"files           : {len(args.ref)}")
    print(f"sentence pairs  : {len(all_scores)}")
    print(f"BLEURT model    : {args.model}")
    print(f"corpus BLEURT   : {corpus_mean:.4f}   (mean over all aligned pairs)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
