# ITSM Data Warehouse

A small, local data warehouse learning project for an Associate Data Modeller /
Data Engineer portfolio. It uses **synthetic IT Service Management (ITSM)
records only** and demonstrates how to model, validate, load, and analyse a
focused set of incident, SLA, configuration item, assignment group, and change
request data.

> **Project status:** The initial SQLite relational model, source-data
> validator, CSV loader, and four analytics queries are implemented. The
> project remains under development; dimensional modelling, SCD Type 2, and
> other roadmap items are not yet implemented.

## Project overview

Operational ITSM records are designed to track work, not necessarily to make
consistent historical reporting easy. Incidents, SLA measurements, assignment
groups, configuration items (CIs), and changes can be stored in different
places, and missing or inconsistent data can make results difficult to trust.

This project brings a small synthetic sample into a documented SQLite model.
Python checks the source CSVs and loads them into related tables; SQL queries
then answer a few clearly defined business questions. The design and code are
kept intentionally small so the modelling choices and data flow are easy to
explain.

## Objectives and technologies

The implemented version demonstrates:

- Business, conceptual, logical, and physical data-model documentation.
- A relational SQLite schema with surrogate keys, business identifiers,
  foreign keys, constraints, and nullable fields.
- Python source-data validation and CSV-to-SQLite loading.
- SQL analytics for incident volumes, SLA outcomes, resolution duration, and
  change outcomes.
- Explicit handling of missing and unmatched values rather than silently
  inventing data.

Technologies used by the implementation:

- **Python 3** and its standard library (`csv`, `sqlite3`, `pathlib`, and other
  standard-library modules) for validation and loading.
- **SQLite** for a lightweight local relational database.
- **SQL** for the schema and business analytics.
- **Git and GitHub** are part of the project’s intended version-control and
  portfolio workflow; the project documentation does not claim that a remote
  GitHub repository is configured.

No third-party Python packages are required by the validator or loader.

## Architecture and data flow

```text
data/raw/*.csv
     |
     +--> src/validate_data.py
     |       Read-only checks for identifiers, references, timestamps,
     |       durations, and missing values
     |
     +--> src/load_data.py
             Read and preflight source records
             Map business identifiers to SQLite surrogate keys
             Execute sql/schema.sql and load in dependency order
             Check table counts and foreign-key integrity
             Publish the database only after a successful load
                         |
                         v
          data/processed/itsm_warehouse.db
                         |
                         v
          sql/queries/*.sql
             Business analytics results
```

The loader uses the existing schema, preserves blank CSV values as SQL `NULL`,
and rejects populated references that do not match a parent record. It builds
the database in a temporary file and replaces the final database only after
the load and checks succeed.

All records in `data/raw/` are fictional and synthetic. For example, `CI008`
represents the fictional Elm Service Portal in the Development environment.
The source files are:

- [`data/raw/assignment_groups.csv`](data/raw/assignment_groups.csv)
- [`data/raw/configuration_items.csv`](data/raw/configuration_items.csv)
- [`data/raw/incidents.csv`](data/raw/incidents.csv)
- [`data/raw/sla_measurements.csv`](data/raw/sla_measurements.csv)
- [`data/raw/change_requests.csv`](data/raw/change_requests.csv)

## Data model

The implemented physical schema is in [`sql/schema.sql`](sql/schema.sql). Its
five tables and grains are:

| Table | Grain |
| --- | --- |
| `assignment_groups` | One row per support group. |
| `configuration_items` | One row per configuration item. |
| `incidents` | One consolidated row per incident. |
| `sla_measurements` | One row per individual SLA measurement. |
| `change_requests` | One row per change request. |

Each table has an integer surrogate primary key and a separate, unique
business identifier. The schema also enforces non-empty business identifiers.
The relationships are:

- `incidents.assignment_group_key` references
  `assignment_groups.assignment_group_key`.
