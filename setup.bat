@echo off
setlocal EnableDelayedExpansion

REM ============================================================================
REM   BIS Compass - One-shot environment setup (Windows)
REM ============================================================================
REM   Replicates the full environment a judge needs to run inference.py.
REM
REM   1. Verify Python is on PATH
REM   2. Install dependencies (requirements.txt)
REM   3. Parse SP 21 PDF -> 559 standards + IS-code whitelist
REM   4. Build FAISS dense index (downloads bge-m3 from HF, ~2.3 GB)
REM   5. Build BM25 sparse index
REM   6. Warm-up inference.py on the public test set
REM      (downloads bge-reranker-v2-m3 from HF, ~2.3 GB)
REM   7. Score the warm-up with eval_script.py
REM
REM   First run:        3-5 min (most of it is HF downloads)
REM   Subsequent runs:  ~30 s (everything is cached, fully offline)
REM
REM   GPU acceleration (optional, NVIDIA Blackwell / Ada / Ampere):
REM   install torch FIRST with CUDA 12.8, then run this script:
REM     pip install torch --index-url https://download.pytorch.org/whl/cu128
REM ============================================================================

echo.
echo ============================================================
echo   BIS Compass - Environment Setup
echo ============================================================
echo.

REM --- 1/7 --------------------------------------------------------------------
echo [1/7] Verifying Python is on PATH...
where python >nul 2>nul
if errorlevel 1 (
    echo   ERROR: 'python' not found. Install Python 3.10+ from python.org.
    exit /b 1
)
python --version
echo.

REM --- 2/7 --------------------------------------------------------------------
echo [2/7] Installing dependencies from requirements.txt...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo   ERROR: dependency install failed. See pip output above.
    exit /b 1
)
echo.

REM --- 3/7 --------------------------------------------------------------------
echo [3/7] Parsing SP 21 PDF (929 pages -^> 559 standards + IS-code whitelist)...
python -m src.ingestion.pdf_parser
if errorlevel 1 (
    echo   ERROR: PDF parsing failed.
    exit /b 1
)
echo.

REM --- 4/7 --------------------------------------------------------------------
echo [4/7] Building FAISS dense index...
echo       First run downloads bge-m3 from HuggingFace (~2.3 GB, 1-3 min).
python -m src.retrieval.index
if errorlevel 1 (
    echo   ERROR: dense index build failed.
    exit /b 1
)
echo.

REM --- 5/7 --------------------------------------------------------------------
echo [5/7] Building BM25 sparse index...
python -m src.retrieval.bm25_index
if errorlevel 1 (
    echo   ERROR: BM25 index build failed.
    exit /b 1
)
echo.

REM --- 6/7 --------------------------------------------------------------------
echo [6/7] Warm-up run on the public test set...
echo       First run downloads bge-reranker-v2-m3 from HuggingFace (~2.3 GB).
python inference.py --input datasets\public_test_set.json --output team_results.json
if errorlevel 1 (
    echo   ERROR: inference.py warm-up failed.
    exit /b 1
)
echo.

REM --- 7/7 --------------------------------------------------------------------
echo [7/7] Scoring the warm-up run...
python eval_script.py --results team_results.json
echo.

echo ============================================================
echo   Setup complete. Environment ready.
echo ============================================================
echo.
echo Run inference on a private test set:
echo   python inference.py --input ^<input.json^> --output ^<output.json^>
echo.

endlocal
