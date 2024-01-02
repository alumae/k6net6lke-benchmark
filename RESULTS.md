# Comparison of speech translation systems

Note that some systems use oracle transcriptions and are only listed for reference.

| Model                                                  | From Estonian |           | To Estonian      ||
|--------------------------------------------------------|:-------------:|:---------:|:-------------:|:---------:|
|                                                        |   *English*   | *Russian* | *English*     | *Russian* |
| _Reference transcripts + GPT3.5-turbo_                 |     36.1      |   28.3    | |
| _Reference transcripts + GPT3.5-turbo-instruct_        |     34.4      |   27.7    | |
| _Reference transcripts + GPT4_                         |     38.3      |   31.3    | |
| _Reference transcripts + Google Translate API_         |     38.9      |   26.1    | |
| _Reference transcripts + NLLB 3.3B*_                   |     31.4      |   25.2    | |
| _Reference transcripts + Neurotõlge_                   |     34.8      |   29.3    | |
| Whisper-large-v2                                       |     17.6      |           |             |         |
| Whisper-large-v3                                       |     14.9      |           |             |         |
| SeamlessM4T v2 (large)*                                |     13.2      |   16.2    |             |         |
| Whisper-medium-et-orthographic + GPT3.5-turbo          |     32.9      |   26.5    |      |
| Whisper-medium-et-orthographic + GPT3.5-turbo-instruct |     31.7      |   25.3    |      |
| Whisper-medium-et-orthographic + GPT4                  |     35.1      |   29.8    |      |
| Whisper-medium-et-orthographic + Neurotõlge            |     31.9      |   26.6    |      |

(*) Those systems usually translate number expressions to digits, while our reference translations use words.

# Comparison of ASR systems

## Estonian

| Model | WER |
|-------|:----------:|
|Whisper-medium-et-orthographic | 10.5 |
|Whisper-large-v3-et-orthographic | 9.7 |


All results are calculated on dev data.
