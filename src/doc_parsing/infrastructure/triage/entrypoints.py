from __future__ import annotations

from importlib.metadata import entry_points

from .registration import TriagePolicyRegistration


class EntryPointLoadError(ValueError):
    pass


def load_entrypoints(
    group: str = "doc_parsing.triage_policies",
) -> list[TriagePolicyRegistration]:
    eps = entry_points()
    if hasattr(eps, "select"):
        candidates = list(eps.select(group=group))
    else:
        candidates = list(eps.get(group, []))

    registrations: list[TriagePolicyRegistration] = []
    for ep in candidates:
        obj = ep.load()
        if isinstance(obj, TriagePolicyRegistration):
            registrations.append(obj)
            continue
        raise EntryPointLoadError(
            f"Entry point '{ep.name}' did not return a TriagePolicyRegistration"
        )

    return registrations
