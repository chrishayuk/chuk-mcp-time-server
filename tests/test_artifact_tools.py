# tests/test_artifact_tools.py
import asyncio
import base64
import uuid
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
import pytest_asyncio

# module under test
import chuk_mcp_artifact_server.tools as tools


# ─────────────────────────────────────────────────────────────────────────────
# Fake in-memory store that mimics the subset of ArtifactStore used by tools
# ─────────────────────────────────────────────────────────────────────────────
class FakeStore:
    def __init__(self) -> None:
        # key: artefact_id  -> meta dict
        self._objects: Dict[str, Dict[str, Any]] = {}

    # ---------- helpers -----------------------------------------------------
    @staticmethod
    def _new_id() -> str:
        return uuid.uuid4().hex

    # ---------- store / write ----------------------------------------------
    async def store(  # upload_file path
        self,
        data: bytes,
        mime: str,
        summary: str,
        filename: str,
        session_id: str,
        meta: Dict[str, Any],
    ) -> str:
        artefact_id = self._new_id()
        self._objects[artefact_id] = {
            "artifact_id": artefact_id,
            "filename": filename,
            "mime": mime,
            "bytes": len(data),
            "summary": summary,
            "stored_at": "2025-06-01T00:00:00Z",
            "session_id": session_id,
            "meta": meta,
        }
        return artefact_id

    async def write_file(  # write_file path (handles overwrite)
        self,
        content: str,
        filename: str,
        mime: str,
        summary: str,
        session_id: str,
        meta: Dict[str, Any],
        encoding: str,
        overwrite_artifact_id: str | None = None,
    ) -> str:
        if overwrite_artifact_id:
            old = self._objects[overwrite_artifact_id]
            if old["session_id"] not in (session_id, None):
                # emulate ProviderError from real backend
                raise tools.ProviderError(
                    f"Cross-session overwrite not permitted. "
                    f"Artifact {overwrite_artifact_id} belongs to session '{old['session_id']}', "
                    f"cannot overwrite from session '{session_id}'."
                )
            # delete old -> graceful path in tools.write_file kicks in
            self._objects.pop(overwrite_artifact_id, None)

        return await self.store(
            data=content.encode(encoding),
            mime=mime,
            summary=summary,
            filename=filename,
            session_id=session_id,
            meta=meta,
        )

    # ---------- read paths --------------------------------------------------
    async def metadata(self, artefact_id: str) -> Dict[str, Any]:
        return self._objects[artefact_id]

    async def retrieve(self, artefact_id: str) -> bytes:  # for _presign_or_inline fallback
        return b"dummy"

    async def list_by_prefix(self, session_id: str, prefix: str, limit: int) -> List[Dict[str, Any]]:
        return [
            meta
            for meta in self._objects.values()
            if meta["session_id"] == session_id and meta["filename"].startswith(prefix)
        ]

    async def get_directory_contents(self, session_id: str, directory: str, limit: int) -> List[Dict[str, Any]]:
        return await self.list_by_prefix(session_id, directory, limit)

    # ---------- misc --------------------------------------------------------
    async def presign_short(self, artefact_id: str) -> str:
        return f"https://example/{artefact_id}"

    async def presign_medium(self, artefact_id: str) -> str:
        return f"https://example/medium/{artefact_id}"

    async def delete(self, artefact_id: str) -> bool:
        return self._objects.pop(artefact_id, None) is not None


# ─────────────────────────────────────────────────────────────────────────────
# Pytest fixtures
# ─────────────────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture(autouse=True)
async def fake_store(monkeypatch):
    """Patch tools.STORE with an in-memory fake for the duration of each test."""
    fake = FakeStore()
    monkeypatch.setattr(tools, "STORE", fake)
    yield fake  # tests receive the fake if they need direct introspection


# ─────────────────────────────────────────────────────────────────────────────
# Actual tests
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_write_and_list_session(fake_store):
    session_id = "abc123"
    result = await tools.write_file(
        content="hello world",
        filename="hello.txt",
        session_id=session_id,
        mime="text/plain",
        summary="demo",
        meta={},
    )
    assert result["session_id"] == session_id
    artefact_id = result["artifact_id"]

    listing = await tools.list_session_files(session_id=session_id)
    assert listing["count"] == 1
    assert listing["artifacts"][0]["artifact_id"] == artefact_id
    assert listing["artifacts"][0]["session_id"] == session_id


@pytest.mark.asyncio
async def test_graceful_overwrite_of_legacy_object(fake_store):
    session_id = "team42"

    # create legacy object with session_id=None
    legacy_id = await fake_store.store(
        data=b"old",
        mime="text/plain",
        summary="legacy",
        filename="doc.txt",
        session_id=None,  # ← legacy missing session
        meta={},
    )

    # overwrite via tools.write_file (should delete & rewrite transparently)
    new = await tools.write_file(
        content="new content",
        filename="doc.txt",
        session_id=session_id,
        mime="text/plain",
        summary="overwrite",
        meta={},
        overwrite_artifact_id=legacy_id,
    )

    assert new["operation"] == "overwrite"
    assert new["session_id"] == session_id
    assert new["artifact_id"] != legacy_id  # got a fresh ID

    # listing shows only the new artefact
    listing = await tools.list_session_files(session_id=session_id)
    ids = [a["artifact_id"] for a in listing["artifacts"]]
    assert new["artifact_id"] in ids
    assert legacy_id not in fake_store._objects  # deleted
