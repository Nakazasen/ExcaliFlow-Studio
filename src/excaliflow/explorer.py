"""Evidence-first codebase explanations for engineers and learners."""

from __future__ import annotations

import ast
import json
import os
import re
from collections import Counter
from pathlib import Path


IGNORED_DIRECTORIES = {
    ".agents", ".env", ".excaliflow", ".git", ".mypy_cache", ".nox",
    ".pytest_cache", ".ruff_cache", ".tmp_smoke", ".tox", ".venv",
    "__pycache__", "build", "coverage", "dist", "dist-packages", "env",
    "graphify-out", "local_cases", "local_runs", "node_modules", "output",
    "site-packages", "target", "vendor", "venv",
}
MAX_SOURCE_FILE_BYTES = 2 * 1024 * 1024
LANGUAGES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".cs": "C#",
    ".bas": "VBA",
    ".cls": "VBA",
}
DECLARATION = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?(?:function|class|interface|struct|fn)\s+([A-Za-z_][\w]*)", re.MULTILINE)
JS_TS_DECLARATION = re.compile(
    r"^\s*(?:export\s+(?:default\s+)?)?(?:async\s+)?(?:function|class|interface|type|enum)\s+([A-Za-z_$][\w$]*)"
    r"|^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>",
    re.MULTILINE,
)
GO_DECLARATION = re.compile(
    r"^\s*(?:type\s+([A-Za-z_]\w*)\s+(?:struct|interface)|func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)\s*\()",
    re.MULTILINE,
)
RUST_DECLARATION = re.compile(
    r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:fn|struct|enum|trait|impl)\s+([A-Za-z_]\w*)",
    re.MULTILINE,
)
JAVA_DECLARATION = re.compile(
    r"^\s*(?:public|private|protected)?\s*(?:abstract\s+|final\s+|static\s+)*(?:class|interface|enum|record)\s+([A-Za-z_]\w*)",
    re.MULTILINE,
)
IMPORT = re.compile(r"^\s*(?:import\s+.*?from\s+|import\s+|use\s+|from\s+)([\w./@-]+)", re.MULTILINE)
CS_DECLARATION = re.compile(
    r"^\s*(?:public|private|protected|internal|file)?\s*(?:static\s+|sealed\s+|abstract\s+|partial\s+|readonly\s+)*"
    r"(class|interface|struct|enum|record(?:\s+struct|\s+class)?)\s+([A-Za-z_]\w*)",
    re.MULTILINE,
)
CS_METHOD = re.compile(
    r"^\s*(?:public|private|protected|internal)\s+(?:static\s+|virtual\s+|override\s+|async\s+|sealed\s+|new\s+)*"
    r"[A-Za-z_][\w.<>\[\], ?]*?\s+([A-Za-z_]\w*)\s*\(",
    re.MULTILINE,
)
CS_USING = re.compile(r"^\s*using\s+(?:static\s+)?([\w.]+)\s*;", re.MULTILINE)
CS_RESERVED_NAMES = {"if", "for", "foreach", "while", "switch", "catch", "using", "return", "new", "lock", "fixed", "sizeof", "typeof"}
VBA_MODULE = re.compile(r'Attribute\s+VB_Name\s*=\s*"([A-Za-z_]\w*)"')
VBA_PROC = re.compile(
    r"^\s*(?:Public\s+|Private\s+|Friend\s+)?(?:Static\s+)?(Sub|Function|Property\s+(?:Get|Let|Set)|Type|Enum)\s+([A-Za-z_]\w*)",
    re.MULTILINE | re.IGNORECASE,
)
VBA_DECLARE_LIB = re.compile(
    r'^\s*(?:Public\s+|Private\s+)?Declare\s+(?:PtrSafe\s+)?(?:Sub|Function)\s+([A-Za-z_]\w*)\s+Lib\s+"([^"]+)"',
    re.MULTILINE | re.IGNORECASE,
)
STOP_WORDS = {
    "a", "an", "and", "are", "about", "code", "does", "explain", "for", "how", "in", "is", "of", "show", "the", "this", "to", "what", "where", "with",
    "cai", "cái", "cho", "cua", "của", "dau", "đâu", "gi", "gì", "ham", "hàm", "la", "là", "lop", "lớp", "nao", "nào", "o", "ở", "toi", "tôi", "ve", "về",
}


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current_root, directories, names in os.walk(root, topdown=True):
        directories[:] = [
            directory
            for directory in directories
            if directory not in IGNORED_DIRECTORIES
            and not directory.startswith((".venv", "venv"))
            and not (Path(current_root) / directory).is_symlink()
        ]
        current = Path(current_root)
        for name in names:
            path = current / name
            if path.suffix.lower() in LANGUAGES:
                files.append(path)
    return sorted(files)


