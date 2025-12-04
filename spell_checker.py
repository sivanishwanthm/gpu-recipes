
import os
import re
import ast
import tokenize
from spellchecker import SpellChecker

# Initialize the spell checker
spell = SpellChecker()

def load_custom_dictionary(filepath):
    """
    Loads a custom dictionary from a file.
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            words = f.read().splitlines()
            spell.word_frequency.load_words(words)
    except Exception as e:
        print(f"Error loading custom dictionary {filepath}: {e}")

def is_mixed_case(word):
    """
    Checks if a word is mixed case (e.g., camelCase or PascalCase).
    """
    return word != word.lower() and word != word.upper()

def check_spelling(text):
    """
    Checks the spelling of words in a given text.
    """
    misspelled = set()
    words = re.findall(r'\b[a-zA-Z]+\b', text)
    for word in words:
        if not word.isupper() and not is_mixed_case(word):
            if spell.unknown([word]):
                misspelled.add(word)
    return misspelled

def find_misspelled_words_in_python(filepath):
    """
    Reads a Python file, extracts comments and docstrings, and finds misspelled words.
    """
    misspelled = set()
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            # Extract docstrings using AST
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                    docstring = ast.get_docstring(node)
                    if docstring:
                        misspelled.update(check_spelling(docstring))
            # Extract comments using tokenize
            f.seek(0)
            tokens = tokenize.generate_tokens(f.readline)
            for token in tokens:
                if token.type == tokenize.COMMENT:
                    misspelled.update(check_spelling(token.string))
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
    return misspelled

def find_misspelled_words_in_markdown(filepath):
    """
    Reads a Markdown file, extracts words, and finds misspelled words, ignoring code blocks.
    """
    misspelled = set()
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            # Remove code blocks
            content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
            content = re.sub(r'`[^`]*`', '', content)
            misspelled.update(check_spelling(content))
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
    return misspelled

def find_misspelled_words(filepath):
    """
    Dispatcher function to find misspelled words based on file type.
    """
    if filepath.endswith('.py'):
        return find_misspelled_words_in_python(filepath)
    elif filepath.endswith('.md'):
        return find_misspelled_words_in_markdown(filepath)
    else:
        return set()

def main():
    """
    Main function to find all markdown and python files and check for misspelled words.
    """
    load_custom_dictionary('custom_dictionary.txt')
    all_misspelled_words = {}
    excluded_files = ['spell_checker.py', 'list.md']
    for root, _, files in os.walk('.'):
        for file in files:
            if file in excluded_files:
                continue
            if file.endswith(('.md', '.py')):
                filepath = os.path.join(root, file)
                misspelled_words = find_misspelled_words(filepath)
                for word in misspelled_words:
                    if word not in all_misspelled_words:
                        all_misspelled_words[word] = []
                    all_misspelled_words[word].append(filepath)

    with open('list.md', 'w') as f:
        f.write('| Misspelled Word | File Path |\n')
        f.write('|---|---|\n')
        for word, files in sorted(all_misspelled_words.items()):
            for file in files:
                f.write(f'| {word} | {file} |\n')

if __name__ == "__main__":
    main()
