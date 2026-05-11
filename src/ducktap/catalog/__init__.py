"""Catalog: pre-printed CLI recipes that DuckTap can rebuild on demand."""
from ducktap.catalog.registry import CatalogEntry, get_entry, list_entries, load_catalog

__all__ = ["CatalogEntry", "list_entries", "get_entry", "load_catalog"]
