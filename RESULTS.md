# Comparison of speech translation systems

Note that some systems use oracle transcriptions and are only listed for reference.

## BLEU and BLEURT scores

Each BLEU cell shows `legacy / **fair**`. **Legacy** is
`./run-mt-eval.sh --normalize false` (sacreBLEU via `MTeval --simple` with
macro-averaged per-file scores, reproducing the pre-fix numbers). **Fair**
is `./run-mt-eval.sh` (the new default): both reference and hypothesis go
through the normalizer in `utils/normalize_asr_text.py` (Estonian uses a
custom cardinal speller, Russian uses `num2words(lang='ru')`, English uses
Whisper's `EnglishTextNormalizer`; Unicode punctuation → space; NFC;
lowercase), then sacreBLEU's `corpus_bleu` with the `13a` tokenizer is
computed over the whole document.

Each BLEURT cell shows the **fair BLEURT-20** score:
`./run-mt-eval.sh --bleurt true`, which additionally runs
`lucadiliello/BLEURT-20` from the `~/.venvs/bleurt` venv over the same
normalized files. Each reference/hypothesis pair is aligned to the
reference sentence boundaries via `mwerSegmenter` (the same aligner used
by sacreBLEU), then scored pair-by-pair with BLEURT-20, and the mean is
reported as the corpus number. BLEURT-20 is multilingual and trained via
RemBERT, so it works for all four of our language directions.

See [BENCHMARK_ISSUES.md](BENCHMARK_ISSUES.md) for why the legacy pipeline
was unfair — short version: it penalised systems that emit numbers in digit
form (`55`) against references that spell them out
(`viiskümmend viis` / `fifty-five` / `пятьдесят пять`).

### From Estonian

| Model | et→en BLEU | et→en BLEURT | et→ru BLEU | et→ru BLEURT |
|-------|:----------:|:------------:|:----------:|:------------:|
| _Reference transcripts + GPT3.5-turbo_ | 36.1 / **41.0** | **0.698** | 28.3 / **29.0** | **0.679** |
| _Reference transcripts + GPT3.5-turbo-instruct_ | 35.1 / **40.0** | **0.702** | 28.2 / **28.9** | **0.685** |
| _Reference transcripts + GPT4_ | 38.3 / **43.5** | **0.705** | 31.3 / **32.0** | **0.687** |
| _Reference transcripts + Google Translate API_ | 38.9 / **44.1** | **0.688** | 26.1 / **25.9** | **0.630** |
| _Reference transcripts + NLLB 3.3B_ (*) | 31.4 / **38.1** | **0.675** | 25.2 / **25.7** | **0.667** |
| _Reference transcripts + Neurotõlge_ | 34.8 / **40.5** | **0.680** | 29.3 / **29.6** | **0.674** |
| _Reference transcripts + DeepL_ | 34.8 / **41.1** | **0.698** | 25.5 / **25.8** | **0.688** |
| Whisper-large-v2 | 17.4 / **23.7** | **0.507** | — | — |
| SeamlessM4T v2 (large) (*) | 13.2 / **18.7** | **0.414** | 16.2 / **17.5** | **0.462** |
| OWSM 3.1 EBF | 0.5 / **2.8** | **0.229** | 0.0 / **0.0** | **0.158** |
| Whisper-medium-et-orthographic + GPT3.5-turbo | 32.9 / **38.7** | **0.669** | 26.5 / **27.8** | **0.639** |
| Whisper-medium-et-orthographic + GPT3.5-turbo-instruct | 32.2 / **37.7** | **0.666** | 25.7 / **27.1** | **0.636** |
| Whisper-medium-et-orthographic + GPT4 | 35.1 / **41.0** | **0.669** | 29.8 / **31.0** | **0.660** |
| Whisper-medium-et-orthographic + Neurotõlge | 31.9 / **38.5** | **0.623** | 26.6 / **27.8** | **0.607** |
| Whisper-medium-et-orthographic + Google Translate API | 35.2 / **41.6** | **0.647** | 23.8 / **24.7** | **0.594** |
| OWSM 3.0, finetuned on extra web data | 8.7 / **14.9** | **0.400** | 5.4 / **6.4** | **0.222** |
| SeamlessM4T v2 (large), finetuned on synth data (ASR + MT) | 35.4 / **41.2** | **0.649** | 26.8 / **28.0** | **0.606** |
| Whisper-large-v3, finetuned on synth data (ASR + MT) | 33.2 / **39.3** | **0.632** | 26.1 / **26.9** | **0.589** |

### To Estonian

This section was added as part of the fair-pipeline re-run. The
previously-published `RESULTS.md` did not include en→et and ru→et numbers
for most cascade systems — they were out-of-scope of the original table
structure. They are computed here because the MT output files already exist
in `outputs/en/mt/` and `outputs/ru/mt/`.

