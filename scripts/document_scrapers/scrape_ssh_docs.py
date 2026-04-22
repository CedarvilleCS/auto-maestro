# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "beautifulsoup4",
# ]
# ///
"""
Script to scrape OpenSSH manual pages from man.openbsd.org
Saves the main manual text content to individual text files
"""

import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# List of URLs to scrape
URLS = [
    "https://man.openbsd.org/ssh",
    "https://man.openbsd.org/sshd",
    "https://man.openbsd.org/ssh_config",
    "https://man.openbsd.org/sshd_config",
    "https://man.openbsd.org/ssh-agent",
    "https://man.openbsd.org/ssh-add",
    "https://man.openbsd.org/sftp",
    "https://man.openbsd.org/scp",
    "https://man.openbsd.org/ssh-keygen",
    "https://man.openbsd.org/sftp-server",
    "https://man.openbsd.org/ssh-keyscan",
    "https://man.openbsd.org/ssh-keysign",
]


def scrape_manual_page(url):
    """
    Scrape a manual page and extract the main manual text content

    Args:
        url: URL of the manual page to scrape

    Returns:
        str: The text content from the main.manual-text section, or None if failed
    """
    try:
        print(f"Fetching: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Find the main element with class "manual-text"
        main_section = soup.find("main", class_="manual-text")

        if main_section:
            # Extract text content
            text_content = main_section.get_text(separator="\n", strip=True)
            return text_content
        else:
            print(f"  Warning: Could not find <main class='manual-text'> in {url}")
            return None

    except requests.RequestException as e:
        print(f"  Error fetching {url}: {e}")
        return None
    except Exception as e:
        print(f"  Error processing {url}: {e}")
        return None


def get_filename_from_url(url):
    """
    Generate a filename from the URL

    Args:
        url: URL to extract the name from

    Returns:
        str: Filename for saving the content
    """
    # Extract the last part of the URL (the command name)
    command_name = url.rstrip("/").split("/")[-1]
    return f"{command_name}_manual.txt"


def main():
    """Main function to scrape all manual pages"""
    print("Starting OpenSSH manual page scraper\n")

    # Create output directory relative to script location
    script_dir = Path(__file__).parent
    output_dir = script_dir / "scraped_raw_docs" / "ssh_docs"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}\n")

    success_count = 0
    fail_count = 0

    for url in URLS:
        content = scrape_manual_page(url)

        if content:
            filename = get_filename_from_url(url)
            filepath = output_dir / filename

            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"  ✓ Saved to: {filepath}")
                success_count += 1
            except Exception as e:
                print(f"  ✗ Error saving file {filepath}: {e}")
                fail_count += 1
        else:
            fail_count += 1

        # Be polite to the server - add a small delay between requests
        time.sleep(0.5)
        print()

    print("\n" + "=" * 50)
    print("Scraping complete!")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {fail_count}")
    print(f"  Total: {len(URLS)}")
    print("=" * 50)


if __name__ == "__main__":
    main()
