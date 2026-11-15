"""
Checks that the guide's code matches the real project.

In a lesson, a code block copied from a real file is marked like this:

    <!-- source: accounts/models.py:1-12 -->
    ```python
    ...exactly lines 1 to 12 of accounts/models.py...
    ```

This script finds every such marker and compares the code block with the real file.
If someone changes the project and forgets the guide, this script says which lesson is
out of date. Run it from the project folder:

    python self-learning-guide/tools/check_guide.py
"""

import re
import sys
from pathlib import Path

GUIDE = Path(__file__).resolve().parent.parent
PROJECT = GUIDE.parent

MARKER = re.compile(
    r"<!-- source: (?P<file>[^:]+):(?P<start>\d+)-(?P<end>\d+) -->\s*\n"
    r"```[\w-]*\n(?P<code>.*?)\n```",
    re.S,
)


def check() -> int:
    problems, checked = [], 0
    for lesson in sorted(GUIDE.rglob("*.md")):
        text = lesson.read_text(encoding="utf-8")
        for match in MARKER.finditer(text):
            checked += 1
            source = PROJECT / match["file"]
            where = (
                f"{lesson.relative_to(GUIDE)} -> {match['file']}:{match['start']}-{match['end']}"
            )
            if not source.exists():
                problems.append(f"{where}: file not found")
                continue
            lines = source.read_text(encoding="utf-8").splitlines()
            real = "\n".join(lines[int(match["start"]) - 1 : int(match["end"])])
            if real != match["code"]:
                problems.append(f"{where}: code differs from the real file")
    for problem in problems:
        print("OUT OF DATE:", problem)
    print(f"Checked {checked} code blocks; {len(problems)} out of date.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(check())
