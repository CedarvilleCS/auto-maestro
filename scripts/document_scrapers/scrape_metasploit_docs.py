"""Script to download Metasploit documentation by cloning to a temporary directory.

This script clones the repository to a system temporary directory,
extracts needed folders, then cleans up automatically.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_URL = "https://github.com/rapid7/metasploit-framework.git"

# Folders we want to download (path in repo -> output folder name)
FOLDERS_TO_EXTRACT = {
    "docs/metasploit-framework.wiki": "metasploit-framework.wiki",
    "documentation/cli": "cli",
    "documentation/modules": "modules",
}

# Wiki subfolders to exclude
WIKI_EXCLUDE = ["dev", "git"]


def main():
    """Download Metasploit documentation folders."""
    print("==========================================")
    print("Metasploit Documentation Extractor")
    print("==========================================")
    print("")

    # Create output directory relative to script location
    script_dir = Path(__file__).parent
    TARGET_DOC_DIR = script_dir / "scraped_raw_docs" / "metasploit_docs"

    # Use a temporary directory for cloning
    with tempfile.TemporaryDirectory() as temp_dir:
        clone_dir = Path(temp_dir) / "msf-clone"

        # 1. Clone repository
        print("[1/4] Cloning repository (depth 1)...")
        try:
            # Simple shallow clone
            subprocess.run(
                ["git", "clone", "--depth", "1", REPO_URL, str(clone_dir)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )

            print("  ✓ Repository cloned to temporary directory")
        except subprocess.CalledProcessError as e:
            print("  ✗ Failed to clone repository")
            if e.stderr:
                print(f"  Error: {e.stderr}")
            sys.exit(1)
        except FileNotFoundError:
            print("  ✗ 'git' command not found. Please ensure git is installed.")
            sys.exit(1)

        print("")

        # 2. Clean up wiki folder
        print("[2/4] Cleaning up wiki subfolders...")
        wiki_path = clone_dir / "docs" / "metasploit-framework.wiki"

        if wiki_path.exists():
            for unwanted in WIKI_EXCLUDE:
                unwanted_path = wiki_path / unwanted
                if unwanted_path.exists():
                    shutil.rmtree(unwanted_path)
                    print(f"  ✓ Removed {unwanted} from wiki")

        print("")

        # 3. Create target directory and copy folders
        print("[3/4] Copying documentation folders...")
        if TARGET_DOC_DIR.exists():
            print(f"  ⚠️  Directory {TARGET_DOC_DIR} already exists. Removing...")
            shutil.rmtree(TARGET_DOC_DIR)

        TARGET_DOC_DIR.mkdir(parents=True, exist_ok=True)

        total_files = 0
        for source_rel_path, output_folder in FOLDERS_TO_EXTRACT.items():
            source_path = clone_dir / source_rel_path
            dest_path = TARGET_DOC_DIR / output_folder

            if source_path.exists():
                shutil.copytree(source_path, dest_path)
                # Count files
                file_count = sum(1 for _ in dest_path.rglob("*") if _.is_file())
                print(f"  ✓ Copied {output_folder} ({file_count} files)")
                total_files += file_count
            else:
                print(f"  ⚠️  Source path not found: {source_rel_path}")

        print("")

        # 4. Summary (cleanup happens automatically when exiting 'with' block)
        print("[4/4] Cleanup")
        print("  ✓ Temporary clone directory will be automatically removed")
        print("")

    print("==========================================")
    print("✓ Documentation extraction complete!")
    print(f"  Total files: {total_files}")
    print(f"  Files saved to: {TARGET_DOC_DIR.absolute()}")
    print("==========================================")


if __name__ == "__main__":
    main()
