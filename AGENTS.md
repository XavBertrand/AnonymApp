# AnonymApp Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-07

## Active Technologies
- Local filesystem with explicit runtime storage (`runtime/outputs`, `runtime/mappings`, `runtime/logs`) (001-build-desktop-anonymizer)
- Python 3.11 + Existing anonymization stack (`transformers`, `torch`, `rapidfuzz`, `Unidecode`, `gliner`); planned desktop/runtime additions `PySide6`, `PyInstaller`; planned test additions `pytest-qt` (001-desktop-case-ui)
- Lightweight local metadata database plus filesystem artifact storage; internal metadata under Windows AppData, case-managed working data under app-managed local storage, user-facing exports under a Windows-friendly documents location; packaged models resolved from `models/` relative to the application root (001-desktop-case-ui)

- Python 3.11 (Windows-compatible) + Existing backend dependencies from `./tmp` scripts, local UI surface (simple CLI for MVP), local config/logging libs (001-build-desktop-anonymizer)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11 (Windows-compatible): Follow standard conventions

## Recent Changes
- 001-desktop-case-ui: Added Python 3.11 + Existing anonymization stack (`transformers`, `torch`, `rapidfuzz`, `Unidecode`, `gliner`); planned desktop/runtime additions `PySide6`, `PyInstaller`; planned test additions `pytest-qt`
- 001-build-desktop-anonymizer: Added Python 3.11 (Windows-compatible) + Existing backend dependencies from `./tmp` scripts, local UI surface (simple CLI for MVP), local config/logging libs

- 001-build-desktop-anonymizer: Added Python 3.11 (Windows-compatible) + Existing backend dependencies from `./tmp` scripts, local UI surface (simple CLI for MVP), local config/logging libs

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
