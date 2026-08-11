# Gemini 3 Flash Preview ASR on Estonian benchmark

This note compares `google/gemini-3-flash-preview` via OpenRouter with the
existing Estonian Whisper ASR baselines.

## Setup

* Date: 2026-06-01
* Model: `google/gemini-3-flash-preview`
* Output directory:
  `outputs/et/asr/gemini-3-flash-preview-openrouter`
* Evaluation command:
  `./run-asr-eval.sh --refdir data/et --source et outputs/et/asr/<system>`
* Metric: normalized benchmark WER. The benchmark normalizer lowercases text,
  expands numbers and units, converts punctuation to spaces, and reports a
  single micro-averaged WER (sum of edits / sum of reference words).

All requests used the whole audio file as a single OpenRouter `input_audio`
message. Five files were sent as the source FLAC. Two files repeatedly failed
as whole-FLAC OpenRouter requests with upstream 502/504 errors, so they were
sent as whole-audio mono 16 kHz 64 kbps MP3 transcodes:

* `16.12.2020_-_Tallinna_Linnavalitsuse_kolmapäevane_pressikonverents-dGJ9HSmZR8A`
* `Valitsuse_pressikonverents__15._oktoober_2020-dJypQ9rLypU`

Those two inputs were still single-request, whole-audio inputs, not chunks.

## WER summary

| System | WER | S | D | I | Ref words |
|---|---:|---:|---:|---:|---:|
| Gemini 3 Flash Preview via OpenRouter | 11.08 | 1689 | 898 | 520 | 28044 |
| Whisper-medium-et-orthographic | 8.80 | 1320 | 592 | 557 | 28044 |
| Whisper-large-v3-et-orthographic | 7.62 | 1236 | 399 | 501 | 28044 |

Gemini is 2.28 absolute WER points behind Whisper medium and 3.46 points behind
Whisper large-v3 on normalized WER.

## Per-file WER

| File | Gemini | Whisper medium | Whisper large-v3 |
|---|---:|---:|---:|
| `16.12.2020_-_Tallinna_Linnavalitsuse_kolmapäevane_pressikonverents-dGJ9HSmZR8A` | 7.63 | 4.17 | 4.21 |
| `Valitsuse_pressikonverents__15._oktoober_2020-dJypQ9rLypU` | 10.65 | 8.32 | 6.91 |
| `aktuaalne-kaamera-ilm-1001-317793` | 7.68 | 7.26 | 5.84 |
| `aktuaalne-kaamera-ilm-1222-327710` | 7.68 | 5.22 | 5.14 |
| `aktuaalne-kaamera-ilm-nadal-322248` | 7.31 | 7.85 | 6.06 |
| `ringvaade-2033-320571` | 17.68 | 14.09 | 12.78 |
| `ringvaade-2071-326938` | 16.85 | 12.11 | 10.83 |

Gemini is closest to Whisper on `aktuaalne-kaamera-ilm-nadal-322248`, where it
beats Whisper medium but remains behind Whisper large-v3. The largest gaps are
on the two `ringvaade` files and the long government press conference.

## Error profile

### 1. Gemini makes many more deletions

Gemini's extra errors relative to Whisper large-v3 are mostly deletions and
substitutions:

| Difference vs Whisper large-v3 | Extra errors |
|---|---:|
| Substitutions | +453 |
| Deletions | +499 |
| Insertions | +19 |

Normalized token balance points in the same direction:

| System | Hyp words | Ref words | Hyp - ref |
|---|---:|---:|---:|
| Gemini | 27666 | 28044 | -378 |
| Whisper medium | 28009 | 28044 | -35 |
| Whisper large-v3 | 28146 | 28044 | +102 |

Gemini is not mainly worse because it hallucinates extra words. Insertions are
about the same as Whisper large-v3. It is worse because it omits more reference
words and misrecognizes more words.

The deletion issue is visible in multi-word deletion spans. Gemini has 90
multi-word deletion spans totaling 329 deleted reference words. Whisper large-v3
has 37 such spans totaling 109 words. Examples from Gemini's normalized
alignment include:

* `kaksikute ema koos lastega ära läinud ... kolmekümneaastaselt seisis madis`
* `siis mingil hetkel sündis veel poeg ... tulin ma üks õhtu töölt koju siis`
* `karl margus ja karl markus nii sarnased nimed ...`

The `ringvaade` files contain 28.9% of the reference words but 44.9% of
Gemini's total edits, so conversational studio material is a clear weak point.

### 2. It is partly non-orthographic around numbers

The benchmark normalizer removes most punctuation, case, hyphen, and digit-vs-
word formatting differences. Even after that normalization, Gemini has many
more number-related substitutions:

| System | Number-like substitutions | Share of substitutions | Share of all edits |
|---|---:|---:|---:|
| Gemini | 271 | 16.0% | 8.7% |
| Whisper medium | 48 | 3.6% | 1.9% |
| Whisper large-v3 | 35 | 2.8% | 1.6% |

Raw output also shows the style difference:

| Text source | Digit-containing raw tokens |
|---|---:|
| Reference transcripts | 5 |
| Gemini | 377 |
| Whisper medium | 3 |
| Whisper large-v3 | 3 |

The common Gemini number substitutions are mostly Estonian case/inflection
mismatches caused by inverse text normalization:

| Reference | Gemini after normalization | Count |
|---|---|---:|
| `tuhande` | `tuhat` | 15 |
| `kahekümne` | `kakskümmend` | 12 |
| `kahe` | `kaks` | 11 |
| `saja` | `sada` | 9 |
| `ühe` | `üks` | 8 |
| `viie` | `viis` | 7 |

So yes, part of Gemini's gap is orthographic/ITN style: it tends to output
digits, while this benchmark's Estonian ASR references are orthographic and
usually spell numbers as inflected words. The fair normalizer helps, but it
does not recover Estonian case from digit forms. For example, a raw digit may
normalize to nominative `kakskümmend`, while the reference has genitive
`kahekümne`.

This is not the same as punctuation or capitalization. Those are normalized
away and do not explain the WER gap.

### 3. Substitutions are also more common outside numbers

Gemini has 1689 substitutions vs 1236 for Whisper large-v3. Apart from number
inflection, common examples include discourse/filler and inflection variants:

* `noh` vs `no`
* `meie` vs `me`
* `ja` vs `jah`
* `neid` vs `need`
* `siis` vs `see`

These are ordinary ASR confusions and conversational-style mismatches. They are
more frequent on the `ringvaade` files than on the news/weather files.

## Conclusion

Gemini 3 Flash Preview is usable on these Estonian long-form files, but it is
not competitive with the Estonian Whisper baselines in this benchmark. The
main gap is:

1. More omissions, especially in conversational `ringvaade` material.
2. More substitutions.
3. A strong non-orthographic number style that produces digit output and then
   case/inflection mismatches after benchmark normalization.

It is not primarily a punctuation/capitalization issue, and it is not mainly an
insertion or hallucination problem.
