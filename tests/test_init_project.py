import os
from pathlib import Path


def test_package_structure():
    """Tests that the main package directory exists inside src/."""
    root_dir = Path(__file__).parent.parent
    package_dir = root_dir / "src" / "mpv_scraper"
    assert package_dir.is_dir()
    assert (package_dir / "__init__.py").is_file()


def test_requirements_files_exist():
    """Tests that the requirements files exist and are not empty."""
    root_dir = Path(__file__).parent.parent
    requirements_file = root_dir / "requirements.txt"
    dev_requirements_file = root_dir / "requirements-dev.txt"

    assert requirements_file.is_file()
    assert dev_requirements_file.is_file()

    assert os.path.getsize(requirements_file) > 0
    assert os.path.getsize(dev_requirements_file) > 0
