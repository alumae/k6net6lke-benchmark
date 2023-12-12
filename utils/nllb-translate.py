import ctranslate2
import argparse
import sentencepiece as spm

def batch_translate(translator, tok, lines, source_lang, target_lang, batch_size, beam_size):
    """
    Translate lines in batches.
    """
    translated_lines = []
    for i in range(0, len(lines), batch_size):
        source_sentences = lines[i:i+batch_size]
        # Subword the source sentences
        source_sents_subworded = tok.encode_as_pieces(source_sentences)
        source_sents_subworded = [[source_lang] + sent + ["</s>"] for sent in source_sents_subworded]
        
        target_prefix = [[target_lang]] * len(source_sentences)
        
        translations_subworded = translator.translate_batch(source_sents_subworded, batch_type="tokens", max_batch_size=batch_size, beam_size=beam_size, target_prefix=target_prefix)
        translations_subworded = [translation.hypotheses[0] for translation in translations_subworded]
        
        
        for translation in translations_subworded:
            if target_lang in translation:
                translation.remove(target_lang)

        # Desubword the target sentences
        translations = tok.decode(translations_subworded)        
        translated_lines.extend(translations)
        
    return translated_lines

def main():
    parser = argparse.ArgumentParser(description='Batch Translation using CTranslate2')
    parser.add_argument('--batch-size', type=int, default=32, help='Batch size for translation')
    parser.add_argument('--beam-size', type=int, default=4, help='Beam size for translation')
    parser.add_argument('model_path', help='Path to the CTranslate2 model')
    parser.add_argument('tokenizer_path', help='Path to the CTranslate2 tokenizer')
    parser.add_argument('source_lang', help='Source language code')
    parser.add_argument('target_lang', help='Target language code')
    parser.add_argument('input_file', help='Path to the input text file')
    parser.add_argument('output_file', help='Path to the output text file')
    

    args = parser.parse_args()

    # Load the source SentecePiece model
    sp = spm.SentencePieceProcessor()
    sp.load(args.tokenizer_path)

    # Load the translator
    translator = ctranslate2.Translator(args.model_path, device="auto")

    # Read input file
    with open(args.input_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    # Remove newlines and strip whitespace
    lines = [line.strip() for line in lines]

    # Translate in batches
    translated_lines = batch_translate(translator, sp, lines, args.source_lang, args.target_lang, args.batch_size, args.beam_size)

    # Write output file
    with open(args.output_file, 'w', encoding='utf-8') as file:
        for line in translated_lines:
            file.write(line + '\n')

    print(f"Translation completed. Output written to {args.output_file}")

if __name__ == "__main__":
    main()
