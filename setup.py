from pathlib import Path
from setuptools import setup, find_packages

README = (Path(__file__).parent / "README.md").read_text(encoding="utf-8")

setup(
    name="mpv_scraper",
    version="1.0.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=[
        "click",
        "lxml",
        "Pillow",
        "requests",
        "python-dotenv",
    ],
    long_description=README,
    long_description_content_type="text/markdown",
    entry_points={
        "console_scripts": [
            "mpv-scraper=mpv_scraper.cli:main",
        ],
    },
)
