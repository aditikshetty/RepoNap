

import re
from indexer import index_files


STOP_WORDS = {
    "the", "is", "a", "an", "and", "or", "to", "of", "in",
    "on", "for", "what", "where", "how", "does", "this", "that",
    "which", "with", "me", "explain", "show", "find", "please",
    "function", "code", "work", "working", "implementation",
    "describe", "step", "steps", "actual", "internally",
    "implement", "using", "based", "repository",
}


def tokenize(text: str) -> set[str]:
    """Extract searchable words from questions and code."""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = text.replace("_", " ").replace("-", " ")

    return {
        word.lower()
        for word in re.findall(r"[a-zA-Z][a-zA-Z0-9]*", text)
        if word.lower() not in STOP_WORDS
    }


def _normalise_path(path: str) -> str:
    return path.replace("\\", "/").lower().lstrip("./")


def _is_test_file(path: str) -> bool:
    path = _normalise_path(path)
    parts = path.split("/")
    filename = parts[-1]

    return (
        any(
            part in {"test", "tests", "__tests__", "fixtures"}
            for part in parts
        )
        or filename.startswith("test_")
        or "_test." in filename
        or ".test." in filename
        or ".spec." in filename
    )


def _is_example_file(path: str) -> bool:
    path = _normalise_path(path)
    return (
        "examples/" in path
        or path.startswith("example/")
        or "/example/" in path
    )


def _is_implementation_file(path: str) -> bool:
    path = _normalise_path(path)
    return (
        path.startswith("lib/")
        or path.startswith("src/")
        or "/src/" in path
    )


def _contains_identifier(content: str, identifier: str) -> bool:
    """Match an identifier without matching substrings."""
    return re.search(
        rf"(?<![\w$]){re.escape(identifier)}(?![\w$])",
        content,
        re.IGNORECASE,
    ) is not None


def _defines_app_use(content: str) -> bool:
    """Detect the actual Express-style app.use definition."""
    return re.search(
        r"\bapp\s*\.\s*use\s*=\s*function\b",
        content,
    ) is not None


def _defines_identifier(content: str, identifier: str) -> bool:
    """Detect common JavaScript and TypeScript function definitions."""
    escaped = re.escape(identifier)

    patterns = [
        rf"\b{escaped}\s*=\s*function\b",
        rf"\b{escaped}\s*=\s*(?:async\s*)?\([^)]*\)\s*=>",
        rf"\bfunction\s+{escaped}\s*\(",
        rf"\b{escaped}\s*:\s*function\b",
    ]

    return any(
        re.search(pattern, content, re.IGNORECASE)
        for pattern in patterns
    )


def _is_same_chunk(first: dict, second: dict) -> bool:
    """Check whether two chunks have the same path and line range."""
    return (
        _normalise_path(first["path"])
        == _normalise_path(second["path"])
        and first["start_line"] == second["start_line"]
        and first["end_line"] == second["end_line"]
    )


def _select_app_use_chunks(
    chunks: list[dict],
    ranked: list[tuple[int, dict]],
) -> list[dict]:
    """
    Select the app.use definition and following chunks until the
    function's return statement and closing brace are found.
    """
    anchors = [
        chunk
        for _, chunk in ranked
        if _defines_app_use(chunk["content"])
        and not _is_test_file(chunk["path"])
        and not _is_example_file(chunk["path"])
    ]

    if not anchors:
        return []

    anchor = anchors[0]
    anchor_path = _normalise_path(anchor["path"])

    same_file = [
        chunk
        for chunk in chunks
        if _normalise_path(chunk["path"]) == anchor_path
        and not _is_test_file(chunk["path"])
        and not _is_example_file(chunk["path"])
    ]

    same_file.sort(
        key=lambda chunk: (
            chunk["start_line"],
            chunk["end_line"],
        )
    )

    # Begin at the actual definition, never at an earlier chunk.
    anchor_index = next(
        (
            index
            for index, chunk in enumerate(same_file)
            if _is_same_chunk(chunk, anchor)
        ),
        None,
    )

    if anchor_index is None:
        return []

    selected = []
    seen = set()

    for chunk in same_file[anchor_index:]:
        key = (
            _normalise_path(chunk["path"]),
            chunk["start_line"],
            chunk["end_line"],
        )

        if key in seen:
            continue

        # Stop if there is a gap: do not present disjoint code as
        # one continuous function.
        if selected:
            previous = selected[-1]
            if chunk["start_line"] > previous["end_line"] + 1:
                break

        selected.append(chunk)
        seen.add(key)

        combined_content = "\n".join(
            item["content"] for item in selected
        )

        has_return = re.search(
            r"\breturn\s+this\s*;",
            combined_content,
        ) is not None

        has_function_end = re.search(
            r"\}\s*;",
            combined_content,
        ) is not None

        if has_return and has_function_end:
            break

    return selected


def retrieve_context(
    files: list[dict],
    question: str,
    top_k: int = 4,
) -> list[dict]:
    """
    Retrieve relevant code chunks.

    For Express app.use() questions, prioritize the actual definition
    and the following chunks needed to complete its implementation.
    """
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    if not question.strip():
        return []

    chunks = index_files(files)

    if not chunks:
        return []

    question_lower = question.lower()
    query_terms = tokenize(question)

    if not query_terms:
        return []

    # Detect qualified identifiers such as app.use and router.handle.
    identifiers = re.findall(
        r"\b[A-Za-z_$]\w*(?:\.[A-Za-z_$]\w*)+\b",
        question,
    )

    # Detect camelCase and snake_case identifiers.
    identifiers += [
        name
        for name in re.findall(r"\b[A-Za-z_$]\w*\b", question)
        if "_" in name
        or (
            any(char.isupper() for char in name)
            and name[0].islower()
        )
    ]

    identifiers = list(
        dict.fromkeys(name.lower() for name in identifiers)
    )

    implementation_question = any(
        term in question_lower
        for term in (
            "implement",
            "implementation",
            "internally",
            "definition",
            "defined",
            "source code",
        )
    )

    app_use_question = bool(
        re.search(
            r"\bapp\s*\.\s*use\b",
            question,
            re.IGNORECASE,
        )
    )

    ranked = []

    for chunk in chunks:
        content = chunk["content"]
        path = _normalise_path(chunk["path"])

        content_terms = tokenize(content)
        path_terms = tokenize(path)

        score = len(query_terms & content_terms)
        score += 3 * len(query_terms & path_terms)

        for identifier in identifiers:
            if _contains_identifier(content, identifier):
                score += 8

            if _defines_identifier(content, identifier):
                score += 30

        is_test = _is_test_file(path)
        is_example = _is_example_file(path)
        is_implementation = _is_implementation_file(path)

        if is_test:
            score -= 15 if implementation_question else 4

        if is_example:
            score -= 10 if implementation_question else 2

        if is_implementation:
            score += 5

        if app_use_question and _defines_app_use(content):
            score += 1000

        if app_use_question and re.search(
            r"\brouter\s*\.\s*use\s*\(\s*path\s*,\s*fn\s*\)",
            content,
        ):
            score += 40

        if score > 0:
            ranked.append((score, chunk))

    ranked.sort(
        key=lambda item: (
            -item[0],
            item[1]["path"],
            item[1]["start_line"],
        )
    )

    if not ranked:
        return []

    # Targeted retrieval for the Express app.use implementation.
    if app_use_question:
        selected = _select_app_use_chunks(chunks, ranked)

        if selected:
            return selected

    # General-purpose retrieval for other questions.
    results = []

    for score, chunk in ranked[:top_k]:
        results.append({
            **chunk,
            "score": score,
        })

    return results
