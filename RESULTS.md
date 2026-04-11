# Comparison of speech translation systems

Note that some systems use oracle transcriptions and are only listed for reference.

## BLEU scores

Each cell shows `legacy / **fair corpus**` BLEU. **Legacy** is
`./run-mt-eval.sh --normalize false` (sacreBLEU via `MTeval --simple` with
macro-averaged per-file scores, reproducing the pre-fix numbers). **Fair
corpus** is `./run-mt-eval.sh` (the new default): both reference and
hypothesis go through the normalizer in `utils/normalize_asr_text.py`
(Estonian uses a custom cardinal speller, Russian uses `num2words(lang='ru')`,
English uses Whisper's `EnglishTextNormalizer`; Unicode punctuation → space;
NFC; lowercase), then sacreBLEU's `corpus_bleu` with the `13a` tokenizer
is computed over the whole document. This is the number to cite when
comparing systems. See [BENCHMARK_ISSUES.md](BENCHMARK_ISSUES.md) for why
the legacy pipeline was unfair — short version: it penalised systems that
emit numbers in digit form (`55`) against references that spell them out
(`viiskümmend viis` / `fifty-five` / `пятьдесят пять`).

### From Estonian

| Model | et→en | et→ru |
|-------|:-----:|:-----:|
| _Reference transcripts + GPT3.5-turbo_ | 36.1 / **40.9** | 28.3 / **29.0** |
| _Reference transcripts + GPT3.5-turbo-instruct_ | 35.1 / **40.0** | 28.2 / **28.9** |
| _Reference transcripts + GPT4_ | 38.3 / **43.5** | 31.3 / **32.0** |
| _Reference transcripts + Google Translate API_ | 38.9 / **44.1** | 26.1 / **25.9** |
| _Reference transcripts + NLLB 3.3B_ (*) | 31.4 / **38.1** | 25.2 / **25.7** |
| _Reference transcripts + Neurotõlge_ | 34.8 / **40.5** | 29.3 / **29.6** |
| _Reference transcripts + DeepL_ | 34.8 / **41.1** | 25.5 / **25.8** |
| Whisper-large-v2 | 17.4 / **23.7** | — |
| SeamlessM4T v2 (large) (*) | 13.2 / **18.7** | 16.2 / **17.5** |
| OWSM 3.1 EBF | 0.5 / **2.8** | 0.0 / **0.0** |
| Whisper-medium-et-orthographic + GPT3.5-turbo | 32.9 / **38.7** | 26.5 / **27.8** |
| Whisper-medium-et-orthographic + GPT3.5-turbo-instruct | 32.2 / **37.7** | 25.7 / **27.1** |
| Whisper-medium-et-orthographic + GPT4 | 35.1 / **41.0** | 29.8 / **31.0** |
| Whisper-medium-et-orthographic + Neurotõlge | 31.9 / **38.5** | 26.6 / **27.8** |
| Whisper-medium-et-orthographic + Google Translate API | 35.2 / **41.6** | 23.8 / **24.7** |
| OWSM 3.0, finetuned on extra web data | 8.7 / **14.9** | 5.4 / **6.4** |
| SeamlessM4T v2 (large), finetuned on synth data (ASR + MT) | 35.4 / **41.2** | 26.8 / **28.0** |
| Whisper-large-v3, finetuned on synth data (ASR + MT) | 33.2 / **39.3** | 26.2 / **26.9** |

### To Estonian

This section was added as part of the fair-pipeline re-run. The
previously-published `RESULTS.md` did not include en→et and ru→et numbers
for most cascade systems — they were out-of-scope of the original table
structure. They are computed here because the MT output files already exist
in `outputs/en/mt/` and `outputs/ru/mt/`.

| Model | en→et | ru→et |
|-------|:-----:|:-----:|
| DeepL | 29.0 / **24.2** | 25.8 / **28.0** |
| Google Translate API | 25.4 / **20.7** | 24.2 / **25.8** |
| GPT3.5-turbo | 21.3 / **18.7** | 23.8 / **27.1** |
| GPT3.5-turbo-instruct | 21.0 / **17.8** | 23.5 / **26.8** |
| GPT4 | 19.9 / **18.6** | 24.6 / **28.9** |
| Neurotõlge | 24.7 / **20.2** | 23.7 / **26.4** |
| NLLB | 21.5 / **19.8** | 19.2 / **22.0** |
| SeamlessM4T v2 (large), finetuned on extra web data + synth data | 18.8 / **17.7** | 16.4 / **20.6** |
| Whisper-large-v3 + DeepL | 19.8 / **19.7** | 16.6 / **22.1** |
| Whisper-large-v3 + Google Translate API | 17.4 / **17.2** | 16.1 / **21.6** |
| Whisper-large-v3 + GPT3.5-turbo | 15.1 / **16.1** | 18.3 / **24.8** |
| Whisper-large-v3 + GPT3.5-turbo-instruct | 15.2 / **15.5** | 18.3 / **24.9** |
| Whisper-large-v3 + GPT4 | 16.3 / **16.4** | 18.3 / **25.5** |
| Whisper-large-v3 + Neurotõlge | 16.1 / **15.9** | 16.0 / **22.5** |
| Whisper-large-v3 + NLLB | 15.4 / **16.3** | 13.2 / **19.0** |
| Whisper-large-v3, finetuned on extra web data + synth data | 10.1 / **9.7** | 14.9 / **20.5** |

### Observations

