#!/usr/bin/env python3
"""
MPV Scraper Reset Script

This script removes all generated files from an MPV directory, restoring it to
its original state before scraping. This is useful for testing and development.

Usage:
    python reset_mpv.py /path/to/mpv/directory
"""

import sys
import shutil
from pathlib import Path
from typing import List


def find_generated_files(mpv_dir: Path) -> List[Path]:
    """Find all generated files and directories in the MPV directory."""
    generated_files = []

    # Files to remove
    files_to_remove = ["gamelist.xml", ".scrape_cache.json", "transaction.log"]

    # Directories to remove
    dirs_to_remove = ["images"]

    # Check root directory
    for file_name in files_to_remove:
        file_path = mpv_dir / file_name
        if file_path.exists():
            generated_files.append(file_path)

    # Check for images directory in root
    for dir_name in dirs_to_remove:
        dir_path = mpv_dir / dir_name
        if dir_path.exists():
            generated_files.append(dir_path)

    # Check subdirectories (show folders and Movies)
    for item in mpv_dir.iterdir():
        if item.is_dir():
            # Check for generated files in subdirectories
            for file_name in files_to_remove:
                file_path = item / file_name
                if file_path.exists():
                    generated_files.append(file_path)

            # Check for images directories
            for dir_name in dirs_to_remove:
                dir_path = item / dir_name
                if dir_path.exists():
                    generated_files.append(dir_path)

    return generated_files


def reset_mpv_directory(mpv_path: str, auto_confirm: bool = False) -> None:
    """Reset an MPV directory by removing all generated files."""
    mpv_dir = Path(mpv_path)

    if not mpv_dir.exists():
        print(f"Error: Directory {mpv_path} does not exist")
        sys.exit(1)

    if not mpv_dir.is_dir():
        print(f"Error: {mpv_path} is not a directory")
        sys.exit(1)

    print(f"Scanning {mpv_dir} for generated files...")
    generated_files = find_generated_files(mpv_dir)

    if not generated_files:
        print("No generated files found. Directory is already clean.")
        return

    print(f"Found {len(generated_files)} generated files/directories:")
    for file_path in generated_files:
        print(f"  - {file_path}")

    # Confirm deletion (unless auto_confirm is True)
    if not auto_confirm:
        response = input("\nDo you want to delete these files? (y/N): ").strip().lower()
        if response not in ["y", "yes"]:
            print("Reset cancelled.")
            return

    # Delete files
    deleted_count = 0
    for file_path in generated_files:
        try:
            if file_path.is_file():
                file_path.unlink()
                print(f"Deleted file: {file_path}")
            elif file_path.is_dir():
                shutil.rmtree(file_path)
                print(f"Deleted directory: {file_path}")
            deleted_count += 1
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")

    print(f"\nReset completed. Deleted {deleted_count} items.")


def main():
    """Main entry point."""
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python reset_mpv.py /path/to/mpv/directory [-y]")
        sys.exit(1)

    mpv_path = sys.argv[1]
    auto_confirm = len(sys.argv) == 3 and sys.argv[2] == "-y"

    reset_mpv_directory(mpv_path, auto_confirm)


if __name__ == "__main__":
    main()
