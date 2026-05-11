from ducktap.catalog import list_entries, get_entry


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
