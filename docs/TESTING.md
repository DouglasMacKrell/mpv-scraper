# Testing Guide

This document explains how to run the full automated test suite, what each group covers, and how mocks are set up.

---

## 1. Environment Setup

```bash
# 1. Activate venv
source .venv/bin/activate

# 2. Install dev dependencies
pip install -r requirements-dev.txt
```

---

## 2. Running Tests

| Scope | Command | Description |
|-------|---------|-------------|
| Full matrix | `pytest -q` | Runs every test. |
| End-to-end   | `pytest -k e2e` | Validates scan → generate pipeline with mocked APIs. |
| Smoke        | `pytest -k smoke` | Verifies each CLI command exits 0 quickly. |
| Regression   | `pytest -k regression` | Focus on rollback/undo safety. |

### Common flags
* `-s` – show CLI output
* `-vv` – verbose test names

---

## 3. Mock Media Library (`mocks/mpv`)

The `mocks/mpv` directory contains stub `.mp4` files organized exactly like a real media collection:

```
/mocks/mpv
  ├── Movies/
  └── <Show Name>/
```

Only filenames are required for parsing tests—the files themselves are zero-byte placeholders.

---

## 4. HTTP Mocking

Network calls are disabled in CI.  Tests use **`pytest-mock`** and simple fixtures to monkey-patch TVDB/TMDB client helpers.  (The `responses` library can be added later if more complex HTTP behaviour is required.)

Example in `tests/e2e/test_pipeline.py`:

```python
mocker.patch("mpv_scraper.tvdb.search_show", return_value=[...])
```

---

## 5. Transaction Log Verification

Rollback tests create a checksum of the directory, run `cli.run`, then `cli.undo`, and assert the checksum matches.  The log file is located at `transaction.log` in the target directory and is consumed by `undo`.

---

## 6. Continuous Integration

GitHub Actions executes the full suite on Python 3.9–3.11.  Wheels are cached between jobs, and pre-commit hooks are enforced.  See `.github/workflows/ci.yml`.

---

Happy testing!
