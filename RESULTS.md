# Comparison of speech translation systems

Note that some systems use oracle transcriptions and are only listed for reference.

| Model             | From Estonian              || To Estonian      ||
|-------------------|:---------------:|:---------:|:-------------:|:---------:|
|                   | *English*       | *Russian* | *English*     | *Russian* |
|_Reference transcripts + GPT3.5_ | 36.1 | 28.3 | |
|_Reference transcripts + GPT4_ | 38.3 | 31.3 | |
|Whisper-large-v2   |       17.6    |         |             |         |
|Whisper-medium-et-orthographic + GPT3.5 | 32.9 | 26.5 |      |
|Whisper-medium-et-orthographic + GPT4 | 35.1 |  |      |

# Comparison of ASR systems

## Estonian

| Model | WER |
|-------|:----------:|
|Whisper-medium-et-orthographic | 10.5 |


All results are calculated on dev data.
