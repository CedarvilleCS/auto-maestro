# pip install chromadb llama-cpp-python sentence-transformers torch scikit-learn

"""
Generic RAG System
==================

A Retrieval-Augmented Generation (RAG) system built to:
1. Process and index text files and documentation from any source
2. Create vector embeddings for efficient semantic search
3. Provide AI-powered query responses using local LLMs via llama-cpp-python

Features:
- Memory-efficient processing of large document collections
- Chunking with automatic overlap for context preservation
- Smart document filtering based on file types
- Incremental database building with resume capability
- Compressed vector storage with optional dimensionality reduction
- Conversational interface with history tracking
- Local LLM inference using llama-cpp-python (no external API needed)

Usage:
  python generic_rag_system.py [options]

Options:
  --rebuild              Rebuild the vector database from scratch
  --clean               Remove documents from paths no longer in configuration
  --compress            Apply vector quantization to reduce storage requirements
  --force               Reprocess all files even if they exist in the database
  --batch-size N        Process files in batches of N (default: 5)
  --chunk-size N        Split documents into N-character chunks (default: 500)
  --model-path PATH     Path to the GGUF model file for llama-cpp-python
  --source-paths PATH   Comma-separated list of source directories to index

Example:
  python generic_rag_system.py --rebuild --source-paths "/path/to/docs,/path/to/code"
  python generic_rag_system.py --model-path "./models/llama-2-7b-chat.gguf"
  python generic_rag_system.py                 # Normal usage after setup

Environment:
  - Requires a GGUF format model file for llama-cpp-python
  - Supports GPU acceleration for embeddings and inference
  - Uses SQLite 3.35+ (via pysqlite3) for ChromaDB storage

Author: Generic RAG System
"""

import argparse
import logging
import os
import time

import chromadb
import numpy as np
from llama_cpp import Llama

# Import SentenceTransformer for embeddings
from sentence_transformers import SentenceTransformer

# Update the ChromaSentenceEmbeddings class to include dimensionality reduction
from sklearn.decomposition import PCA

# Set up logging to suppress ChromaDB warnings and telemetry
logging.basicConfig(level=logging.INFO)
chroma_logger = logging.getLogger("chromadb")
chroma_logger.setLevel(logging.ERROR)  # Only show errors, not warnings

# Suppress urllib3 and requests telemetry warnings
urllib3_logger = logging.getLogger("urllib3.connectionpool")
urllib3_logger.setLevel(logging.ERROR)
backoff_logger = logging.getLogger("backoff")
backoff_logger.setLevel(logging.ERROR)
requests_logger = logging.getLogger("requests")
requests_logger.setLevel(logging.ERROR)

# Set environment variable to disable ChromaDB telemetry

os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

# Configuration section
#
# The system allows flexible configuration through command-line arguments
# and these default values. In production, you might want to move these
# to a configuration file.
#
# Key configuration parameters:
# - chroma_directory: Where the vector database is stored
# - embedding_model: The model used for creating vector embeddings
# - source paths: Where to find documents to index
# - LLM model: Path to the GGUF model file for response generation


