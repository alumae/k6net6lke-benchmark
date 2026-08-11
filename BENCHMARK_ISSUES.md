# Fairness issues in `run-asr-eval.sh`

This document reviews the ASR evaluation driver in `run-asr-eval.sh` and the
`ASReval` tool it relies on (from the `SLTev` Python package). It summarises
what the pipeline actually does, lists the places where it is not a fair or
standard way to benchmark ASR on this dataset, and sketches the changes needed
to fix them.

## What the current pipeline does

`run-asr-eval.sh` pairs reference transcripts (`*.<lang>.OSt`) with ASR
hypotheses (`*.<lang>.asr`), feeds each pair into `ASReval`, and averages the
per-file `LPW` scores:

```bash
ASReval -i $interleaved_string -f asr ost --simple \
  | tee /dev/stderr \
  | grep LPW | awk '{sum+=$2} END {print("\n\nAverage WER: ", sum/NR)}'
```

Under `--simple`, `ASReval` runs `WER_by_mwersegmenter_without_moses_tokenizer`
from `SLTev/ASRev.py`, which:

1. Reads both files and applies the **Moses tokenizer** line by line.
2. Runs **`mwerSegmenter`** to align the hypothesis against the reference
   segment boundaries. *(This step is good — it means the ASR system is free
   to choose its own segmentation.)*
3. For each aligned segment pair, applies `text_preprocessing`
   (`SLTev/ASRev.py:23-26`):
   ```python
   def text_preprocessing(text):
       text = text.lower().translate(str.maketrans("", "", string.punctuation))
       text = re.sub(" +", " ", text)
       return text
   ```
4. Computes word-level WER via `jiwer.wer()` on the preprocessed strings and
   averages the per-segment values into one `LPW` number per file.
5. The shell script then averages those per-file `LPW` values with `sum/NR`.

Distilled, the normalization applied to both reference and hypothesis is:

| Step | Applied? | Notes |
|---|---|---|
| Lowercasing | yes | `text.lower()` |
| ASCII punctuation stripping | yes | `string.punctuation`, **deleted with no replacement** |
| Whitespace collapsing | yes | |
| Unicode / smart-quote / em-dash / ellipsis stripping | **no** | `„ " " « » – — …` all survive |
| Unicode NFC/NFKC normalization | **no** | composed vs. decomposed `õ`/`ü` would mismatch |
| Digit ↔ word normalization | **no** | `Covid-19` vs `Covid üheksateist` counts as errors |
| Date / time / currency / unit normalization | **no** | `16.12.2020`, `15:30`, `€50`, `15 °C` handled raw |
| Abbreviation / acronym expansion | **no** | `U.S.A.` vs `u s a` vs `usa` mismatch |
| Hesitation / filler handling | **no** | `uh`, `öö`, `ee` all count |
| Unweighted file averaging | ⚠ | a 30 s clip counts the same as a 20 min clip |
| Sentence-segmentation independence | yes | handled by `mwerSegmenter` |

The approach is broadly in the family of standard ASR evaluation
(lowercase + strip punctuation + word-level WER + mwerSegmenter alignment).
But four concrete issues make it *not* a fair comparison in the form it ships.

---

## Issue 1 — Numbers written as words vs. as digits

This is the biggest real-world effect and it is visible directly in the
benchmark data.

**Reference** — `data/et/aktuaalne-kaamera-ilm-nadal-322248.et.OSt`, line 60:

> "Hommikuse seisuga on haiglas viiskümmend viis **Covid-19** patsienti,
> juhitaval hingamisel on neli inimest."

**Hypothesis** — `outputs/et/asr/whisper-large-v3-et-orthographic/aktuaalne-kaamera-ilm-nadal-322248.et.asr`, line 40:

> "Hommikuse seisuga on haiglas viiskümmend viis **Covid üheksateist**
> patsienti, juhitaval hingamisel on neli inimest, eile suri…"

