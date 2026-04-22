"""Script to download THC-Hydra documentation by cloning to a temporary directory.

This script clones the repository to a system temporary directory,
extracts needed files, then cleans up automatically.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_URL = "https://github.com/vanhauser-thc/thc-hydra.git"
BRANCH = "master"

# Files we want to extract (paths in repo)
FILES_TO_EXTRACT = [
    "README",
    "hydra.1",
]


def main():
    """Download THC-Hydra documentation files."""
    print("==========================================")
    print("THC-Hydra Documentation Extractor")
    print("==========================================")
    print("")

    # Create output directory relative to script location
    script_dir = Path(__file__).parent
    OUTPUT_DIR = script_dir / "scraped_raw_docs" / "hydra_docs"

    # Use a temporary directory for cloning
    with tempfile.TemporaryDirectory() as temp_dir:
        clone_dir = Path(temp_dir) / "hydra-clone"

        # 1. Clone repository
        print("[1/4] Cloning repository (depth 1)...")
        try:
            # Simple shallow clone - sparse checkout doesn't work for individual files
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

        # 2. Create output directory
        print("[2/4] Creating output directory...")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ Created {OUTPUT_DIR}")
        print("")

        # 3. Extract files
        print("[3/4] Extracting documentation files...")
        success_count = 0

        for file_name in FILES_TO_EXTRACT:
            source_file = clone_dir / file_name

            if source_file.exists():
                # Add .txt extension for README for Windows compatibility
                output_name = f"{file_name}.txt" if file_name == "README" else file_name
                dest_file = OUTPUT_DIR / output_name

                shutil.copy2(source_file, dest_file)
                print(f"  ✓ Copied {output_name}")
                success_count += 1
            else:
                print(f"  ⚠️  {file_name} not found in repository")

        print("")

        # 4. Summary (cleanup happens automatically when exiting 'with' block)
        print("[4/4] Cleanup")
        print("  ✓ Temporary clone directory will be automatically removed")
        print("")

    if success_count > 0:
        print("==========================================")
        print("✓ Documentation extraction complete!")
        print(f"  Successfully extracted {success_count}/{len(FILES_TO_EXTRACT)} files")
        print(f"  Files saved to: {OUTPUT_DIR.absolute()}")
        print("==========================================")
    else:
        print("✗ No files were extracted successfully")
        sys.exit(1)


if __name__ == "__main__":
    main()
