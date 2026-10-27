"""Load the synthetic ITSM CSV files into a local SQLite warehouse."""

from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path
from uuid import uuid4


CSV_COLUMNS = {
    "assignment_groups.csv": (
        "assignment_group_id",
        "group_name",
        "group_type",
        "active_status",
    ),
    "configuration_items.csv": (
        "ci_id",
        "ci_name",
        "ci_type",
        "environment",
        "lifecycle_status",
    ),
    "incidents.csv": (
        "incident_id",
        "short_description",
        "priority",
        "status",
        "opened_at",
        "resolved_at",
        "assignment_group_id",
        "primary_ci_id",
        "source_created_at",
        "source_updated_at",
    ),
    "sla_measurements.csv": (
        "sla_measurement_id",
        "incident_id",
        "sla_type",
        "target_duration_seconds",
        "actual_elapsed_seconds",
        "measurement_status",
        "breach_indicator",
        "measurement_started_at",
        "measurement_ended_at",
    ),
    "change_requests.csv": (
        "change_id",
        "primary_ci_id",
        "change_type",
        "status",
        "planned_start_at",
        "planned_end_at",
        "actual_completed_at",
        "outcome_classification",
    ),
}

TABLE_BY_FILE = {
    "assignment_groups.csv": "assignment_groups",
    "configuration_items.csv": "configuration_items",
    "incidents.csv": "incidents",
    "sla_measurements.csv": "sla_measurements",
    "change_requests.csv": "change_requests",
}

LOAD_ORDER = (
    "assignment_groups.csv",
    "configuration_items.csv",
    "incidents.csv",
    "sla_measurements.csv",
    "change_requests.csv",
)

BUSINESS_ID_COLUMNS = {
    "assignment_groups.csv": "assignment_group_id",
    "configuration_items.csv": "ci_id",
    "incidents.csv": "incident_id",
    "sla_measurements.csv": "sla_measurement_id",
    "change_requests.csv": "change_id",
}


class LoadError(Exception):
    """Raised when source data cannot safely be loaded."""


def read_source_files(project_root: Path) -> dict[str, list[dict[str, str]]]:
    """Read all CSVs and verify headers and business identifiers."""
    source_dir = project_root / "data" / "raw"
    rows_by_file: dict[str, list[dict[str, str]]] = {}

    for filename in LOAD_ORDER:
        path = source_dir / filename
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                if tuple(reader.fieldnames or ()) != CSV_COLUMNS[filename]:
                    raise LoadError(
                        f"{filename}: expected columns "
                        f"{', '.join(CSV_COLUMNS[filename])}; found "
                        f"{reader.fieldnames}."
                    )

                rows: list[dict[str, str]] = []
                for line_number, row in enumerate(reader, start=2):
                    if None in row or any(value is None for value in row.values()):
                        raise LoadError(
                            f"{filename}: malformed CSV row at line {line_number}."
                        )
                    rows.append({column: row[column] for column in CSV_COLUMNS[filename]})
        except (OSError, csv.Error) as error:
            raise LoadError(f"{filename}: could not read CSV: {error}") from error

        rows_by_file[filename] = rows

    check_business_identifiers(rows_by_file)
    return rows_by_file


def check_business_identifiers(
    rows_by_file: dict[str, list[dict[str, str]]],
) -> None:
    """Fail before loading if any business identifier is blank or duplicated."""
    errors: list[str] = []

    for filename, rows in rows_by_file.items():
        identifier_column = BUSINESS_ID_COLUMNS[filename]
        seen: set[str] = set()

        for row in rows:
            identifier = row[identifier_column]
            if not identifier.strip():
                errors.append(
                    f"{filename}: empty business identifier in "
                    f"{identifier_column}."
                )
            elif identifier in seen:
                errors.append(
                    f"{filename}: duplicate {identifier_column}={identifier}."
                )
            else:
                seen.add(identifier)

    if errors:
        raise LoadError(
            "Business identifier checks failed:\n  " + "\n  ".join(errors)
        )


