# AnonymApp

AnonymApp is a local text anonymization CLI for plain `.txt` documents.

It anonymizes personally identifiable information with a transformer-based backend, writes the anonymized text to disk, and stores a mapping artifact that can later be used to restore the original text.

## What this repository does

This repository currently provides:

- A command-line interface for anonymizing and deanonymizing `.txt` files
- A single supported backend: `transformer`
- Local readiness checks for Python dependencies and model availability
- Local runtime output folders for anonymized files, mappings, and logs
- A canonical mapping format used for reversible deanonymization

The current anonymization flow is local-first and CPU-only by default. The bundled transformer backend uses GLiNER-based entity detection when the required model and Python packages are available.

## Project layout

```text
src/        Application code
tests/      Unit, integration, and contract tests
tmp/        Bundled backend scripts used by the wrappers
runtime/    Generated outputs, mappings, and logs at runtime
```

## Requirements

- Python 3.11 or newer
- Local access to the GLiNER model `urchade/gliner_multi_pii-v1`
- Installed Python dependencies from `pyproject.toml`

Required runtime packages include:

- `transformers`
- `torch`
- `rapidfuzz`
- `Unidecode`
- `gliner`

## Installation

You can install the project with either `uv` or `pip`.

### Option 1: `uv`

```bash
uv sync
```

### Option 2: `pip`

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

If you do not install the project in editable mode, make sure the repository root is on `PYTHONPATH` before invoking the CLI.

## Model provisioning

Readiness checks expect the transformer model to be available locally.

The application looks for the model in one of these places:

- `ANONYMAPP_TRANSFORMER_MODEL_PATH`
- `HF_HOME` cache under the usual Hugging Face model layout
- `~/.cache/huggingface` if `HF_HOME` is not set

If the model is missing, the backend is reported as unavailable and anonymization will fail with an actionable readiness error.

## CLI usage

The CLI entry point is:

```bash
python3 -m src.app.cli.main
```

### Check readiness

```bash
python3 -m src.app.cli.main readiness
```

Example output:

```text
[transformer] ready
  - transformers: pass (critical) - available
  - torch: pass (critical) - available
  ...
```

### Anonymize a text file

```bash
python3 -m src.app.cli.main anonymize --input /path/to/input.txt
```

Optional arguments:

- `--engine transformer`
- `--output /path/to/output.txt`
- `--mapping /path/to/mapping.json`

When `--output` and `--mapping` are omitted, the CLI writes files under `runtime/outputs` and `runtime/mappings`.

### Deanonymize a text file

```bash
python3 -m src.app.cli.main deanonymize \
  --input /path/to/anonymized.txt \
  --mapping /path/to/mapping.json
```

Optional argument:

- `--output /path/to/restored.txt`

Deanonymization uses the mapping artifact produced during anonymization and restores placeholders back to their original values.
Deanonymization uses the mapping artifact produced during anonymization to restore original values in the anonymized text.

## Runtime output

The application creates these folders automatically:

- `runtime/outputs`
- `runtime/mappings`
- `runtime/logs`

Default file naming:

- Anonymized output: `<input_stem>.transformer.anon.txt`
- Mapping artifact: `<input_stem>.transformer.mapping.json`
- Deanonymized output: `<deanonymize_input_stem>.<origin_backend>.deanon.txt`

## Typical workflow

```bash
python3 -m src.app.cli.main readiness
python3 -m src.app.cli.main anonymize --input ./sample.txt
python3 -m src.app.cli.main deanonymize \
  --input ./runtime/outputs/sample.transformer.anon.txt \
  --mapping ./runtime/mappings/sample.transformer.mapping.json
```

## Development

Run tests:

```bash
python3 -m pytest
```

Run lint checks:

```bash
python3 -m ruff check .
```

## Current scope and limitations

- Only `.txt` document processing is implemented
- Only the `transformer` backend is supported
- The default wrapper forces CPU execution
- Successful anonymization depends on local model availability and installed runtime dependencies
