"""Skill manifest generator.

Emits skills in multiple agent-harness formats:
- Claude Code (SKILL.md with YAML frontmatter)
- Cursor (rules/<name>.mdc)
- Codex / generic (JSON tools definition)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from ducktap.core import plugins
from ducktap.core.naming import cli_command_name
from ducktap.core.spec import APISpec

_TEMPLATES_DIR = Path(__file__).parent / "templates"


class SkillGenerator:
    name = "skill"
    target = "skill"

    def generate(self, spec: APISpec, out_dir: str, **opts: Any) -> list[str]:
        env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        env.filters["cmd"] = cli_command_name

        cli_bin = f"{spec.name}-dt-cli"
        mcp_bin = f"{spec.name}-dt-mcp"
        skill_name = f"ducktap-{spec.name}"

        root = Path(out_dir) / "skills" / skill_name
        root.mkdir(parents=True, exist_ok=True)

        ctx = {
            "spec": spec, "cli_bin": cli_bin, "mcp_bin": mcp_bin,
            "skill_name": skill_name, "harnesses": opts.get("harnesses", ["claude-code"]),
        }
        written: list[str] = []
        # Always produce the Claude SKILL.md
        for tpl, dst in [
            ("skill/SKILL.md.j2", root / "SKILL.md"),
            ("skill/tools.json.j2", root / "tools.json"),
            ("skill/cursor.mdc.j2", root / f"{skill_name}.mdc"),
        ]:
            text = env.get_template(tpl).render(**ctx)
            dst.write_text(text, encoding="utf-8")
            written.append(str(dst))
        return written


plugins.register_generator(SkillGenerator())