def preflight_references(
    rows_by_file: dict[str, list[dict[str, str]]],
) -> list[str]:
    """Find populated references that cannot be mapped to a parent row."""
    group_ids = {
        row["assignment_group_id"]
        for row in rows_by_file["assignment_groups.csv"]
    }
    ci_ids = {row["ci_id"] for row in rows_by_file["configuration_items.csv"]}
    incident_ids = {
        row["incident_id"] for row in rows_by_file["incidents.csv"]
    }
    errors: list[str] = []

    reference_checks = (
        (
            "incidents.csv",
            "incident_id",
            "assignment_group_id",
            group_ids,
        ),
        ("incidents.csv", "incident_id", "primary_ci_id", ci_ids),
        ("change_requests.csv", "change_id", "primary_ci_id", ci_ids),
    )

    for filename, record_column, reference_column, valid_ids in reference_checks:
        for row in rows_by_file[filename]:
            reference = row[reference_column]
            if reference and reference not in valid_ids:
                errors.append(
                    f"{filename}: record {record_column}={row[record_column]}, "
                    f"reference column {reference_column}, unmatched identifier "
                    f"{reference}."
                )

    # SLA incident references are mandatory in the schema, so both a missing
    # and a populated-but-unknown incident ID prevent a safe load.
    for row in rows_by_file["sla_measurements.csv"]:
        incident_id = row["incident_id"]
        if not incident_id:
            errors.append(
                "sla_measurements.csv: record "
                f"sla_measurement_id={row['sla_measurement_id']}, reference "
                "column incident_id, required identifier is missing."
            )
        elif incident_id not in incident_ids:
            errors.append(
                "sla_measurements.csv: record "
                f"sla_measurement_id={row['sla_measurement_id']}, reference "
                f"column incident_id, unmatched identifier {incident_id}."
            )

    return errors


def nullable_text(value: str) -> str | None:
    """Convert an empty CSV cell to SQL NULL; preserve other text as written."""
    return value if value != "" else None


def nullable_integer(
    value: str,
    filename: str,
    record_id: str,
    column: str,
) -> int | None:
    """Convert an optional integer cell and reject invalid values."""
    if value == "":
        return None

    try:
        return int(value)
    except ValueError as error:
        raise LoadError(
            f"{filename}: record {record_id}, column {column}: "
            f"expected an integer or blank, found {value!r}."
        ) from error


def load_parent_tables(
    connection: sqlite3.Connection,
    rows_by_file: dict[str, list[dict[str, str]]],
) -> tuple[dict[str, int], dict[str, int]]:
    """Insert groups and CIs, returning business-ID-to-surrogate-key maps."""
    group_keys: dict[str, int] = {}
    ci_keys: dict[str, int] = {}

    for row in rows_by_file["assignment_groups.csv"]:
        cursor = connection.execute(
            """
            INSERT INTO assignment_groups (
                assignment_group_id, group_name, group_type, active_status
            ) VALUES (?, ?, ?, ?)
            """,
            (
                row["assignment_group_id"],
                row["group_name"],
                nullable_text(row["group_type"]),
                row["active_status"],
            ),
        )
        group_keys[row["assignment_group_id"]] = cursor.lastrowid

    for row in rows_by_file["configuration_items.csv"]:
        cursor = connection.execute(
            """
            INSERT INTO configuration_items (
                ci_id, ci_name, ci_type, environment, lifecycle_status
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                row["ci_id"],
                row["ci_name"],
                row["ci_type"],
                nullable_text(row["environment"]),
                row["lifecycle_status"],
            ),
        )
        ci_keys[row["ci_id"]] = cursor.lastrowid

    return group_keys, ci_keys


def load_incidents(
    connection: sqlite3.Connection,
    rows: list[dict[str, str]],
    group_keys: dict[str, int],
    ci_keys: dict[str, int],
) -> dict[str, int]:
    """Insert incidents and return their business-ID-to-key map."""
    incident_keys: dict[str, int] = {}

    for row in rows:
        cursor = connection.execute(
            """
            INSERT INTO incidents (
                incident_id, short_description, priority, status, opened_at,
                resolved_at, assignment_group_key, primary_ci_key,
                source_created_at, source_updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["incident_id"],
                nullable_text(row["short_description"]),
                row["priority"],
                row["status"],
                nullable_text(row["opened_at"]),
                nullable_text(row["resolved_at"]),
                group_keys.get(row["assignment_group_id"]),
                ci_keys.get(row["primary_ci_id"]),
                nullable_text(row["source_created_at"]),
                nullable_text(row["source_updated_at"]),
            ),
        )
        incident_keys[row["incident_id"]] = cursor.lastrowid

    return incident_keys


