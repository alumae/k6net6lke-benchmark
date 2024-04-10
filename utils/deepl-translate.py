import argparse
import requests
import os

def translate_text(text, source_lang, target_lang, api_key):
    """Translate text using DeepL API."""
    url = "https://api.deepl.com/v2/translate"
    payload = {
        "auth_key": api_key,
        "text": text,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "split_sentences": "nonewlines",
        "tag_handling":"xml", 
        "non_splitting_tags":"<sep/>"
    }
    response = requests.post(url, data=payload)
    #breakpoint()
    return response.json()['translations'][0]['text']

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Translate text file using DeepL.")
    parser.add_argument("source_file", help="Path to the source text file")
    parser.add_argument("target_file", help="Path to save the translated text file")
    parser.add_argument("source_lang", help="Source language (e.g., EN)")
    parser.add_argument("target_lang", help="Target language (e.g., DE)")
    
    args = parser.parse_args()

    api_key = os.environ.get("DEEPL_API_KEY")
    
    # Read the source file
    with open(args.source_file, "r", encoding="utf-8") as file:
        text = file.read()

    # Translate the text
    translated_text = translate_text(text, args.source_lang, args.target_lang, api_key)

    # Save the translated text to the target file
    with open(args.target_file, "w", encoding="utf-8") as file:
        file.write(translated_text)

    print("Translation completed successfully.")

if __name__ == "__main__":
    main()
