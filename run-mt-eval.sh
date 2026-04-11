#!/bin/bash

# Begin configuration section.

refdir=data/et
source=et
target=en
normalize=true   # apply fair normalization (see BENCHMARK_ISSUES.md)

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. ${__dir}/utils/parse_options.sh

if [ $# -ne 1 ]; then
  echo "Usage: $0 --refdir <dir-with-reference-OSt-files> --source <source_lang> --target <target_lang> [--normalize true|false] <dir-with-MT-output-files>"
  echo "E.g.: $0 --target en outputs/et/mt/whisper-large-v2"
  echo
  echo "  --normalize true  (default) applies the fair normalization pipeline"
  echo "                    described in BENCHMARK_ISSUES.md (spells digits"
  echo "                    out in words for et/ru, uses Whisper's canonical"
  echo "                    form for en, fixes punctuation, strips Unicode"
  echo "                    quotes) and reports corpus-level sacreBLEU+chrF."
  echo "  --normalize false reproduces the original MTeval --simple pipeline"
  echo "                    with macro-averaged per-file sacreBLEU. Use for"
  echo "                    backwards-compatible comparisons with old results."
  exit 1;
fi

mtdir=$1

set -e # exit on error

ref_files=${refdir}/*.${target}.OSt

basenames=()
for file in $ref_files; do
    basenames+=($(basename "$file" .${target}.OSt ))
done

mt_files=$(for basename in "${basenames[@]}"; do ls ${mtdir}/${basename}.${source}.${target}.mt; done)

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
    base1="$(basename "${arr1[$i]}" .${source}.${target}.mt )"
    base2="$(basename "${arr2[$i]}" .${target}.OSt )"
    if [ "$base1" != "$base2" ]; then
        echo "Basename mismatch: $base1 vs $base2"
        exit 1
    fi
done

if [ "$normalize" = "false" ]; then
    # ------------------------------------------------------------------
    # Legacy path: MTeval --simple + macro-averaged per-file sacreBLEU.
    # Kept so old RESULTS.md numbers can be reproduced. See
    # BENCHMARK_ISSUES.md for why this is not the recommended mode.
    # ------------------------------------------------------------------
    interleaved=()
    for i in "${!arr1[@]}"; do
        interleaved+=("${arr1[$i]}" "${arr2[$i]}")
    done
    interleaved_string="${interleaved[@]}"

    SCRATCH=$(mktemp -t tmp.XXXXXXXXXX)
    MTeval -i $interleaved_string -f mt ref --simple > $SCRATCH

    cat $SCRATCH > /dev/stderr
    cat $SCRATCH > ${mtdir}/${source}.${target}.results.txt

    # NB: the original pipeline used `awk '{sum+=$4}' ... sum/NR` which
    # silently returns 0 under locales with comma decimal separator
    # (e.g. et_EE). We use a tiny Python aggregator so the legacy numbers
    # are actually reproducible on any locale.
    python3 -c '
import sys
vals = []
for line in sys.stdin:
    parts = line.split()
    if len(parts) >= 4 and parts[1] == "sacreBLEU":
        try:
            vals.append(float(parts[3]))
        except ValueError:
            pass
if vals:
    print()
    print(f"Average BLEU (legacy macro): {sum(vals)/len(vals):.3f}")
else:
    print("No sacreBLEU lines found")
' < $SCRATCH | tee -a ${mtdir}/${source}.${target}.results.txt
    exit 0
fi

# ----------------------------------------------------------------------
# Fair path: normalize both sides and compute corpus-level sacreBLEU.
# ----------------------------------------------------------------------

workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

normalizer="${__dir}/utils/normalize_asr_text.py"
aggregator="${__dir}/utils/aggregate_bleu.py"

# Collect all (input, output) pairs so we can run the normalizer ONCE per
# language pair (English path loads Whisper's EnglishTextNormalizer which
# takes ~2s; don't pay that cost per file).
ref_norm_args=()
hyp_norm_args=()
normalize_cmd=(python3 "$normalizer" --lang "$target")

for i in "${!arr1[@]}"; do
    hyp_in="${arr1[$i]}"
    ref_in="${arr2[$i]}"
    base="$(basename "$hyp_in" .${source}.${target}.mt)"
    hyp_out="$workdir/$base.hyp"
    ref_out="$workdir/$base.ref"
    # Reference is in the TARGET language; hypothesis is the MT output,
    # also in the target language. Both pass through the same normalizer.
    normalize_cmd+=(--in "$hyp_in" --out "$hyp_out" --in "$ref_in" --out "$ref_out")
    ref_norm_args+=(--ref "$ref_out")
    hyp_norm_args+=(--hyp "$hyp_out")
done

"${normalize_cmd[@]}"

python3 "$aggregator" "${ref_norm_args[@]}" "${hyp_norm_args[@]}" \
  | tee ${mtdir}/${source}.${target}.results.txt
