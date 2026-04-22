@echo off
echo ========================================
echo Generic RAG System - Environment Setup
echo ========================================
echo Using UV for fast package management
echo.

REM Check if uv is installed
uv --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: uv is not installed or not in PATH
    echo Please install uv first: https://docs.astral.sh/uv/getting-started/installation/
    echo Or run: curl -LsSf https://astral.sh/uv/install.sh ^| sh
    pause
    exit /b 1
)

echo UV found:
uv --version
echo.

REM Check if Python is available (uv can manage Python versions)
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found in PATH, uv will install it...
    echo.
)

REM Create virtual environment with uv (automatically installs Python if needed)
echo Creating virtual environment 'rag_env' with Python 3.12...
uv venv rag_env --python 3.12

REM Check if venv creation was successful
if not exist "rag_env\Scripts\activate.bat" (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo Virtual environment created successfully!
echo.

REM Activate virtual environment
echo Activating virtual environment...
call rag_env\Scripts\activate.bat

REM Install required packages using uv
echo.
echo Installing required packages with uv...
echo This will be much faster than pip!
echo.

echo Installing all dependencies...
uv pip install chromadb llama-cpp-python sentence-transformers torch scikit-learn numpy

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo To use the RAG system:
echo 1. Activate the environment: rag_env\Scripts\activate.bat
echo 2. Download a GGUF model file (e.g., from HuggingFace)
echo 3. Run: python generic_rag_system.py --model-path "path\to\model.gguf" --source-paths "path\to\documents"
echo.
echo Example model downloads:
echo - Llama 2 7B Chat: https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF
echo - Code Llama 7B: https://huggingface.co/TheBloke/CodeLlama-7B-GGUF
echo - Mistral 7B: https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF
echo.
echo Environment location: %CD%\rag_env
echo.
echo UV benefits used:
echo - Faster package resolution and installation
echo - Automatic Python version management
echo - Better dependency conflict resolution
echo.
pause