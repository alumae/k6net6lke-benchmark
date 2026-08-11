"""
Shared mwerSegmenter alignment helpers for the k6net6lke MT benchmark.

Both BLEU and BLEURT must be computed over *segments*, not over whole
concatenated documents, and both must use the *same* segmentation or the
two metrics stop describing the same thing. This module is the single
implementation both aggregators call.

MT systems do not have to reproduce the reference's sentence boundaries:
a system may merge two reference sentences into one line or split one into
three. mwerSegmenter re-flows the hypothesis token stream onto the
reference's segment boundaries by minimising word error rate, which is the
same aligner SLTev uses internally for `calc_bleu_score_segmenterlevel`.
The result is a hypothesis list with exactly one entry per reference
segment, so scoring is well defined.

The binary ships with SLTev (`pip install SLTev`); it is also picked up
from PATH if installed separately.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path


def find_mwersegmenter() -> str:
    # Prefer the binary shipped with SLTev — it's where everything else here
    # gets it from, and avoids a second install step.
    try:
        import SLTev  # type: ignore

        candidate = Path(SLTev.__file__).parent / "mwerSegmenter"
        if candidate.exists():
            return str(candidate)
    except ImportError:
        pass
    for p in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(p) / "mwerSegmenter"
        if candidate.exists():
            return str(candidate)
    raise RuntimeError(
        "mwerSegmenter binary not found. Install SLTev (`pip install SLTev`) "
        "so the bundled binary is available, or place it on PATH."
    )


def align_with_mwersegmenter(
    ref_lines: list[str], hyp_lines: list[str]
) -> list[str]:
    """Return a list of `len(ref_lines)` hypothesis strings, each aligned
    to the corresponding reference sentence.
    """
    if not ref_lines:
        return []
    # If both sides already have the same line count, skip the binary and
    # just trust the line-parallel structure. This is the common case for
    # systems (like NLLB) that respect reference segmentation.
    if len(ref_lines) == len(hyp_lines):
        return hyp_lines

    mwer = find_mwersegmenter()
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        ref_path = tdp / "temp_ref"
        hyp_path = tdp / "temp_translate"
        ref_path.write_text("\n".join(ref_lines) + "\n", encoding="utf-8")
        hyp_path.write_text("\n".join(hyp_lines) + "\n", encoding="utf-8")
        # mwerSegmenter writes __segments to the CURRENT directory.
        subprocess.run(
            [mwer, "-mref", "temp_ref", "-hypfile", "temp_translate"],
            cwd=str(tdp),
            check=True,
            capture_output=True,
        )
        segments = (tdp / "__segments").read_text(encoding="utf-8").splitlines()
    # Pad / truncate defensively so count matches ref.
    if len(segments) < len(ref_lines):
        segments = segments + [""] * (len(ref_lines) - len(segments))
    return segments[: len(ref_lines)]


def load_lines(path: Path) -> list[str]:
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if s:
            lines.append(s)
    return lines