# Create a more memory-efficient wrapper for SentenceTransformer
class ChromaSentenceEmbeddings:
    """
    Memory-efficient wrapper for SentenceTransformer with optional PCA dimensionality
    reduction.

    This class generates embeddings in batches to minimize memory usage, and can
    optionally reduce dimensions with PCA to save storage space. GPU acceleration
    is used when available.

    Args:
        model_name (str): The SentenceTransformer model to use
        use_gpu (bool): Whether to use GPU acceleration
        target_dimensions (int, optional): If provided, reduce embeddings to this
            dimension
    """

    def __init__(
        self,
        model_name="all-MiniLM-L6-v2",
        use_gpu=False,
        target_dimensions=None,
    ):
        # Use CPU for better compatibility on laptops without CUDA
        device = "cuda" if use_gpu else "cpu"
        self.model = SentenceTransformer(model_name, device=device)
        print(f"Initialized SentenceTransformer with model {model_name} on {device}")

        # Make PCA optional - only use if target_dimensions is specified
        self.target_dimensions = target_dimensions
        self.pca = None
        self.use_pca = target_dimensions is not None

    def __call__(self, input):
        if isinstance(input, str):
            input = [input]

        # Process in smaller batches to reduce memory usage
        batch_size = 8
        all_embeddings = []

        for i in range(0, len(input), batch_size):
            batch = input[i : i + batch_size]
            batch_embeddings = self.model.encode(batch)
            all_embeddings.extend(batch_embeddings)

        # Apply dimensionality reduction if needed and enough data is available
        if self.use_pca and len(all_embeddings) > 0:
            all_embeddings = np.array(all_embeddings)

            # Only fit PCA if we haven't already, and we have enough samples
            if self.pca is None and len(all_embeddings) >= self.target_dimensions:
                print(
                    f"Fitting PCA to reduce dimensions from {
                        all_embeddings.shape[1]
                    } to {self.target_dimensions}"
                )
                self.pca = PCA(n_components=self.target_dimensions)
                all_embeddings = self.pca.fit_transform(all_embeddings)
            elif self.pca is not None:
                # Apply existing PCA transformation
                all_embeddings = self.pca.transform(all_embeddings)
            else:
                # Not enough samples yet, keep original dimensions
                print(
                    f"Not enough samples for PCA ({len(all_embeddings)} < {
                        self.target_dimensions
                    }), keeping original dimensions"
                )

        return (
            all_embeddings.tolist()
            if isinstance(all_embeddings, np.ndarray)
            else all_embeddings
        )

    def name(self):
        """Return the name of this embedding function for ChromaDB compatibility"""
        return "ChromaSentenceEmbeddings"

    def embed_query(self, input):
        """Embed a single query string - required by ChromaDB API"""
        # Handle both string and list inputs from ChromaDB
        if isinstance(input, list):
            if len(input) == 1:
                text = input[0]
            else:
                # If multiple queries, just use the first one
                text = input[0] if input else ""
        else:
            text = str(input) if input else ""

        # Use the same encoding approach as the __call__ method
        embeddings = self.model.encode([text], convert_to_tensor=False)

        # Apply PCA if available and configured
        if self.use_pca and self.pca is not None:
            embeddings = self.pca.transform(embeddings)

        # ChromaDB expects a list of embeddings, even for a single query
        return [embeddings[0].tolist()]


# Define functions first
def should_process_file(file_path):
    """Check if a file should be processed based on extension and size"""
    # Skip binary files and non-text files
    binary_extensions = {
        # Image formats
        ".gif",
        ".png",
        ".jpg",
        ".jpeg",
        ".ico",
        ".svg",
        ".xcf",
        # Compiled/binary files
        ".bin",
        ".so",
        ".dll",
        ".exe",
        ".obj",
        ".o",
        ".pdf",
        # Compressed files
        ".zip",
        ".tar",
        ".gz",
        ".xpi",
        ".whl",
        ".ap_",
        # Database files
        ".db",
        ".ics",
        # Document formats
        ".odt",
        ".pdf",
        # Map files
        ".map",
        # Resource/binary data
        ".lnk",
        ".2",
        ".jar",
        # Other binary formats
        ".ps",
        ".xcf",
        ".dia",
    }

    ext = os.path.splitext(file_path)[1].lower()
    if ext in binary_extensions:
        return False

    # Skip very large files (adjust size limit as needed)
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > 100:
            print(f"Skipping large file: {file_path} ({size_mb:.1f}MB)")
            return False
    except:  # noqa: E722
        pass

    return True


def file_exists_in_collection(file_path, collection):
    """Check if a file has already been added to the collection"""
    # Query the collection for documents with this file path
    try:
        # Try using the where parameter instead of filter
        results = collection.query(
            query_texts=[""], where={"file_path": file_path}, n_results=1
        )
        return len(results["ids"][0]) > 0
    except Exception:
        # If that fails too, try a different approach
        try:
            all_data = collection.get()
            for metadata in all_data.get("metadatas", []):
                if metadata and metadata.get("file_path") == file_path:
                    return True
            return False
        except Exception as e2:
            print(f"Warning: Could not check if file exists in collection: {e2}")
            return False


