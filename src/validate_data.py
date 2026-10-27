"""Read-only data-quality checks for the synthetic ITSM source CSV files."""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

EXPECTED_COLUMNS = {
    "assignment_groups.csv": [
        "assignment_group_id",
        "group_name",
        "group_type",
        "active_status",
    ],
    "configuration_items.csv": [
        "ci_id",
        "ci_name",
        "ci_type",
        "environment",
        "lifecycle_status",
    ],
    "incidents.csv": [
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
    ],
    "sla_measurements.csv": [
        "sla_measurement_id",
        "incident_id",
        "sla_type",
        "target_duration_seconds",
        "actual_elapsed_seconds",
        "measurement_status",
        "breach_indicator",
        "measurement_started_at",
        "measurement_ended_at",
    ],
    "change_requests.csv": [
        "change_id",
        "primary_ci_id",
        "change_type",
        "status",
        "planned_start_at",
        "planned_end_at",
        "actual_completed_at",
        "outcome_classification",
    ],
}

IDENTIFIER_COLUMNS = {
    "assignment_groups.csv": "assignment_group_id",
    "configuration_items.csv": "ci_id",
    "incidents.csv": "incident_id",
    "sla_measurements.csv": "sla_measurement_id",
    "change_requests.csv": "change_id",
}

# Expected labels require both the recorded value and the finding reason to
# match the deliberate sample-data case.
EXPECTED_CASES = {
    ("incidents.csv", "INC1014", "opened_at"): (
        "",
        "Opening timestamp is missing;",
        "deliberate missing opening timestamp example",
    ),
    ("sla_measurements.csv", "SLA022", "actual_elapsed_seconds"): (
        "",
        "SLA value is missing;",
        "deliberate incomplete SLA example",
    ),
    ("sla_measurements.csv", "SLA022", "breach_indicator"): (
        "",
        "SLA value is missing;",
        "deliberate incomplete SLA example",
    ),
    ("sla_measurements.csv", "SLA022", "measurement_started_at"): (
        "",
        "SLA value is missing;",
        "deliberate incomplete SLA example",
    ),
    ("sla_measurements.csv", "SLA022", "measurement_ended_at"): (
        "",
        "SLA value is missing;",
        "deliberate incomplete SLA example",
    ),
    ("change_requests.csv", "CHG007", "outcome_classification"): (
        "",
        "Outcome is missing;",
        "deliberate missing change outcome example",
    ),
}


@dataclass
class Finding:
    filename: str
    record_id: str
    column: str
    severity: str
    reason: str
    expected_case: str | None = None

    @property
    def is_error(self) -> bool:
        return self.severity == "ERROR"


@dataclass
class CsvReadResult:
    rows: list[dict[str, str | None]]
    status: str


def add_finding(
    findings: list[Finding],
    filename: str,
    record_id: str,
    column: str,
    severity: str,
    reason: str,
    actual_value: str | None = None,
) -> None:
    """Store a finding and verify any matching deliberate sample-data case."""
    expected_case = None
    case = EXPECTED_CASES.get((filename, record_id, column))
    if (
        case is not None
        and actual_value == case[0]
        and reason.startswith(case[1])
    ):
        expected_case = case[2]

    findings.append(
        Finding(
            filename=filename,
            record_id=record_id,
            column=column,
            severity=severity,
            reason=reason,
            expected_case=expected_case,
        )
    )


def read_csv_file(
    project_root: Path,
    filename: str,
    findings: list[Finding],
) -> CsvReadResult:
    """Read one CSV without changing it and check its header."""
    path = project_root / "data" / "raw" / filename

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            headers = reader.fieldnames

            if headers != EXPECTED_COLUMNS[filename]:
                add_finding(
                    findings,
                    filename,
                    "(file-level)",
                    "header",
                    "ERROR",
                    f"Expected columns {EXPECTED_COLUMNS[filename]}, "
                    f"found {headers}.",
                )
                return CsvReadResult([], "invalid header; rows not loaded")

            rows: list[dict[str, str | None]] = []
            identifier_column = IDENTIFIER_COLUMNS[filename]

            for line_number, row in enumerate(reader, start=2):
                if None in row:
                    add_finding(
                        findings,
                        filename,
                        str(row.get(identifier_column) or f"line {line_number}"),
                        "row",
                        "ERROR",
                        "Row contains more values than the header.",
                    )
                if any(value is None for value in row.values()):
                    add_finding(
                        findings,
                        filename,
                        str(row.get(identifier_column) or f"line {line_number}"),
                        "row",
                        "ERROR",
                        "Row contains fewer values than the header.",
                    )
                rows.append(row)

            return CsvReadResult(rows, "read successfully")
    except OSError as error:
        add_finding(
            findings,
            filename,
            "(file-level)",
            "file",
            "ERROR",
            f"Could not read file: {error}",
        )
        return CsvReadResult([], "could not be read")
    except csv.Error as error:
        add_finding(
            findings,
            filename,
            "(file-level)",
            "CSV format",
            "ERROR",
            f"Could not parse CSV: {error}",
        )
        return CsvReadResult([], "CSV parse error; rows may be incomplete")


