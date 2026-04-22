# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "beautifulsoup4",
# ]
# ///
"""
Script to scrape hashcat wiki pages and save as text files.
Extracts content from <div class="page"> within <div class="dokuwiki">
from the hashcat.net wiki pages.
"""

import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# URLs to scrape
URLS = [
    "https://hashcat.net/wiki/doku.php?id=hashcat",
    "https://hashcat.net/wiki/doku.php?id=hashcat_utils",
    "https://hashcat.net/wiki/doku.php?id=dictionary_attack",
    "https://hashcat.net/wiki/doku.php?id=combinator_attack",
    "https://hashcat.net/wiki/doku.php?id=mask_attack",
    "https://hashcat.net/wiki/doku.php?id=hybrid_attack",
    "https://hashcat.net/wiki/doku.php?id=toggle_attack_with_rules",
    "https://hashcat.net/wiki/doku.php?id=association_attack",
    "https://hashcat.net/wiki/doku.php?id=rule_based_attack",
    "https://hashcat.net/wiki/doku.php?id=toggle_case_attack",
    "https://hashcat.net/wiki/doku.php?id=example_hashes",
    "https://hashcat.net/wiki/doku.php?id=hash_format_guidance",
    "https://hashcat.net/wiki/doku.php?id=ubernoobs",
    "https://hashcat.net/wiki/doku.php?id=timeout_patch",
    "https://hashcat.net/wiki/doku.php?id=hccapx",
    "https://hashcat.net/wiki/doku.php?id=restore",
    "https://hashcat.net/wiki/doku.php?id=cracking_wpawpa2",
    "https://hashcat.net/wiki/doku.php?id=rules_with_maskprocessor",
    "https://hashcat.net/wiki/doku.php?id=hybrid_atttack_with_rules",
    "https://hashcat.net/wiki/doku.php?id=machine_readable",
    "https://hashcat.net/wiki/doku.php?id=distributing-work",
    "https://hashcat.net/wiki/doku.php?id=hash-type-categories",
    "https://hashcat.net/wiki/doku.php?id=combination_count_formula",
    "https://hashcat.net/wiki/doku.php?id=ssh_running_process",
    "https://hashcat.net/wiki/doku.php?id=hashcat_on_windows_ssh",
]


def scrape_hashcat_wiki(url):
    """
    Scrape a hashcat wiki page and extract content from <div class="page">

    Args:
        url: URL of the wiki page to scrape

    Returns:
        str: The text content from the page div, or None if failed
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    try:
        response = requests.get(url, timeout=15, headers=headers)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            print("  ⚠️  Website blocked the request (403 Forbidden)")
            return None
        print(f"  ✗ HTTP Error: {e}")
        return None
    except requests.RequestException as e:
        print(f"  ✗ Request Error: {e}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")

    # Find the dokuwiki div
    dokuwiki_div = soup.find("div", class_="dokuwiki")
    if not dokuwiki_div:
        print("  ✗ Could not find <div class='dokuwiki'>")
        return None

    # Find the page div within dokuwiki
    page_div = dokuwiki_div.find("div", class_="page")
    if not page_div:
        print("  ✗ Could not find <div class='page'> within dokuwiki div")
        return None

    # Extract text content
    text_content = page_div.get_text(separator="\n", strip=True)
    return text_content


def get_filename_from_url(url):
    """
    Generate a filename from the URL

    Args:
        url: URL to extract the name from

    Returns:
        str: Filename for saving the content
    """
    # Extract the id parameter from the URL
    # Example: https://hashcat.net/wiki/doku.php?id=hashcat -> hashcat
    if "?id=" in url:
        page_id = url.split("?id=")[-1]
        # Replace underscores with spaces for readability
        page_name = page_id.replace("_", " ")
        return f"{page_name}.txt"
    else:
        # Fallback: use the last part of the URL
        page_name = url.rstrip("/").split("/")[-1]
        return f"{page_name}.txt"


def main():
    """Main function to scrape all hashcat wiki pages"""
    print("Starting hashcat wiki page scraper\n")

    print(f"Found {len(URLS)} URLs to process\n")

    # Create output directory relative to script location
    script_dir = Path(__file__).parent
    output_dir = script_dir / "scraped_raw_docs" / "hashcat_docs"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}\n")

    success_count = 0
    fail_count = 0

    for i, url in enumerate(URLS, 1):
        print(f"[{i}/{len(URLS)}] Processing: {url}")

        content = scrape_hashcat_wiki(url)

        if content:
            filename = get_filename_from_url(url)
            filepath = output_dir / filename

            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"  ✓ Saved to: {filepath.name}")
                print(f"  Content length: {len(content)} characters")
                success_count += 1
            except Exception as e:
                print(f"  ✗ Error saving file {filepath}: {e}")
                fail_count += 1
        else:
            print("  ✗ Could not extract content")
            fail_count += 1

        # Be polite to the server - add a delay between requests
        time.sleep(0.5)
        print()

    print("=" * 60)
    print("Scraping complete!")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {fail_count}")
    print(f"  Total: {len(URLS)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
