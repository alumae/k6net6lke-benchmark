import sys
import html
from google.cloud import translate_v2 as translate

def translate_file(input_file, source_language, target_language, output_file):
    translate_client = translate.Client()

    # Read the input file
    with open(input_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    text = "<br/>".join(lines)
    # Translate the text
    translation = translate_client.translate(text, format_="text", source_language=source_language, target_language=target_language)

    # Decode HTML entities in the translated text
    decoded_text = html.unescape(translation['translatedText'].replace("<br/>", "\n"))

    # Write the translated text to the output file
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(decoded_text + "\n")

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python script.py input_file source_language target_language output_file")
        sys.exit(1)

    input_file = sys.argv[1]
    source_language = sys.argv[2]
    target_language = sys.argv[3]
    output_file = sys.argv[4]

    translate_file(input_file, source_language, target_language, output_file)

