-- Enable foreign-key checks for this database connection. The application must
-- also enable this pragma on every connection that uses the database.
PRAGMA foreign_keys = ON;

-- One row per assignment group. The source identifier remains unique and
-- non-empty; group status values are not restricted until their domain is
-- agreed.
CREATE TABLE assignment_groups (
    assignment_group_key INTEGER PRIMARY KEY,
    assignment_group_id TEXT NOT NULL UNIQUE
        CHECK (length(trim(assignment_group_id)) > 0),
    group_name TEXT NOT NULL,
    group_type TEXT,
    active_status TEXT NOT NULL
);

-- One row per configuration item. CI names are not assumed unique, and no
-- unconfirmed type or lifecycle-status values are enumerated here.
CREATE TABLE configuration_items (
    configuration_item_key INTEGER PRIMARY KEY,
    ci_id TEXT NOT NULL UNIQUE
        CHECK (length(trim(ci_id)) > 0),
    ci_name TEXT NOT NULL,
    ci_type TEXT NOT NULL,
    environment TEXT,
    lifecycle_status TEXT NOT NULL
);

-- One consolidated row per incident in the initial model. The assignment
-- group and primary CI references remain nullable until source mandatoryness
-- is confirmed. opened_at and resolved_at remain nullable for incomplete and
-- unresolved records; timestamp validation is handled in Python.
CREATE TABLE incidents (
    incident_key INTEGER PRIMARY KEY,
    incident_id TEXT NOT NULL UNIQUE
        CHECK (length(trim(incident_id)) > 0),
    short_description TEXT,
    priority TEXT NOT NULL,
    status TEXT NOT NULL,
    opened_at TEXT,
    resolved_at TEXT,
    assignment_group_key INTEGER,
    primary_ci_key INTEGER,
    source_created_at TEXT,
    source_updated_at TEXT,
    FOREIGN KEY (assignment_group_key)
        REFERENCES assignment_groups (assignment_group_key),
    FOREIGN KEY (primary_ci_key)
        REFERENCES configuration_items (configuration_item_key)
);

-- One row per individual SLA measurement. Multiple measurements may belong
-- to one incident. Nullable measurement values preserve incomplete or
-- ineligible records; NULL breach_indicator means not currently evaluable.
CREATE TABLE sla_measurements (
    sla_measurement_key INTEGER PRIMARY KEY,
    sla_measurement_id TEXT NOT NULL UNIQUE
        CHECK (length(trim(sla_measurement_id)) > 0),
    incident_key INTEGER NOT NULL,
    sla_type TEXT,
    target_duration_seconds INTEGER
        CHECK (
            target_duration_seconds IS NULL
            OR target_duration_seconds >= 0
        ),
    actual_elapsed_seconds INTEGER
        CHECK (
            actual_elapsed_seconds IS NULL
            OR actual_elapsed_seconds >= 0
        ),
    measurement_status TEXT,
    breach_indicator INTEGER
        CHECK (
            breach_indicator IS NULL
            OR breach_indicator IN (0, 1)
        ),
    measurement_started_at TEXT,
    measurement_ended_at TEXT,
    FOREIGN KEY (incident_key)
        REFERENCES incidents (incident_key)
);

-- One row per change request. The primary CI reference remains nullable until
-- source mandatoryness is confirmed. Missing outcomes remain NULL and are not
-- treated as successful changes.
CREATE TABLE change_requests (
    change_request_key INTEGER PRIMARY KEY,
    change_id TEXT NOT NULL UNIQUE
        CHECK (length(trim(change_id)) > 0),
    primary_ci_key INTEGER,
    change_type TEXT,
    status TEXT NOT NULL,
    planned_start_at TEXT,
    planned_end_at TEXT,
    actual_completed_at TEXT,
    outcome_classification TEXT,
    FOREIGN KEY (primary_ci_key)
        REFERENCES configuration_items (configuration_item_key)
);
