# anonymizer-standalone

Standalone offline document anonymizer extracted from `ASR_jetson`.

## Scope

- Input formats: PDF + DOCX (must-have), TXT + XLSX (nice-to-have)
- Output: flat `.txt` anonymized files (one output txt per input)
- Mapping: clear JSON at `<output>/mapping.json`
- Deanonymization: replace placeholders from mapping (file or stdin text)
- Batch mode: folder input, optional concatenated output file
- Offline-only: no network policy in standalone runtime

## Repo layout

- `packages/anonymizer_core`: core library + CLI
- `packages/anonymizer_app`: local desktop UI (Tkinter)
- `tests/data`: fixtures and golden samples
- `tests/acceptance`: acceptance tests + gate scripts
- `scripts/build_windows.ps1`: PyInstaller build script (future packaging)

## Dev run

```bash
cd anonymizer-standalone
uv run anonymizer anonymize \
  --input tests/data/anonymization/fixtures/us1 \
  --output /tmp/anonymized_out \
  --case-id CASE-DEMO-001 \
  --report /tmp/anonymized_out/report.json \
  --concat
```

```bash
cd anonymizer-standalone
uv run anonymizer deanonymize \
  --mapping /tmp/anonymized_out/mapping.json \
  --text-file /tmp/anonymized_out/anonymized_txt/sample_txt.txt \
  --output /tmp/anonymized_out/restored.txt
```

stdin mode (for UI or pipes):

```bash
cat /tmp/anonymized_out/anonymized_txt/sample_txt.txt | \
uv run anonymizer deanonymize \
  --mapping /tmp/anonymized_out/mapping.json \
  --text-stdin \
  --output /tmp/anonymized_out/restored_stdin.txt
```

Run core module directly in dev:

```bash
cd anonymizer-standalone
uv run python -m anonymizer_core.cli anonymize --input tests/data/anonymization/fixtures/us1 --output /tmp/anonymized_out --case-id CASE-DEV-001 --report /tmp/anonymized_out/report.json
```

Run local UI:

```bash
cd anonymizer-standalone
uv run python -m anonymizer_app.main
```

## Acceptance gates

```bash
cd anonymizer-standalone
./tests/acceptance/run_us1_gate.sh
./tests/acceptance/run_us2_gate.sh
./tests/acceptance/run_us3_gate.sh
```