# Function to add text-readable files to ChromaDB recursively with chunking
def add_files_to_chromadb(folder_path, collection, skip_existing=True):
    processed = 0
    added = 0
    skipped_existing = 0
    chunks_added = 0
    skipped = 0
    start_time = time.time()

    print(f"Starting to process files in {folder_path}...")

    # First pass to count total files for percentage calculation
    total_files = 0
    for root, dirs, files in os.walk(folder_path):
        # Skip hidden directories and files
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        files = [f for f in files if not f.startswith(".")]
        total_files += len(files)

    print(f"Found {total_files} files in {folder_path}")

    # Process files one by one with memory management
    file_count = 0
    for root, dirs, files in os.walk(folder_path):
        # Skip hidden directories and files
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        files = [f for f in files if not f.startswith(".")]

        for file in files:
            file_count += 1
            file_path = os.path.join(root, file)

            # Check if we should process this file
            if not should_process_file(file_path):
                skipped += 1
                continue

            # Skip if file already exists in collection (unless force reprocessing)
            if skip_existing and file_exists_in_collection(file_path, collection):
                skipped_existing += 1
                if file_count % 100 == 0:
                    progress = file_count / total_files * 100
                    print(
                        f"Progress: {file_count}/{total_files} files ({progress:.1f}%) - {skipped_existing} already indexed"  # noqa: E501
                    )
                continue

            print(f"Processing {file_count}/{total_files}: {file_path}")

            # Process the file
            result = process_file_with_limited_memory(file_path, collection)
            processed += result["processed"]
            added += result["added"]
            chunks_added += result["chunks_added"]
            skipped += result["skipped"]

            # Progress update
            if file_count % 10 == 0:
                elapsed = time.time() - start_time
                rate = file_count / elapsed if elapsed > 0 else 0
                progress = file_count / total_files * 100
                print(
                    f"Progress: {file_count}/{total_files} files ({progress:.1f}%) - {rate:.2f} files/sec"  # noqa: E501
                )

    # Final summary
    elapsed = time.time() - start_time
    print(f"\nSummary for {folder_path}:")
    print(f"  Total files processed: {processed}")
    print(f"  Successfully added: {added}")
    print(f"  Skipped (already exists): {skipped_existing}")
    print(f"  Skipped (unsuitable/errors): {skipped}")
    print(f"  Total chunks added: {chunks_added}")
    print(f"  Total time: {elapsed:.1f} seconds ({elapsed / 60:.1f} minutes)")
    print(
        f"  Average speed: {processed / elapsed:.2f} files/sec, {chunks_added / elapsed:.2f} chunks/sec"  # noqa: E501
    )
    print("------------------------------------")


def process_file_with_limited_memory(file_path, collection):
    processed = 0
    added = 0
    chunks_added = 0
    skipped = 0
    try:
        # For very large files, read and process in chunks
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB

        if file_size > 50:
            print(f" - Large file ({file_size:.1f}MB), processing in chunks...")
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    chunk_texts = []
                    chunk_count = 0

                    while True:
                        # Read file in 10MB chunks
                        chunk = f.read(10 * 1024 * 1024)
                        if not chunk:
                            break

                        # Split this chunk into smaller pieces
                        text_chunks = split_text_into_chunks(
                            chunk, chunk_size=1000, chunk_overlap=100
                        )

                        for text_chunk in text_chunks:
                            if text_chunk.strip():  # Only add non-empty chunks
                                chunk_texts.append(text_chunk)
                                chunk_count += 1

                                # Add in batches to avoid memory issues
                                if len(chunk_texts) >= 50:
                                    collection.add(
                                        documents=chunk_texts,
                                        metadatas=[
                                            {
                                                "file_path": file_path,
                                                "chunk_id": f"{chunk_count - len(chunk_texts) + i}",  # noqa: E501
                                            }
                                            for i in range(len(chunk_texts))
                                        ],
                                        ids=[
                                            f"{file_path}_chunk_{chunk_count - len(chunk_texts) + i}"  # noqa: E501
                                            for i in range(len(chunk_texts))
                                        ],
                                    )
                                    chunks_added += len(chunk_texts)
                                    chunk_texts = []

                    # Add remaining chunks
                    if chunk_texts:
                        collection.add(
                            documents=chunk_texts,
                            metadatas=[
                                {
                                    "file_path": file_path,
                                    "chunk_id": f"{chunk_count - len(chunk_texts) + i}",
                                }
                                for i in range(len(chunk_texts))
                            ],
                            ids=[
                                f"{file_path}_chunk_{chunk_count - len(chunk_texts) + i}"  # noqa: E501
                                for i in range(len(chunk_texts))
                            ],
                        )
                        chunks_added += len(chunk_texts)

                    processed += 1
                    added += 1
                    print(f" - Added {chunk_count} chunks")

            except Exception as e:
                skipped += 1
                print(f" - Error processing large file: {str(e)}")

        else:
            # Regular processing for smaller files
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                if content.strip():  # Only process non-empty files
                    # Split content into chunks
                    chunks = split_text_into_chunks(
                        content, chunk_size=1000, chunk_overlap=100
                    )

                    # Add chunks to collection
                    collection.add(
                        documents=chunks,
                        metadatas=[
                            {"file_path": file_path, "chunk_id": str(i)}
                            for i in range(len(chunks))
                        ],
                        ids=[f"{file_path}_chunk_{i}" for i in range(len(chunks))],
                    )

                    processed += 1
                    added += 1
                    chunks_added += len(chunks)
                    print(f" - Added {len(chunks)} chunks")
                else:
                    skipped += 1
                    print(" - Skipped (empty file)")

            except Exception as e:
                skipped += 1
                print(f" - Error: {str(e)}")

    except Exception as e:
        skipped += 1
        print(f" - Error: {str(e)}")

    return {
        "processed": processed,
        "added": added,
        "chunks_added": chunks_added,
        "skipped": skipped,
    }


