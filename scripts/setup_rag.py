#!/usr/bin/env python
"""Unified script for scraping documentation and building RAG databases.

This script handles both documentation collection and RAG database creation
for security tools in AutoMAESTRO.
"""

import argparse
import hashlib
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, List, Tuple

import chromadb

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from packages.backend.src.backend.ai_graph import ChromaSentenceEmbeddings

# Tool configurations - maps tool names to their scrapers and docs
TOOL_CONFIGS: Dict[str, Dict[str, str]] = {
    "nmap": {
        "docs_path": "./scripts/document_scrapers/scraped_raw_docs/nmap_docs",
        "description": "Nmap network scanning and discovery tool",
        "scraper_module": "scrape_nmap_docs",
    },
    "metasploit": {
        "docs_path": "./scripts/document_scrapers/scraped_raw_docs/metasploit_docs",
        "description": "Metasploit penetration testing framework",
        "scraper_module": "scrape_metasploit_docs",
    },
    "hydra": {
        "docs_path": "./scripts/document_scrapers/scraped_raw_docs/hydra_docs",
        "description": "THC-Hydra password cracking tool",
        "scraper_module": "scrape_hydra_docs",
    },
    "hashcat": {
        "docs_path": "./scripts/document_scrapers/scraped_raw_docs/hashcat_docs",
        "description": "Hashcat password recovery tool",
        "scraper_module": "scrape_hashcat_docs",
    },
    "ssh": {
        "docs_path": "./scripts/document_scrapers/scraped_raw_docs/ssh_docs",
        "description": "OpenSSH secure shell documentation",
        "scraper_module": "scrape_ssh_docs",
    },
    "telnet": {
        "docs_path": "./scripts/document_scrapers/scraped_raw_docs/telnet_docs",
        "description": "Telnet protocol documentation",
        "scraper_module": "scrape_telnet_docs",
    },
    "psexec": {
        "docs_path": "./scripts/document_scrapers/scraped_raw_docs/psexec_docs",
        "description": "PsExec remote execution tool",
        "scraper_module": "scrape_psexec_docs",
    },
}


def import_scraper(module_name: str) -> Callable[[], None]:
    """Dynamically import a scraper module.

    Args:
        module_name: Name of the scraper module to import

    Returns:
        The main() function from the scraper module
    """
    scraper_path = Path(__file__).parent / "document_scrapers"
    sys.path.insert(0, str(scraper_path))

    module = __import__(module_name)
    return module.main


def scrape_tool_docs(
    tool_name: str, config: Dict[str, str], force: bool = False
) -> bool:
    """Scrape documentation for a specific tool.

    Args:
        tool_name: Name of the tool
        config: Tool configuration dictionary
        force: Force re-scraping even if docs exist

    Returns:
        True if scraping succeeded, False otherwise
    """
    docs_path = Path(config["docs_path"])

    # Check if docs already exist
    if not force and docs_path.exists() and any(docs_path.iterdir()):
        print(f"   Documentation already exists for {tool_name}, skipping scrape")
        print("   (Use --force-scrape to re-download)")
        return True

    print(f"   Scraping {tool_name} documentation...")

    try:
        scraper_func = import_scraper(config["scraper_module"])
        scraper_func()
        print(f"   ✓ {tool_name} documentation scraped successfully")
        return True
    except Exception as e:
        print(f"   ✗ Failed to scrape {tool_name}: {str(e)}")
        return False


