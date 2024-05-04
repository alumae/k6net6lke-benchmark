# Comparison of speech translation systems

Note that some systems use oracle transcriptions and are only listed for reference.

## BLEU scores

| Model                                                  | From Estonian |           | To Estonian      ||
|--------------------------------------------------------|:-------------:|:---------:|:-------------:|:---------:|
|                                                        |   *English*   | *Russian* | *English*     | *Russian* |
| _Reference transcripts + GPT3.5-turbo_                 |     36.1      |   28.3    | |
| _Reference transcripts + GPT3.5-turbo-instruct_        |     34.4      |   27.7    | |
| _Reference transcripts + GPT4_                         |     38.3      |   31.3    | |
| _Reference transcripts + Google Translate API_         |     38.9      |   26.1    | |
| _Reference transcripts + NLLB 3.3B*_                   |     31.4      |   25.2    | |
| _Reference transcripts + Neurotõlge_                   |     34.8      |   29.3    | |
| _Reference transcripts + DeepL_                        |     34.8      |   25.5    | |
| Whisper-large-v2                                       |     17.6      |           |             |         |
| Whisper-large-v3                                       |     14.9      |           |             |         |
| SeamlessM4T v2 (large)*                                |     13.2      |   16.2    |             |         |
| OWSM 3.1 EBF                                           |      0.5      |   0.0         |  | |
| Whisper-medium-et-orthographic + GPT3.5-turbo          |     32.9      |   26.5    |      |
| Whisper-medium-et-orthographic + GPT3.5-turbo-instruct |     31.7      |   25.3    |      |
| Whisper-medium-et-orthographic + GPT4                  |     35.1      |   29.8    |      |
| Whisper-medium-et-orthographic + Neurotõlge            |     31.9      |   26.6    |      |
| Whisper-medium-et-orthographic + Google Translate API  |     34.7      |   23.4    |      |
| OWSM 3.0, finetuned on extra web data                  |      8.7      |    5.4    |      |
| SeamlessM4T v2 (large), finetuned on extra web data    |      19.3     |   14.4        |      | 
| SeamlessM4T v2 (large), finetuned on synth data (ASR + MT) |     35.4      |   26.8    | |
| SeamlessM4T v2 (large), finetuned on extra web data + synth data (ASR + MT) |     34.7      |    25.9  | |
| Whisper-large-v3, finetuned on extra web data   |  17.8         |       | |
| Whisper-large-v3, finetuned on synth data (ASR + MT)   |      33.2     |   26.1    | |
| Whisper-large-v3, finetuned on extra web data +  synth data (ASR + MT)   |      33.0     |   25.5    | |
| OWSM 3.1 EBF , finetuned on synth data (ASR + MT)   |      25.8     | 18.7      | |


(*) Those systems usually translate number expressions to digits, while our reference translations use words.

## BLEURT scores

| Model                                                  | From Estonian |           | To Estonian      ||
|--------------------------------------------------------|:-------------:|:---------:|:-------------:|:---------:|
|                                                        |   *English*   | *Russian* | *English*     | *Russian* |
| _Reference transcripts + Google Translate API_         |     0.690      |       | |
| _Reference transcripts + DeepL_                        |     0.678      |       | |
| Whisper-medium-et-orthographic + Google Translate API  |     0.628      |  0.617     |      |
| SeamlessM4T v2 (large)                                 |     0.348      |   0.426    | |
| SeamlessM4T v2 (large), finetuned on extra web data    |     0.468      |   0.488    | |
| SeamlessM4T v2 (large), finetuned on synth data (ASR + MT) |  0.618       |   0.603    | |
| SeamlessM4T v2 (large), finetuned on extra web data + synth data (ASR + MT) |     0.617      |   0.605   | |
| Whisper-large-v3, finetuned on extra web data   |  0.500         |       | |
| Whisper-large-v3, finetuned on synth data (ASR + MT)   |   0.611        |  0.605    | |
| Whisper-large-v3, finetuned on extra web data +  synth data (ASR + MT)   |  0.614 | 0.603 ||
| OWSM 3.1 EBF , finetuned on synth data (ASR + MT)   |     0.541      |       | |








# Comparison of ASR systems

## Estonian

| Model | WER |
|-------|:----------:|
|Whisper-medium-et-orthographic | 10.5 |
|Whisper-large-v3-et-orthographic | 9.7 |


All results are calculated on dev data.
