
from pathlib import Path
import base64
import re
import shutil
import subprocess
import tempfile
from urllib.parse import urlparse

import streamlit as st

from scanner import scan_repository
from indexer import index_files
from retriever import retrieve_context
from local_llm import ask_gemma
from report import generate_report


st.set_page_config(
    page_title="RepoNap | Codebase Onboarding",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# GitHub URL validation
# ============================================================

def parse_github_url(value: str):
    """Return a normalized HTTPS GitHub clone URL, or None."""
    if not isinstance(value, str) or not value or value != value.strip():
        return None

    try:
        parsed = urlparse(value)

        if (
            parsed.scheme != "https"
            or parsed.netloc.lower() != "github.com"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port is not None
            or parsed.query
            or parsed.fragment
        ):
            return None

        match = re.fullmatch(
            r"/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?",
            parsed.path,
        )

        if not match:
            return None

        owner, repository = match.groups()

        if owner in {".", ".."} or repository in {".", ".."}:
            return None

        return f"https://github.com/{owner}/{repository}.git"

    except (ValueError, AttributeError):
        return None


# ============================================================
# Evidence selection helpers
# ============================================================

def is_app_use_question(question: str) -> bool:
    """Detect questions specifically about Express app.use()."""
    return bool(
        re.search(r"\bapp\s*\.\s*use\b", question, re.IGNORECASE)
    )


def is_test_or_example(path: str) -> bool:
    """Identify test and example files."""
    normalized = path.replace("\\", "/").lower()
    parts = normalized.split("/")

    return (
        any(
            part in {
                "test",
                "tests",
                "example",
                "examples",
                "fixtures",
            }
            for part in parts
        )
        or normalized.endswith((".test.js", ".spec.js"))
    )


def select_app_use_evidence(chunks: list[dict]) -> list[dict]:
    """Prefer Express's actual app.use implementation as evidence."""
    implementation = [
        chunk
        for chunk in chunks
        if chunk.get("path", "")
        .replace("\\", "/")
        .lower()
        .endswith("lib/application.js")
        and not is_test_or_example(chunk.get("path", ""))
    ]

    anchor = next(
        (
            chunk
            for chunk in implementation
            if re.search(
                r"\bapp\s*\.\s*use\s*=\s*function\b",
                chunk.get("content", ""),
            )
        ),
        None,
    )

    if anchor is None:
        return []

    selected = [anchor]
    content = anchor.get("content", "")

    has_return = bool(
        re.search(r"\breturn\s+this\s*;", content)
    )
    has_function_end = bool(
        re.search(r"\n\s*};", content)
    )

    if not (has_return and has_function_end):
        later = [
            chunk
            for chunk in implementation
            if chunk.get("start_line", 0)
            > anchor.get("start_line", 0)
        ]

        if later:
            next_chunk = min(
                later,
                key=lambda chunk: chunk.get("start_line", 0),
            )
            selected.append(next_chunk)

    unique = {}

    for chunk in selected:
        key = (
            chunk.get("path"),
            chunk.get("start_line"),
            chunk.get("end_line"),
        )
        unique[key] = chunk

    return sorted(
        unique.values(),
        key=lambda chunk: chunk.get("start_line", 0),
    )


# ============================================================
# UI styling
# ============================================================

def load_background_css():
    """Use assets/reponap-bg.png when available."""
    background_path = (
        Path(__file__).parent / "assets" / "reponap-bg.png"
    )

    if background_path.exists():
        encoded = base64.b64encode(
            background_path.read_bytes()
        ).decode("utf-8")

        background = (
            f'url("data:image/png;base64,{encoded}")'
        )
    else:
        background = "none"

    st.markdown(
        f"""
        <style>
        :root {{
            --rn-bg: #070817;
            --rn-border: rgba(153, 112, 255, .25);
            --rn-text: #f4f2ff;
            --rn-muted: #aaa8c8;
            --rn-purple: #9b6cff;
        }}

        html, body, [data-testid="stAppViewContainer"] {{
            background: var(--rn-bg);
            color: var(--rn-text);
        }}

        [data-testid="stAppViewContainer"] {{
            background-image:
                linear-gradient(
                    rgba(5, 6, 20, .48),
                    rgba(5, 6, 20, .91)
                ),
                {background};
            background-position: center top;
            background-size: cover;
            background-attachment: fixed;
        }}

        [data-testid="stHeader"] {{
            background: rgba(5, 6, 20, .20);
        }}

        .block-container {{
            max-width: 1450px;
            padding-top: 10.5rem;
            padding-bottom: 3rem;
        }}

        [data-testid="stSidebar"] {{
            background: linear-gradient(
                180deg,
                rgba(10, 11, 31, .97),
                rgba(14, 11, 35, .96)
            );
            border-right: 1px solid var(--rn-border);
        }}

        [data-testid="stSidebar"] > div:first-child {{
            padding-top: 1.5rem;
        }}

        h1, h2, h3 {{
            color: var(--rn-text) !important;
            letter-spacing: -.025em;
        }}

        p, label, .stMarkdown,
        [data-testid="stCaptionContainer"] {{
            color: var(--rn-muted);
        }}

        .rn-eyebrow {{
            display: inline-flex;
            align-items: center;
            gap: .45rem;
            padding: .38rem .72rem;
            border-radius: 999px;
            color: #d8caff;
            font-size: .78rem;
            letter-spacing: .08em;
            text-transform: uppercase;
            background: rgba(129, 82, 255, .12);
            border: 1px solid rgba(161, 122, 255, .25);
        }}

        .rn-hero-title {{
            font-size: clamp(2rem, 4.1vw, 3.5rem);
            line-height: 1.08;
            font-weight: 800;
            letter-spacing: -.055em;
            margin: .85rem 0 .65rem;
            color: #fff;
        }}

        .rn-gradient {{
            background: linear-gradient(
                90deg,
                #a78bfa,
                #f0abfc 48%,
                #7dd3fc
            );
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }}

        .rn-subtitle {{
            max-width: 760px;
            font-size: 1.03rem;
            line-height: 1.7;
            color: #c0bfdc;
        }}

        .rn-panel {{
            background: linear-gradient(
                145deg,
                rgba(21, 21, 52, .88),
                rgba(10, 12, 30, .90)
            );
            border: 1px solid var(--rn-border);
            border-radius: 20px;
            padding: 1.15rem 1.25rem;
            box-shadow: 0 16px 48px rgba(0, 0, 0, .16);
        }}

        .rn-panel-title {{
            font-size: 1.02rem;
            color: #f5f1ff;
            font-weight: 700;
            margin-bottom: .25rem;
        }}

        .rn-panel-copy {{
            color: #aaa8c8;
            font-size: .9rem;
            line-height: 1.55;
        }}

        div[data-testid="stMetric"] {{
            background: rgba(19, 20, 47, .82);
            border: 1px solid var(--rn-border);
            border-radius: 16px;
            padding: 1rem 1.1rem;
        }}

        div[data-testid="stMetricLabel"] p {{
            color: #b8b5d6 !important;
        }}

        div[data-testid="stMetricValue"] {{
            color: #fff !important;
        }}

        .stTextInput input,
        .stTextArea textarea {{
            background: rgba(7, 8, 25, .82) !important;
            color: #f5f3ff !important;
            border: 1px solid rgba(155, 108, 255, .34) !important;
            border-radius: 12px !important;
        }}

        .stTextInput input:focus,
        .stTextArea textarea:focus {{
            border-color: #a78bfa !important;
            box-shadow: 0 0 0 .15rem rgba(167,139,250,.16) !important;
        }}

        .stButton > button,
        .stDownloadButton > button {{
            border-radius: 12px;
            border: 1px solid rgba(176, 137, 255, .45);
            background: linear-gradient(100deg, #7045d8, #a64ac7);
            color: white;
            font-weight: 700;
            min-height: 2.8rem;
            transition: transform .16s ease, filter .16s ease;
        }}

        .stButton > button:hover,
        .stDownloadButton > button:hover {{
            filter: brightness(1.12);
            transform: translateY(-1px);
            color: white;
            border-color: rgba(221, 185, 255, .85);
        }}

        div[data-testid="stExpander"] {{
            background: rgba(12, 13, 34, .82);
            border: 1px solid var(--rn-border);
            border-radius: 14px;
        }}

        [data-testid="stAlert"] {{
            border-radius: 12px;
        }}

        hr {{
            border-color: rgba(153, 112, 255, .2);
        }}

        code {{
            color: #e7d7ff !important;
        }}

        @media (max-width: 900px) {{
            .block-container {{
                padding-top: 7rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }}

            .rn-hero-title {{
                font-size: clamp(1.9rem, 7vw, 2.8rem);
            }}

            .rn-panel {{
                padding: 1rem;
            }}
        }}

        @media (max-width: 600px) {{
            .block-container {{
                padding-top: 5rem;
            }}

            .rn-subtitle {{
                font-size: .95rem;
            }}

            div[data-testid="stMetric"] {{
                padding: .75rem;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


load_background_css()


# ============================================================
# Hero section
# ============================================================

st.markdown(
    """
    <div class="rn-eyebrow">
        ✦ Local-first AI developer tool
    </div>

    <div class="rn-hero-title">
        Understand any codebase.<br>
        <span class="rn-gradient">Without the guesswork.</span>
    </div>

    <div class="rn-subtitle">
        RepoNap scans a repository, maps its source files,
        and uses Gemma to help you understand unfamiliar code
        — with retrieved snippets you can inspect.
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")


# ============================================================
# Session state
# ============================================================

if "repo_files" not in st.session_state:
    st.session_state.repo_files = []

if "repo_root" not in st.session_state:
    st.session_state.repo_root = ""

if "clone_dir" not in st.session_state:
    st.session_state.clone_dir = None

if "last_question" not in st.session_state:
    st.session_state.last_question = ""

if "last_answer" not in st.session_state:
    st.session_state.last_answer = ""

if "last_evidence" not in st.session_state:
    st.session_state.last_evidence = []


def remove_previous_clone():
    """Remove the previous temporary clone created by RepoNap."""
    clone_dir = st.session_state.get("clone_dir")

    if clone_dir:
        shutil.rmtree(clone_dir, ignore_errors=True)
        st.session_state.clone_dir = None


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:
    st.markdown("## 🚀 RepoNap")
    st.caption("Your local codebase copilot")
    st.divider()

    st.markdown("### Connect a repository")

    repo_input = st.text_input(
        "GitHub URL or local folder path",
        placeholder="https://github.com/owner/repository",
        help=(
            "Public GitHub repositories and local folders "
            "are supported."
        ),
    )

    scan_button = st.button(
        "✦  Analyze repository",
        type="primary",
        use_container_width=True,
    )

    st.markdown(
        """
        <div class="rn-panel-copy">
            Tip: start with a small repository to get results faster.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()
    st.markdown("**How it works**")
    st.markdown(
        "1. Connect a repository\n"
        "2. Scan and index source files\n"
        "3. Ask questions with code evidence"
    )
    st.caption("AI runs through your configured local Ollama server.")


# ============================================================
# Repository scanning
# ============================================================

if scan_button:
    value = repo_input.strip()
    root = None
    is_github_url = value.startswith(("https://", "http://"))

    if not value:
        st.error("Enter a local folder path or public GitHub URL.")

    elif is_github_url:
        clone_url = parse_github_url(value)

        if clone_url is None:
            st.error(
                "Invalid URL. Enter an HTTPS GitHub repository URL, "
                "such as https://github.com/owner/repository"
            )

        else:
            clone_dir = None

            try:
                with st.spinner(
                    "Connecting to GitHub and cloning the repository…"
                ):
                    clone_dir = tempfile.mkdtemp(prefix="reponap-")

                    result = subprocess.run(
                        [
                            "git",
                            "clone",
                            "--depth",
                            "1",
                            "--no-recurse-submodules",
                            "--",
                            clone_url,
                            clone_dir,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=180,
                        check=False,
                    )

                if result.returncode != 0:
                    shutil.rmtree(clone_dir, ignore_errors=True)

                    st.error(
                        "Could not clone the repository. Check the URL, "
                        "internet connection, and whether the repository "
                        "is public."
                    )

                else:
                    remove_previous_clone()
                    st.session_state.clone_dir = clone_dir
                    root = Path(clone_dir)

            except FileNotFoundError:
                if clone_dir:
                    shutil.rmtree(clone_dir, ignore_errors=True)

                st.error(
                    "Git was not found. Install Git, then restart "
                    "PowerShell and Streamlit."
                )

            except subprocess.TimeoutExpired:
                if clone_dir:
                    shutil.rmtree(clone_dir, ignore_errors=True)

                st.error(
                    "Cloning timed out. Try again or use a smaller repository."
                )

            except OSError as exc:
                if clone_dir:
                    shutil.rmtree(clone_dir, ignore_errors=True)

                st.error(f"Could not clone repository: {exc}")

    else:
        root = Path(value).expanduser()

        if not root.is_dir():
            st.error(
                "That local folder does not exist. Check the path and try again."
            )
            root = None

    if root is not None:
        try:
            with st.spinner(
                "Scanning source files and preparing the code index…"
            ):
                files = scan_repository(str(root))

            st.session_state.repo_files = files
            st.session_state.repo_root = str(root.resolve())
            st.session_state.last_question = ""
            st.session_state.last_answer = ""
            st.session_state.last_evidence = []

            if files:
                st.success(
                    f"Repository ready — scanned {len(files)} readable source files."
                )
            else:
                st.warning(
                    "No supported source files were found in this repository."
                )

        except (OSError, ValueError) as exc:
            st.error(f"Could not scan repository: {exc}")


# ============================================================
# Main workspace
# ============================================================

files = st.session_state.repo_files
repo_root = st.session_state.repo_root

if files:
    chunks = index_files(files)

    st.markdown("## Repository overview")
    st.caption(f"Workspace · `{Path(repo_root).name or repo_root}`")

    total_lines = sum(
        len(file["content"].splitlines())
        for file in files
    )

    metric1, metric2, metric3 = st.columns(3)

    metric1.metric("Source files", f"{len(files):,}")
    metric2.metric("Indexed code chunks", f"{len(chunks):,}")
    metric3.metric("Lines of code", f"{total_lines:,}")

    overview_tab, ask_tab, files_tab = st.tabs(
        [
            "✨ Overview & report",
            "💬 Ask RepoNap",
            "📁 File explorer",
        ]
    )

    # --------------------------------------------------------
    # Overview and report
    # --------------------------------------------------------

    with overview_tab:
        left, right = st.columns([1.35, 1], gap="large")

        with left:
            st.markdown(
                """
                <div class="rn-panel">
                    <div class="rn-panel-title">
                        Your codebase is ready
                    </div>
                    <div class="rn-panel-copy">
                        Start with the onboarding report, then ask RepoNap
                        about specific functions, files, or application
                        flows. Answers include retrieved snippets for
                        you to verify.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with right:
            st.markdown(
                """
                <div class="rn-panel">
                    <div class="rn-panel-title">
                        Suggested questions
                    </div>
                    <div class="rn-panel-copy">
                        • Where does the application start?<br>
                        • Which modules call each other?<br>
                        • Explain a specific function<br>
                        • Where is input validation handled?
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.write("")

        try:
            report = generate_report(repo_root, files, chunks)

            st.download_button(
                label="⬇  Download onboarding report (.md)",
                data=report,
                file_name="README_ONBOARDING.md",
                mime="text/markdown",
                use_container_width=True,
            )

        except (OSError, ValueError, KeyError, TypeError) as exc:
            st.error(f"Could not generate the report: {exc}")

    # --------------------------------------------------------
    # Ask RepoNap
    # --------------------------------------------------------

    with ask_tab:
        st.markdown("### Ask questions in plain English")

        st.caption(
            "RepoNap retrieves relevant source code first, "
            "then asks Gemma to explain it."
        )

        question = st.text_area(
            "Your question",
            value=st.session_state.last_question,
            placeholder=(
                "Example: Which function validates GitHub repository URLs?"
            ),
            max_chars=2000,
            height=110,
        )

        ask_clicked = st.button(
            "✦  Ask RepoNap",
            type="primary",
            use_container_width=True,
        )

        if ask_clicked:
            if not question.strip():
                st.warning("Enter a question first.")

            else:
                try:
                    with st.spinner(
                        "Searching the repository for relevant code…"
                    ):
                        evidence = retrieve_context(
                            files,
                            question,
                            top_k=4,
                        )

                    if is_app_use_question(question):
                        targeted_evidence = select_app_use_evidence(evidence)

                        if targeted_evidence:
                            evidence = targeted_evidence

                    if not evidence:
                        st.warning(
                            "No matching code was found. Try a function "
                            "name, filename, or more specific keyword."
                        )

                    else:
                        context_parts = []

                        for item in evidence:
                            context_parts.append(
                                f"File: {item['path']}\n"
                                f"Lines: {item['start_line']}-"
                                f"{item['end_line']}\n"
                                f"Code:\n{item['content']}"
                            )

                        context = "\n\n---\n\n".join(context_parts)

                        with st.spinner(
                            "Gemma is analyzing the retrieved code…"
                        ):
                            answer = ask_gemma(question, context)

                        st.session_state.last_question = question
                        st.session_state.last_answer = answer
                        st.session_state.last_evidence = evidence

                except Exception as exc:
                    st.error(
                        f"Request failed: {exc}\n\n"
                        "Check that Ollama is running, the configured "
                        "Gemma model is available, and the local LLM "
                        "function accepts a question and context."
                    )

        if st.session_state.last_answer:
            st.markdown("#### RepoNap's answer")

            with st.container(border=True):
                st.write(st.session_state.last_answer)

            st.markdown("#### Source evidence")

            for item in st.session_state.last_evidence:
                title = (
                    f"{item['path']} · lines "
                    f"{item['start_line']}–{item['end_line']}"
                )

                with st.expander(title):
                    st.code(item["content"], language=None)

            st.caption(
                "Retrieved snippets are evidence candidates. Check the "
                "source before relying on an AI-generated explanation."
            )

    # --------------------------------------------------------
    # File explorer
    # --------------------------------------------------------

    with files_tab:
        st.markdown("### Scanned source files")

        search_text = st.text_input(
            "Filter files by path",
            placeholder="e.g. app.py, src/, tests",
        )

        filtered_files = [
            file
            for file in files
            if search_text.lower() in file["path"].lower()
        ]

        st.caption(
            f"Showing {len(filtered_files)} of {len(files)} files"
        )

        for file in filtered_files:
            line_count = len(file["content"].splitlines())

            with st.expander(
                f"📄 {file['path']} · {line_count} lines"
            ):
                st.code(file["content"], language=None)

else:
    # --------------------------------------------------------
    # First-time welcome screen
    # --------------------------------------------------------

    st.markdown(
        """
        <div class="rn-panel">
            <div class="rn-panel-title">
                Ready for your first repository?
            </div>
            <div class="rn-panel-copy">
                Use the left panel to paste a public GitHub URL or enter
                a local folder path. RepoNap will scan supported source
                files, prepare an index, and help you explore the project.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    tip1, tip2, tip3 = st.columns(3)

    with tip1:
        st.markdown(
            """
            <div class="rn-panel">
                <div class="rn-panel-title">01 · Connect</div>
                <div class="rn-panel-copy">
                    Paste a public GitHub URL or a local repository path.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with tip2:
        st.markdown(
            """
            <div class="rn-panel">
                <div class="rn-panel-title">02 · Understand</div>
                <div class="rn-panel-copy">
                    Review the file inventory and generate an onboarding report.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with tip3:
        st.markdown(
            """
            <div class="rn-panel">
                <div class="rn-panel-title">03 · Ask</div>
                <div class="rn-panel-copy">
                    Ask Gemma questions grounded in retrieved source code.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# Footer
# ============================================================

st.divider()

st.caption(
    "RepoNap · Local-first codebase onboarding · "
    "AI requests run through your configured Ollama server. "
    "Review generated explanations before relying on them."
)