After the `text_preprocessing` step above, the critical span becomes:

- Reference: `covid19`   (one token — the hyphen is *deleted* with no space,
  so `Covid` and `19` are glued together)
- Hypothesis: `covid üheksateist` (two tokens)

The system actually transcribed what the anchor said — `üheksateist` is
"nineteen" spelled out in Estonian — but the scorer records **one substitution
and one insertion**. The acoustically correct transcription is penalised.

The same pattern will bite every time a number, date, percentage, temperature,
age, phone number, or unit appears. Some examples the current benchmark
contains or will contain with other ASR systems:

- `21-aastane` in the reference vs `kahekümne üheaastane` in the hypothesis
- `16.12.2020` vs `kuueteistkümnes detsember kaks tuhat kakskümmend`
- `15 °C` vs `viisteist kraadi`
- `kell 9.30` vs `kell üheksa kolmkümmend` or `pool kümme`

Estonian (and Russian) speakers almost always *say* numbers, dates, and times
as words, while reference transcripts — written by humans or pulled from
subtitles — tend to use digits. ASR systems that correctly transcribe what was
said are punished; ASR systems that silently "inverse-text-normalise" into
digits are rewarded for mimicking the reference's formatting rather than the
audio.

Standard practice on modern ASR leaderboards (Whisper, ESPnet, NeMo) is to
**normalise both sides** — typically by spelling digits out as words, or by
converting both to a canonical form — before scoring. Ignoring this is the
single biggest fairness problem with the current script.

## Issue 2 — Hyphens and slashes are deleted without a space

`str.translate(str.maketrans("", "", string.punctuation))` *removes*
punctuation rather than replacing it with a space. That quietly corrupts any
token that is only separated by punctuation:

| Input | After current normalization |
|---|---|
| `Covid-19` | `covid19` |
| `15-20` | `1520` |
| `TV3/ETV` | `tv3etv` |
| `kell 9.30` | `kell 930` |
| `E-tähe` | `etähe` |
| `U.S.A.` | `usa` |

This merges what should be multiple tokens into one and creates spurious
"words" that can match neither the reference nor the hypothesis. It also
interacts badly with Issue 1: the reference's `Covid-19` becomes `covid19` as
a single token, guaranteeing a mismatch against any word-based ASR output.

The standard fix is one line — replace with space instead of deleting:

```python
text.translate(str.maketrans(string.punctuation, " " * len(string.punctuation)))
```

This is what Whisper's `BasicTextNormalizer` and ESPnet's scoring scripts do.

## Issue 3 — Non-ASCII punctuation leaks through

`string.punctuation` is **ASCII only**:

```
!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~
```

Any smart quote, typographic dash, ellipsis, or non-Latin punctuation survives
the normalization step and stays glued to adjacent words. In this repo's
current reference set, a grep for `[„""«»–—…]` across `data/et/*.OSt` finds
**295 occurrences** spread across 19 files:

```
data/et/ringvaade-2033-320571.ru.OSt:53
data/et/aktuaalne-kaamera-ilm-1001-317793.ru.OSt:48
data/et/ringvaade-2071-326938.ru.OSt:47
data/et/Valitsuse_pressikonverents__15._oktoober_2020-dJypQ9rLypU.ru.OSt:39
...
```

Whenever the reference uses `„Aktuaalne Kaamera"` (low-open + right-curly
quotes, common in Estonian editorial text) and the ASR produces
`"Aktuaalne Kaamera"` or `Aktuaalne Kaamera` (no quotes, as Whisper usually
does), the comparison sees:

- ref: `„aktuaalne kaamera"` (two tokens with garbage prefix/suffix)
- hyp: `aktuaalne kaamera`

