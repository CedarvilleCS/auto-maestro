# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "beautifulsoup4",
# ]
# ///
r"""
Script to scrape telnet documentation pages and save as text files.
Extracts specific content sections from Oracle docs and Microsoft Learn docs.
"""

from pathlib import Path

import requests
from bs4 import BeautifulSoup

# URLs to scrape
URLS = {
    "telnet - Microsoft Learn": "https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/telnet",
    "telnet close": "https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/telnet-close",
    "telnet display": "https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/telnet-display",
    "telnet open": "https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/telnet-open",
    "telnet quit": "https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/telnet-quit",
    "telnet send": "https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/telnet-send",
    "telnet set": "https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/telnet-set",
    "telnet status": "https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/telnet-status",
    "telnet unset": "https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/telnet-unset",
    "telnet - man pages section 1_ User Commands": "https://docs.oracle.com/cd/E86824_01/html/E54763/telnet-1.html",
}


def scrape_oracle_docs(url):
    """
    Scrape content from Oracle documentation page (starting from main_content anchor).
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
        raise

    soup = BeautifulSoup(response.content, "html.parser")

    # Find the main content anchor
    main_anchor = soup.find("a", id="main_content")
    if not main_anchor:
        print("  ✗ Could not find main_content anchor")
        return None

    # Get the parent element that contains the content
    content_container = main_anchor.find_parent("div", class_="pagePane")
    if not content_container:
        # Try to get content after the anchor
        content_container = main_anchor.parent

    if content_container:
        return content_container.get_text(separator="\n", strip=True)

    print("  ✗ Could not extract content")
    return None


def scrape_microsoft_learn(url):
    """Scrape content from Microsoft Learn page (div data-main-column)."""
    # Add headers to avoid 403 errors
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
    response = requests.get(url, timeout=10, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")

    # Try multiple ways to find the main content
    # Method 1: CSS selector for data-main-column
    main_column = soup.select_one("[data-main-column]")
    if main_column:
        return main_column.get_text(separator="\n", strip=True)

    # Method 2: Look for main content by id
    main_content = soup.find("main", id="main")
    if main_content:
        return main_content.get_text(separator="\n", strip=True)

    # Method 3: Find main tag
    main_tag = soup.find("main")
    if main_tag:
        return main_tag.get_text(separator="\n", strip=True)

    # Debug: Show what we're getting
    print("  ✗ Could not find main content")
    print(f"  DEBUG: Response length: {len(response.text)} bytes")
    print(f"  DEBUG: Title found: {soup.title.string if soup.title else 'None'}")
    print(f"  DEBUG: Has <main> tag: {soup.find('main') is not None}")
    print(
        f"  DEBUG: Has [data-main-column]: {soup.select_one('[data-main-column]') is not None}"  # noqa: E501
    )

    # Save HTML for inspection
    debug_file = Path(__file__).parent / f"debug_{url.split('/')[-1]}.html"
    with open(debug_file, "w", encoding="utf-8") as f:
        f.write(response.text)
    print(f"  DEBUG: Saved response to {debug_file.name} for inspection")

    return None


def main():
    # Create output directory relative to script location
    script_dir = Path(__file__).parent
    output_dir = script_dir / "scraped_raw_docs" / "telnet_docs"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}\n")

    print(f"Found {len(URLS)} URLs to process\n")

    for name, url in URLS.items():
        print(f"Processing: {name}")
        print(f"  URL: {url}")

        try:
            # Determine which scraping method to use
            if "microsoft.com" in url or "learn.microsoft" in url:
                content = scrape_microsoft_learn(url)
            elif "docs.oracle.com" in url or "oracle.com" in url:
                content = scrape_oracle_docs(url)
            else:
                print(f"  ✗ Unknown URL format: {url}")
                continue

            if content:
                # Generate output filename in the subfolder
                output_file = output_dir / f"{name}.txt"

                # Save to file
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(content)

                print(f"  ✓ Saved to: {output_file.name}")
                print(f"  Content length: {len(content)} characters\n")
            else:
                print(f"  ✗ Could not extract content from {url}\n")

        except requests.RequestException as e:
            print(f"  ✗ Error fetching {url}: {e}\n")
        except Exception as e:
            print(f"  ✗ Error processing {name}: {e}\n")

    print("Scraping complete!")


if __name__ == "__main__":
    main()
