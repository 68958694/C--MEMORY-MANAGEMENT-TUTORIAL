"""Coding: JARVIS writes whole projects into your workspace folder and opens them.

Projects live in ~/jarvis-projects/<name>/ (set JARVIS_WORKSPACE to change).
JARVIS writes the files but never runs them by itself - you stay in control of
what executes on your machine.
"""

import re
import webbrowser
from pathlib import Path

from jarvis import config, llm, skills

MAX_CONTEXT_CHARS = 150_000  # how much existing code to show the AI when improving a project
TEXT_SUFFIXES = {".html", ".css", ".js", ".ts", ".jsx", ".tsx", ".json", ".py", ".md", ".txt", ".toml",
                 ".yml", ".yaml", ".sql", ".sh", ".bat", ".ps1", ".c", ".h", ".cpp", ".java", ".go", ".rs",
                 ".php", ".rb", ".svg", ".env.example", ".gitignore", ".cfg", ".ini", ".xml", ".csv"}

BUILD_PROMPT = """You are an expert software engineer. Build this project completely:

{request}

Rules:
- Produce complete, working code. No placeholders, no "TODO", no "rest of code here".
- Prefer the simplest stack that does the job. For websites, landing pages, dashboards, games and tools
  that can run in a browser, use plain HTML/CSS/JavaScript with an index.html at the root so it opens with
  a double-click and needs no install. Only use a backend or framework when the request truly needs one.
- Make it look polished and modern, and work on phones.
- Include a short README.md explaining what it is and exactly how to run it.

Reply with JSON only, in this shape:
{{"summary": "one sentence describing what you built",
  "run": "one short sentence on how to run or open it",
  "files": [{{"path": "relative/path.ext", "content": "full file content"}}]}}"""

IMPROVE_PROMPT = """You are an expert software engineer working on an existing project.

Requested change:
{request}

Current project files:
{files}

Make the change. Return every file you create or modify, each with its complete new content
(not a diff). Leave unchanged files out. To delete a file, return it with "delete": true.

Reply with JSON only, in this shape:
{{"summary": "one sentence describing what you changed",
  "files": [{{"path": "relative/path.ext", "content": "full file content"}}]}}"""


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:60] or "project"


def project_dir(name: str) -> Path:
    return config.WORKSPACE_DIR / slugify(name)


def _safe_path(root: Path, rel: str) -> Path:
    """Resolve `rel` inside `root`, refusing absolute paths and ../ escapes."""
    target = (root / rel.lstrip("/\\")).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"refusing to write outside the project: {rel}")
    return target


def _write_files(root: Path, files: list) -> int:
    written = 0
    for f in files:
        if not isinstance(f, dict) or not f.get("path"):
            continue
        target = _safe_path(root, str(f["path"]))
        if f.get("delete"):
            target.unlink(missing_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(f.get("content", "")), encoding="utf-8")
        written += 1
    return written


def _open(root: Path) -> None:
    index = root / "index.html"
    if index.exists():
        webbrowser.open(index.resolve().as_uri())
    else:
        skills.open_path(root)


def build_project(name: str, request: str) -> str:
    root = project_dir(name)
    if root.exists() and any(root.iterdir()):
        return improve_project(name, request)
    data = llm.generate_json(BUILD_PROMPT.format(request=request))
    files = data.get("files") if isinstance(data, dict) else None
    if not files:
        return "The AI didn't return any files. Try describing the project in a bit more detail."
    root.mkdir(parents=True, exist_ok=True)
    count = _write_files(root, files)
    _open(root)
    return (f"Built {root.name} with {count} files in {root}. {data.get('summary', '')} "
            f"{data.get('run', '')}").strip()


def _read_project(root: Path) -> str:
    parts, total = [], 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(p.startswith(".") or p == "node_modules" for p in path.relative_to(root).parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if total + len(text) > MAX_CONTEXT_CHARS:
            parts.append(f"--- {path.relative_to(root).as_posix()} (omitted: too large)")
            continue
        total += len(text)
        parts.append(f"--- {path.relative_to(root).as_posix()}\n{text}")
    return "\n\n".join(parts)


def improve_project(name: str, change_request: str) -> str:
    root = project_dir(name)
    if not root.exists():
        return build_project(name, change_request)
    data = llm.generate_json(IMPROVE_PROMPT.format(request=change_request, files=_read_project(root)))
    files = data.get("files") if isinstance(data, dict) else None
    if not files:
        return "The AI didn't suggest any file changes. Could you describe the change differently?"
    count = _write_files(root, files)
    _open(root)
    return f"Updated {count} files in {root.name}. {data.get('summary', '')}".strip()


def list_projects() -> str:
    if not config.WORKSPACE_DIR.exists():
        return "I haven't built any projects yet."
    names = sorted(p.name for p in config.WORKSPACE_DIR.iterdir() if p.is_dir())
    if not names:
        return "I haven't built any projects yet."
    return f"Your projects: {', '.join(names)}. They're in {config.WORKSPACE_DIR}."


def open_project(name: str) -> str:
    root = project_dir(name)
    if not root.exists():
        return f"I can't find a project called {name}. {list_projects()}"
    _open(root)
    return f"Opening {root.name}."
