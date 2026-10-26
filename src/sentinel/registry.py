"""Tool registry loader. Labels come only from here; unknown means untrusted + restricted (invariant 6)."""

from __future__ import annotations

from pathlib import Path

import yaml

from .models import ToolEntry

CONFIG_DIR = Path(__file__).parent / "config"


class RegistryError(Exception):
    """The registry file is missing, malformed, or invalid. Sentinel refuses to start."""


class Registry:
    def __init__(self, tools: dict[str, ToolEntry], default: dict):
        self._tools = tools
        self._default = default

    def get(self, name: str) -> ToolEntry:
        """Return the entry for `name`; an unregistered tool gets the conservative default (known=False)."""
        entry = self._tools.get(name)
        if entry is not None:
            return entry
        return ToolEntry(name=name, known=False, **self._default)

    def is_known(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> list[str]:
        return sorted(self._tools)


def load_registry(path: Path | None = None) -> Registry:
    path = path or CONFIG_DIR / "registry.yaml"
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        default = raw["default"]
        tools = {name: ToolEntry(name=name, **spec) for name, spec in raw["tools"].items()}
        ToolEntry(name="__default__", known=False, **default)  # validate the default too
    except Exception as e:  # noqa: BLE001 - any failure to load must stop startup
        raise RegistryError(f"invalid registry {path}: {e}") from e
    return Registry(tools, default)
