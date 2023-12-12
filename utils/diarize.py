import argparse
from pyannote.audio import Pipeline
import torch

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Diarize long audio file")
    parser.add_argument("--diarization-model", type=str, default="pyannote/speaker-diarization-3.1")
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("audio", type=str)
    parser.add_argument("output_rttm")

    args = parser.parse_args()

    diarization_model = Pipeline.from_pretrained(args.diarization_model)
    diarization_model = diarization_model.to(torch.device("cuda:0"))
    diarization_raw = diarization_model(args.audio)

    # dump the diarization output to disk using RTTM format
    with open(args.output_rttm, "w") as rttm:
        diarization_raw.write_rttm(rttm)
