@echo off
REM One-command setup for Balmorel Results Analysis Tool on Windows.
REM
REM   setup.bat
REM
REM Strategy:
REM   * If `conda` is available — create or update the conda env defined
REM     in environment.yml, then `pip install -e .` inside it.
REM   * Otherwise — fall back to `pip install` in the currently active Python.
REM
REM After install, checks for a GAMS installation and prints a warning (not
REM an error) if it isn't found.

setlocal EnableDelayedExpansion

set ENV_NAME=balmorel-results-viz
set REPO_DIR=%~dp0
cd /d "%REPO_DIR%"

REM ── Locate/use conda or fall back to pip ───────────────────────────────
set NEXT_STEP=

where conda >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Using conda to set up env '%ENV_NAME%'...

    REM Check if env exists. /B = match beginning of line (no regex ambiguity).
    call conda env list | findstr /B /C:"%ENV_NAME% " >nul 2>nul
    if !ERRORLEVEL! EQU 0 (
        echo   Env '%ENV_NAME%' already exists -- updating dependencies.
        call conda env update -n %ENV_NAME% -f environment.yml --prune
    ) else (
        call conda env create -n %ENV_NAME% -f environment.yml
    )
    if !ERRORLEVEL! NEQ 0 (
        echo ERROR: conda env create/update failed.
        exit /b 1
    )

    call conda activate %ENV_NAME%
    if !ERRORLEVEL! NEQ 0 (
        echo ERROR: conda activate failed. If this is a fresh conda install,
        echo        run 'conda init cmd.exe' once, then re-open cmd and try again.
        exit /b 1
    )

    echo Installing the dashboard package in editable mode...
    pip install -e . --quiet
    if !ERRORLEVEL! NEQ 0 (
        echo ERROR: pip install -e . failed.
        exit /b 1
    )

    set NEXT_STEP=conda activate %ENV_NAME%
) else (
    echo conda not found -- installing into the current Python env.
    where python >nul 2>nul
    if !ERRORLEVEL! NEQ 0 (
        echo ERROR: No 'python' on PATH either. Install Python 3.10+ first.
        exit /b 1
    )

    REM Python 3.10+ required (pybalmorel needs it).
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
    if !ERRORLEVEL! NEQ 0 (
        for /f "delims=" %%v in ('python -c "import sys; print('.'.join(map(str,sys.version_info[:3])))"') do set PY_VER=%%v
        echo.
        echo ERROR: Python 3.10+ is required, but the active Python is !PY_VER!.
        echo.
        echo Either:
        echo   - Activate a Python 3.10+ env. For example:
        echo         py -3.11 -m venv .venv
        echo         .venv\Scripts\activate.bat
        echo   - Or install conda/miniconda -- setup.bat will then create a
        echo     clean 'balmorel-results-viz' env automatically.
        exit /b 1
    )

    pip install --upgrade pip --quiet
    pip install -r requirements.txt -r requirements-export.txt -e . --quiet
    if !ERRORLEVEL! NEQ 0 (
        echo ERROR: pip install failed.
        exit /b 1
    )
    set NEXT_STEP=REM (current Python env already has everything)
)

REM ── GAMS sanity check (warn only) ──────────────────────────────────────
echo.
echo Checking for a GAMS installation...
where gams >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    for /f "delims=" %%g in ('where gams') do (
        echo   GAMS found at: %%~dpg
        goto :gams_ok
    )
) else (
    echo   WARNING: GAMS not found on PATH.
    echo   You can still re-view existing zips by pointing the dashboard at
    echo   a folder of already-exported archives:
    echo       set BALMOREL_ROOT=C:\path\to\Balmorel
    echo       streamlit run streamlit_app.py --server.headless=true
    echo   To enable full exports, add GAMS to PATH or pass --gams-dir at run time.
)

:gams_ok

REM ── Final message ──────────────────────────────────────────────────────
echo.
echo Setup complete.
echo.
echo Next steps:
echo   %NEXT_STEP%
echo.
echo   REM 1. Export scenarios to .zip archives:
echo   python -m balmorel_dashboard C:\path\to\Balmorel
echo.
echo   REM 2. Launch the dashboard (auto-loads scenarios from BALMOREL_ROOT):
echo   set BALMOREL_ROOT=C:\path\to\Balmorel
echo   streamlit run streamlit_app.py --server.headless=true
echo.

endlocal