def value_of(row: dict[str, str | None], column: str) -> str:
    """Return a CSV cell as text, treating an absent cell as empty."""
    return row.get(column) or ""


def check_business_identifiers(
    filename: str,
    rows: list[dict[str, str | None]],
    findings: list[Finding],
) -> None:
    """Check that each business identifier is non-empty and unique."""
    identifier_column = IDENTIFIER_COLUMNS[filename]
    seen: set[str] = set()

    for row in rows:
        identifier = value_of(row, identifier_column)

        if not identifier.strip():
            add_finding(
                findings,
                filename,
                "(missing identifier)",
                identifier_column,
                "ERROR",
                "Business identifier is empty or whitespace-only.",
            )
            continue

        if identifier in seen:
            add_finding(
                findings,
                filename,
                identifier,
                identifier_column,
                "ERROR",
                "Business identifier is duplicated within this CSV.",
            )
        else:
            seen.add(identifier)

        for column, cell_value in row.items():
            if (
                cell_value is not None
                and cell_value
                and not cell_value.strip()
            ):
                add_finding(
                    findings,
                    filename,
                    identifier or "(missing identifier)",
                    column or "row",
                    "ERROR",
                    "Cell contains whitespace instead of a genuinely blank "
                    "value.",
                )


def check_references(
    rows_by_file: dict[str, list[dict[str, str | None]]],
    findings: list[Finding],
) -> None:
    """Check populated references; report missing and unmatched separately."""
    groups = {
        value_of(row, "assignment_group_id")
        for row in rows_by_file["assignment_groups.csv"]
    }
    configuration_items = {
        value_of(row, "ci_id")
        for row in rows_by_file["configuration_items.csv"]
    }
    incidents = {
        value_of(row, "incident_id")
        for row in rows_by_file["incidents.csv"]
    }

    reference_rules = [
        (
            "incidents.csv",
            "incident_id",
            "assignment_group_id",
            groups,
            False,
        ),
        ("incidents.csv", "incident_id", "primary_ci_id", configuration_items, False),
        (
            "sla_measurements.csv",
            "sla_measurement_id",
            "incident_id",
            incidents,
            True,
        ),
        (
            "change_requests.csv",
            "change_id",
            "primary_ci_id",
            configuration_items,
            False,
        ),
    ]

    for filename, id_column, reference_column, valid_ids, required in reference_rules:
        for row in rows_by_file[filename]:
            record_id = value_of(row, id_column) or "(missing identifier)"
            reference = value_of(row, reference_column)

            if not reference.strip():
                severity = "ERROR" if required else "INFO"
                add_finding(
                    findings,
                    filename,
                    record_id,
                    reference_column,
                    severity,
                    "Reference is missing."
                    if required
                    else "Optional or unresolved reference is missing.",
                )
            elif reference not in valid_ids:
                add_finding(
                    findings,
                    filename,
                    record_id,
                    reference_column,
                    "ERROR",
                    f"Populated reference {reference!r} does not match a "
                    "business identifier in the referenced CSV.",
                    actual_value=reference,
                )


def parse_timestamp(
    filename: str,
    record_id: str,
    column: str,
    value: str,
    findings: list[Finding],
) -> datetime | None:
    """Parse a timestamp only when it exactly follows the UTC project format."""
    if not value:
        return None

    try:
        parsed = datetime.strptime(value, TIMESTAMP_FORMAT)
    except ValueError:
        add_finding(
            findings,
            filename,
            record_id,
            column,
            "ERROR",
            "Timestamp must use YYYY-MM-DDTHH:MM:SSZ (UTC).",
        )
        return None

    if parsed.strftime(TIMESTAMP_FORMAT) != value:
        add_finding(
            findings,
            filename,
            record_id,
            column,
            "ERROR",
            "Timestamp must exactly match YYYY-MM-DDTHH:MM:SSZ (UTC).",
        )
        return None

    return parsed.replace(tzinfo=timezone.utc)


