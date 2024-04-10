import sys
from googletrans import Translator, LANGUAGES

def translate_file(input_file, src_lang, dest_lang, output_file):
    translator = Translator()
    translated_lines = []

    # Read the input file
    with open(input_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    
    # Translate each line
    for line in lines:
        translated = translator.translate(line, src=src_lang, dest=dest_lang)
        translated_lines.append(translated.text)

    # Write the translated text to the output file
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write('\n'.join(translated_lines))

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python script.py input_file source_language target_language output_file")
        sys.exit(1)

    input_file = sys.argv[1]
    source_language = sys.argv[2]
    target_language = sys.argv[3]
    output_file = sys.argv[4]

    translate_file(input_file, source_language, target_language, output_file)

