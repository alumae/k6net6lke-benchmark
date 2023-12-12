#!/usr/bin/env python3

import sys
import requests
import argparse
from pathlib import Path

def neurotolge_translate(src_list, src_lang, tgt_lang):
    response = requests.post("https://api.tartunlp.ai/translation/v2", json={"text": src_list, "src": src_lang, "tgt": tgt_lang})
    try:
        return response.json()['result']        
    except Exception as e:
        raise e
 
def partition(strings, max_chars=5000):
    """
    Partitions a list of strings into sublists, each with a total character count
    not exceeding max_chars.

    :param strings: List of strings to partition.
    :param max_chars: Maximum number of characters allowed in each sublist.
    """
    current_sublist = []
    current_count = 0

    for string in strings:
        if current_count + len(string) > max_chars:
            if current_sublist:
                yield current_sublist
            current_sublist = [string]
            current_count = len(string)
        else:
            current_sublist.append(string)
            current_count += len(string)

    if current_sublist:
        yield current_sublist

def translate_file(src_lang, tgt_lang, infile, outfile, transl_func=neurotolge_translate, max_chars=5000):
    with open(infile, 'r') as file_handle:
        lines = [line.strip() for line in file_handle]

    with open(outfile, 'w') as output_file_handle:
        for chunk in partition(lines, max_chars=max_chars):
            translations = transl_func(chunk, src_lang, tgt_lang)

            try:
                for translation in translations:
                    print(translation, file=output_file_handle)
            except TypeError as error:
                sys.stderr.write("Error: {}\n".format(len(" ".join(chunk))))
                raise error

def main():
    parser = argparse.ArgumentParser(description='Translate text using neurotolge API.')
    parser.add_argument('src_lang', help='Source language')
    parser.add_argument('tgt_lang', help='Target language')
    parser.add_argument('infile',  type=Path , help='Input file')
    parser.add_argument('outfile',  type=Path, help='Output file')

    args = parser.parse_args()

    translate_file(args.src_lang, args.tgt_lang, args.infile, args.outfile)

if __name__ == "__main__":
    main()
