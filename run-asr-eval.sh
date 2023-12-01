#!/bin/bash

# Begin configuration section.

refdir=data/et
source=et

. ./utils/parse_options.sh

if [ $# -ne 1 ]; then
  echo "Usage: $0 --refdir <dir-with-reference-OSt-files> --source <source_lang> --target <target_lang> <dir-with-output-files-from-asr>"
  echo "E.g.: $0 outputs/et/mt/outputs/et/mt/whisper-large-v2"
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


# Interleave arrays
interleaved=()
for i in "${!arr1[@]}"; do
    interleaved+=("${arr1[$i]}" "${arr2[$i]}")
done

# Convert interleaved array to string
interleaved_string="${interleaved[@]}"


ASReval -i $interleaved_string -f asr ost --simple | tee /dev/stderr | grep LPW | awk '{sum+=$2} END {print("\n\nAverage WER: ", sum/NR)}'
