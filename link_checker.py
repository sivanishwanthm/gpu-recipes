
import os
import re
import requests
import csv
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# List of file extensions to check
FILE_EXTENSIONS = ('.md', '.mdx', '.html')
# Report filename
REPORT_FILENAME = 'broken_links.csv'

def find_files(directory):
    """Find all files with the specified extensions in a directory."""
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(FILE_EXTENSIONS):
                yield os.path.join(root, file)

def extract_links(filepath):
    """Extract all links from a given file, stripping extraneous characters."""
    links = set()
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    if filepath.endswith('.html'):
        soup = BeautifulSoup(content, 'html.parser')
        for a in soup.find_all('a', href=True):
            links.add(a['href'].strip())
    else:  # .md, .mdx
        # Regex for Markdown links: [text](url)
        for link in re.findall(r'\[.*?\]\((.*?)\)', content):
            # Strip whitespace and surrounding parens
            clean_link = link.strip().strip('()')
            links.add(clean_link)
        # Regex for raw URLs (optional, can be noisy)
        # for link in re.findall(r'https?://[^\s"`\'<>]+', content):
        #     links.add(link)

    return links

def check_link(filepath, link):
    """
    Checks a single link.
    Returns an error message if the link is broken, otherwise None.
    """
    if not link or link.startswith('#') or link.startswith('mailto:') or link.startswith('tel:'):
        return None

    # Clean the link before parsing
    cleaned_link = link.strip().strip('()')
    parsed_link = urlparse(cleaned_link)

    # External link
    if parsed_link.scheme in ['http', 'https']:
        try:
            response = requests.head(link, timeout=10, allow_redirects=True)
            if not response.ok:
                return f'HTTP {response.status_code}'
        except requests.RequestException as e:
            return f'Error: {e.__class__.__name__}'
        return None

    # Internal link
    # Remove query params or fragments
    link_path = parsed_link.path
    if not link_path:
        return None

    # Resolve the absolute path for the link
    base_dir = os.path.dirname(filepath)
    absolute_path = os.path.abspath(os.path.join(base_dir, link_path))

    if not os.path.exists(absolute_path):
        return 'File not found'

    return None

def main():
    """Main function to run the link checker."""
    broken_links = []

    print("Starting link check...")
    for filepath in find_files('.'):
        print(f"Scanning {filepath}...")
        links = extract_links(filepath)
        for link in links:
            error = check_link(filepath, link)
            if error:
                broken_links.append({
                    'File Path': filepath,
                    'Broken URL': link,
                    'Error Code': error
                })
                print(f"  BROKEN: {link} ({error})")

    if broken_links:
        # Sort the broken_links list to prioritize "File not found" errors
        broken_links.sort(key=lambda x: x['Error Code'] != 'File not found')

        print(f"\nFound {len(broken_links)} broken links.")
        # Write to CSV
        with open(REPORT_FILENAME, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['File Path', 'Broken URL', 'Error Code'])
            writer.writeheader()
            writer.writerows(broken_links)
        print(f"Report saved to {REPORT_FILENAME}")
    else:
        print("\nNo broken links found.")

if __name__ == '__main__':
    main()