and scores substitutions. The fix is `unicodedata.normalize("NFC", s)` plus a
punctuation filter based on the Unicode `P*` category (for example via the
`regex` package's `\p{P}`) rather than `string.punctuation`.

## Issue 4 — Unweighted macro-average over files

`run-asr-eval.sh` line 59 ends with:

```awk
awk '{sum+=$2} END {print("\n\nAverage WER: ", sum/NR)}'
```

This averages per-file WERs with equal weight. A 30-second weather clip
counts the same as a 20-minute press conference. A very short noisy clip with
WER = 0.8 moves the average by the same amount as a long clean clip — which
is not how system quality should be measured.

The standard convention for `sclite`, Kaldi `compute-wer`, ESPnet, and every
Whisper-style leaderboard is a **micro-average**:

```
WER = sum(S + D + I) / sum(N_ref_words)
```

i.e. sum up substitutions, deletions and insertions across all files, divide
by the total number of reference words. On heterogeneous corpora this
produces a different ordering than the macro-average, and it is also what
every public number you might want to compare to has been computed with.

## Secondary issues

- **No Unicode normalization.** If one side uses composed `õ` (U+00F5) and
  the other uses `o` + `˜` (U+006F U+0303), they compare as different words.
  `unicodedata.normalize("NFC", s)` fixes it and is free.
- **No filler handling.** `öö`, `ee`, `uhh`, `uh` all count as errors if one
  side has them and the other does not. Whether to strip is a policy choice,
  but the current script does not even document the choice.
- **Throws away the sanity check.** `ASReval` can compute three WER variants
  (`LPC`, `LPW`, `LPW + Moses`); `--simple` keeps only one. Running all three
  and comparing them would at least expose pipeline bugs.

---

## What "fair" looks like elsewhere

- **Whisper leaderboards / `openai-whisper`.** Use Whisper's
  `BasicTextNormalizer` (non-English) or `EnglishTextNormalizer`, which both
  NFC-normalize, lowercase, replace Unicode punctuation with space, collapse
  whitespace, and (for English) expand contractions, currencies and digits.
  For English they are the de facto standard.
- **Kaldi `compute-wer`** and **ESPnet's `score_sclite`.** Use `sclite` with a
  glm (global mapping) file and report micro-averaged WER over the corpus,
  not per-file macro-average.
- **NeMo** ships WFST-based inverse text normalisers for several languages
  (including Russian) specifically so that digit/date/currency variants do
  not show up as WER errors.

None of these are magic — they are two dozen lines of text transformation plus
a good number speller. The current benchmark is missing both pieces.

---

## Proposed fix (summary)

Add a small language-aware normalizer that is applied to *both* reference and
hypothesis before `ASReval` sees the files, and switch the final aggregation
from macro- to micro-average. Specifically:

1. **New file** `utils/normalize_asr_text.py`, with pipeline:
   1. `unicodedata.normalize("NFC", s)`.
   2. Estonian path: run `estnltk.Text(s).tag_layer(['compound_tokens'])` and
      rewrite each compound-token span by its `type`:
      - `numeric_date` → spelled out via `num2words(lang='et', to='ordinal')`
        + month table + `num2words(lang='et')` for the year.
      - `numeric_time` → spelled out (e.g. `12:30` → `kaksteist kolmkümmend`).
      - `numeric` → `num2words(int(match), lang='et')`. Case-ending variants
        such as `21-aastane` are already one compound token in `estnltk` —
        split at the hyphen, spell the numeric side, keep the suffix.
      - `email`, `www_address`, `xml_tag` → drop entirely.
   3. Unit and symbol table: `%` → `protsenti`, `°C` → `kraadi`, `€` →
      `eurot`, `$` → `dollarit`, `&` → `ja`, etc.
   4. Unicode-aware punctuation → **space** (not empty) via `\p{P}`.
   5. `str.lower()`.
   6. Whitespace collapse + strip.
   7. Per-language exit hatches: English uses Whisper's
      `EnglishTextNormalizer`; Russian uses `num2words(lang='ru')` for
      cardinals (document the ordinal limitation).
2. **Modify** `run-asr-eval.sh` to pipe every input file through the
   normalizer into a scratch directory before calling `ASReval`, and replace
   the `awk '{sum+=$2} END {print sum/NR}'` aggregation with a micro-average
   that sums edit counts and reference-word counts across files. The
   mwerSegmenter alignment step stays — it is the one piece that already
   works correctly.
3. **Expose** a `--normalize=false` flag so the old numbers are still
   reproducible for backwards comparison.
4. **Document** the full pipeline in `README.md` so future submissions are
   comparable.

The new dependencies are `estnltk`, `num2words`, and `regex` — all pure
Python, all pip-installable, no Rust toolchain or build step required.

---

# Fairness issues in `run-mt-eval.sh` (BLEU)

The translation benchmark has the **same structural problem** as the ASR one,
plus a few of its own. This section extends the review to the MT side.

## What the current MT pipeline does

`run-mt-eval.sh` calls `MTeval --simple` from `SLTev`, which dispatches to
`simple_mt_evaluation` → `wordbased_segmenter_bleu_score_evaluation`
(`SLTev/evaluator.py`). That function:

1. Runs `mwerSegmenter` to re-align the MT hypothesis against the
   reference segmentation.
2. Calls `sacrebleu.corpus_bleu(sys, refs, force=True)` on the re-segmented
   output, **with sacreBLEU's default tokenizer (`13a`) and
   `lowercase=False`**.

The per-file sacreBLEU numbers are then averaged by the shell with
`awk '{sum+=$4} END {print sum/NR}'` — an unweighted macro average across
files. Exactly the same awk pattern as the ASR script, and exactly the same
latent bug: under `LC_NUMERIC=et_EE.UTF-8` (the maintainer's default
shell locale) awk parses `17.448` as `17` and the reported number is
silently wrong.

So the actual transformation applied to both sides before scoring is
sacreBLEU's `13a` tokenizer, which:

- Splits ASCII punctuation from word characters.
- Leaves **case preserved** (`lowercase=False` by default).
- Leaves **digits preserved as digits** (`13a` has no number normaliser).
- Leaves contractions, currencies, and unit symbols untouched.
- Does no Unicode NFC / smart-quote handling.

## The same four fairness problems surface here

### 1. Digit-vs-word asymmetry — measured

Counting digit-containing tokens across the current benchmark data (from a
regex scan of each corpus):

| Corpus                                  | Unique digit tokens | Total occurrences |
|-----------------------------------------|--------------------:|------------------:|
| `data/et/*.en.OSt` (English references) |                   4 |                11 |
| `data/et/*.ru.OSt` (Russian references) |                  18 |                22 |
| `outputs/et/mt/whisper-large-v2/*.en.mt`|                 199 |               410 |
| `outputs/et/mt/seamlessM4T_v2_large/*.en.mt` |             102 |               194 |
| `outputs/et/mt/nllb-3.3B/*.en.mt`       |                  73 |               109 |
| `outputs/et/mt/gpt4/*.en.mt`            |                   2 |                 2 |
| `outputs/et/mt/deepl/*.en.mt`           |                  19 |                22 |

The English reference set has **4** digit-containing tokens
(`19`, `TV3`, `2`, `2023`). The whisper-large-v2 et→en output has
**199 unique / 410 total** — a 50× imbalance. SacreBLEU's `13a`
tokenizer leaves both sides as-is, so every `55` in the hypothesis fails to
match `fifty-five` in the reference, and vice versa. This is exactly the
situation the footnote `(*)` in the old `RESULTS.md` flagged
("Those systems usually translate number expressions to digits, while our
reference translations use words"). What the footnote doesn't say is that
the same penalty applies — in varying amounts — to **every ranked system**.

Applying the same spell-out to both sides collapses the asymmetry. A
representative re-run on et→en:

| System                                   | Legacy macro | Fair corpus | Δ     |
|------------------------------------------|-------------:|------------:|------:|
| Whisper-large-v2                         |         17.6 |        23.7 | +6.1  |
| SeamlessM4T v2 (large)*                  |         13.2 |        18.7 | +5.5  |
| NLLB 3.3B (ref transcripts)              |         31.4 |        38.1 | +6.7  |
| DeepL (ref transcripts)                  |         34.8 |        41.1 | +6.3  |
| Neurotõlge (ref transcripts)             |         34.8 |        40.5 | +5.7  |
| GPT4 (ref transcripts)                   |         38.3 |        43.5 | +5.2  |
| Whisper-medium + GPT4 cascade            |         35.1 |        41.0 | +5.9  |
| OWSM 3.1 EBF                             |          0.5 |         2.8 | +2.4  |

Every system gains. Heavy digit emitters (Whisper, SeamlessM4T, NLLB)
gain the most; word-preserving systems (GPT4, DeepL) gain less but still
measurably. This matches the prediction: the digit penalty was real and
uniform.

### 2. Punctuation handling

sacreBLEU's `13a` tokenizer splits ASCII punctuation from words but keeps
non-ASCII editorial punctuation (`„ " " « » – — …`) glued to adjacent tokens.
The Estonian and Russian references contain these characters in bulk (295
occurrences across `data/et/*.OSt`); MT systems typically output straight
quotes or none. The result is "tokens" like `„Aktuaalne` on the reference
side that never match the hypothesis's `Aktuaalne`. Fix: NFC + Unicode
`\p{P}` → space on both sides before tokenisation, which is what the new
normalizer does.

### 3. Macro vs corpus average

`run-mt-eval.sh` averages per-file sacreBLEU scores with `sum/NR`. SacreBLEU's
own recommendation is to report **corpus-level BLEU**, not a macro average of
per-segment/per-file scores — because BLEU is a non-linear function of
n-gram counts, a macro average over 7 files is not mathematically equivalent
to a corpus-level score over the same data. The two numbers diverge in ways
that depend on file length and error distribution, and only the corpus score
is comparable across research papers. The new `aggregate_bleu.py` reports
both for diagnostics but recommends the corpus number.

### 4. Locale-sensitive awk aggregation

Same bug as the ASR script: `awk '{sum+=$4}'` under
`LC_NUMERIC=et_EE.UTF-8` parses `17.448` as `17` and silently reports a
wrong average. The new pipeline computes the aggregate in Python which is
locale-independent; the `--normalize false` path also runs the aggregation
in Python so that the legacy reproduction is actually reproducible.

## What the new MT pipeline does

`./run-mt-eval.sh` (the new default) runs:

1. Normalise every reference file (`*.<target>.OSt`) and every hypothesis
   file (`*.<source>.<target>.mt`) through `utils/normalize_asr_text.py`
   using `--lang <target>`. Both sides go through exactly the same
   transformation.
2. Call `utils/aggregate_bleu.py`, which reads the normalised file pairs,
   joins each file's lines with spaces, and runs
   `sacrebleu.corpus_bleu(sys_list, [ref_list], tokenize='13a', force=True)`.
   It reports per-file BLEU for diagnostics, a macro average (for
   comparison with the legacy number), and the corpus BLEU (the number to
   cite). It also reports corpus chrF, which is more robust to tokenisation
   choices than BLEU and is increasingly the default secondary metric in
   recent MT evaluations.
3. Optional: when run with `--bleurt true`, the same normalized file pairs
   are also passed through `utils/aggregate_bleurt.py`, which loads the
   full `lucadiliello/BLEURT-20` (~576M params, RemBERT-based, multilingual
   over 100+ languages) from a dedicated Python venv at `~/.venvs/bleurt`.
   Each ref/hyp file pair is line-aligned — or, if the line counts differ,
   re-aligned via `mwerSegmenter` (the same aligner SLTev uses for
   sacreBLEU) so that BLEURT gets true sentence-parallel pairs. Per-pair
   scores are averaged into a corpus BLEURT. BLEURT catches fluency /
   adequacy issues that BLEU misses (paraphrases, word-order variants,
   synonym substitutions), and is the de facto secondary learned metric
   alongside sacreBLEU/chrF on modern MT leaderboards.

The `--bleurt` path requires an extra one-time setup:

    python3 -m venv --system-site-packages ~/.venvs/bleurt
    ~/.venvs/bleurt/bin/pip install 'transformers>=4.40,<5' bleurt-pytorch

`bleurt-pytorch` is not compatible with `transformers` 5.x, so the
isolated venv is necessary — but since it uses `--system-site-packages`
it inherits torch/CUDA from the base install and only adds ~200 MB.

The BLEURT-20 model (~2.3 GB) is downloaded to `~/.cache/huggingface/hub/`
on first use.

Everything the normalizer does on the ASR side applies here, with the one
per-language choice that English goes through Whisper's
`EnglishTextNormalizer` (`words → digits` canonical form — the leaderboard
standard) while Estonian and Russian go `digits → words` via the custom
Estonian speller and `num2words(lang='ru')` respectively. The direction
doesn't matter for fairness; only symmetry does.

## Known limitations on the MT side

- **Russian inflection**. `num2words(lang='ru')` produces nominative cardinal
  forms. Russian references often use case-inflected forms (`в 2020 году` →
  the reference has `в две тысячи двадцатом году`, but spelling `2020` from
  digits gives `две тысячи двадцать`). This means the fair pipeline still
  miscounts some Russian year mentions — the resulting et→ru BLEU lift is
  smaller (≈ +0.5 to +1.3) than the et→en lift (≈ +5 to +7). A proper fix
  would need a morphology-aware speller (e.g. `RuleBasedNumberFormat` via
  ICU `pyicu`, or a language-specific rule table). Left as future work.

- **Ordinal dates and times in Estonian**. The compound-token tagger
  rewrites `16.12.2020` and `12:30` as cardinal numbers + month name +
  cardinal year. Speakers commonly use inflected ordinal forms
  (`kuueteistkümnendal detsembril kahe tuhande kahekümnendal aastal`), which
  the pipeline doesn't produce. Fortunately the benchmark's reference files
  contain almost no digit dates in running text — the only issue we
  measured was `Covid-19` — so the practical impact is small. The
  infrastructure is in place to add a proper ordinal speller when needed.

- **Whisper English normalizer has its own quirks**. It splits `TV3` into
  `tv 3` (two tokens), drops punctuation from `8:00 am` into `8 0 am`,
  canonicalises `100,000 euros` to `€100000`. These are all symmetric (the
  same transform is applied to both sides) so they don't bias the ranking —
  but anyone reading the normalised tokens for debugging will see these
  artefacts.

---

## Backwards compatibility

Fixing the normaliser changes every number in `RESULTS.md`. For WER the
expected direction is **downwards** (lower WER) for every system; for BLEU
it is **upwards** (higher BLEU) — in both cases because most of the current
"errors" are scoring artefacts rather than real translation or transcription
mistakes. Systems that happened to match the reference's formatting
conventions will benefit less than systems that did not; some rankings may
therefore change. This is a feature, not a bug: the new numbers describe
transcription and translation quality rather than formatting mimicry.

Old and new numbers **should not be mixed in the same table**. Both the
ASR and the MT section of `RESULTS.md` now show legacy and fair columns
side-by-side with a methodology footnote.

The old behaviour remains accessible via `./run-asr-eval.sh --normalize false`
and `./run-mt-eval.sh --normalize false`, so you can still reproduce any
pre-existing number exactly (the legacy paths were also patched to fix a
locale-sensitive awk aggregation bug that silently reported
`Average WER/BLEU: 0` under `LC_NUMERIC=et_EE.UTF-8`).
