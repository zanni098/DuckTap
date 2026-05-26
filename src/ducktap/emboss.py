"""Emboss: brand-stamp generated CLIs with a custom identity.

Applies a user-supplied brand (name, description, author, license) to the
generated CLI package metadata and help text.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class BrandStamp:
    name: str = ""
    description: str = ""
    author: str = ""
    license: str = "MIT"
    homepage: str = ""

    def apply_to_pyproject(self, path: Path) -> None:
        """Rewrite pyproject.toml with branded metadata."""
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        out: list[str] = []
        in_project = False
        for line in lines:
            if line.strip().startswith("[project]"):
                in_project = True
            if in_project and line.strip().startswith("[") and not line.strip().startswith("[project]"):
                in_project = False
            if in_project and "name = " in line and self.name:
                out.append(f'name = "{self.name}"')
                continue
            if in_project and "description = " in line and self.description:
                out.append(f'description = "{self.description}"')
                continue
            out.append(line)
        path.write_text("\n".join(out) + "\n", encoding="utf-8")

    def apply_to_readme(self, path: Path) -> None:
        """Prepend brand header to README.md."""
        if not path.exists():
            return
        original = path.read_text(encoding="utf-8")
        header = f"# {self.name or 'Generated CLI'}\n\n"
        if self.description:
            header += f"{self.description}\n\n"
        if self.author:
            header += f"**Author:** {self.author}  \n"
        if self.license:
            header += f"**License:** {self.license}  \n"
        if self.homepage:
            header += f"**Homepage:** {self.homepage}  \n"
        header += "\n---\n\n"
        path.write_text(header + original, encoding="utf-8")


def emboss(out_dir: str, name: str, stamp: BrandStamp) -> list[str]:
    """Apply a brand stamp to a generated CLI directory."""
    root = Path(out_dir) / f"{name}-dt-cli"
    modified: list[str] = []
    if (root / "pyproject.toml").exists():
        stamp.apply_to_pyproject(root / "pyproject.toml")
        modified.append(str(root / "pyproject.toml"))
    if (root / "README.md").exists():
        stamp.apply_to_readme(root / "README.md")
        modified.append(str(root / "README.md"))
    return modified