| Model | en→et BLEU | en→et BLEURT | ru→et BLEU | ru→et BLEURT |
|-------|:----------:|:------------:|:----------:|:------------:|
| DeepL | 29.0 / **24.2** | **0.557** | 25.8 / **28.0** | **0.665** |
| Google Translate API | 25.4 / **20.7** | **0.545** | 24.2 / **25.8** | **0.722** |
| GPT3.5-turbo | 21.3 / **18.7** | **0.536** | 23.8 / **27.1** | **0.683** |
| GPT3.5-turbo-instruct | 21.0 / **17.8** | **0.537** | 23.5 / **26.8** | **0.677** |
| GPT4 | 19.9 / **18.6** | **0.543** | 24.6 / **28.9** | **0.696** |
| Neurotõlge | 24.7 / **20.2** | **0.530** | 23.7 / **26.4** | **0.695** |
| NLLB | 21.5 / **19.8** | **0.508** | 19.2 / **22.0** | **0.668** |
| SeamlessM4T v2 (large), finetuned on extra web data + synth data | 18.8 / **17.6** | **0.466** | 16.4 / **20.6** | **0.559** |
| Whisper-large-v3 + DeepL | 19.8 / **19.7** | **0.509** | 16.6 / **22.1** | **0.609** |
| Whisper-large-v3 + Google Translate API | 17.4 / **17.2** | **0.479** | 16.1 / **21.6** | **0.604** |
| Whisper-large-v3 + GPT3.5-turbo | 15.1 / **16.1** | **0.472** | 18.3 / **24.8** | **0.643** |
| Whisper-large-v3 + GPT3.5-turbo-instruct | 15.2 / **15.4** | **0.475** | 18.3 / **24.9** | **0.638** |
| Whisper-large-v3 + GPT4 | 16.3 / **16.4** | **0.500** | 18.3 / **25.5** | **0.649** |
| Whisper-large-v3 + Neurotõlge | 16.1 / **15.9** | **0.461** | 16.0 / **22.5** | **0.595** |
| Whisper-large-v3 + NLLB | 15.4 / **16.3** | **0.438** | 13.2 / **19.0** | **0.564** |
| Whisper-large-v3, finetuned on extra web data + synth data | 10.1 / **9.7** | **0.344** | 14.9 / **20.5** | **0.534** |

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

6. **BLEURT-20 and fair BLEU agree on the ranking but disagree on the
   gap**. For et→en, GPT4 and Google Translate are within 0.02 BLEURT of
   each other (0.705 vs 0.688) even though their fair BLEU differ by 0.6
   (43.5 vs 44.1). BLEURT's verdict: the reference-transcript cascades
   are a tight cluster of roughly equivalent quality. The direct
   speech-translation systems (Whisper-large-v2, SeamlessM4T, OWSM) sit
   in a clearly separate lower tier. OWSM 3.1 EBF stands out as the only
   system with a negative-territory BLEURT for et→ru (0.158), which
   matches its legacy BLEU of 0.0 — genuinely broken output.

7. **For et→ru, BLEURT reveals the Russian normalisation limitation most
   clearly**. The et→ru BLEU numbers only moved by +0.3 to +1.3 under
   fair normalization (because `num2words(lang='ru')` produces only
   nominative forms), but the BLEURT numbers for the reference-transcript
   cascades (0.63–0.69) are close to the et→en numbers (0.67–0.71). That
   is: BLEURT sees the systems as roughly as good for et→ru as for
   et→en, while fair BLEU still shows a 10-point gap. The gap is the
   metric's sensitivity to the word-level digit/word mismatches that
   fair normalization didn't fully close for Russian. A better Russian
   number speller would mostly close the BLEU gap but leave BLEURT
   unchanged — that's a useful diagnostic.

8. **en→et shows the biggest fair/legacy BLEU disagreement but BLEURT
   numbers are stable**. The en→et corpus BLEU often dropped under fair
   normalization (an artefact of the 5-file test set being heterogeneous,
   see point 3). BLEURT on the same data shows that DeepL (BLEURT 0.557)
   genuinely is the best en→et system in this set, followed by Google
   Translate (0.545) — the same ranking the legacy BLEU gave. So
   rankings-wise BLEURT confirms the legacy BLEU story for en→et even
   where corpus BLEU got noisy.

To reproduce any single cell: `./run-mt-eval.sh --refdir data/<src>
--source <src> --target <tgt> outputs/<src>/mt/<system-dir>`. Add
`--normalize false` to reproduce the legacy number.

(*) Systems marked in the original table as "translating number expressions
to digits while references use words". That warning is now obsolete for the
fair column — the normalizer handles it — but the legacy column still
shows the penalty.

*(The previously-separate BLEURT table is merged into the BLEU tables
above.)*








# Comparison of ASR systems

## Estonian

| Model                            | WER (legacy) | WER (fair) |
|----------------------------------|:------------:|:----------:|
| Whisper-medium-et-orthographic   |     10.5     |    8.8     |
| Whisper-large-v3-et-orthographic |      9.7     |    7.6     |
| Gemini 3 Flash Preview via OpenRouter |      —       |    11.1    |

All results are calculated on dev data.

**Note on methodology.** "Legacy" WER is `ASReval --simple` from the `SLTev`
package — lowercase + ASCII-punctuation stripped (with the `Covid-19 → covid19`
merging bug) + macro-averaged per-file LPW. It corresponds to
`./run-asr-eval.sh --normalize false`.

"Fair" WER additionally spells digit tokens as Estonian words, replaces
(rather than deletes) punctuation with a space, strips Unicode editorial
punctuation, and uses NFC normalization. Both reference and hypothesis go
through exactly the same pipeline before scoring. It corresponds to
`./run-asr-eval.sh` (the new default). It reports a single micro-averaged
number (sum of all edits / sum of all reference words) — the industry-standard
convention used by Whisper, Kaldi, and ESPnet.

See [BENCHMARK_ISSUES.md](BENCHMARK_ISSUES.md) for the detailed rationale.

See [GEMINI3_FLASH_ET_ASR.md](GEMINI3_FLASH_ET_ASR.md) for the Gemini 3 Flash
Preview ASR run, comparison with the Estonian Whisper baselines, and error
profile.