1. **From Estonian every system gains under fair normalization** — the
   floor lifts by +0.5 to +6.7 BLEU. The gain is biggest for systems that
   aggressively inverse-text-normalise numbers to digits (Whisper direct ST
   +6.3, NLLB +6.7, SeamlessM4T +5.5) and smaller for word-preserving
   systems like the reference+DeepL and reference+GPT4 cascades (still
   +5.2 to +6.3 — some of their "errors" were also formatting artefacts).
   This confirms the unfairness was structural: every system was paying a
   penalty for digit-vs-word asymmetry regardless of translation quality.

2. **et→ru gains are much smaller** (+0.3 to +1.3) than et→en (+5 to +7).
   The reason is a known limitation of the current pipeline:
   `num2words(lang='ru')` produces only nominative cardinal forms, but
   Russian references use case-inflected forms (`в две тысячи двадцатом
   году` vs the spell-out `в две тысячи двадцать году`). A morphology-aware
   Russian speller (ICU `RuleBasedNumberFormat` or similar) would close the
   gap. Documented in `BENCHMARK_ISSUES.md`.

3. **en→et fair BLEU is often LOWER than legacy**. This is a small-test-set
   artefact, not a normalisation problem. The en→et split has only **5 files**
   of very uneven size (the two longest contain ~50% of the words), and
   sacreBLEU's corpus-level number diverges from a per-file macro average
   more on such unbalanced test sets. For apples-to-apples comparison with
   the legacy macro numbers, look at the `macro BLEU` column in the
   per-run output — it tracks the legacy numbers within ±0.5 BLEU for
   en→et. The corpus number is the one to cite because it's what the rest
   of the MT world reports, but it has higher variance on this test set.

4. **ru→et fair corpus BLEU is reliably HIGHER than legacy** (+0.6 to
   +7.0), even though it shares the same test-set size caveat. The fair
   corpus numbers move the cascades like `Whisper-large-v3 + GPT4`
   (legacy 18.3 → fair 25.5) into the same neighbourhood as the
   reference-transcript cascades — a more honest picture than the legacy
   numbers suggest.

5. **Several rankings change**. Under the legacy BLEU ranking for et→en,
   `_Reference transcripts + Google Translate API_` was rank 1 (38.9);
   under fair corpus BLEU it is still rank 1 (44.1) but the gap to
   `_Reference transcripts + GPT4_` (fair 43.5) has narrowed. More
   notably, the direct Whisper-large-v2 system jumps from 17.4 to 23.7 —
   still far from the cascades, but less comically bad than the legacy
   number made it look.

To reproduce any single cell: `./run-mt-eval.sh --refdir data/<src>
--source <src> --target <tgt> outputs/<src>/mt/<system-dir>`. Add
`--normalize false` to reproduce the legacy number.

(*) Systems marked in the original table as "translating number expressions
to digits while references use words". That warning is now obsolete for the
fair column — the normalizer handles it — but the legacy column still
shows the penalty.

## BLEURT scores

| Model                                                  | From Estonian |           | To Estonian      ||
|--------------------------------------------------------|:-------------:|:---------:|:-------------:|:---------:|
|                                                        |   *English*   | *Russian* | *English*     | *Russian* |
| _Reference transcripts + Google Translate API_         |     0.690      |       | |
| _Reference transcripts + DeepL_                        |     0.678      |       | |
| Whisper-medium-et-orthographic + Google Translate API  |     0.628      |  0.617     |      |  
| SeamlessM4T v2 (large)                                 |     0.348      |   0.426    | |   0.448 |
| SeamlessM4T v2 (large), finetuned on extra web data    |     0.468      |   0.488    | |   0.261
| SeamlessM4T v2 (large), finetuned on synth data (ASR + MT) |  0.618       |   0.603    |    | 0.494 |
| SeamlessM4T v2 (large), finetuned on extra web data + synth data (ASR + MT) |     0.617      |   0.605   | | 0.426 |
| Whisper-large-v3, finetuned on extra web data   |  0.496         |  0.413     | | 0.523
| Whisper-large-v3, finetuned on synth data (ASR + MT)   |   0.611        |  0.605    | | 0.269 |
| Whisper-large-v3, finetuned on extra web data +  synth data (ASR + MT)   |  0.614 | 0.603 ||  0.522
| OWSM 3.1 EBF , finetuned on synth data (ASR + MT)   |     0.541      |       | | 0.360








# Comparison of ASR systems

## Estonian

| Model                            | WER (legacy) | WER (fair, macro) | WER (fair, micro) |
|----------------------------------|:------------:|:-----------------:|:-----------------:|
| Whisper-medium-et-orthographic   |     10.5     |        8.4        |        8.8        |
| Whisper-large-v3-et-orthographic |      9.7     |        7.4        |        7.6        |

All results are calculated on dev data.

**Note on methodology.** "Legacy" WER is `ASReval --simple` from the `SLTev`
package — lowercase + ASCII-punctuation stripped (with the `Covid-19 → covid19`
merging bug) + macro-averaged per-file LPW. It corresponds to
`./run-asr-eval.sh --normalize false`.

"Fair" WER additionally spells digit tokens as Estonian words, replaces
(rather than deletes) punctuation with a space, strips Unicode editorial
punctuation, and uses NFC normalization. Both reference and hypothesis go
through exactly the same pipeline before scoring. It corresponds to
`./run-asr-eval.sh` (the new default). Report the micro-averaged number
(sum of all edits / sum of all reference words) — that is the
industry-standard convention used by Whisper, Kaldi, and ESPnet.

See [BENCHMARK_ISSUES.md](BENCHMARK_ISSUES.md) for the detailed rationale.