def load_sla_measurements(
    connection: sqlite3.Connection,
    rows: list[dict[str, str]],
    incident_keys: dict[str, int],
) -> None:
    """Insert SLA rows, preserving incomplete values as SQL NULL."""
    for row in rows:
        measurement_id = row["sla_measurement_id"]
        connection.execute(
            """
            INSERT INTO sla_measurements (
                sla_measurement_id, incident_key, sla_type,
                target_duration_seconds, actual_elapsed_seconds,
                measurement_status, breach_indicator,
                measurement_started_at, measurement_ended_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                measurement_id,
                incident_keys[row["incident_id"]],
                nullable_text(row["sla_type"]),
                nullable_integer(
                    row["target_duration_seconds"],
                    "sla_measurements.csv",
                    measurement_id,
                    "target_duration_seconds",
                ),
                nullable_integer(
                    row["actual_elapsed_seconds"],
                    "sla_measurements.csv",
                    measurement_id,
                    "actual_elapsed_seconds",
                ),
                nullable_text(row["measurement_status"]),
                nullable_integer(
                    row["breach_indicator"],
                    "sla_measurements.csv",
                    measurement_id,
                    "breach_indicator",
                ),
                nullable_text(row["measurement_started_at"]),
                nullable_text(row["measurement_ended_at"]),
            ),
        )


def load_change_requests(
    connection: sqlite3.Connection,
    rows: list[dict[str, str]],
    ci_keys: dict[str, int],
) -> None:
    """Insert changes and map optional primary CI business IDs to surrogate keys."""
    for row in rows:
        connection.execute(
            """
            INSERT INTO change_requests (
                change_id, primary_ci_key, change_type, status,
                planned_start_at, planned_end_at, actual_completed_at,
                outcome_classification
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["change_id"],
                ci_keys.get(row["primary_ci_id"]),
                nullable_text(row["change_type"]),
                row["status"],
                nullable_text(row["planned_start_at"]),
                nullable_text(row["planned_end_at"]),
                nullable_text(row["actual_completed_at"]),
                nullable_text(row["outcome_classification"]),
            ),
        )


def create_and_load_database(
    project_root: Path,
    rows_by_file: dict[str, list[dict[str, str]]],
) -> tuple[Path, dict[str, int]]:
    """Build a temporary database and publish it only after all checks succeed."""
    output_dir = project_root / "data" / "processed"
    final_path = output_dir / "itsm_warehouse.db"
    temporary_path = output_dir / f".itsm_warehouse.{uuid4().hex}.tmp.db"
    connection: sqlite3.Connection | None = None
    published = False

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        connection = sqlite3.connect(temporary_path)
        connection.execute("PRAGMA foreign_keys = ON")
        if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            raise LoadError("SQLite foreign-key enforcement could not be enabled.")

        schema_path = project_root / "sql" / "schema.sql"
        schema_sql = schema_path.read_text(encoding="utf-8")
        connection.executescript(schema_sql)
        connection.execute("BEGIN")

        group_keys, ci_keys = load_parent_tables(connection, rows_by_file)
        incident_keys = load_incidents(
            connection,
            rows_by_file["incidents.csv"],
            group_keys,
            ci_keys,
        )
        load_sla_measurements(
            connection,
            rows_by_file["sla_measurements.csv"],
            incident_keys,
        )
        load_change_requests(
            connection,
            rows_by_file["change_requests.csv"],
            ci_keys,
        )

        actual_counts: dict[str, int] = {}
        for filename in LOAD_ORDER:
            table_name = TABLE_BY_FILE[filename]
            actual_count = connection.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]
            expected_count = len(rows_by_file[filename])
            if actual_count != expected_count:
                raise LoadError(
                    f"{table_name}: expected {expected_count} rows, "
                    f"found {actual_count}."
                )
            actual_counts[table_name] = actual_count

        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()
        if foreign_key_errors:
            details = "; ".join(str(error) for error in foreign_key_errors)
            raise LoadError(f"Foreign-key check failed: {details}")

        connection.commit()
        connection.close()
        connection = None
        temporary_path.replace(final_path)
        published = True
        return final_path, actual_counts
    finally:
        if connection is not None:
            connection.rollback()
            connection.close()
        if not published and temporary_path.exists():
            temporary_path.unlink()


def main() -> int:
    """Preflight sources, load atomically, and print a concise summary."""
    project_root = Path(__file__).resolve().parents[1]
    print("ITSM CSV-to-SQLite loader")
    print(f"Project root: {project_root}")

    try:
        (project_root / "data" / "processed").mkdir(parents=True, exist_ok=True)
        rows_by_file = read_source_files(project_root)
        print("CSV row counts:")
        for filename in LOAD_ORDER:
            print(f"  {filename}: {len(rows_by_file[filename])}")

        reference_errors = preflight_references(rows_by_file)
        if reference_errors:
            print("Preflight failed; no database was published.")
            for error in reference_errors:
                print(f"  ERROR: {error}")
            print(f"Total errors: {len(reference_errors)}")
            return 1

        database_path, counts = create_and_load_database(
            project_root,
            rows_by_file,
        )
        print("Database row counts:")
        for table_name in (
            "assignment_groups",
            "configuration_items",
            "incidents",
            "sla_measurements",
            "change_requests",
        ):
            print(f"  {table_name}: {counts[table_name]}")
        print("Foreign-key check: passed")
        print(f"Database published: {database_path}")
        return 0
    except (LoadError, OSError, sqlite3.Error, UnicodeError) as error:
        print(f"Load failed; no new database was published. ERROR: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