- `incidents.primary_ci_key` references
  `configuration_items.configuration_item_key`.
- `sla_measurements.incident_key` references `incidents.incident_key`.
- `change_requests.primary_ci_key` references
  `configuration_items.configuration_item_key`.

An incident may have multiple SLA measurements. Incident group/CI references
and change CI references are nullable in the current design; an SLA measurement
must reference an incident. The models and their assumptions are documented in
[`docs/`](docs/) and shown in
[`models/physical_model.mmd`](models/physical_model.mmd).

The current implementation is a **relational model**, not a dimensional star
schema. A fact-and-dimension model is a future enhancement.

## Python components

### Source data validator

[`src/validate_data.py`](src/validate_data.py) reads the five CSV files without
changing them. It checks business identifiers, references, timestamp format
and chronology, SLA durations and breach indicators, and missing values. It
reports expected deliberate sample-data findings separately from unexpected
errors.

The validator intentionally reports the missing `opened_at` value for
`INC1014` as an error. This is a retained data-quality example, not an
unexpected software failure. Therefore, the current validator exits with code
`1` even though it reports zero unexpected errors. It also reports the
incomplete `SLA022` measurement and missing `CHG007` outcome as informational
findings.

### CSV-to-SQLite loader

[`src/load_data.py`](src/load_data.py) validates file headers and identifiers,
preflights foreign-key references, and loads records in dependency order:

1. Assignment groups
2. Configuration items
3. Incidents
4. SLA measurements
5. Change requests

The loader maps source business IDs to generated surrogate keys, retains
legitimate missing values as SQL `NULL`, checks row counts and foreign keys,
and does not publish a partial database if loading fails.

## Business analytics

The four saved queries are in [`sql/queries/`](sql/queries/). The results below
were executed against a local SQLite database generated by running
[`src/load_data.py`](src/load_data.py). The generated database is excluded from
the Git repository; readers can recreate it by following the load instructions
below.

| Query | Business question and method | Verified result |
| --- | --- | --- |
| [`01_incidents_by_assignment_group.sql`](sql/queries/01_incidents_by_assignment_group.sql) | How many incidents are assigned to each support group? A left join includes groups with no incidents. | **20 incidents total:** Application Support 6, Platform Operations 6, Service Desk 4, Database Operations 4. |
| [`02_sla_breach_rate.sql`](sql/queries/02_sla_breach_rate.sql) | What percentage of SLA measurements breached? The rate denominator includes only measurements with a known breach indicator. | **25 total:** 6 breached, 18 met target, 1 unknown; **25%** breach rate (6 of 24 known outcomes). |
| [`03_incident_resolution_time.sql`](sql/queries/03_incident_resolution_time.sql) | How long does it take to resolve an incident? Includes resolved incidents with valid UTC timestamps and a non-negative elapsed duration. | **18 eligible**, 2 excluded; **2.52 hours** average, 1.17 minimum, 4.17 maximum. |
| [`04_change_success_rate.sql`](sql/queries/04_change_success_rate.sql) | What percentage of change requests were successful? The denominator includes only known outcomes. | **8 total:** 5 successful, 2 failed, 1 unknown; **71.43%** success rate (5 of 7 known outcomes). |

The resolution query’s two excluded records are unresolved in the current
data. `INC1014` also has a missing opening timestamp. The query returns `NULL`
duration statistics if no incidents qualify, rather than presenting empty-set
results as zero.

## Data-quality decisions

- **Synthetic data only:** Do not use real company, employee, customer,
  incident, or client records in this learning project.
- **Identifiers:** Business identifiers must be present, non-empty, and unique
  within their source file. Duplicate identifiers are not silently merged.
- **References:** A populated group or CI reference must match a corresponding
  source entity. The sample references for `INC1018`, `INC1019`, and `CHG008`
  have been corrected to `GRP003` or `CI008`.