class _PythonVisitor(ast.NodeVisitor):
    def __init__(self, relative_path: str) -> None:
        self.relative_path = relative_path
        self.scope: list[str] = []
        self.symbols: list[dict] = []
        self.relationships: list[dict] = []

    def _symbol(self, name: str, kind: str, node: ast.AST) -> None:
        qualified = ".".join([*self.scope, name])
        docstring = ast.get_docstring(node) if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) else None
        self.symbols.append({
            "name": name,
            "qualified_name": qualified,
            "kind": kind,
            "file": self.relative_path,
            "line": getattr(node, "lineno", 1),
            "docstring": (docstring or "").split("\n")[0].strip(),
        })

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._symbol(node.name, "class", node)
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._symbol(node.name, "method" if self.scope else "function", node)
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Import(self, node: ast.Import) -> None:
        for item in node.names:
            self.relationships.append({"from": self.relative_path, "to": item.name, "kind": "imports", "line": node.lineno})

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        target = "." * node.level + (node.module or "")
        self.relationships.append({"from": self.relative_path, "to": target or "relative module", "kind": "imports", "line": node.lineno})


def inspect_codebase(project_dir: str | Path) -> dict:
    """Return only source-backed facts suitable for diagrams and explanations."""
    root = Path(project_dir).resolve()
    if not root.is_dir():
        raise ValueError(f"Codebase directory does not exist: {root}")
    symbols: list[dict] = []
    relationships: list[dict] = []
    languages: Counter[str] = Counter()
    parse_warnings: list[str] = []
    files = _source_files(root)
    for path in files:
        language = LANGUAGES[path.suffix.lower()]
        languages[language] += 1
        relative = _relative(root, path)
        try:
            if path.stat().st_size > MAX_SOURCE_FILE_BYTES:
                parse_warnings.append(f"{relative}: source file exceeds {MAX_SOURCE_FILE_BYTES} bytes and was skipped")
                continue
        except OSError as error:
            parse_warnings.append(f"{relative}: source file metadata could not be read ({error})")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        suffix = path.suffix.lower()
        if suffix == ".py":
            try:
                visitor = _PythonVisitor(relative)
                visitor.visit(ast.parse(text, filename=relative))
                symbols.extend(visitor.symbols)
                relationships.extend(visitor.relationships)
            except SyntaxError as error:
                parse_warnings.append(f"{relative}:{error.lineno}: Python syntax could not be parsed")
            except (RecursionError, MemoryError) as error:
                parse_warnings.append(f"{relative}: Python AST exceeded safe analysis limits ({type(error).__name__})")
            continue
        if suffix == ".cs":
            current_type = ""
            for match in CS_DECLARATION.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                kind_kw, name = match.group(1).split()[0], match.group(2)
                current_type = name
                symbols.append({"name": name, "qualified_name": name, "kind": kind_kw, "file": relative, "line": line, "docstring": ""})
            for match in CS_METHOD.finditer(text):
                name = match.group(1)
                if name in CS_RESERVED_NAMES:
                    continue
                line = text.count("\n", 0, match.start()) + 1
                qualified = f"{current_type}.{name}" if current_type else name
                symbols.append({"name": name, "qualified_name": qualified, "kind": "method", "file": relative, "line": line, "docstring": ""})
            for match in CS_USING.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                relationships.append({"from": relative, "to": match.group(1), "kind": "imports", "line": line})
            continue
        if suffix in {".bas", ".cls"}:
            mod_name = Path(relative).stem
            mod_match = VBA_MODULE.search(text)
            if mod_match:
                mod_name = mod_match.group(1)
                line = text.count("\n", 0, mod_match.start()) + 1
                symbols.append({"name": mod_name, "qualified_name": mod_name, "kind": "module", "file": relative, "line": line, "docstring": ""})
            for match in VBA_PROC.finditer(text):
                proc_kind = match.group(1).split()[0].lower()
                proc_name = match.group(2)
                line = text.count("\n", 0, match.start()) + 1
                symbols.append({"name": proc_name, "qualified_name": f"{mod_name}.{proc_name}", "kind": proc_kind, "file": relative, "line": line, "docstring": ""})
            for match in VBA_DECLARE_LIB.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                relationships.append({"from": relative, "to": match.group(2), "kind": "imports", "line": line})
            continue
        decl_pattern = {
            ".js": JS_TS_DECLARATION,
            ".jsx": JS_TS_DECLARATION,
            ".ts": JS_TS_DECLARATION,
            ".tsx": JS_TS_DECLARATION,
            ".go": GO_DECLARATION,
            ".rs": RUST_DECLARATION,
            ".java": JAVA_DECLARATION,
        }.get(suffix, DECLARATION)
        for match in decl_pattern.finditer(text):
            decl_name = next((group for group in match.groups() if group), None)
            if not decl_name:
                continue
            line = text.count("\n", 0, match.start()) + 1
            symbols.append({"name": decl_name, "qualified_name": decl_name, "kind": "declaration", "file": relative, "line": line, "docstring": ""})
        for match in IMPORT.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            relationships.append({"from": relative, "to": match.group(1), "kind": "imports", "line": line})
    return {
        "root": str(root),
        "files": [_relative(root, path) for path in files],
        "languages": dict(sorted(languages.items())),
        "symbols": symbols,
        "relationships": relationships,
        "parse_warnings": parse_warnings,
        "fidelity": "Source scan: Python AST plus declaration/import extraction for other supported languages.",
    }


