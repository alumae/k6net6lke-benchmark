import argparse
import librosa 
#from espnet2.bin.s2t_inference import Speech2Text
from pathlib import Path
import torch

#from pyannote.audio import Pipeline
import pandas as pd
#from pydub import AudioSegment, silence, utils
import librosa
import hashlib
import io
import logging
from tqdm import tqdm



# Function to merge rows based on conditions
def merge_rows(df, time_diff_threshold=1.0, max_speech_length=30.0, speech_min_length=0.25):
    i = 0
    while i < len(df):
        # Check if the speaker is different from both previous and next speakers
        # And if the duration is less than the threshold
        if (i > 0 and i < len(df) - 1 and
            df.iloc[i]['speaker'] != df.iloc[i - 1]['speaker'] and
            df.iloc[i]['speaker'] != df.iloc[i + 1]['speaker'] and
            df.iloc[i]['end'] - df.iloc[i]['start'] < speech_min_length):
            # Delete the row
            df = df.drop(df.index[i])
            # Reset the index
            df = df.reset_index(drop=True)
        else:
            i += 1
                
    i = 0
    while i < len(df) - 1:
        # Check if the current and next row have the same speaker
        # and if the time difference is less than the threshold
        if df.iloc[i]['speaker'] == df.iloc[i + 1]['speaker'] and \
           df.iloc[i + 1]['start'] - df.iloc[i]['end'] < time_diff_threshold and \
           df.iloc[i + 1]['end'] - df.iloc[i]['start'] < max_speech_length:
            # Update the end time of the current row
            df.at[i, 'end'] = df.iloc[i + 1]['end']
            # Drop the next row
            df = df.drop(df.index[i + 1])
            # Reset the index
            df = df.reset_index(drop=True)
        else:
            i += 1
            
    i = 0
    while i < len(df):
        # Delete short remaining segments
        if df.iloc[i]['end'] - df.iloc[i]['start'] < speech_min_length:
            # Delete the row
            df = df.drop(df.index[i])
            # Reset the index
            df = df.reset_index(drop=True)
        else:
            i += 1
            
    return df

def construct_segments(rttm_file):
        
    lines = []
    for l in open(args.rttm_file):
        ss = l.split()
        start = float(ss[3])
        length = float(ss[4])
        speaker = ss[7]
        lines.append({"start": start, "end": start+ length, "speaker": speaker})
    
    diarized_segments = pd.DataFrame(lines)
    

    diarized_segments = merge_rows(diarized_segments)    
    return diarized_segments


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Decode long audio file")
    parser.add_argument("--src-lang", type=str, default="est")
    parser.add_argument("--tgt-lang", type=str, default="eng")
    parser.add_argument("--beam", type=int, default=3)
    parser.add_argument("--max-segment-length", type=float, default=30.0)
    parser.add_argument("--device", type=str, default="cuda")    
    parser.add_argument("--model-type", type=str, default="espnet")
    parser.add_argument("--load-checkpoint", type=str, default="None")
    
    parser.add_argument("model",  type=str)
    parser.add_argument("audio_file",  type=Path)
    parser.add_argument("rttm_file",  type=Path)
    parser.add_argument("output_file",  type=Path)
    args = parser.parse_args()
   
    device = torch.device(args.device)
    #audio_segment = AudioSegment.from_file(args.audio_file)
    
    audio, rate = librosa.load(args.audio_file, sr=16000) #
    #assert audio_segment.frame_rate == 16000
    
    diarized_segments = construct_segments(args.rttm_file)

    if args.model_type == "seamless":
        logging.info("Doing S2TT using a Seamless model")
        from seamless_communication.inference import Translator
        dtype = torch.float16
        translator = Translator(
            model_name_or_card=args.model,        
            vocoder_name_or_card="vocoder_v2",
            device=device,
            dtype=dtype,
            apply_mintox=False,
        )
        if args.load_checkpoint:
            try:
              translator.model.load_state_dict(torch.load(args.load_checkpoint))
            except:
              pass

        with open(args.output_file, "w", encoding="utf-8") as f:
            
            for index, row in tqdm(diarized_segments.iterrows()):
                #audio = torch.tensor(audio_segment[row["start"]*16000:row["end"]*16000].get_array_of_samples()).to(device)
                audio_segment = torch.tensor(audio[int(row["start"]*16000):int(row["end"]*16000)]).to(device)
                    
                out_texts, _ = translator.predict(input=audio_segment, task_str="S2TT", src_lang=args.src_lang, tgt_lang=args.tgt_lang)
                
                out_text = str(out_texts[0])
                
                print(out_text)
                print(out_text, file=f, flush=True)
    elif args.model_type == "espnet":
        logging.info("Doing S2TT using a Espnet model")
        
        from espnet2.bin.s2t_inference import Speech2Text        
        s2t = Speech2Text.from_pretrained(
            model_tag=args.model,
            device=str(device),
            beam_size=1,
            ctc_weight=0.0,
            maxlenratio=0.0,
            lang_sym=f"<{args.src_lang}>",
            task_sym=f"<st_{args.tgt_lang}>",
            predict_time=False,
            quantize_s2t_model=False
        )
        
        with open(args.output_file, "w", encoding="utf-8") as f:            
            for index, row in tqdm(diarized_segments.iterrows()):
                
                audio_segment = torch.tensor(audio[int(row["start"]*16000):int(row["end"]*16000)]).to(device)
                #breakpoint()
                # if audio.dtype == torch.int64:
                    # audio =  audio / 2**31                    
                # if audio.dtype == torch.int32:
                    # audio =  audio / 2**15

                #breakpoint()
                s2t.maxlenratio = -min(300, int((len(audio_segment) / rate) * 10))  # assuming 10 tokens per second
                utts = s2t.decode_long(
                                audio_segment,
                                condition_on_prev_text=False,
                                init_text="",
                                end_time_threshold="<29.00>"
                                )                
                
                #print(utts)
                out_text = " ".join([utt[2] for utt in utts])
                
                print(out_text, file=f, flush=True)
        
    else:
        raise Excepton(f"Unknown model type: {args.model_type}")
        
    
    
