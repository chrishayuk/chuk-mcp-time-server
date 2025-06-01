# chuk_mcp_artifact_server/models.py
"""
Pydantic models and enums for the Artifact MCP server.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
#  Enum of tool names
# --------------------------------------------------------------------------- #
class ArtifactTools(str, Enum):
    LIST_SESSION_FILES = "list_session_files"
    UPLOAD_FILE = "upload_file"
    DOWNLOAD_FILE = "download_file"
    GET_METADATA = "get_metadata"
    UPDATE_METADATA = "update_metadata"
    DELETE_FILE = "delete_file"
    COPY_FILE = "copy_file"
    LIST_DIRECTORY = "list_directory"
    MOVE_FILE = "move_file"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"


# --------------------------------------------------------------------------- #
#  Shared sub-models
# --------------------------------------------------------------------------- #
class ArtifactInfo(BaseModel):
    """Compact information about a stored artefact."""

    artifact_id: str = Field(..., description="Unique identifier of the artefact")
    filename: Optional[str] = Field(None, description="Original filename if any")
    mime: str = Field(..., description="MIME type, e.g. image/png")
    bytes: int = Field(..., description="File size in bytes")
    summary: Optional[str] = Field(None, description="Short user supplied summary")
    stored_at: str = Field(..., description="UTC ISO-8601 timestamp of storage")
    session_id: Optional[str] = Field(None, description="Owning session (if any)")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")


# --------------------------------------------------------------------------- #
#  Input models - UPDATED WITH SESSION REQUIREMENTS
# --------------------------------------------------------------------------- #
class ListSessionFilesInput(BaseModel):
    session_id: Optional[str] = Field(None, description="Session id to list files from (optional if context available)")
    prefix: Optional[str] = Field(
        None,
        description="Optional filename prefix to emulate directories (charts/2025/)",
    )


class UploadFileInput(BaseModel):
    data_base64: str = Field(..., description="Base64-encoded file bytes")
    filename: str = Field(..., description="Filename, inc. extension")
    mime: str = Field(..., description="MIME type")
    session_id: Optional[str] = Field(None, description="Session id for grouping (optional if context available)")
    summary: str = Field("", description="Human readable summary")
    meta: Dict[str, Any] = Field(default_factory=dict, description="User metadata")


class DownloadFileInput(BaseModel):
    artifact_id: str = Field(..., description="Id of artefact to download")
    presign: bool = Field(
        True,
        description="Return presigned URL instead of inline base64 when possible",
    )


class GetMetadataInput(BaseModel):
    artifact_id: str = Field(..., description="Id of artefact")


class UpdateMetadataInput(BaseModel):
    artifact_id: str = Field(..., description="Id of artefact")
    meta: Dict[str, Any] = Field(..., description="Metadata to merge / overwrite")


class DeleteFileInput(BaseModel):
    artifact_id: str = Field(..., description="Id of artefact to delete")


class CopyFileInput(BaseModel):
    artifact_id: str = Field(..., description="Source artefact id")
    filename: Optional[str] = Field(None, description="Optional new filename")
    session_id: Optional[str] = Field(
        None, 
        description="Target session id (if None, copies within same session)"
    )
    meta: Dict[str, Any] = Field(default_factory=dict, description="Extra metadata")


class ListDirectoryInput(BaseModel):
    directory: str = Field(..., description="Pseudo directory prefix to list")
    session_id: Optional[str] = Field(None, description="Session id to list within (optional if context available)")


class MoveFileInput(BaseModel):
    artifact_id: str = Field(..., description="Id of artefact to move/rename")
    new_filename: Optional[str] = Field(None, description="New filename")
    new_meta: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ReadFileInput(BaseModel):
    artifact_id: str = Field(..., description="Id of artefact to read")
    as_text: bool = Field(True, description="Return as text (True) or binary (False)")
    encoding: str = Field("utf-8", description="Text encoding for text mode")


class WriteFileInput(BaseModel):
    content: str = Field(..., description="File content to write")
    filename: str = Field(..., description="Filename for the new file")
    session_id: Optional[str] = Field(None, description="Session id for grouping (optional if context available)")
    mime: str = Field("text/plain", description="MIME type")
    summary: str = Field("", description="File summary")
    meta: Dict[str, Any] = Field(default_factory=dict, description="User metadata")
    encoding: str = Field("utf-8", description="Text encoding")
    overwrite_artifact_id: Optional[str] = Field(
        None, description="Artifact ID to overwrite (optional)"
    )


# --------------------------------------------------------------------------- #
#  Output models
# --------------------------------------------------------------------------- #
class ListSessionFilesResult(BaseModel):
    count: int = Field(..., description="Number of artefacts returned")
    session_id: str = Field(..., description="Session ID that was used")
    artifacts: List[ArtifactInfo] = Field([], description="List of artefact infos")


class UploadFileResult(ArtifactInfo):
    """Upload result with additional fields."""
    download_url: Optional[str] = Field(None, description="Short presigned URL")
    operation: str = Field("create", description="Type of operation performed")


class DownloadFileResult(BaseModel):
    artifact: ArtifactInfo = Field(..., description="Artefact info")
    download_url: Optional[str] = Field(None, description="Presigned URL if used")
    data_base64: Optional[str] = Field(
        None, description="Inline bytes when presigning unavailable / disabled"
    )


class UpdateMetadataResult(ArtifactInfo):
    """Alias - returns updated info."""


class DeleteFileResult(BaseModel):
    success: bool = Field(..., description="True if artefact deleted")
    artifact_id: str = Field(..., description="ID of the deleted artifact")


class CopyFileResult(ArtifactInfo):
    source_artifact_id: str = Field(..., description="Id of original artefact")
    operation: str = Field("copy", description="Type of operation performed")


class ListDirectoryResult(BaseModel):
    """Directory listing result."""
    count: int = Field(..., description="Number of artefacts returned")
    session_id: str = Field(..., description="Session ID that was used")
    directory: str = Field(..., description="Directory that was listed")
    artifacts: List[ArtifactInfo] = Field([], description="List of artefact infos")


class MoveFileResult(ArtifactInfo):
    """Returns updated artifact info after move/rename."""
    operation: str = Field("move", description="Type of operation performed")


class ReadFileResult(BaseModel):
    artifact_id: str = Field(..., description="Id of artefact that was read")
    content_type: str = Field(..., description="Content type: 'text' or 'binary'")
    content: Optional[str] = Field(None, description="Text content if as_text=True")
    content_base64: Optional[str] = Field(None, description="Base64 binary content if as_text=False")
    encoding: Optional[str] = Field(None, description="Text encoding used")
    bytes: Optional[int] = Field(None, description="Size in bytes for binary content")


class WriteFileResult(ArtifactInfo):
    """Write file result with additional fields."""
    download_url: Optional[str] = Field(None, description="Short presigned URL")
    operation: str = Field("create", description="Type of operation performed (create/overwrite)")