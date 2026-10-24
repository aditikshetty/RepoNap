# RepoNap

**Understand a codebase without reading every file manually.**

RepoNap is a local-first codebase exploration tool that helps developers inspect a repository, find relevant code, understand project structure, and ask questions about their code using a locally running language model.

## Features

- **Repository scanning:** Scan a local code repository and inspect its files.
- **Codebase exploration:** Browse files and understand the project structure.
- **Code search and retrieval:** Retrieve relevant code snippets for a question.
- **Ask RepoNap:** Ask questions about a repository and receive answers grounded in retrieved code context.
- **Local AI:** Use Ollama with Gemma to generate answers locally.
- **Repository insights:** View available repository metrics and analysis.
- **Report generation:** Generate a report from repository analysis.
- **Evidence-based answers:** Use relevant code snippets to help verify generated explanations.

## Tech Stack

- Python
- Streamlit
- Ollama
- Gemma
- pytest

## Prerequisites

Install the following before running RepoNap:

- Python 3.11
- Git, if you want to analyze GitHub repositories by cloning them
- Ollama
- A Gemma model available in Ollama

## Installation

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd RepoNap
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with your actual GitHub repository URL.

Alternatively, download the repository as a ZIP file and extract it.

### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can run commands using the virtual environment's Python executable directly.

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Set up Ollama

Install Ollama from https://ollama.com/.

Download the model used by your application. For example, if your application is configured for `gemma3:1b`:

```powershell
ollama pull gemma3:1b
```

Ensure Ollama is running before asking RepoNap to generate AI answers.

### 5. Run RepoNap

```powershell
python -m streamlit run app.py
```

Open the local URL printed in the terminal by Streamlit.

## Running Tests

Run the test suite from the project directory:

```powershell
python -m pytest -v
```

To check Python syntax:

```powershell
python -m py_compile app.py
```

## How to Use

1. Start RepoNap.
2. Select a local repository or provide a supported GitHub repository URL.
3. Scan the repository.
4. Explore the available file and repository information.
5. Ask questions about the codebase.
6. Review the generated answer and supporting code evidence where available.
7. Generate a report if the feature is available in your version.

## Privacy and Limitations

- RepoNap is designed to use a locally running language model for AI answers.
- Repository scanning and retrieval depend on the file types and rules supported by the application.
- AI-generated explanations can be inaccurate. Verify important claims against the source code.
- GitHub repository access requires a working internet connection.
- Model performance depends on your hardware and the model you have installed.
- Do not assume every file type or repository is supported.

## Development

The project is organized into modules for the application interface, repository scanning, indexing, retrieval, local AI interaction, and report generation.

Tests are included to check selected application and module behavior.

## License

No license has been specified yet. Add a license file if you intend to distribute the project under an open-source license.
