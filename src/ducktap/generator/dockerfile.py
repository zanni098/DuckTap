"""Dockerfile generator.

For every language CLI that already exists in the output directory, emit a
multi-stage ``Dockerfile`` next to it. The build stage compiles/installs the
project; the runtime stage copies only the artifact it needs (a static binary,
a populated virtualenv, or compiled JS), which keeps the final image small.

The generator is language-aware rather than language-driven: it only writes a
Dockerfile for a CLI that is actually present, so ``press --docker`` with a
default target set produces a Python Dockerfile, and a full multi-language
press produces one per language.

Base images come in two flavours, selected with ``--docker-base``:

* ``alpine`` (default) -- Alpine, the smallest practical images.
* ``slim`` -- Debian-based, for teams that need glibc.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from ducktap.core import plugins
from ducktap.core.spec import APISpec

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


# Per-base image choices and the shell snippets that fetch build/runtime
# packages. Keeping them in one table means a template only has to interpolate.
_BASES: dict[str, dict[str, str]] = {
    "alpine": {
        "python_build": "python:3.12-alpine",
        "python_runtime": "python:3.12-alpine",
        "go_build": "golang:1.22-alpine",
        "go_runtime": "alpine:3.20",
        "rust_build": "rust:1.82-alpine",
        "rust_runtime": "alpine:3.20",
        "node_build": "node:20-alpine",
        "node_runtime": "node:20-alpine",
        "go_toolchain": "RUN apk add --no-cache git",
        "rust_toolchain": "RUN apk add --no-cache build-base perl",
        "ca_install": "RUN apk add --no-cache ca-certificates",
    },
    "slim": {
        "python_build": "python:3.12-slim",
        "python_runtime": "python:3.12-slim",
        "go_build": "golang:1.22-bookworm",
        "go_runtime": "debian:bookworm-slim",
        "rust_build": "rust:1.82-slim-bookworm",
        "rust_runtime": "debian:bookworm-slim",
        "node_build": "node:20-bookworm-slim",
        "node_runtime": "node:20-bookworm-slim",
        "go_toolchain": (
            "RUN apt-get update && apt-get install -y --no-install-recommends git "
            "&& rm -rf /var/lib/apt/lists/*"
        ),
        "rust_toolchain": (
            "RUN apt-get update && apt-get install -y --no-install-recommends pkg-config "
            "&& rm -rf /var/lib/apt/lists/*"
        ),
        "ca_install": (
            "RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates "
            "&& rm -rf /var/lib/apt/lists/*"
        ),
    },
}

# Aliases accepted on the command line, mapped onto a canonical base.
_BASE_ALIASES = {
    "alpine": "alpine",
    "slim": "slim",
    "debian": "slim",
    "bookworm": "slim",
}


class DockerfileGenerator:
    name = "dockerfile"
    target = "dockerfile"

    def generate(self, spec: APISpec, out_dir: str, **opts: Any) -> list[str]:
        base = _BASE_ALIASES.get(str(opts.get("docker_base", "alpine")).lower())
        if base is None:
            raise ValueError(
                "unknown docker base "
                f"{opts.get('docker_base')!r}; expected one of: alpine, slim"
            )

        env = _env()
        root = Path(out_dir)
        written: list[str] = []

        for lang, dirname, binary, template in _languages(spec.name):
            project = root / dirname
            if not project.exists():
                continue
            has_lock = (project / "requirements.lock").exists()
            ctx = {
                "cli_bin": binary,
                "rust_bin": binary,
                "base": base,
                "has_requirements_lock": has_lock,
                "requirements_copy": (
                    "requirements.txt requirements.lock" if has_lock else "requirements.txt"
                ),
                "requirements_file": "requirements.lock" if has_lock else "requirements.txt",
                "create_user": _create_user_command(base),
                "build_image": _BASES[base][f"{lang}_build"],
                "runtime_image": _BASES[base][f"{lang}_runtime"],
                "go_toolchain": _BASES[base]["go_toolchain"],
                "rust_toolchain": _BASES[base]["rust_toolchain"],
                "ca_install": _BASES[base]["ca_install"],
            }
            text = env.get_template(template).render(**ctx)
            dst = project / "Dockerfile"
            dst.write_text(text, encoding="utf-8")
            written.append(str(dst))

        return written


def _create_user_command(base: str) -> str:
    """A non-root user, in the syntax the base distro understands."""
    if base == "alpine":
        return "RUN addgroup -S app && adduser -S app -G app"
    return "RUN groupadd --system app && useradd --system --gid app app"


def _languages(name: str) -> list[tuple[str, str, str, str]]:
    """(template key, project dir, CLI binary, template path) for each language.

    Names mirror the individual generators exactly -- if a generator's output
    directory or binary ever changes, this table has to change with it.
    """
    rust_bin = name.replace("-", "_") + "_dt_rs"
    return [
        ("python", f"{name}-dt-cli", f"{name}-dt-cli", "dockerfile/Dockerfile.python.j2"),
        ("go", f"{name}-dt-go", f"{name}-dt-go", "dockerfile/Dockerfile.go.j2"),
        ("rust", f"{name}-dt-rs", rust_bin, "dockerfile/Dockerfile.rust.j2"),
        ("node", f"{name}-dt-ts", f"{name}-dt-ts", "dockerfile/Dockerfile.typescript.j2"),
    ]


plugins.register_generator(DockerfileGenerator())
