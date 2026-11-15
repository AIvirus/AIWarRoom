"""
The self-learning guide quotes real project files line by line. If a file changes and the
lesson doesn't, students would be taught code that no longer exists, so this test fails.
"""

import importlib.util
from pathlib import Path

CHECKER = Path(__file__).resolve().parents[2] / "self-learning-guide" / "tools" / "check_guide.py"


def test_every_quoted_code_block_matches_the_real_file(capsys):
    spec = importlib.util.spec_from_file_location("check_guide", CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.check() == 0, capsys.readouterr().out
