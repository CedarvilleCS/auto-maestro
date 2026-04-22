# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "beautifulsoup4",
# ]
# ///
"""
Script to scrape PsExec documentation pages and save as text files.

Extracts content from Microsoft Learn.
"""

from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

# URLs to scrape
URLS = {
    "PsExec - Microsoft Learn": "https://learn.microsoft.com/en-us/sysinternals/downloads/psexec",
}


def scrape_microsoft_learn(url: str) -> Optional[str]:
    """Scrape content from Microsoft Learn page.

    Args:
        url: URL to scrape

    Returns:
        Extracted text content, or None if extraction failed
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
        print("  ✗ HTTP Error")
        return None
    except requests.RequestException:
        print("  ✗ Request Error")
        return None

    soup = BeautifulSoup(response.content, "html.parser")

    # Try multiple selectors for main content
    selectors = ["[data-main-column]", "main#main", "main"]

    for selector in selectors:
        main_content = soup.select_one(selector)
        if main_content:
            return main_content.get_text(separator="\n", strip=True)

    print("  ✗ Could not find main content")
    return None


def main() -> None:
    """Main function to scrape all PsExec documentation pages."""
    print("Starting PsExec documentation scraper\n")

    # Create output directory relative to script location
    script_dir = Path(__file__).parent
    output_dir = script_dir / "scraped_raw_docs" / "psexec_docs"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}\n")

    print(f"Found {len(URLS)} URLs to process\n")

    success_count = 0
    fail_count = 0

    for name, url in URLS.items():
        print(f"Processing: {name}")
        print(f"  URL: {url}")

        content = scrape_microsoft_learn(url)

        if content:
            # Generate output filename
            output_file = output_dir / f"{name}.txt"

            # Save to file
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(f"Source URL: {url}\n")
                    f.write("=" * 70 + "\n\n")
                    f.write(content)

                print(f"  ✓ Saved to: {output_file.name}")
                success_count += 1
            except OSError:
                print("  ✗ Error saving file")
                fail_count += 1
        else:
            print("  ✗ Could not extract content")
            fail_count += 1

        print()

    print("=" * 60)
    print("Scraping complete!")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {fail_count}")
    print(f"  Total: {len(URLS)}")
    print(f"  Files saved to: {output_dir.absolute()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
