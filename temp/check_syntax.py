"""检查 src/ 下所有 Python 文件的语法。"""
import ast
import sys
from pathlib import Path

bad = []
for p in Path("src").rglob("*.py"):
    try:
        ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError as e:
        bad.append(f"{p}: {e}")

if bad:
    print("Syntax errors:")
    for b in bad:
        print(f"  {b}")
    sys.exit(1)
else:
    print(f"Syntax OK ({len(list(Path('src').rglob('*.py')))} files)")
