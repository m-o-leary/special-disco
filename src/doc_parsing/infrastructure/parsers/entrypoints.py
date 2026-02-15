from __future__ import annotations

from importlib.metadata import entry_points

from .registration import AdapterRegistration


class EntryPointLoadError(ValueError):
    pass


def load_entrypoints(group: str = "doc_parsing.adapters") -> list[AdapterRegistration]:
    eps = entry_points()
    if hasattr(eps, "select"):
        candidates = list(eps.select(group=group))
    else:
        candidates = list(eps.get(group, []))

    registrations: list[AdapterRegistration] = []
    for ep in candidates:
        obj = ep.load()
        if isinstance(obj, AdapterRegistration):
            registrations.append(obj)
            continue
        raise EntryPointLoadError(
            f"Entry point '{ep.name}' did not return an AdapterRegistration"
        )

    return registrations
