from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from track_it.constants import SCHEMA_VERSION
from track_it.errors import ProjectMigrationError

Migration = Callable[[dict[str, Any]], dict[str, Any]]
MIGRATIONS: dict[int, Migration] = {}


def migrate(data: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(data)
    version = int(result.get("schema_version", 0))
    if version > SCHEMA_VERSION:
        raise ProjectMigrationError(
            f"Project schema {version} is newer than supported {SCHEMA_VERSION}."
        )
    while version < SCHEMA_VERSION:
        migration = MIGRATIONS.get(version)
        if migration is None:
            raise ProjectMigrationError(f"No migration exists from schema {version}.")
        result = migration(result)
        next_version = int(result.get("schema_version", version))
        if next_version <= version:
            raise ProjectMigrationError(f"Migration from schema {version} did not advance.")
        version = next_version
    return result
