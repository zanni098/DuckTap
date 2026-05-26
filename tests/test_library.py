"""Tests for the DuckTap Library registry."""
from __future__ import annotations

import os
import tempfile

from ducktap.library import (
    LibraryEntry,
    add,
    list_entries,
    remove,
    search,
)


def test_library_empty() -> None:
    with tempfile.TemporaryDirectory() as td:
        os.environ["DUCKTAP_HOME"] = td
        assert list_entries() == []


def test_library_add_and_list() -> None:
    with tempfile.TemporaryDirectory() as td:
        os.environ["DUCKTAP_HOME"] = td
        entry = LibraryEntry(name="petstore", version="1.0.0", description="Petstore CLI")
        add(entry)
        entries = list_entries()
        assert len(entries) == 1
        assert entries[0].name == "petstore"
        assert entries[0].version == "1.0.0"


def test_library_update_existing() -> None:
    with tempfile.TemporaryDirectory() as td:
        os.environ["DUCKTAP_HOME"] = td
        add(LibraryEntry(name="petstore", version="1.0.0"))
        add(LibraryEntry(name="petstore", version="1.1.0"))
        entries = list_entries()
        assert len(entries) == 1
        assert entries[0].version == "1.1.0"


def test_library_search() -> None:
    with tempfile.TemporaryDirectory() as td:
        os.environ["DUCKTAP_HOME"] = td
        add(LibraryEntry(name="petstore", version="1.0.0", description="A pet store"))
        add(LibraryEntry(name="github", version="2.0.0", tags=["vcs"]))

        assert len(search("pet")) == 1
        assert search("pet")[0].name == "petstore"
        assert len(search("vcs")) == 1
        assert len(search("zzzz")) == 0


def test_library_remove() -> None:
    with tempfile.TemporaryDirectory() as td:
        os.environ["DUCKTAP_HOME"] = td
        add(LibraryEntry(name="petstore", version="1.0.0"))
        assert remove("petstore")
        assert not remove("petstore")
        assert list_entries() == []