def check_timestamps(
    rows_by_file: dict[str, list[dict[str, str | None]]],
    findings: list[Finding],
) -> None:
    """Validate populated timestamps and compare valid chronological pairs."""
    timestamp_columns = {
        "incidents.csv": (
            "incident_id",
            ("opened_at", "resolved_at", "source_created_at", "source_updated_at"),
        ),
        "sla_measurements.csv": (
            "sla_measurement_id",
            ("measurement_started_at", "measurement_ended_at"),
        ),
        "change_requests.csv": (
            "change_id",
            ("planned_start_at", "planned_end_at", "actual_completed_at"),
        ),
    }
    chronology_pairs = {
        "incidents.csv": (
            ("opened_at", "resolved_at"),
            ("source_created_at", "source_updated_at"),
        ),
        "sla_measurements.csv": (("measurement_started_at", "measurement_ended_at"),),
        "change_requests.csv": (("planned_start_at", "planned_end_at"),),
    }
    parsed_values: dict[tuple[str, str, str], datetime] = {}

    for filename, (id_column, columns) in timestamp_columns.items():
        for row in rows_by_file[filename]:
            record_id = value_of(row, id_column) or "(missing identifier)"

            for column in columns:
                value = value_of(row, column)
                if not value:
                    continue

                parsed = parse_timestamp(
                    filename, record_id, column, value, findings
                )
                if parsed is not None:
                    parsed_values[(filename, record_id, column)] = parsed

    # A missing opening time is its own finding, separate from invalid values.
    for row in rows_by_file["incidents.csv"]:
        record_id = value_of(row, "incident_id") or "(missing identifier)"
        if not value_of(row, "opened_at").strip():
            add_finding(
                findings,
                "incidents.csv",
                record_id,
                "opened_at",
                "ERROR",
                "Opening timestamp is missing; time-based calculations that "
                "need it must exclude this incident, but other analyses may "
                "still use the record.",
                actual_value=value_of(row, "opened_at"),
            )

    for filename, pairs in chronology_pairs.items():
        id_column, _ = timestamp_columns[filename]
        for row in rows_by_file[filename]:
            record_id = value_of(row, id_column) or "(missing identifier)"

            for earlier_column, later_column in pairs:
                earlier = parsed_values.get((filename, record_id, earlier_column))
                later = parsed_values.get((filename, record_id, later_column))
                if earlier is not None and later is not None and later < earlier:
                    add_finding(
                        findings,
                        filename,
                        record_id,
                        later_column,
                        "ERROR",
                        f"{later_column} occurs before {earlier_column}.",
                    )


def check_incident_statuses(
    rows: list[dict[str, str | None]],
    findings: list[Finding],
) -> None:
    """Check status/timestamp consistency without inventing a status list."""
    for row in rows:
        incident_id = value_of(row, "incident_id") or "(missing identifier)"
        status = value_of(row, "status").strip()
        resolved_at = value_of(row, "resolved_at").strip()

        if status == "Resolved" and not resolved_at:
            add_finding(
                findings,
                "incidents.csv",
                incident_id,
                "resolved_at",
                "ERROR",
                "Status is Resolved but the resolution timestamp is missing.",
            )
        elif status and status != "Resolved" and resolved_at:
            add_finding(
                findings,
                "incidents.csv",
                incident_id,
                "resolved_at",
                "REVIEW",
                "A resolution timestamp is populated while status is not "
                "Resolved; confirm the lifecycle/status interpretation.",
            )


