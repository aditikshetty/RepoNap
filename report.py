
from datetime import datetime


def generate_report(
    repo_root: str,
    files: list[dict],
    chunks: list[dict],
) -> str:
    """Generate a Markdown onboarding report from indexed files."""

    lines = [
        "# RepoNap — Codebase Onboarding Report",
        "",
        f"Generated: {datetime.now().astimezone().isoformat(timespec='minutes')}",
        f"Repository: `{repo_root}`",
        "",
        "## Overview",
        "",
        f"- Readable source files scanned: {len(files)}",
        f"- Code chunks indexed: {len(chunks)}",
        "",
        "## File Inventory",
        "",
    ]

    if files:
        for file in files:
            line_count = len(file["content"].splitlines())
            lines.append(f"- `{file['path']}` — {line_count} lines")
    else:
        lines.append("No supported source files were found.")

    extensions = {}
    for file in files:
        name = file["path"]
        extension = "." + name.rsplit(".", 1)[-1] if "." in name else "(no extension)"
        extensions[extension] = extensions.get(extension, 0) + 1

    lines.extend(["", "## Languages and File Types", ""])

    if extensions:
        for extension, count in sorted(extensions.items()):
            lines.append(f"- `{extension}`: {count} file(s)")
    else:
        lines.append("No file types detected.")

    lines.extend([
        "",
        "## Getting Started",
        "",
        "1. Identify the application's entry point.",
        "2. Read the README and dependency/configuration files.",
        "3. Trace how the main components call one another.",
        "4. Run tests before changing code.",
        "5. Review configuration and security-sensitive code carefully.",
        "",
        "## Limitations",
        "",
        "- This report inventories files; it does not prove that the application runs.",
        "- Entry points and architecture should be verified by inspecting the source.",
        "- Generated summaries may be incomplete.",
        "",
    ])

    return "\n".join(lines)
