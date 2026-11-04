@echo off
rem One command for the whole analysis: run_all [--quick] [--fast] [--from STEP]
"%~dp0venv\Scripts\python.exe" "%~dp0run_all.py" %*