def check_sla_values(
    rows: list[dict[str, str | None]],
    findings: list[Finding],
) -> None:
    """Validate SLA numeric fields and report incomplete values as missing."""
    nullable_sla_columns = (
        "sla_type",
        "target_duration_seconds",
        "actual_elapsed_seconds",
        "measurement_status",
        "breach_indicator",
        "measurement_started_at",
        "measurement_ended_at",
    )

    for row in rows:
        measurement_id = value_of(row, "sla_measurement_id") or "(missing identifier)"

        for column in ("target_duration_seconds", "actual_elapsed_seconds"):
            value = value_of(row, column)
            if not value:
                continue

            if not value.isascii() or not value.isdecimal():
                negative_integer = (
                    value.startswith("-")
                    and value[1:].isascii()
                    and value[1:].isdecimal()
                )
                add_finding(
                    findings,
                    "sla_measurements.csv",
                    measurement_id,
                    column,
                    "ERROR",
                    "Duration cannot be negative."
                    if negative_integer
                    else "Duration must be a non-negative integer number of "
                    "seconds; decimals and non-numeric text are invalid.",
                )
                continue

        indicator = value_of(row, "breach_indicator")
        if indicator and indicator not in {"0", "1"}:
            add_finding(
                findings,
                "sla_measurements.csv",
                measurement_id,
                "breach_indicator",
                "ERROR",
                "Breach indicator must be 0, 1, or blank.",
            )

        for column in nullable_sla_columns:
            if not value_of(row, column).strip():
                add_finding(
                    findings,
                    "sla_measurements.csv",
                    measurement_id,
                    column,
                    "INFO",
                    "SLA value is missing; it remains unknown and is not "
                    "treated as compliant or breached.",
                    actual_value=value_of(row, column),
                )


def check_change_outcomes(
    rows: list[dict[str, str | None]],
    findings: list[Finding],
) -> None:
    """Report missing outcomes without inferring success or failure."""
    for row in rows:
        if not value_of(row, "outcome_classification").strip():
            change_id = value_of(row, "change_id") or "(missing identifier)"
            add_finding(
                findings,
                "change_requests.csv",
                change_id,
                "outcome_classification",
                "INFO",
                "Outcome is missing; do not infer success or failure.",
                actual_value=value_of(row, "outcome_classification"),
            )


def print_report(
    rows_by_file: dict[str, list[dict[str, str | None]]],
    read_status_by_file: dict[str, str],
    findings: list[Finding],
) -> None:
    """Print file counts and every finding in a readable format."""
    print("ITSM synthetic CSV data-quality report")
    print("Files are read only; no source records are changed.")
    print("\nRecord counts:")
    for filename in EXPECTED_COLUMNS:
        status = read_status_by_file[filename]
        if status == "read successfully":
            print(f"  {filename}: {len(rows_by_file[filename])} records ({status})")
        else:
            print(f"  {filename}: count unavailable ({status})")

    print("\nFindings:")
    if not findings:
        print("  No findings.")
    else:
        for finding in findings:
            label = finding.severity
            if finding.expected_case:
                label = f"EXPECTED {label}"

            print(
                f"  [{label}] {finding.filename} | "
                f"ID={finding.record_id} | column={finding.column} | "
                f"{finding.reason}"
                + (
                    f" ({finding.expected_case})"
                    if finding.expected_case
                    else ""
                )
            )

    errors = [finding for finding in findings if finding.is_error]
    expected_errors = [
        finding for finding in errors if finding.expected_case is not None
    ]
    unexpected_errors = [
        finding for finding in errors if finding.expected_case is None
    ]
    informational = [
        finding for finding in findings if finding.severity != "ERROR"
    ]

    print("\nSummary:")
    print(f"  Errors: {len(errors)}")
    print(f"  Expected deliberate error cases: {len(expected_errors)}")
    print(f"  Unexpected errors: {len(unexpected_errors)}")
    print(f"  Informational/review findings: {len(informational)}")
    if errors:
        print("  Result: VALIDATION ERRORS FOUND.")
    else:
        print("  Result: No validation errors found.")


def main() -> int:
    """Load the raw CSV files, run checks, and return an appropriate exit code."""
    project_root = Path(__file__).resolve().parents[1]
    findings: list[Finding] = []
    read_results = {
        filename: read_csv_file(project_root, filename, findings)
        for filename in EXPECTED_COLUMNS
    }
    rows_by_file = {
        filename: result.rows for filename, result in read_results.items()
    }
    read_status_by_file = {
        filename: result.status for filename, result in read_results.items()
    }

    for filename, rows in rows_by_file.items():
        check_business_identifiers(filename, rows, findings)

    check_references(rows_by_file, findings)
    check_timestamps(rows_by_file, findings)
    check_incident_statuses(rows_by_file["incidents.csv"], findings)
    check_sla_values(rows_by_file["sla_measurements.csv"], findings)
    check_change_outcomes(rows_by_file["change_requests.csv"], findings)
    print_report(rows_by_file, read_status_by_file, findings)

    return 1 if any(finding.is_error for finding in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
