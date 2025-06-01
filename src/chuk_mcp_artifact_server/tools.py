"""
Async MCP tools for artefact storage and retrieval.

Key enhancements
────────────────
• Startup diagnostics at DEBUG level
• Robust _info() that derives artefact_id from S3 keys and injects
  fallback session_id values when the backend omits them
• Every tool now passes a fallback_session_id to _info(), ensuring
  responses never show `"session_id": null`
• Safe-overwrite fallback: if S3 blocks an overwrite because the original
  object’s session_id is None, we delete then re-write inside the caller’s
  session
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Any, Dict, List, Optional

from chuk_artifacts.exceptions import ProviderError
from chuk_mcp_runtime.artifacts import ArtifactStore
from chuk_mcp_runtime.common.mcp_tool_decorator import mcp_tool
from chuk_mcp_runtime.session.session_management import validate_session_parameter
from pydantic import ValidationError

from .models import (
    ArtifactInfo,
    CopyFileInput,
    CopyFileResult,
    DeleteFileInput,
    DeleteFileResult,
    DownloadFileInput,
    DownloadFileResult,
    GetMetadataInput,
    ListDirectoryInput,
    ListDirectoryResult,
    ListSessionFilesInput,
    ListSessionFilesResult,
    MoveFileInput,
    MoveFileResult,
    ReadFileInput,
    ReadFileResult,
    UpdateMetadataInput,
    UpdateMetadataResult,
    UploadFileInput,
    UploadFileResult,
    WriteFileInput,
    WriteFileResult,
)

# ────────────────────────────────────────────────────────────────
#  Logger & store
# ────────────────────────────────────────────────────────────────
logger = logging.getLogger("mcp-artifact-server")
logger.setLevel(logging.DEBUG)

STORE = ArtifactStore()

# ────────────────────────────────────────────────────────────────
#  Startup diagnostics
# ────────────────────────────────────────────────────────────────
def _log_startup_config(store: ArtifactStore) -> None:
    """Log effective storage/session configuration (secrets redacted)."""
    provider   = os.getenv("ARTIFACT_PROVIDER", "<unset>")
    bucket     = os.getenv("ARTIFACT_BUCKET",  "<unset>")
    region     = os.getenv("AWS_REGION",       "<unset>")
    endpoint   = os.getenv("ARTIFACT_S3_ENDPOINT", "<default>")
    path_style = os.getenv("ARTIFACT_S3_FORCE_PATH_STYLE", "false")

    try:
        internal = {
            "provider": store._store.provider,            # type: ignore[attr-defined]
            "bucket":   store._store.bucket,              # type: ignore[attr-defined]
            "region":   getattr(store._store, "region", "<unknown>"),
        }
    except AttributeError:
        internal = "n/a"

    logger.debug(
        "🔎 ArtifactStore configuration:\n"
        "    provider  = %s\n"
        "    bucket    = %s\n"
        "    region    = %s\n"
        "    endpoint  = %s\n"
        "    pathStyle = %s\n"
        "    internal  = %s",
        provider, bucket, region, endpoint, path_style, internal
    )

_log_startup_config(STORE)

# ────────────────────────────────────────────────────────────────
#  Helper functions
# ────────────────────────────────────────────────────────────────
async def _info(
    meta: Dict[str, Any],
    fallback_id: Optional[str] = None,
    fallback_session_id: Optional[str] = None,
) -> ArtifactInfo:
    """Convert raw store metadata → canonical `ArtifactInfo`."""
    art_id = (
        meta.get("artifact_id")
        or meta.get("id")
        or (meta.get("key") or "").split("/")[-1]
        or fallback_id
    )
    if not art_id:
        raise KeyError("artifact_id")

    return ArtifactInfo.model_validate(
        {
            "artifact_id": art_id,
            "filename": meta.get("filename"),
            "mime": meta["mime"],
            "bytes": meta["bytes"],
            "summary": meta.get("summary"),
            "stored_at": meta["stored_at"],
            "session_id": meta.get("session_id") or fallback_session_id,
            "meta": meta.get("meta", {}),
        }
    )


async def _presign_or_inline(artifact_id: str, presign: bool) -> Dict[str, str | None]:
    """Return medium-TTL presigned URL or inline base64 payload."""
    if presign:
        try:
            return {
                "download_url": await STORE.presign_medium(artifact_id),
                "data_base64": None,
            }
        except Exception as exc:
            logger.info("Presign unavailable – falling back to inline: %s", exc)

    data = await STORE.retrieve(artifact_id)
    return {"download_url": None, "data_base64": base64.b64encode(data).decode()}


async def _store_and_build_info(
    *, content: bytes, filename: str, mime: str, summary: str,
    session_id: str, meta: Dict[str, Any]
) -> tuple[str, ArtifactInfo]:
    """Shared utility for write_file & upload_file."""
    art_id   = await STORE.store(
        data=content, mime=mime, summary=summary,
        filename=filename, session_id=session_id, meta=meta
    )
    meta_raw = await STORE.metadata(art_id)
    info     = await _info(meta_raw, fallback_id=art_id, fallback_session_id=session_id)
    return art_id, info

# ────────────────────────────────────────────────────────────────
#  Session-aware listing tools
# ────────────────────────────────────────────────────────────────
@mcp_tool(
    name="list_session_files",
    description="List artefacts in the given session (uses session context if session_id not provided).",
)
async def list_session_files(session_id: Optional[str] = None, prefix: Optional[str] = None) -> Dict:
    """List files in a session with optional prefix filter."""
    try:
        sess = validate_session_parameter(session_id, "list_session_files")
        inp  = ListSessionFilesInput(session_id=sess, prefix=prefix)
    except ValidationError as exc:
        raise ValueError(f"Invalid input: {exc}") from exc

    try:
        meta_list = await STORE.list_by_prefix(sess, inp.prefix or "", limit=1000)
        artifacts = [await _info(m, fallback_session_id=sess) for m in meta_list]
    except Exception as exc:
        raise ValueError(f"Failed to list session files: {exc}") from exc

    return ListSessionFilesResult(count=len(artifacts), session_id=sess, artifacts=artifacts).model_dump()


@mcp_tool(
    name="list_directory",
    description="List artefacts in a directory within a session (uses session context if session_id not provided).",
)
async def list_directory(directory: str, session_id: Optional[str] = None) -> Dict:
    """List files in a pseudo-directory inside a session."""
    try:
        sess = validate_session_parameter(session_id, "list_directory")
        inp  = ListDirectoryInput(directory=directory, session_id=sess)
    except ValidationError as exc:
        raise ValueError(f"Invalid directory input: {exc}") from exc

    try:
        meta_list = await STORE.get_directory_contents(sess, inp.directory, limit=1000)
        artifacts = [await _info(m, fallback_session_id=sess) for m in meta_list]
    except Exception as exc:
        raise ValueError(f"Failed to list directory: {exc}") from exc

    return ListDirectoryResult(count=len(artifacts), session_id=sess, directory=directory, artifacts=artifacts).model_dump()

# ────────────────────────────────────────────────────────────────
#  upload_file
# ────────────────────────────────────────────────────────────────
@mcp_tool(
    name="upload_file",
    description="Upload (store) a file from base64 bytes (uses session context if session_id not provided).",
)
async def upload_file(
    data_base64: str, filename: str, mime: str,
    session_id: Optional[str] = None, summary: str | None = "",
    meta: Optional[Dict[str, Any]] = None,
) -> Dict:
    try:
        sess = validate_session_parameter(session_id, "upload_file")
        inp  = UploadFileInput(
            data_base64=data_base64, filename=filename, mime=mime,
            summary=summary or "", session_id=sess, meta=meta or {}
        )
    except ValidationError as exc:
        raise ValueError(f"Invalid upload input: {exc}") from exc

    try:
        content = base64.b64decode(inp.data_base64)
    except Exception as exc:
        raise ValueError(f"data_base64 not valid base64: {exc}") from exc

    art_id, info = await _store_and_build_info(
        content=content, filename=inp.filename, mime=inp.mime,
        summary=inp.summary, session_id=sess, meta=inp.meta
    )

    try:
        url = await STORE.presign_short(art_id)
    except Exception:
        url = None

    return UploadFileResult(**info.model_dump(), download_url=url).model_dump()

# ────────────────────────────────────────────────────────────────
#  write_file  (safe overwrite)
# ────────────────────────────────────────────────────────────────
@mcp_tool(
    name="write_file",
    description="Write content to a new file (uses session context if session_id not provided).",
)
async def write_file(
    content: str, filename: str, session_id: Optional[str] = None,
    mime: str = "text/plain", summary: str = "",
    meta: Optional[Dict[str, Any]] = None, encoding: str = "utf-8",
    overwrite_artifact_id: Optional[str] = None,
) -> Dict:
    try:
        sess = validate_session_parameter(session_id, "write_file")
        inp  = WriteFileInput(
            content=content, filename=filename, mime=mime,
            summary=summary or f"Written file: {filename}",
            session_id=sess, meta=meta or {}, encoding=encoding,
            overwrite_artifact_id=overwrite_artifact_id
        )
    except ValidationError as exc:
        raise ValueError(f"Invalid write input: {exc}") from exc

    # Attempt normal write / overwrite
    try:
        art_id = await STORE.write_file(
            inp.content, filename=inp.filename, mime=inp.mime, summary=inp.summary,
            session_id=sess, meta=inp.meta, encoding=inp.encoding,
            overwrite_artifact_id=inp.overwrite_artifact_id
        )
        meta_raw = await STORE.metadata(art_id)
        info     = await _info(meta_raw, fallback_id=art_id, fallback_session_id=sess)

    # Graceful overwrite fallback
    except ProviderError as exc:
        msg = str(exc)
        if overwrite_artifact_id and "Cross-session overwrite not permitted" in msg and "belongs to session 'None'" in msg:
            try:
                await STORE.delete(overwrite_artifact_id)
            except Exception:
                logger.warning("Failed to delete old artefact %s", overwrite_artifact_id)

            art_id, info = await _store_and_build_info(
                content=inp.content.encode(inp.encoding),
                filename=inp.filename, mime=inp.mime, summary=inp.summary,
                session_id=sess, meta=inp.meta
            )
        else:
            raise ValueError(str(exc)) from exc

    try:
        url = await STORE.presign_short(art_id)
    except Exception:
        url = None

    op = "overwrite" if overwrite_artifact_id else "create"
    return WriteFileResult(**info.model_dump(), download_url=url, operation=op).model_dump()

# ────────────────────────────────────────────────────────────────
#  download_file
# ────────────────────────────────────────────────────────────────
@mcp_tool(name="download_file", description="Download or presign an artefact.")
async def download_file(artifact_id: str, presign: bool = True) -> Dict:
    """Retrieve or presign a stored artefact."""
    try:
        inp = DownloadFileInput(artifact_id=artifact_id, presign=presign)
    except ValidationError as exc:
        raise ValueError(f"Invalid download input: {exc}") from exc

    try:
        meta = await STORE.metadata(inp.artifact_id)
    except Exception as exc:
        raise ValueError(str(exc)) from exc

    info  = await _info(meta, fallback_id=inp.artifact_id, fallback_session_id=meta.get("session_id"))
    extra = await _presign_or_inline(inp.artifact_id, inp.presign)
    return DownloadFileResult(artifact=info, **extra).model_dump()

# ────────────────────────────────────────────────────────────────
#  get_metadata
# ────────────────────────────────────────────────────────────────
@mcp_tool(name="get_metadata", description="Return full metadata for an artefact.")
async def get_metadata(artifact_id: str) -> Dict:
    """Return stored metadata for an artefact."""
    try:
        inp = GetMetadataInput(artifact_id=artifact_id)
    except ValidationError as exc:
        raise ValueError(f"Invalid input: {exc}") from exc

    try:
        meta = await STORE.metadata(inp.artifact_id)
    except Exception as exc:
        raise ValueError(str(exc)) from exc

    return (await _info(meta, fallback_id=inp.artifact_id, fallback_session_id=meta.get("session_id"))).model_dump()

# ────────────────────────────────────────────────────────────────
#  update_metadata
# ────────────────────────────────────────────────────────────────
@mcp_tool(name="update_metadata", description="Merge or overwrite artefact metadata.")
async def update_metadata(artifact_id: str, meta: Dict[str, Any]) -> Dict:
    """Merge new metadata into an existing artefact."""
    try:
        inp = UpdateMetadataInput(artifact_id=artifact_id, meta=meta)
    except ValidationError as exc:
        raise ValueError(f"Invalid update input: {exc}") from exc

    try:
        await STORE.update_metadata(inp.artifact_id, new_meta=inp.meta, merge=True)
        meta_full = await STORE.metadata(inp.artifact_id)
    except Exception as exc:
        raise ValueError(str(exc)) from exc

    return UpdateMetadataResult(
        **(await _info(meta_full, fallback_id=inp.artifact_id, fallback_session_id=meta_full.get("session_id"))).model_dump()
    ).model_dump()

# ────────────────────────────────────────────────────────────────
#  delete_file
# ────────────────────────────────────────────────────────────────
@mcp_tool(name="delete_file", description="Delete an artefact permanently.")
async def delete_file(artifact_id: str) -> Dict:
    """Delete an artefact."""
    try:
        inp = DeleteFileInput(artifact_id=artifact_id)
    except ValidationError as exc:
        raise ValueError(f"Invalid delete input: {exc}") from exc

    try:
        success = await STORE.delete(inp.artifact_id)
    except Exception as exc:
        raise ValueError(str(exc)) from exc

    return DeleteFileResult(success=bool(success), artifact_id=artifact_id).model_dump()

# ────────────────────────────────────────────────────────────────
#  copy_file
# ────────────────────────────────────────────────────────────────
@mcp_tool(name="copy_file", description="Copy an existing artefact within the same session.")
async def copy_file(
    artifact_id: str, filename: Optional[str] = None, meta: Optional[Dict[str, Any]] = None
) -> Dict:
    """Copy a file within its current session."""
    try:
        inp = CopyFileInput(artifact_id=artifact_id, filename=filename, session_id=None, meta=meta or {})
    except ValidationError as exc:
        raise ValueError(f"Invalid copy input: {exc}") from exc

    try:
        new_id = await STORE.copy_file(
            inp.artifact_id, new_filename=inp.filename, target_session_id=None, new_meta=inp.meta
        )
        meta_new = await STORE.metadata(new_id)
    except Exception as exc:
        raise ValueError(str(exc)) from exc

    return CopyFileResult(
        **(await _info(meta_new, fallback_id=new_id, fallback_session_id=meta_new.get("session_id"))).model_dump(),
        source_artifact_id=inp.artifact_id,
    ).model_dump()

# ────────────────────────────────────────────────────────────────
#  move_file
# ────────────────────────────────────────────────────────────────
@mcp_tool(name="move_file", description="Move/rename a file within the same session.")
async def move_file(
    artifact_id: str, new_filename: Optional[str] = None, new_meta: Optional[Dict[str, Any]] = None
) -> Dict:
    """Move/rename a file within its current session."""
    try:
        updated_meta = await STORE.move_file(
            artifact_id, new_filename=new_filename, new_meta=new_meta or {}
        )
        info = await _info(updated_meta, fallback_id=artifact_id, fallback_session_id=updated_meta.get("session_id"))
    except Exception as exc:
        raise ValueError(str(exc)) from exc

    return MoveFileResult(**info.model_dump(), operation="move").model_dump()

# ────────────────────────────────────────────────────────────────
#  read_file
# ────────────────────────────────────────────────────────────────
@mcp_tool(name="read_file", description="Read file content as text or binary.")
async def read_file(
    artifact_id: str, as_text: bool = True, encoding: str = "utf-8"
) -> Dict:
    """Read file content."""
    try:
        content = await STORE.read_file(artifact_id, as_text=as_text, encoding=encoding)
    except Exception as exc:
        raise ValueError(str(exc)) from exc

    if as_text:
        return ReadFileResult(
            artifact_id=artifact_id, content_type="text", content=content, encoding=encoding
        ).model_dump()

    return ReadFileResult(
        artifact_id=artifact_id,
        content_type="binary",
        content_base64=base64.b64encode(content).decode(),
        bytes=len(content),
    ).model_dump()
