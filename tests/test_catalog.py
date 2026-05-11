from ducktap.catalog import get_entry, list_entries


def test_catalog_loads():
    entries = list_entries()
    names = [e.name for e in entries]
    assert "petstore" in names
    assert "github" in names


def test_get_entry():
    e = get_entry("petstore")
    assert e is not None
    assert e.spec_url
    assert e.source() == e.spec_url