- **Missing timestamps:** `INC1014.opened_at` remains blank intentionally. Do
  not invent a timestamp; exclude the incident from calculations that require
  a valid opening time while retaining it for other analyses.
- **SLA outcomes:** `breach_indicator` is stored as `1`, `0`, or `NULL`.
  `NULL` means the outcome is unknown or not evaluable; it is not evidence that
  an SLA was met or breached. The breach-rate query excludes unknowns from the
  rate denominator and reports their count.
- **Change outcomes:** A missing outcome remains `NULL`. It is not assumed to
  mean either a successful or a failed change. The success-rate query uses only
  the known `Successful` and `Failed` values in its denominator.
- **Timestamps and durations:** Timestamps are stored as text in the synthetic
  data using ISO 8601 UTC strings ending in `Z`. The timezone convention and
  duration business semantics remain decisions to confirm. SLA durations use
  seconds in the physical schema.
- **Business definitions:** SLA eligibility, business-time clocks, complete
  status domains, and several source-mandatory fields have not been fully
  defined. The current analytics are learning examples over this sample, not
  final operational policy.

## Run the project on Windows

Run commands from the project root:

```powershell
cd D:\DataProjects\ITSM-Data-Warehouse
```

### Validate the source CSVs

```powershell
python .\src\validate_data.py
```

The current report intentionally includes the missing `INC1014.opened_at`
finding and exits with code `1`. Check the report for the distinction between
expected deliberate findings and unexpected errors; the expected missing
timestamp does not by itself mean the validator malfunctioned.

### Load or rebuild the SQLite database

```powershell
python .\src\load_data.py
```

The loader reads `data/raw/`, executes `sql/schema.sql`, and writes
`data/processed/itsm_warehouse.db` after a successful load. It stops before
publishing if populated foreign-key references cannot be matched. A successful
run replaces the database at that path.

### Execute an analytics query read-only

The following PowerShell example runs one saved query using Python's built-in
SQLite support. Change `$queryFile` to another query path to run a different
query:

```powershell
$queryFile = ".\sql\queries\01_incidents_by_assignment_group.sql"
@'
import sqlite3
import sys
from pathlib import Path

database = Path("data/processed/itsm_warehouse.db").resolve()
query = Path(sys.argv[1]).read_text(encoding="utf-8")
connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
try:
    cursor = connection.execute(query)
    print([column[0] for column in cursor.description])
    for row in cursor.fetchall():
        print(row)
finally:
    connection.close()
'@ | python - $queryFile
```

For example, set `$queryFile` to
`".\sql\queries\02_sla_breach_rate.sql"` to run the SLA query.

## Current limitations and future enhancements

The current project is intentionally small and has several open modelling and
business questions:

- The sample is synthetic and small; it is not representative of a production
  workload.
- The database is a normalized relational schema. A dimensional star schema
  with fact and dimension tables is planned but not yet implemented.
- SCD Type 2 history for changing group or CI attributes is not implemented.
- The initial model records one primary CI per incident or change, and does
  not preserve the history of assignment, status, or priority changes.
- SLA eligibility, clock/pause rules, timezone confirmation, timestamp
  precision, and several allowed-value domains still need business decisions.
- The project has no implemented data dictionary or metadata catalogue yet;
  fuller lineage and architecture documentation are also future work.
- The `tests/` directory does not yet contain an automated test suite.

Realistic next steps include confirming the open business rules, designing the
dimensional model and SCD Type 2 approach, documenting the data dictionary and
lineage, and adding repeatable automated tests for validation, loading, and
analytics.

## Project documentation

- [Business requirements](docs/business_requirements.md)
- [Conceptual data model](docs/conceptual_data_model.md)
- [Logical data model](docs/logical_data_model.md)
- [Physical data model](docs/physical_data_model.md)
- [Conceptual Mermaid diagram](models/conceptual_model.mmd)
- [Logical Mermaid diagram](models/logical_model.mmd)
- [Physical Mermaid diagram](models/physical_model.mmd)
