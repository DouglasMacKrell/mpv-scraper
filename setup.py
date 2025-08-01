from setuptools import setup, find_packages

setup(
    name="mpv_scraper",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    install_requires=[
        "click",
        "lxml",
        "Pillow",
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "mpv-scraper=mpv_scraper.cli:main",
        ],
    },
)
