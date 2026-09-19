"""Create a clean, production distribution ZIP archive for DigiRaksha."""

import os
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ZIP = PROJECT_ROOT / "DigiRaksha_Full_Bundle_SIH2026.zip"

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".vscode",
    ".idea",
    "__pycache__",
    "dist",
    "build",
    "hf-cache",
}

EXCLUDE_FILES = {
    "dhwani_multilingual.onnx",
    "digiraksha.db",
    "digiraksha.db-wal",
    "digiraksha.db-shm",
    "digiraksha.db-journal",
    "DigiRaksha_Full_Bundle_SIH2026.zip",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".swp",
    ".swo",
    ".DS_Store",
}


def should_exclude(rel_path: Path) -> bool:
    parts = rel_path.parts
    # Check directory exclusion
    for part in parts[:-1]:
        if part in EXCLUDE_DIRS:
            return True

    # Check filename exclusion
    name = rel_path.name
    if name in EXCLUDE_FILES:
        return True

    if rel_path.suffix in EXCLUDE_EXTENSIONS:
        return True

    # Ignore uploads and reports contents, keep directories empty
    if len(parts) > 2 and parts[0] == "data" and parts[1] in ("uploads", "reports"):
        return True

    return False


def build_zip():
    print(f"Building clean distribution ZIP from: {PROJECT_ROOT}")
    print(f"Destination: {OUTPUT_ZIP}")

    if OUTPUT_ZIP.exists():
        OUTPUT_ZIP.unlink()

    file_count = 0
    total_uncompressed_bytes = 0

    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        # Walk the project directory
        for root, dirs, files in os.walk(PROJECT_ROOT):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            root_path = Path(root)
            rel_root = root_path.relative_to(PROJECT_ROOT)

            for file in files:
                rel_file = rel_root / file
                if should_exclude(rel_file):
                    continue

                abs_file = root_path / file
                archive_name = str(Path("DigiRaksha") / rel_file)

                zf.write(abs_file, archive_name)
                size = abs_file.stat().st_size
                total_uncompressed_bytes += size
                file_count += 1

        # Add empty placeholder files for data/uploads and data/reports
        zf.writestr("DigiRaksha/data/uploads/.gitkeep", "")
        zf.writestr("DigiRaksha/data/reports/.gitkeep", "")

    zip_size = OUTPUT_ZIP.stat().st_size
    print("\n--- Packaging Complete ---")
    print(f"Files included: {file_count}")
    print(f"Total uncompressed size: {total_uncompressed_bytes / (1024 * 1024):.2f} MB")
    print(f"Final ZIP size: {zip_size / (1024 * 1024):.2f} MB")
    print(f"Saved at: {OUTPUT_ZIP}")


if __name__ == "__main__":
    build_zip()
