"""Tiny template engine: `{kind:name}` is replaced by money.format_<kind>(values[name])."""
import re
from pathlib import Path

from src import money

TEMPLATES = Path(__file__).parent / "templates"


def render_template(name, **values):
    text = (TEMPLATES / name).read_text(encoding="utf-8")

    def sub(m):
        kind, key = m.group(1), m.group(2)
        return getattr(money, "format_" + kind)(values[key])

    return re.sub(r"\{(\w+):(\w+)\}", sub, text).rstrip("\n")