# Function to split text into chunks with overlap
def split_text_into_chunks(text, chunk_size=1000, chunk_overlap=100):
    # Simple line-based chunking
    lines = text.split("\n")
    chunks = []
    current_chunk = []
    current_size = 0

    for line in lines:
        line_size = len(line) + 1  # +1 for the newline character

        if current_size + line_size > chunk_size and current_chunk:
            # Save current chunk
            chunks.append("\n".join(current_chunk))

            # Start new chunk with overlap
            overlap_lines = (
                current_chunk[-chunk_overlap // 50 :] if chunk_overlap > 0 else []
            )
            current_chunk = overlap_lines[:]
            current_size = sum(len(line) + 1 for line in current_chunk)

        current_chunk.append(line)
        current_size += line_size

    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append("\n".join(current_chunk))

    # Handle very small files - if no chunks were created, use the whole text
    if not chunks:
        chunks = [text]

    return chunks


# Function to query ChromaDB and retrieve top-X sources
def query_chromadb(query, collection, top_k=5):
    """
    Search the vector database for documents matching the query.

    Args:
        query (str): The search query
        collection: ChromaDB collection to search
        top_k (int): Number of results to return

    Returns:
        list: Formatted search results with content and metadata
    """
    results = collection.query(query_texts=[query], n_results=top_k)

    # Format the results
    formatted_results = []
    for i, (doc, metadata) in enumerate(
        zip(results["documents"][0], results["metadatas"][0])
    ):
        formatted_results.append({"content": doc, "metadata": metadata})

    return formatted_results


# Generate response using llama-cpp-python
def generate_response(query, collection, llm, top_k=10, conversation_history=None):
    """
    Generate an AI response to a query using RAG approach with llama-cpp-python.

    This function:
    1. Retrieves relevant context from the database
    2. Formats a prompt with context and conversation history
    3. Queries the local LLM for a response

    Args:
        query (str): The user's question
        collection: ChromaDB collection to search for context
        llm: Loaded llama-cpp-python Llama model
        top_k (int): Number of context documents to include
        conversation_history (list): Previous exchanges for continuity

    Returns:
        tuple: (generated response, source documents used)
    """
    sources = query_chromadb(query, collection, top_k=top_k)
    context = "\n\n---\n\n".join([source["content"] for source in sources])

    # Include conversation history in the prompt if available
    history_text = ""
    if conversation_history and len(conversation_history) > 0:
        history_text = "Previous conversation:\n"
        for exchange in conversation_history:
            history_text += f"Q: {exchange['query']}\nA: {exchange['response']}\n\n"

    # Prepare prompt with context and query - optimized for token efficiency
    prompt = f"""Based on the context below, answer the question concisely and accurately. Do not repeat or continue the source text.

Context:
{context[:1200]}

Q: {query}
A:"""  # noqa: E501

    # Generate response using llama-cpp-python
    try:
        response = llm(
            prompt,
            max_tokens=1200,
            temperature=0.7,
            top_p=0.9,
            echo=False,
            stop=["Q:"],  # Only stop on new questions, allow multi-paragraph responses
        )
        return response["choices"][0]["text"].strip(), sources
    except Exception as e:
        return f"Error generating response: {str(e)}", sources


def compress_collection(collection_name, client, bits=8):
    """Compress vectors in ChromaDB collection using quantization"""
    collection = client.get_collection(name=collection_name)

    # Get all embeddings
    result = collection.get()
    ids = result["ids"]
    docs = result["documents"]
    metadatas = result["metadatas"]

    # If there are embeddings
    if "embeddings" in result and result["embeddings"]:
        embeddings = np.array(result["embeddings"])

        # Calculate min and max for normalization
        min_val = embeddings.min()
        max_val = embeddings.max()

        # Normalize to 0-255 range for 8-bit quantization
        normalized = (
            (embeddings - min_val) / (max_val - min_val) * (2**bits - 1)
        ).astype(np.uint8)

        # Delete original collection
        client.delete_collection(name=collection_name)

        # Create new collection
        new_collection = client.create_collection(name=collection_name)

        # Add data back with quantized embeddings
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i : i + batch_size]
            batch_docs = docs[i : i + batch_size]
            batch_metas = metadatas[i : i + batch_size]
            batch_embeddings = normalized[i : i + batch_size].tolist()

            new_collection.add(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_metas,
                embeddings=batch_embeddings,
            )

        print(f"Collection compressed: original shape {embeddings.shape}")
        return True
    return False


