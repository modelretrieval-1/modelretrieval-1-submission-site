from __future__ import annotations

import hashlib
import re
import sqlite3
from csv import DictReader
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from io import StringIO
from pathlib import Path

from app.accounts import Subtask
from app.config import Settings

JST = timezone(timedelta(hours=9), name="JST")
REQUIRED_COLUMNS: dict[Subtask, set[str]] = {
    "A": {"task_id", "model_id", "relevance_score"},
    "B": {"image_id", "model_id"},
}


@dataclass(frozen=True)
class GroundTruthVersion:
    id: int
    subtask: Subtask
    version_label: str
    stored_file_path: str
    file_sha256: str
    uploaded_by_organizer_id: int
    uploaded_at_jst: str
    is_active: bool
    validation_status: str
    notes: str | None


@dataclass(frozen=True)
class GroundTruthRequirements:
    subtask: Subtask
    ground_truth_version_id: int
    required_topic_ids: frozenset[str]
    required_doc_ids: frozenset[str]


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def jst_now_text() -> str:
    return datetime.now(UTC).astimezone(JST).strftime("%Y-%m-%d %H:%M:%S")


def safe_filename(filename: str) -> str:
    name = Path(filename).name.strip() or "ground-truth.txt"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


def validate_ground_truth_content(subtask: Subtask, content: bytes) -> list[str]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return ["Ground-truth file must be UTF-8 encoded."]

    reader = DictReader(StringIO(text))
    if reader.fieldnames is None:
        return ["Ground-truth file must include a CSV header row."]

    fieldnames = {field.strip() for field in reader.fieldnames if field is not None}
    missing_columns = sorted(REQUIRED_COLUMNS[subtask] - fieldnames)
    if missing_columns:
        return [f"Missing required column(s): {', '.join(missing_columns)}."]

    has_row = False
    for row in reader:
        if any((value or "").strip() for value in row.values()):
            has_row = True
            break

    if not has_row:
        return ["Ground-truth file must include at least one data row."]

    return []


def _ground_truth_id_columns(subtask: Subtask) -> tuple[str, str]:
    if subtask == "A":
        return "task_id", "model_id"
    return "image_id", "model_id"


def extract_ground_truth_requirements(version: GroundTruthVersion) -> GroundTruthRequirements:
    topic_column, doc_column = _ground_truth_id_columns(version.subtask)
    content = Path(version.stored_file_path).read_text(encoding="utf-8-sig")
    reader = DictReader(StringIO(content))
    required_topic_ids: set[str] = set()
    required_doc_ids: set[str] = set()

    for row in reader:
        topic_id = (row.get(topic_column) or "").strip()
        doc_id = (row.get(doc_column) or "").strip()
        if topic_id:
            required_topic_ids.add(topic_id)
        if doc_id:
            required_doc_ids.add(doc_id)

    return GroundTruthRequirements(
        subtask=version.subtask,
        ground_truth_version_id=version.id,
        required_topic_ids=frozenset(required_topic_ids),
        required_doc_ids=frozenset(required_doc_ids),
    )


def store_ground_truth_file(
    settings: Settings,
    *,
    subtask: Subtask,
    filename: str,
    content: bytes,
) -> tuple[Path, str]:
    digest = sha256_bytes(content)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    destination_dir = settings.ground_truth_dir / subtask
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{timestamp}_{safe_filename(filename)}"
    destination.write_bytes(content)
    return destination, digest


def create_ground_truth_version(
    connection: sqlite3.Connection,
    *,
    subtask: Subtask,
    version_label: str,
    stored_file_path: Path,
    file_sha256: str,
    uploaded_by_organizer_id: int,
    notes: str | None = None,
    validation_status: str = "uploaded",
) -> GroundTruthVersion:
    uploaded_at_jst = jst_now_text()
    cursor = connection.execute(
        """
        INSERT INTO ground_truth_versions (
          subtask,
          version_label,
          stored_file_path,
          file_sha256,
          uploaded_by_organizer_id,
          uploaded_at_jst,
          validation_status,
          notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            subtask,
            version_label,
            str(stored_file_path),
            file_sha256,
            uploaded_by_organizer_id,
            uploaded_at_jst,
            validation_status,
            notes,
        ),
    )
    connection.commit()
    return GroundTruthVersion(
        id=cursor.lastrowid,
        subtask=subtask,
        version_label=version_label,
        stored_file_path=str(stored_file_path),
        file_sha256=file_sha256,
        uploaded_by_organizer_id=uploaded_by_organizer_id,
        uploaded_at_jst=uploaded_at_jst,
        is_active=False,
        validation_status=validation_status,
        notes=notes,
    )


def list_ground_truth_versions(connection: sqlite3.Connection) -> list[GroundTruthVersion]:
    rows = connection.execute(
        """
        SELECT
          id,
          subtask,
          version_label,
          stored_file_path,
          file_sha256,
          uploaded_by_organizer_id,
          uploaded_at_jst,
          is_active,
          validation_status,
          notes
        FROM ground_truth_versions
        ORDER BY uploaded_at_jst DESC, id DESC
        """
    ).fetchall()
    return [
        GroundTruthVersion(
            id=row["id"],
            subtask=row["subtask"],
            version_label=row["version_label"],
            stored_file_path=row["stored_file_path"],
            file_sha256=row["file_sha256"],
            uploaded_by_organizer_id=row["uploaded_by_organizer_id"],
            uploaded_at_jst=row["uploaded_at_jst"],
            is_active=bool(row["is_active"]),
            validation_status=row["validation_status"],
            notes=row["notes"],
        )
        for row in rows
    ]


def get_active_ground_truth_version(
    connection: sqlite3.Connection,
    subtask: Subtask,
) -> GroundTruthVersion | None:
    row = connection.execute(
        """
        SELECT
          id,
          subtask,
          version_label,
          stored_file_path,
          file_sha256,
          uploaded_by_organizer_id,
          uploaded_at_jst,
          is_active,
          validation_status,
          notes
        FROM ground_truth_versions
        WHERE subtask = ? AND is_active = 1
        """,
        (subtask,),
    ).fetchone()
    if row is None:
        return None

    return GroundTruthVersion(
        id=row["id"],
        subtask=row["subtask"],
        version_label=row["version_label"],
        stored_file_path=row["stored_file_path"],
        file_sha256=row["file_sha256"],
        uploaded_by_organizer_id=row["uploaded_by_organizer_id"],
        uploaded_at_jst=row["uploaded_at_jst"],
        is_active=bool(row["is_active"]),
        validation_status=row["validation_status"],
        notes=row["notes"],
    )


def get_active_ground_truth_requirements(
    connection: sqlite3.Connection,
    subtask: Subtask,
) -> GroundTruthRequirements | None:
    version = get_active_ground_truth_version(connection, subtask)
    if version is None:
        return None
    return extract_ground_truth_requirements(version)


def activate_ground_truth_version(connection: sqlite3.Connection, version_id: int) -> bool:
    row = connection.execute(
        """
        SELECT subtask, validation_status
        FROM ground_truth_versions
        WHERE id = ?
        """,
        (version_id,),
    ).fetchone()
    if row is None or row["validation_status"] != "validated":
        return False

    connection.execute(
        """
        UPDATE ground_truth_versions
        SET is_active = 0
        WHERE subtask = ?
        """,
        (row["subtask"],),
    )
    connection.execute(
        """
        UPDATE ground_truth_versions
        SET is_active = 1
        WHERE id = ?
        """,
        (version_id,),
    )
    connection.commit()
    return True
