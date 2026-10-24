
import ast


def index_files(
    files: list[dict],
    chunk_size: int = 40,
    overlap: int = 5,
) -> list[dict]:
    """
    Split scanned files into chunks with source line numbers.

    For Python files, also record function definitions that overlap
    each chunk. Preserve the original chunking behavior.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be between 0 and chunk_size - 1")

    chunks = []
    step = chunk_size - overlap

    for file in files:
        path = file["path"]
        content = file["content"]
        lines = content.splitlines()
        function_definitions = []

        # Extract Python function locations when the file parses correctly.
        if path.lower().endswith(".py"):
            try:
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(
                        node,
                        (ast.FunctionDef, ast.AsyncFunctionDef),
                    ):
                        function_definitions.append({
                            "name": node.name,
                            "start_line": node.lineno,
                            "end_line": getattr(
                                node, "end_lineno", node.lineno
                            ),
                        })

            except SyntaxError:
                # Still index the file even if it has incomplete Python code.
                function_definitions = []

        for start in range(0, len(lines), step):
            end = min(start + chunk_size, len(lines))
            chunk_start_line = start + 1
            chunk_end_line = end

            chunk_functions = [
                function["name"]
                for function in function_definitions
                if (
                    function["start_line"] <= chunk_end_line
                    and function["end_line"] >= chunk_start_line
                )
            ]

            chunks.append({
                "path": path,
                "start_line": chunk_start_line,
                "end_line": chunk_end_line,
                "content": "\n".join(lines[start:end]),
                "functions": sorted(set(chunk_functions)),
            })

            if end == len(lines):
                break

    return chunks
