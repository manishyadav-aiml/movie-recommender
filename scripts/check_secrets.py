"""Scan the project (and git history, if any) for accidentally committed secrets.

Usage: python -m scripts.check_secrets
For a deeper scan before publishing, also run:  gitleaks detect   (or enable GitHub secret scanning)
"""
import re
import subprocess
import sys
from pathlib import Path

PATTERNS = {
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "Private key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "Google API key": re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
    "Slack token": re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}"),
    "Hard-coded secret": re.compile(
        r"""(?i)\b(api[_-]?key|secret[_-]?key|secret|token|passwd|password)\b\s*[:=]\s*['"][^'"\s]{12,}['"]"""),
    "Password hash literal": re.compile(r"(?:scrypt|pbkdf2):[a-z0-9:]+\$[A-Za-z0-9+/]{8,}\$[0-9a-f]{40,}"),
}
SKIP_DIRS = {".git", "data", "venv", ".venv", "node_modules", "__pycache__", "raw", "docs", "instance"}
SKIP_SUFFIX = {".png", ".gz", ".zip", ".pkl", ".db", ".ico", ".ipynb"}
ROOT = Path(__file__).resolve().parent.parent


def scan_text(label: str, text: str) -> list[str]:
    hits = []
    for name, rx in PATTERNS.items():
        for m in rx.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            hits.append(f"{label}:{line}: {name}")
    return hits


def main() -> int:
    findings = []
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if (not path.is_file() or set(rel.parts) & SKIP_DIRS or path.suffix in SKIP_SUFFIX
                or rel.name == "check_secrets.py"):
            continue
        if rel.name == ".env":
            findings.append(f"{rel}: a real .env file exists - make sure it is git-ignored and never pushed")
            continue
        try:
            findings += scan_text(str(rel), path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            pass

    gitignore = (ROOT / ".gitignore").read_text() if (ROOT / ".gitignore").exists() else ""
    if ".env" not in gitignore:
        findings.append(".gitignore: .env is not ignored")

    if (ROOT / ".git").exists():  # history scan: secrets removed later still live in old commits
        try:
            log = subprocess.run(["git", "log", "-p", "--all"], cwd=ROOT, capture_output=True, text=True, timeout=120).stdout
            findings += scan_text("git-history", log)
        except (OSError, subprocess.SubprocessError):
            print("note: could not read git history")

    if findings:
        print("Possible secrets found:")
        print("\n".join(" - " + f for f in findings))
        return 1
    print("No secrets found in the working tree" + (" or git history." if (ROOT / ".git").exists() else "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