def split_text_into_chunks(
    text: str, chunk_size: int = 1000, chunk_overlap: int = 100
) -> List[str]:
    """Split text into overlapping chunks.

    Args:
        text: Text to split
        chunk_size: Maximum size of each chunk
        chunk_overlap: Number of characters to overlap between chunks

    Returns:
        List of text chunks
    """
    lines = text.split("\n")
    chunks = []
    current_chunk = []
    current_size = 0

    for line in lines:
        line_size = len(line) + 1

        if current_size + line_size > chunk_size and current_chunk:
            chunks.append("\n".join(current_chunk))
            overlap_lines = (
                current_chunk[-chunk_overlap // 50 :] if chunk_overlap > 0 else []
            )
            current_chunk = overlap_lines[:]
            current_size = sum(len(line) + 1 for line in current_chunk)

        current_chunk.append(line)
        current_size += line_size

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks or [text]


def generate_file_hash(file_path: Path) -> str:
    """Generate a short hash of the file path for unique IDs.

    Args:
        file_path: Path to the file

    Returns:
        8-character hash string
    """
    path_str = str(file_path)
    return hashlib.md5(path_str.encode()).hexdigest()[:8]


def process_file(
    file_path: Path, tool_name: str
) -> Tuple[str, List[str], List[Dict], List[str]]:
    """Process a single file and prepare data for batch insertion.

    Args:
        file_path: Path to the file to process
        tool_name: Name of the tool this documentation belongs to

    Returns:
        Tuple of (file_name, chunks, metadatas, ids)
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if content.strip():
            chunks = split_text_into_chunks(content)

            # Generate unique file identifier
            file_hash = generate_file_hash(file_path)

            # Prepare metadata and IDs
            metadatas = [
                {
                    "tool": tool_name,
                    "file_path": str(file_path),
                    "chunk_id": str(i),
                    "file_name": file_path.name,
                }
                for i in range(len(chunks))
            ]
            # Use file hash to ensure uniqueness even with duplicate filenames
            ids = [f"{tool_name}_{file_hash}_chunk_{i}" for i in range(len(chunks))]

            return (file_path.name, chunks, metadatas, ids)
        else:
            return (file_path.name, [], [], [])
    except Exception as e:
        print(f"   [ERROR] Processing {file_path.name}: {str(e)}")
        return (file_path.name, [], [], [])


def add_tool_docs_to_collection(
    tool_name: str,
    docs_path: Path,
    collection: chromadb.Collection,
    max_workers: int,
    batch_size: int = 50,
) -> int:
    """Add all documentation files for a tool to the collection.

    Uses parallel processing for efficient chunking and indexing.

    Args:
        tool_name: Name of the tool
        docs_path: Path to directory containing tool documentation
        collection: ChromaDB collection to add to
        max_workers: Maximum number of parallel workers
        batch_size: Number of chunks to batch before inserting into ChromaDB

    Returns:
        Total number of chunks added
    """
    if not docs_path.exists():
        print(f"   [WARNING] Documentation directory does not exist: {docs_path}")
        return 0

    # Collect all files to process
    files_to_process = []
    for root, dirs, files in os.walk(docs_path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for file in files:
            if not file.startswith("."):
                files_to_process.append(Path(root) / file)

    if not files_to_process:
        print(f"   [WARNING] No files found in {docs_path}")
        return 0

    print(f"   Found {len(files_to_process)} file(s) to process")
    print(
        f"   Processing with {max_workers} worker(s), "
        f"batch size: {batch_size} chunks..."
    )

    total_chunks = 0
    files_processed = 0
    files_completed = 0

    # Batch accumulators
    batch_documents = []
    batch_metadatas = []
    batch_ids = []

    def insert_batch():
        """Insert accumulated batch into ChromaDB."""
        nonlocal total_chunks
        if batch_documents:
            collection.add(
                documents=batch_documents, metadatas=batch_metadatas, ids=batch_ids
            )
            total_chunks += len(batch_documents)
            batch_documents.clear()
            batch_metadatas.clear()
            batch_ids.clear()

    # Process files in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all file processing tasks
        future_to_file = {
            executor.submit(process_file, file_path, tool_name): file_path
            for file_path in files_to_process
        }

        # Collect results as they complete
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            files_completed += 1

            try:
                file_name, chunks, metadatas, ids = future.result()

                if chunks:
                    files_processed += 1
                    # Add to batch
                    batch_documents.extend(chunks)
                    batch_metadatas.extend(metadatas)
                    batch_ids.extend(ids)

                    print(
                        f"   [{files_completed}/{len(files_to_process)}] "
                        f"SUCCESS: {file_name}: {len(chunks)} chunk(s)"
                    )

                    # Insert batch if it reaches batch_size
                    if len(batch_documents) >= batch_size:
                        insert_batch()
                else:
                    print(
                        f"   [{files_completed}/{len(files_to_process)}] "
                        f"SKIPPED: {file_name}: (empty file)"
                    )
            except Exception as e:
                print(
                    f"   [{files_completed}/{len(files_to_process)}] "
                    f"ERROR: {file_path.name}: {str(e)}"
                )

    # Insert any remaining items in the batch
    insert_batch()

    print(
        f"   Summary: {files_processed}/{len(files_to_process)} "
        f"files processed, {total_chunks} total chunks"
    )
    return total_chunks


def setup_tool_collection(
    client: chromadb.PersistentClient,
    embedding_function: ChromaSentenceEmbeddings,
    tool_name: str,
    config: Dict[str, str],
    rebuild: bool,
    force_scrape: bool,
    max_workers: int,
    batch_size: int,
) -> Tuple[str, int]:
    """Set up a collection for a specific tool.

    Args:
        client: ChromaDB client
        embedding_function: Embedding function to use
        tool_name: Name of the tool
        config: Tool configuration dictionary
        rebuild: Whether to rebuild the RAG collection from scratch
        force_scrape: Whether to force re-scraping documentation
        max_workers: Maximum number of parallel workers for file processing
        batch_size: Number of chunks to batch before inserting

    Returns:
        Tuple of (tool_name, number of chunks added)
    """
    collection_name = f"{tool_name}_docs"

    print(f"\n{'─' * 60}")
    print(f"{tool_name.upper()}")
    print(f"   Description: {config['description']}")

    # Step 1: Scrape documentation if needed
    if not scrape_tool_docs(tool_name, config, force_scrape):
        print(f"   [ERROR] Failed to scrape documentation for {tool_name}")
        return (tool_name, 0)

    # Step 2: Build RAG database
    print(f"   Collection: {collection_name}")

    # Delete collection if rebuild flag is set
    if rebuild and collection_name in [c.name for c in client.list_collections()]:
        print("   Deleting existing collection for rebuild...")
        client.delete_collection(name=collection_name)

    # Create or get collection
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_function,
        metadata={"tool": tool_name, "description": config["description"]},
    )

    # Add documentation with parallel file processing
    docs_path = Path(config["docs_path"])
    chunks = add_tool_docs_to_collection(
        tool_name, docs_path, collection, max_workers, batch_size
    )

    if chunks > 0:
        print(f"   [SUCCESS] {tool_name.upper()} completed: {chunks} chunks indexed")
    else:
        print(f"   [WARNING] {tool_name.upper()} completed with no chunks indexed")

    return (tool_name, chunks)


def scrape_and_build_tool(
    client: chromadb.PersistentClient,
    embedding_function: ChromaSentenceEmbeddings,
    tool_name: str,
    config: Dict[str, str],
    rebuild: bool,
    force_scrape: bool,
    file_workers: int,
    batch_size: int,
) -> Tuple[str, int]:
    """Scrape and build RAG for a single tool in parallel.

    This function is designed to be run in a thread pool for parallel tool processing.

    Args:
        client: ChromaDB client
        embedding_function: Embedding function to use
        tool_name: Name of the tool
        config: Tool configuration dictionary
        rebuild: Whether to rebuild the RAG collection from scratch
        force_scrape: Whether to force re-scraping documentation
        file_workers: Number of parallel workers for file processing
        batch_size: Number of chunks to batch before inserting

    Returns:
        Tuple of (tool_name, number of chunks added)
    """
    return setup_tool_collection(
        client,
        embedding_function,
        tool_name,
        config,
        rebuild,
        force_scrape,
        file_workers,
        batch_size,
    )


def main() -> None:
    """Initialize and populate tool-specific RAG databases."""
    # Detect number of CPU cores, fallback to 4 if detection fails
    default_workers = os.cpu_count() or 4

    parser = argparse.ArgumentParser(
        description=(
            "Scrape documentation and build RAG databases "
            "for security tools in AutoMAESTRO"
        )
    )
    parser.add_argument(
        "--tools",
        type=str,
        help="Comma-separated list of tools to set up (default: all)",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild the RAG databases from scratch",
    )
    parser.add_argument(
        "--force-scrape",
        action="store_true",
        help="Force re-scraping of documentation even if it exists",
    )
    parser.add_argument(
        "--scrape-only",
        action="store_true",
        help="Only scrape documentation, don't build RAG database",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available tools and exit",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=default_workers,
        help=(
            f"Number of parallel workers (default: {default_workers}, "
            f"auto-detected from CPU cores)"
        ),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of chunks to batch before inserting into ChromaDB (default: 50)",
    )
    parser.add_argument(
        "--parallel-tools",
        type=int,
        default=1,
        help="Number of tools to process in parallel (default: 1, sequential)",
    )
    args = parser.parse_args()

    # List available tools
    if args.list:
        print("\nAvailable tools:")
        for tool, config in TOOL_CONFIGS.items():
            print(f"  * {tool:12} - {config['description']}")
        print()
        return

    # Determine which tools to set up
    if args.tools:
        tools_to_setup = [t.strip().lower() for t in args.tools.split(",")]
        # Validate tool names
        invalid_tools = [t for t in tools_to_setup if t not in TOOL_CONFIGS]
        if invalid_tools:
            print(f"[ERROR] Invalid tool names: {', '.join(invalid_tools)}")
            print(f"Valid tools: {', '.join(TOOL_CONFIGS.keys())}")
            sys.exit(1)
    else:
        tools_to_setup = list(TOOL_CONFIGS.keys())

    # Print configuration
    print("\n" + "=" * 60)
    print("AutoMAESTRO RAG System Setup")
    print("=" * 60)
    print(f"Tools to set up: {len(tools_to_setup)}/{len(TOOL_CONFIGS)}")
    if args.tools:
        print(f"   Selected: {', '.join(tools_to_setup)}")
    print(f"Scrape mode: {'FORCE' if args.force_scrape else 'AUTO (skip if exists)'}")

    if args.scrape_only:
        print("Mode: SCRAPE ONLY (no RAG database build)")
    else:
        print(f"RAG rebuild mode: {'ON' if args.rebuild else 'OFF'}")
        print(f"Parallel tools: {args.parallel_tools}")
        print(f"File workers per tool: {args.workers} (CPU cores: {os.cpu_count()})")
        print(f"Batch size: {args.batch_size} chunks")

        chroma_directory = "./chroma_db"
        os.makedirs(chroma_directory, exist_ok=True)
        print(f"Database location: {chroma_directory}")

    # Handle scrape-only mode
    if args.scrape_only:
        print("\n" + "=" * 60)
        print("Scraping Documentation")
        print("=" * 60)

        success_count = 0

        # Parallel scraping if multiple tools
        if args.parallel_tools > 1 and len(tools_to_setup) > 1:
            print(f"Scraping {len(tools_to_setup)} tools in parallel...")
            with ThreadPoolExecutor(max_workers=args.parallel_tools) as executor:
                future_to_tool = {
                    executor.submit(
                        scrape_tool_docs,
                        tool_name,
                        TOOL_CONFIGS[tool_name],
                        args.force_scrape,
                    ): tool_name
                    for tool_name in tools_to_setup
                }

                for idx, future in enumerate(as_completed(future_to_tool), 1):
                    tool_name = future_to_tool[future]
                    print(f"\n[{idx}/{len(tools_to_setup)}] {tool_name}...")
                    if future.result():
                        success_count += 1
        else:
            # Sequential scraping
            for idx, tool_name in enumerate(tools_to_setup, 1):
                print(f"\n[{idx}/{len(tools_to_setup)}] {tool_name}...")
                if scrape_tool_docs(
                    tool_name, TOOL_CONFIGS[tool_name], args.force_scrape
                ):
                    success_count += 1

        print(f"\n{'=' * 60}")
        print("Scraping Complete!")
        print(f"{'=' * 60}")
        print(f"Successfully scraped: {success_count}/{len(tools_to_setup)} tools")
        print("=" * 60 + "\n")
        return

    # Full workflow: scrape + build RAG
    client = chromadb.PersistentClient(path=chroma_directory)
    embedding_function = ChromaSentenceEmbeddings(
        model_name="all-MiniLM-L6-v2", use_gpu=False
    )

    # Process tools
    total_chunks = 0
    success_count = 0

    # Parallel processing if multiple tools
    if args.parallel_tools > 1 and len(tools_to_setup) > 1:
        print(
            f"\nProcessing {len(tools_to_setup)} tools in parallel "
            f"(max {args.parallel_tools} at a time)..."
        )
        with ThreadPoolExecutor(max_workers=args.parallel_tools) as executor:
            future_to_tool = {
                executor.submit(
                    scrape_and_build_tool,
                    client,
                    embedding_function,
                    tool_name,
                    TOOL_CONFIGS[tool_name],
                    args.rebuild,
                    args.force_scrape,
                    args.workers,
                    args.batch_size,
                ): tool_name
                for tool_name in tools_to_setup
            }

            for idx, future in enumerate(as_completed(future_to_tool), 1):
                tool_name = future_to_tool[future]
                print(f"\n[{idx}/{len(tools_to_setup)}] Completed {tool_name}")
                try:
                    _, chunks = future.result()
                    total_chunks += chunks
                    if chunks > 0:
                        success_count += 1
                except Exception as e:
                    print(f"   [ERROR] Setting up {tool_name}: {str(e)}")
    else:
        # Sequential processing
        for idx, tool_name in enumerate(tools_to_setup, 1):
            print(f"\n[{idx}/{len(tools_to_setup)}] Processing {tool_name}...")
            try:
                _, chunks = setup_tool_collection(
                    client,
                    embedding_function,
                    tool_name,
                    TOOL_CONFIGS[tool_name],
                    args.rebuild,
                    args.force_scrape,
                    args.workers,
                    args.batch_size,
                )
                total_chunks += chunks
                if chunks > 0:
                    success_count += 1
            except Exception as e:
                print(f"   [ERROR] Setting up {tool_name}: {str(e)}")

    # Summary
    print(f"\n{'=' * 60}")
    print("Setup Complete!")
    print(f"{'=' * 60}")
    print(f"Successfully set up: {success_count}/{len(tools_to_setup)} tools")
    print(f"Total chunks indexed: {total_chunks:,}")
    print(f"Database location: {chroma_directory}")

    if success_count < len(tools_to_setup):
        print(f"[WARNING] {len(tools_to_setup) - success_count} tool(s) had issues")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
