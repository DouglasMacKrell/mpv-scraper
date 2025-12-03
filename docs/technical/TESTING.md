# Testing Guide

This document explains how to run the full automated test suite, what each group covers, how mocks are set up, and coverage improvement guidelines.

---

## 1. Environment Setup

```bash
# 1. Activate venv
source .venv/bin/activate

# 2. Install dev dependencies
pip install -r requirements-dev.txt

# 3. Set up API keys (for real API tests)
# Create .env file or export environment variables:
export TVDB_API_KEY2="your_v4_api_key"  # For V4 API tests
export TVDB_API_KEY="your_api_key"      # Fallback
export TMDB_API_KEY="your_tmdb_key"     # For movie tests
```

### Testing with Real APIs

Some tests can run against real APIs. These require API keys to be set:

```bash
# Check if API keys are set
pytest tests/test_api_keys.py -v -s

# Run manual V4 API verification script
python test_tvdb_v4_manual.py
```

---

## 2. Running Tests

### Quick Reference

| Scope | Command | Description |
|-------|---------|-------------|
| Full matrix | `pytest -q` | Runs every test (excludes integration tests by default). |
| All tests including integration | `pytest -m integration` | Runs all tests including e2e/integration tests. |
| End-to-end (mocked) | `pytest tests/e2e/ -v -m integration --no-cov` | Validates scan → generate pipeline with mocked APIs. |
| End-to-end (real API) | `pytest tests/e2e/test_pipeline_v4_real.py -v -m integration --no-cov` | Tests with real TVDB V4 API calls (requires TVDB_API_KEY2). |
| TVDB V4 tests | `pytest tests/test_tvdb_v4.py -v` | Tests specifically for TVDB V4 API integration. |
| Smoke        | `pytest -k smoke` | Verifies each CLI command exits 0 quickly. |
| Regression   | `pytest -k regression` | Focus on rollback/undo safety. |

### Common Flags
* `-s` – show CLI output
* `-v` / `-vv` – verbose test names
* `--no-cov` – disable coverage reporting (faster, use for integration tests)
* `-m integration` – include integration/e2e tests (excluded by default)
* `--tb=short` – shorter traceback format
* `-k <pattern>` – run tests matching pattern

### Test Categories

#### Unit Tests
```bash
# Run all unit tests (default, excludes integration)
pytest -q

# Run specific test file
pytest tests/test_tvdb_v4.py -v

# Run tests matching pattern
pytest -k "tvdb" -v
```

#### Integration/E2E Tests
```bash
# Run all e2e tests (mocked APIs)
pytest tests/e2e/ -v -m integration --no-cov

# Run specific e2e test
pytest tests/e2e/test_pipeline.py -v -m integration --no-cov

# Run real API e2e test (requires TVDB_API_KEY2)
pytest tests/e2e/test_pipeline_v4_real.py -v -m integration --no-cov
```

#### TVDB V4 API Tests
```bash
# Run all V4 API tests
pytest tests/test_tvdb_v4.py -v

# Run updated existing tests
pytest tests/test_tvdb.py tests/unit/test_api_client_coverage.py::TestTVDBAPICoverage -v

# Run all TVDB-related tests
pytest -k "tvdb" -v
```

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

### Mocked Tests (Default)

Most tests use mocked API responses for speed and reliability:

```python
# Example from tests/e2e/test_pipeline.py
with patch("mpv_scraper.scraper.tvdb") as mock_tvdb:
    mock_tvdb.search_show.return_value = [{"id": 1, "name": "Test Show"}]
    mock_tvdb.get_series_extended.return_value = {...}
```

### Real API Tests

Some tests can optionally use real APIs when API keys are available:

- **`tests/e2e/test_pipeline_v4_real.py`** - Tests with real TVDB V4 API
- **`test_tvdb_v4_manual.py`** - Manual verification script

These tests are skipped automatically if API keys are not set:

```bash
# Will skip if TVDB_API_KEY2 not set
pytest tests/e2e/test_pipeline_v4_real.py -v -m integration --no-cov
```

---

## 5. Transaction Log Verification