def _format_languages(languages: dict[str, int]) -> str:
    return ", ".join(f"{language} ({count})" for language, count in languages.items()) or "no supported source files"


def _evidence(item: dict) -> str:
    return f"Evidence: `{item['file']}:{item['line']}`"


def _matching_symbols(report: dict, question: str) -> list[dict]:
    words = {word.lower() for word in re.findall(r"[^\W\d][\w.\\/-]*", question, re.UNICODE) if word.lower() not in STOP_WORDS}
    scored: list[tuple[int, dict]] = []
    for symbol in report["symbols"]:
        haystack = " ".join((symbol["name"], symbol["qualified_name"], symbol["file"])).lower()
        score = sum(word in haystack for word in words)
        if score:
            scored.append((score, symbol))
    return [symbol for _, symbol in sorted(scored, key=lambda pair: (-pair[0], pair[1]["file"], pair[1]["line"]))[:5]]


def explain_codebase(report: dict, audience: str = "engineer") -> str:
    if audience not in {"engineer", "learner"}:
        raise ValueError("Audience must be engineer or learner.")
    root_name = Path(report["root"]).name
    lines = [f"# {root_name}: codebase guide", "", "## Evidence-backed map", ""]
    lines.append(f"- Supported source files found: {len(report['files'])}.")
    lines.append(f"- Languages: {_format_languages(report['languages'])}.")
    lines.append(f"- Relationships found: {len(report['relationships'])} import statements.")
    lines.extend(["", "## Key building blocks", ""])
    for symbol in report["symbols"][:12]:
        description = f"{symbol['kind']} `{symbol['qualified_name']}`"
        if audience == "learner":
            description = f"`{symbol['qualified_name']}` is a {symbol['kind']} — a named building block the program can reuse."
        if symbol["docstring"]:
            description += f" {symbol['docstring']}"
        lines.append(f"- {description} ({_evidence(symbol)})")
    if audience == "learner":
        lines.extend(["", "## Suggested reading order", "", "1. Start with the first files listed below; they give you the vocabulary of this project.", "2. Follow each import relationship to see which file relies on another.", "3. Ask a focused question with `excaliflow ask --audience learner --question \"What is Name?\"`."])
    else:
        lines.extend(["", "## Engineering follow-up", "", "- Use the existing architecture viewer for the relationship graph.", "- Use `excaliflow ask` for a source-cited lookup before changing a component."])
    if report["parse_warnings"]:
        lines.extend(["", "## Scan limitations", "", *[f"- {warning}" for warning in report["parse_warnings"]]])
    lines.extend(["", "## Fidelity", "", report["fidelity"]])
    return "\n".join(lines) + "\n"


