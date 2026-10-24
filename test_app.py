
import pytest

from app import parse_github_url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "https://github.com/openai/whisper",
            "https://github.com/openai/whisper.git",
        ),
        (
            "https://github.com/openai/whisper.git",
            "https://github.com/openai/whisper.git",
        ),
        (
            "https://github.com/openai/whisper/",
            "https://github.com/openai/whisper.git",
        ),
        (
            "http://github.com/openai/whisper",
            None,
        ),
        (
            "https://gitlab.com/openai/whisper",
            None,
        ),
        (
            "https://github.com/openai",
            None,
        ),
        (
            "https://github.com/openai/whisper?tab=readme",
            None,
        ),
        (
            "https://github.com/openai/whisper#readme",
            None,
        ),
        (
            "https://user:pass@github.com/openai/whisper",
            None,
        ),
        (
            "https://github.com:443/openai/whisper",
            None,
        ),
        (
           " https://github.com/links-lang/links-examples",
           None, 
        ),
    ],
)
def test_parse_github_url(url, expected):
    assert parse_github_url(url) == expected