Rollback tests create a checksum of the directory, run `cli.run`, then `cli.undo`, and assert the checksum matches.  The log file is located at `transaction.log` in the target directory and is consumed by `undo`.

---

## 6. Continuous Integration

GitHub Actions executes the full suite on Python 3.9–3.11.  Wheels are cached between jobs, and pre-commit hooks are enforced.  See `.github/workflows/ci.yml`.

### Coverage Monitoring
- **Coverage threshold**: 65% minimum (enforced in CI)
- **Coverage reports**: HTML reports generated and uploaded as artifacts
- **Coverage badges**: Displayed in README.md
- **PR comments**: Automatic coverage percentage comments on pull requests

---

## 7. Coverage Improvement Guidelines

### Current Coverage Status
- **Overall coverage**: 69.47% (target: 80%+)
- **Test execution time**: ~36 seconds (target: <40 seconds)
- **Test reliability**: 100% pass rate

### Coverage Targets by Module
| Module | Current | Target | Priority |
|--------|---------|--------|----------|
| `cli.py` | 73% | 85%+ | High |
| `tui.py` | 26% | 70%+ | High |
| `tui_app.py` | 34% | 70%+ | High |
| `tmdb.py` | 58% | 80%+ | Medium |
| `images.py` | 61% | 80%+ | Medium |

### Testing Best Practices
1. **Performance-focused**: Keep test execution time under 0.1 seconds per test
2. **Real functionality**: Test actual code paths, not just mocks
3. **Error conditions**: Test failure scenarios and edge cases
4. **Integration testing**: Use lightweight real functionality tests
5. **Coverage monitoring**: Run coverage reports before committing

### Adding New Tests
1. **Unit tests**: Test individual functions and classes
2. **Integration tests**: Test real functionality without heavy operations
3. **Performance tests**: Ensure tests don't become time sinks
4. **Coverage verification**: Check that new tests improve coverage

### Coverage Reporting
```bash
# Run coverage report locally
python scripts/coverage_report.py

# Generate HTML report
pytest --cov=src/mpv_scraper --cov-report=html

# Check specific module coverage
pytest --cov=src/mpv_scraper.cli --cov-report=term-missing

# Run tests without coverage (faster for integration tests)
pytest tests/e2e/ -v -m integration --no-cov
```

## 8. Manual Testing Scripts

### TVDB V4 API Manual Test

A manual verification script is available to test the V4 API integration:

```bash
# Run manual V4 API test
python test_tvdb_v4_manual.py
```

This script will:
- Test authentication with `TVDB_API_KEY2`
- Search for a show (default: "The Simpsons")
- Retrieve series extended information
- Display results and confirm everything works

### Debug Scripts

```bash
# Test TVDB logo fetching
python debug_tvdb.py

# Check API keys
pytest tests/test_api_keys.py -v -s
```

## 9. Test File Organization

```
tests/
├── e2e/                          # End-to-end tests
│   ├── test_pipeline.py         # Basic pipeline (mocked)
│   ├── test_pipeline_extended.py # Multi-season (mocked)
│   ├── test_pipeline_real.py     # Metadata validation (mocked)
│   └── test_pipeline_v4_real.py  # Real V4 API tests (NEW)
├── integration/                  # Integration tests
├── smoke/                        # Smoke tests
├── regression/                   # Regression tests
├── unit/                         # Unit tests
├── test_tvdb.py                  # TVDB tests (updated for V4)
├── test_tvdb_v4.py               # TVDB V4 specific tests (NEW)
└── test_api_keys.py              # API key verification
```

## 10. Running Tests Locally - Quick Start

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Run all tests (excluding integration)
pytest -q

# 3. Run e2e tests (mocked)
pytest tests/e2e/ -v -m integration --no-cov

# 4. Run real API e2e test (if you have TVDB_API_KEY2)
pytest tests/e2e/test_pipeline_v4_real.py -v -m integration --no-cov

# 5. Run V4 API tests
pytest tests/test_tvdb_v4.py -v

# 6. Manual verification
python test_tvdb_v4_manual.py
```

---

Happy testing!