def answer_question(report: dict, question: str, audience: str = "engineer") -> str:
    if not question.strip():
        raise ValueError("Question must not be empty.")
    lower = question.lower()
    if any(term in lower for term in ("overview", "architecture", "the codebase", "this codebase", "the project", "project overview", "tổng quan", "kiến trúc", "ứng dụng này làm gì", "dự án này")):
        return explain_codebase(report, audience)
    if any(term in lower for term in ("depend", "import", "relationship", "connect", "phụ thuộc", "liên kết", "kết nối")):
        internal_modules: set[str] = set()
        for file in report["files"]:
            module = Path(file).with_suffix("").as_posix().replace("/", ".")
            internal_modules.update({module, module.rsplit(".", 1)[-1]})
            if module.startswith("src."):
                internal_modules.add(module.removeprefix("src."))
        internal = [relation for relation in report["relationships"] if relation["to"].lstrip(".").split(".")[0] in internal_modules]
        candidates = internal + [relation for relation in report["relationships"] if relation not in internal]
        query_terms = {
            word.lower() for word in re.findall(r"[^\W\d][\w.\\/-]*", question, re.UNICODE)
            if word.lower() not in STOP_WORDS and word.lower() not in {"depend", "dependency", "import", "relationship", "connect"}
        }
        focused = [
            relation for relation in candidates
            if any(term in f"{relation['from']} {relation['to']}".lower() for term in query_terms)
        ]
        matches = (focused or candidates)[:12]
        if not matches:
            return "No import relationships were found by the supported source scan.\n\nFidelity: " + report["fidelity"]
        lines = ["# Relationship answer", ""]
        for relation in matches:
            lines.append(f"- `{relation['from']}:{relation['line']}` imports `{relation['to']}`.")
        lines.extend(["", "## Fidelity", "", report["fidelity"]])
        return "\n".join(lines) + "\n"
    matches = _matching_symbols(report, question)
    if not matches:
        return ("I could not find a matching declaration in the supported source scan. "
                "Try an exact function, class, or file name.\n\nFidelity: " + report["fidelity"] + "\n")
    lines = ["# Source-backed answer", ""]
    for symbol in matches:
        if audience == "learner":
            text = f"`{symbol['qualified_name']}` is a {symbol['kind']}. Think of it as a named piece of the program that other code can use."
        else:
            text = f"`{symbol['qualified_name']}` is declared as a {symbol['kind']}."
        if symbol["docstring"]:
            text += f" Its source documentation says: {symbol['docstring']}"
        lines.append(f"- {text} {_evidence(symbol)}")
    lines.extend(["", "## Fidelity", "", report["fidelity"]])
    return "\n".join(lines) + "\n"


def serialise_answer(report: dict, question: str | None, audience: str, output_format: str) -> str:
    if output_format == "json":
        payload = {"audience": audience, "question": question, "report": report}
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    return answer_question(report, question, audience) if question else explain_codebase(report, audience)
