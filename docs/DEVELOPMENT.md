# Development Guide

This guide covers the development workflow, testing, and quality assurance processes for the MPV Metadata Scraper.

## Test Automation Setup

### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality and test coverage. These run automatically before each commit.

#### Installation

```bash
# Install pre-commit
pip install pre-commit

# Install the hooks
pre-commit install
```

#### What They Do

- **Code Formatting:** Black and Ruff automatically format and lint your code
- **Tests:** Pytest runs automatically before each commit
- **Smart Test Selection:** Only runs tests relevant to changed files

#### Manual Execution

```bash
# Run all pre-commit hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run pytest
pre-commit run black
```

### Pre-push Hooks

A Git pre-push hook ensures all tests pass before pushing to remote.

#### Installation

The pre-push hook is already installed in `.git/hooks/pre-push`. It will run automatically on every push.

#### What It Does

- **Full Test Suite:** Runs the complete test suite before allowing push
- **Automatic Blocking:** Push is blocked if any tests fail
- **Helpful Error Messages:** Provides clear guidance on fixing test failures

#### Manual Execution

```bash
# Test the pre-push hook without actually pushing
git push --dry-run
```

## Testing Strategy

### Test Categories

- **Unit Tests:** Test individual functions and classes
- **Integration Tests:** Test interactions between components
- **End-to-End Tests:** Test complete workflows
- **Smoke Tests:** Quick validation of basic functionality

### Running Tests

```bash
# Run all tests
python -m pytest

# Run specific categories
python -m pytest tests/e2e/          # End-to-end tests
python -m pytest tests/integration/  # Integration tests
python -m pytest tests/smoke/        # Smoke tests

# Run with verbose output
python -m pytest -v

# Run with coverage
python -m pytest --cov=mpv_scraper

# Run specific test file
python -m pytest tests/test_parser.py

# Run specific test function
python -m pytest tests/test_parser.py::test_parse_tv_filename
```

### Test Development

#### Writing New Tests

1. **Follow Naming Convention:** `test_<function_name>.py`
2. **Use Descriptive Names:** Test names should clearly describe what's being tested
3. **Include Edge Cases:** Test error conditions and boundary cases
4. **Mock External Dependencies:** Use `unittest.mock` for API calls and file operations

#### Example Test Structure

```python
def test_function_name():
    """Test description of what this test validates."""
    # Arrange
    input_data = "test input"

    # Act
    result = function_under_test(input_data)

    # Assert
    assert result == expected_output
```

## Code Quality

### Linting and Formatting

- **Black:** Code formatting (automatic)
- **Ruff:** Linting and import sorting (automatic)
- **Pre-commit:** Runs both before commits

### Manual Code Quality Checks

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Fix linting issues
ruff check --fix src/ tests/
```

## Debugging

### Common Issues

1. **Pre-commit Hooks Failing:**
   - Run `pre-commit run --all-files` to see detailed errors
   - Fix formatting issues with `black` and `ruff --fix`
   - Ensure all tests pass with `python -m pytest`

2. **Pre-push Hook Blocking:**
   - Run `python -m pytest` to see test failures
   - Fix failing tests
   - Try push again

3. **Test Failures:**
   - Check if you're in the correct virtual environment
   - Ensure all dependencies are installed: `pip install -r requirements-dev.txt`
   - Run tests with verbose output: `python -m pytest -v`

### Debugging Tests

```bash
# Run tests with debug output
python -m pytest -v -s

# Run single test with debugger
python -m pytest tests/test_parser.py::test_parse_tv_filename -s

# Run tests and stop on first failure
python -m pytest -x
```

## Best Practices

1. **Always Run Tests:** Before committing, ensure all tests pass
2. **Write Tests First:** Consider TDD for new features
3. **Keep Tests Fast:** Use mocks for slow operations
4. **Test Edge Cases:** Include error conditions and boundary tests
5. **Update Documentation:** Keep README and docstrings current

## Troubleshooting

### Hook Installation Issues

```bash
# Reinstall pre-commit hooks
pre-commit uninstall
pre-commit install

# Update pre-commit
pip install --upgrade pre-commit
pre-commit autoupdate
```

### Virtual Environment Issues

```bash
# Ensure you're in the right environment
which python
echo $VIRTUAL_ENV

# Recreate virtual environment if needed
deactivate
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```
