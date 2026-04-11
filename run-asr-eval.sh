#!/bin/bash

# Begin configuration section.

refdir=data/et
source=et
normalize=true   # apply fair normalization (see BENCHMARK_ISSUES.md)

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. ${__dir}/utils/parse_options.sh

if [ $# -ne 1 ]; then
  echo "Usage: $0 --refdir <dir-with-reference-OSt-files> --source <source_lang> [--normalize true|false] <dir-with-output-files-from-asr>"
  echo "E.g.: $0 outputs/et/asr/whisper-large-v3-et-orthographic"
  echo
  echo "  --normalize true  (default) applies the fair normalization pipeline"
  echo "                    described in BENCHMARK_ISSUES.md (spells digits"
  echo "                    out in words, fixes the hyphen-deletion bug, strips"
  echo "                    Unicode punctuation) and reports micro-averaged WER."
  echo "  --normalize false reproduces the original pipeline (ASReval --simple"
  echo "                    with macro-averaged per-file LPW). Use for"
  echo "                    backwards-compatible comparisons with old results."
  exit 1;
fi

mtdir=$1

set -e # exit on error

mt_files=${mtdir}/*.${source}.asr
ref_files=${refdir}/*.${source}.OSt

# Convert strings to arrays
arr1=($mt_files)
arr2=($ref_files)

# Check if lengths are equal
if [ "${#arr1[@]}" -ne "${#arr2[@]}" ]; then
    echo "Lists are not of equal length."
    exit 1
fi

# Check if basenames (without directories and extensions) are the same
for i in "${!arr1[@]}"; do
    base1="$(basename "${arr1[$i]}" .${source}.asr )"
    base2="$(basename "${arr2[$i]}" .${source}.OSt )"
    if [ "$base1" != "$base2" ]; then
        echo "Basename mismatch: $base1 vs $base2"
        exit 1
    fi
done

if [ "$normalize" = "false" ]; then
    # ------------------------------------------------------------------
    # Legacy path: ASReval --simple + macro-averaged LPW. Kept so old
    # numbers in RESULTS.md can be reproduced. See BENCHMARK_ISSUES.md
    # for why this is not the recommended mode.
    # ------------------------------------------------------------------
    interleaved=()
    for i in "${!arr1[@]}"; do
        interleaved+=("${arr1[$i]}" "${arr2[$i]}")
    done
    interleaved_string="${interleaved[@]}"

    # NB: the original one-liner used `awk '{sum+=$2}' sum/NR` which is
    # broken under locales with comma decimal separator (e.g. et_EE) —
    # awk parses "0.078" as 0 and the average comes out as 0. We use a
    # tiny Python aggregator so the legacy numbers are actually
    # reproducible on any locale.
    ASReval -i $interleaved_string -f asr ost --simple \
      | tee /dev/stderr \
      | python3 -c '
import sys
vals = []
for line in sys.stdin:
    parts = line.split()
    if parts and parts[0] == "LPW" and len(parts) >= 2:
        try:
            vals.append(float(parts[1]))
        except ValueError:
            pass
if vals:
    print()
    print(f"Average WER (legacy macro): {sum(vals)/len(vals)*100:.2f}")
else:
    print("No LPW lines found")
'
    exit 0
fi

# ----------------------------------------------------------------------
# Fair path: normalize both sides and compute micro-averaged WER.
# ----------------------------------------------------------------------

workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

normalizer="${__dir}/utils/normalize_asr_text.py"
aggregator="${__dir}/utils/aggregate_wer.py"

# Collect all (input, output) pairs so we can run the normalizer ONCE per
# language pair (English path loads Whisper's EnglishTextNormalizer which
# takes ~2s; don't pay that cost per file).
ref_norm_args=()
hyp_norm_args=()
normalize_cmd=(python3 "$normalizer" --lang "$source")

for i in "${!arr1[@]}"; do
    hyp_in="${arr1[$i]}"
    ref_in="${arr2[$i]}"
    base="$(basename "$hyp_in" .${source}.asr)"
    hyp_out="$workdir/$base.hyp"
    ref_out="$workdir/$base.ref"
    normalize_cmd+=(--in "$hyp_in" --out "$hyp_out" --in "$ref_in" --out "$ref_out")
    ref_norm_args+=(--ref "$ref_out")
    hyp_norm_args+=(--hyp "$hyp_out")
done

"${normalize_cmd[@]}"

python3 "$aggregator" "${ref_norm_args[@]}" "${hyp_norm_args[@]}"
