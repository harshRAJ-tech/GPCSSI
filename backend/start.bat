@echo off
echo Starting Cyber Investigation Intelligence Platform (CIIP)...
echo.

:: Check if the virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found. Please run: python -m venv .venv
    exit /b 1
)

:: Activate the virtual environment
call .venv\Scripts\activate.bat

:: Start the FastAPI server using uvicorn for better performance in the terminal
echo Starting server on http://127.0.0.1:8000
echo Press Ctrl+C to stop the server.
echo.
python main.py
