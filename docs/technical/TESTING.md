# Testing Guide

This document explains how to run the full automated test suite, what each group covers, how mocks are set up, and coverage improvement guidelines.

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
```

---

Happy testing!