def remove_outdated_documents(collection, valid_paths):
    """Remove documents from the collection that aren't in the valid paths."""
    # Get all documents
    result = collection.get(include=["metadatas"])

    # Find IDs of documents to remove
    ids_to_remove = []
    for idx, metadata in enumerate(result["metadatas"]):
        # Skip None metadata
        if metadata is None:
            continue

        file_path = metadata.get("file_path", "")
        # Check if this file path starts with any of our valid paths
        if not any(file_path.startswith(path) for path in valid_paths):
            ids_to_remove.append(result["ids"][idx])

    # Remove documents if any found
    if ids_to_remove:
        collection.delete(ids=ids_to_remove)
        print(f"Removed {len(ids_to_remove)} outdated documents")
    else:
        print("No outdated documents found")


# Main function to handle user queries with conversation history
def main():
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Generic RAG system with llama-cpp-python"
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild the database from scratch",
    )
    parser.add_argument(
        "--batch-size", type=int, default=5, help="Batch size for processing"
    )
    parser.add_argument(
        "--chunk-size", type=int, default=500, help="Chunk size in characters"
    )
    parser.add_argument("--clean", action="store_true", help="Clean outdated documents")
    parser.add_argument(
        "--compress",
        action="store_true",
        help="Compress the database using quantization",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reprocessing of existing files",
    )
    parser.add_argument(
        "--model-path",
        type=str,
        required=True,
        help="Path to the GGUF model file",
    )
    parser.add_argument(
        "--source-paths",
        type=str,
        help="Comma-separated list of source directories",
    )
    args = parser.parse_args()

    # Initialize ChromaDB with SentenceTransformer embeddings
    chroma_directory = "./chroma_db"
    os.makedirs(chroma_directory, exist_ok=True)

    client = chromadb.PersistentClient(path=chroma_directory)
    embedding_function = ChromaSentenceEmbeddings(
        model_name="all-MiniLM-L6-v2", use_gpu=False
    )
    collection = client.get_or_create_collection(
        name="generic_docs", embedding_function=embedding_function
    )

    # Define data paths
    if args.source_paths:
        valid_paths = [path.strip() for path in args.source_paths.split(",")]
    else:
        valid_paths = ["./documents", "./data"]  # Default paths
        print(f"No source paths specified, using defaults: {valid_paths}")

    # Handle database operations
    if args.clean or args.rebuild:
        if collection.count() > 0:
            if args.clean:
                remove_outdated_documents(collection, valid_paths)
            if args.rebuild:
                client.delete_collection(name="generic_docs")
                collection = client.create_collection(
                    name="generic_docs", embedding_function=embedding_function
                )

    if args.rebuild or collection.count() == 0:
        for path in valid_paths:
            if os.path.exists(path):
                print(f"Adding files from {path}...")
                add_files_to_chromadb(path, collection, skip_existing=(not args.force))
            else:
                print(f"Warning: Path does not exist: {path}")
    else:
        print(f"Using existing database with {collection.count()} documents")

    if args.compress and collection.count() > 0:
        print("Compressing collection...")
        compress_collection("generic_docs", client, bits=8)

    # Initialize llama-cpp-python
    print(f"Loading model from {args.model_path}...")
    try:
        llm = Llama(
            model_path=args.model_path,
            n_ctx=0,  # Use max context length
            n_gpu_layers=0,  # Use CPU only (0 = no GPU layers)
            verbose=False,
        )
        print("Model loaded successfully on CPU!")
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    # Interactive query loop
    conversation_history = []

    print("\nGeneric RAG System Ready!")
    print("Ask questions about your indexed documents. Type 'quit' to exit.")
    print("-" * 50)

    while True:
        query = input("\nEnter your query (or 'quit' to exit): ")
        if query.lower() == "quit":
            break

        # Generate response
        response, sources = generate_response(
            query,
            collection,
            llm,
            top_k=3,
            conversation_history=conversation_history,
        )

        # Update conversation history
        conversation_history.append({"query": query, "response": response})
        if len(conversation_history) > 5:  # Keep last 5 exchanges
            conversation_history = conversation_history[-5:]

        print("\nResponse:\n", response)
        print("\nTop Sources:")
        for i, source in enumerate(sources[:3], 1):
            file_path = source["metadata"].get("file_path", "Unknown")
            print(f"{i}. {file_path}")


if __name__ == "__main__":
    main()
