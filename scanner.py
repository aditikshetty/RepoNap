
from pathlib import Path

IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".idea",
    "dist",
    "build",
}

IGNORED_FILES = {
    ".env",
    ".env.local",
    ".env.production",
}

ALLOWED_EXTENSIONS = {
    ".py", ".java", ".js", ".ts", ".jsx", ".tsx",
    ".cpp", ".c", ".h", ".hpp",
    ".rs", ".go", ".html", ".css",
    ".json", ".yml", ".yaml", ".toml",
    ".md", ".txt", ".sql", ".sh",
}

MAX_FILE_SIZE = 500_000  # 500 KB


def scan_repository(root: str) -> list[dict]:
    """Collect safe, readable source files from a repository."""
    root_path = Path(root).resolve()

    if not root_path.is_dir():
        raise ValueError(f"Not a directory: {root}")

    files = []

    for path in root_path.rglob("*"):
        # Skip directories we don't want to traverse.
        if any(part in IGNORED_DIRS for part in path.parts):
            continue

        if not path.is_file():
            continue

        # Avoid following symbolic links.
        if path.is_symlink():
            continue

        if path.name.lower() in IGNORED_FILES:
            continue

        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue

        try:
            if path.stat().st_size > MAX_FILE_SIZE:
                continue

            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        files.append({
            "path": path.relative_to(root_path).as_posix(),
            "content": content,
        })

    return sorted(files, key=lambda item: item["path"])
