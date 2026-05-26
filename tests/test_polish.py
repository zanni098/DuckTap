"""Tests for LLM polish/rename without hitting real APIs."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ducktap.core.spec import APISpec, Operation
from ducktap.polish import polish, rename

MINI_SPEC = APISpec(
    name="mini",
    display_name="Mini API",
    version="1.0.0",
    base_url="https://example.test/api",
    operations=[
        Operation(
            operation_id="list_pets",
            method="GET",
            path="/pets",
            summary="List all pets",
        ),
        Operation(
            operation_id="get_pet_by_id_that_is_very_long_and_unwieldy",
            method="GET",
            path="/pets/{petId}",
            summary="Fetch one pet",
        ),
    ],
)


def test_polish_rewrites_summaries(tmp_path: Path) -> None:
    spec_path = tmp_path / "mini.json"
    spec_path.write_text(MINI_SPEC.model_dump_json(by_alias=True))

    with patch("ducktap.polish.chat") as mock_chat:
        mock_chat.return_value = "List pets\nReturns a list of all pets in the system."
        spec = polish(str(spec_path), out_json=None)

    assert spec.operations[0].summary == "List pets"
    assert spec.operations[0].description == "Returns a list of all pets in the system."


def test_polish_skips_when_llm_unavailable(tmp_path: Path) -> None:
    spec_path = tmp_path / "mini.json"
    spec_path.write_text(MINI_SPEC.model_dump_json(by_alias=True))

    with patch("ducktap.polish.chat") as mock_chat:
        mock_chat.side_effect = RuntimeError("litellm not installed")
        spec = polish(str(spec_path), out_json=None)

    # Should gracefully skip LLM step and return original spec
    assert spec.operations[0].summary == "List all pets"


def test_rename_suggests_better_ids(tmp_path: Path) -> None:
    spec_path = tmp_path / "mini.json"
    spec_path.write_text(MINI_SPEC.model_dump_json(by_alias=True))

    with patch("ducktap.polish.chat") as mock_chat:
        mock_chat.return_value = "get_pet"
        mapping = rename(str(spec_path), out_json=None, dry_run=False)

    assert "get_pet_by_id_that_is_very_long_and_unwieldy" in mapping
    assert mapping["get_pet_by_id_that_is_very_long_and_unwieldy"] == "get_pet"


def test_rename_dry_run_does_not_mutate(tmp_path: Path) -> None:
    spec_path = tmp_path / "mini.json"
    spec_path.write_text(MINI_SPEC.model_dump_json(by_alias=True))

    with patch("ducktap.polish.chat") as mock_chat:
        mock_chat.return_value = "get_pet"
        mapping = rename(str(spec_path), out_json=None, dry_run=True)

    # Mapping should still be returned
    assert "get_pet_by_id_that_is_very_long_and_unwieldy" in mapping
    # But original spec should be unchanged
    spec = APISpec.model_validate_json(spec_path.read_text(encoding="utf-8"))
    assert spec.operations[1].operation_id == "get_pet_by_id_that_is_very_long_and_unwieldy"
