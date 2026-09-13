"""Durable local Mongo-compatible storage for the Windows offline edition.

The application already talks to Mongo-compatible collection methods.  This
adapter keeps that contract while snapshotting a mongomock database to a local
JSON file after every mutating operation.  It is intentionally opt-in through
OFFLINE_MODE so the hosted Neon setup remains unchanged.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any

from bson import json_util

logger = logging.getLogger(__name__)

_COLLECTION_MUTATIONS = {
    "bulk_write",
    "delete_many",
    "delete_one",
    "drop",
    "find_one_and_delete",
    "find_one_and_replace",
    "find_one_and_update",
    "insert_many",
    "insert_one",
    "replace_one",
    "update_many",
    "update_one",
}

_DATABASE_MUTATIONS = {"drop_collection", "create_collection"}


class PersistentMongoClient:
    """A small persistence wrapper around mongomock.MongoClient."""

    def __init__(self, path: str | os.PathLike[str], db_name: str):
        import mongomock

        self.path = Path(path).expanduser().resolve()
        self.db_name = db_name
        self._lock = RLock()
        self._client = mongomock.MongoClient(
            uuidRepresentation="standard",
            tz_aware=True,
        )
        self._load()

    def __getitem__(self, name: str) -> "PersistentDatabase":
        return PersistentDatabase(self, self._client[name])

    def get_database(self, name: str | None = None) -> "PersistentDatabase":
        return self[name or self.db_name]

    def close(self) -> None:
        self.save()
        self._client.close()

    def _load(self) -> None:
        if not self.path.exists():
            return

        try:
            raw = self.path.read_text(encoding="utf-8")
            snapshot = json_util.loads(raw)
        except Exception as exc:
            raise RuntimeError(
                f"Local database file is not readable: {self.path}. "
                "Restore a backup or remove the file after making a copy."
            ) from exc

        if not isinstance(snapshot, dict):
            raise RuntimeError(f"Local database file has an invalid format: {self.path}")

        database = self._client[self.db_name]
        for collection_name, documents in snapshot.items():
            if not isinstance(documents, list):
                raise RuntimeError(
                    f"Local database collection is invalid: {collection_name}"
                )
            if documents:
                database[collection_name].insert_many(documents)

    def save(self) -> None:
        """Atomically persist all collections to disk."""
        with self._lock:
            database = self._client[self.db_name]
            snapshot: dict[str, list[dict[str, Any]]] = {}
            for name in database.list_collection_names():
                snapshot[name] = list(database[name].find({}))

            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.path.parent,
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(json_util.dumps(snapshot, indent=2, ensure_ascii=False))
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary_name, self.path)
            finally:
                if os.path.exists(temporary_name):
                    os.unlink(temporary_name)


class PersistentDatabase:
    def __init__(self, client: PersistentMongoClient, database: Any):
        self._client = client
        self._database = database

    def __getitem__(self, name: str) -> "PersistentCollection":
        return PersistentCollection(self._client, self._database[name])

    def __getattr__(self, name: str) -> Any:
        attribute = getattr(self._database, name)
        if name not in _DATABASE_MUTATIONS or not callable(attribute):
            return attribute

        def wrapped(*args: Any, **kwargs: Any) -> Any:
            result = attribute(*args, **kwargs)
            self._client.save()
            return result

        return wrapped


class PersistentCollection:
    def __init__(self, client: PersistentMongoClient, collection: Any):
        self._client = client
        self._collection = collection

    def __getattr__(self, name: str) -> Any:
        attribute = getattr(self._collection, name)
        if name not in _COLLECTION_MUTATIONS or not callable(attribute):
            return attribute

        def wrapped(*args: Any, **kwargs: Any) -> Any:
            result = attribute(*args, **kwargs)
            self._client.save()
            return result

        return wrapped
