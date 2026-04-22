"""Script to scrape Nmap documentation from the official book.

This script extracts content from <section class="sect1"> elements
from the Nmap Reference Guide table of contents.
"""

import re
import time
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Base URL for the Nmap book table of contents
TOC_URL = "https://nmap.org/book/toc.html"
TOC_SELECTOR = "ul.toc"


def sanitize_filename(url: str) -> str:
    """Convert URL to a safe filename.

    Args:
        url: URL to convert

    Returns:
        Sanitized filename with .txt extension
    """
    # Parse the URL to get the path
    parsed = urlparse(url)
    path = parsed.path

    # Remove .html extension and leading slash
    if path.endswith(".html"):
        path = path[:-5]
    if path.startswith("/"):
        path = path[1:]

    # Replace slashes and other problematic characters with underscores
    filename = re.sub(r'[/\\:*?"<>|]', "_", path)

    # Remove consecutive underscores and trailing underscores
    filename = re.sub(r"_+", "_", filename).strip("_")

    # If filename is empty, use the domain
    if not filename:
        filename = parsed.netloc.replace(".", "_")

    return filename + ".txt"


def extract_toc_links(base_url: str, selector: str) -> set:
    """Extract all documentation links from the table of contents.

    Args:
        base_url: URL of the TOC page
        selector: CSS selector for the TOC section

    Returns:
        Set of full URLs (without fragments)
    """
    print(f"Fetching table of contents from: {base_url}")

    try:
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  ✗ Error fetching TOC: {e}")
        return set()

    soup = BeautifulSoup(response.text, "html.parser")

    # Find the table of contents section
    toc_section = soup.select_one(selector)

    if not toc_section:
        print(f"  ✗ Could not find element matching selector: {selector}")
        return set()

    # Extract and normalize URLs (remove fragments)
    base_urls = set()
    links = toc_section.find_all("a")

    for link in links:
        href = link.get("href")
        if href:
            full_url = urljoin(base_url, href)
            # Remove fragment identifier
            base_url_only = urldefrag(full_url)[0]
            base_urls.add(base_url_only)

    print(f"  ✓ Found {len(links)} total links")
    print(f"  ✓ Grouped into {len(base_urls)} unique base pages")

    return base_urls


def extract_section_text(url: str) -> str:
    """Extract text content from <section class="sect1"> elements.

    Args:
        url: URL of the documentation page

    Returns:
        Extracted text content, or None if extraction failed
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  ✗ Error fetching: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # Find all section elements with class="sect1"
    sections = soup.find_all("section", class_="sect1")

    if not sections:
        print("  ⚠️  No <section class='sect1'> found")
        return None

    # Extract text from all matching sections
    all_text = []
    for section in sections:
        text = section.get_text(separator="\n", strip=True)
        if text:
            all_text.append(text)

    if all_text:
        return "\n\n---\n\n".join(all_text)
    else:
        print("  ⚠️  No text content found in sections")
        return None


def main():
    """Scrape all Nmap documentation pages."""
    print("=" * 60)
    print("Nmap Documentation Scraper")
    print("=" * 60)
    print("")

    # Create output directory relative to script location
    script_dir = Path(__file__).parent
    output_dir = script_dir / "scraped_raw_docs" / "nmap_docs"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}\n")

    # Step 1: Extract all documentation URLs from TOC
    doc_urls = extract_toc_links(TOC_URL, TOC_SELECTOR)

    if not doc_urls:
        print("✗ No URLs found to process")
        return

    print(f"\nFound {len(doc_urls)} documentation pages to scrape\n")

    # Step 2: Process each URL
    success_count = 0
    fail_count = 0

    for i, url in enumerate(sorted(doc_urls), 1):
        print(f"[{i}/{len(doc_urls)}] Processing: {url}")

        content = extract_section_text(url)

        if content:
            filename = sanitize_filename(url)
            filepath = output_dir / filename

            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f"Source URL: {url}\n")
                    f.write("=" * 70 + "\n\n")
                    f.write(content)

                print(f"  ✓ Saved to: {filename}")
                print(f"  Content length: {len(content)} characters")
                success_count += 1
            except Exception as e:
                print(f"  ✗ Error saving file: {e}")
                fail_count += 1
        else:
            print("  ✗ Could not extract content")
            fail_count += 1

        # Be polite to the server
        time.sleep(0.5)
        print()

    # Summary
    print("=" * 60)
    print("Scraping complete!")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {fail_count}")
    print(f"  Total: {len(doc_urls)}")
    print(f"  Files saved to: {output_dir.absolute()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
