"""The skill is the agent-facing contract: every command and flag it documents
has to exist in the CLI it documents.

Operations are grouped under their first tag, so a skill listing the ungrouped
`get-pet-by-id` (rather than `pet get-pet-by-id`), or the raw parameter name
`--petId` (rather than the kebab-cased `--pet-id`), sends every agent that
reads it into "no such command".
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

from ducktap.core.pipeline import press

FIXTURE = Path(__file__).parent / "fixtures" / "petstore.yaml"


@pytest.fixture(scope="module")
def pressed(tmp_path_factory):
    out = tmp_path_factory.mktemp("skillcheck")
    result = press(str(FIXTURE), str(out), targets=["python-cli", "skill"])
    return result.spec, out


@pytest.fixture(scope="module")
def cli_group(pressed):
    _, out = pressed
    sys.path.insert(0, str(out / "petstore-dt-cli"))
    try:
        for mod in [m for m in sys.modules if m.startswith("petstore_dt_cli")]:
            del sys.modules[mod]
        yield importlib.import_module("petstore_dt_cli.main").cli
    finally:
        sys.path.remove(str(out / "petstore-dt-cli"))
        for mod in [m for m in sys.modules if m.startswith("petstore_dt_cli")]:
            del sys.modules[mod]


def _resolve(group, parts: list[str]):
    """Walk a click command tree; return the command or None."""
    node = group
    for part in parts:
        if not hasattr(node, "commands"):
            return None
        node = node.commands.get(part)
        if node is None:
            return None
    return node


def test_every_tools_json_command_exists(pressed, cli_group):
    _, out = pressed
    tools = json.loads(
        (out / "skills" / "ducktap-petstore" / "tools.json").read_text(encoding="utf-8")
    )
    assert tools["tools"], "no tools emitted"
    for tool in tools["tools"]:
        parts = tool["command"].split()[1:]  # drop the binary name
        assert _resolve(cli_group, parts) is not None, (
            f"skill documents `{tool['command']}` but the CLI has no such command"
        )


def test_every_tools_json_flag_exists(pressed, cli_group):
    _, out = pressed
    tools = json.loads(
        (out / "skills" / "ducktap-petstore" / "tools.json").read_text(encoding="utf-8")
    )
    for tool in tools["tools"]:
        command = _resolve(cli_group, tool["command"].split()[1:])
        available = {opt for param in command.params for opt in param.opts}
        for parameter in tool["parameters"]:
            # Collisions get a location-prefixed flag; the documented flag is
            # only required to be *a* flag on the command.
            assert parameter["flag"] in available or any(
                opt.endswith(parameter["flag"].lstrip("-")) for opt in available
            ), f"{tool['command']} has no flag {parameter['flag']}"


def test_skill_md_lists_grouped_invocations(pressed):
    _, out = pressed
    skill = (out / "skills" / "ducktap-petstore" / "SKILL.md").read_text(encoding="utf-8")
    assert "petstore-dt-cli pet get-pet-by-id" in skill
    assert "petstore-dt-cli get-pet-by-id" not in skill
    assert "--pet-id" in skill and "--petId" not in skill


def test_skill_md_documents_the_real_exit_codes(pressed):
    _, out = pressed
    skill = (out / "skills" / "ducktap-petstore" / "SKILL.md").read_text(encoding="utf-8")
    assert "exit code 1" not in skill
    for code in ("3", "4", "5", "7", "10"):
        assert f"| {code} |" in skill
