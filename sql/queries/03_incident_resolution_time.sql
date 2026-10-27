-- Business question: How long does it take, on average, to resolve an incident?
-- Treat a timestamp as valid only when it has the expected UTC ISO 8601
-- shape and SQLite can parse and round-trip it without changing its value.
-- Include only incidents with status 'Resolved', valid timestamps, and a
-- non-negative duration. Unresolved or otherwise ineligible incidents are
-- counted as excluded and do not affect the average, minimum, or maximum.
-- Report resolution durations in hours, rounded to two decimal places.
WITH timestamp_checks AS (
    SELECT
        incident_key,
        status,
        opened_at,
        resolved_at,
        (
            opened_at IS NOT NULL
            AND length(opened_at) = 20
            AND opened_at GLOB '????-??-??T??:??:??Z'
            AND substr(opened_at, 1, 4) NOT GLOB '*[^0-9]*'
            AND substr(opened_at, 6, 2) NOT GLOB '*[^0-9]*'
            AND substr(opened_at, 9, 2) NOT GLOB '*[^0-9]*'
            AND substr(opened_at, 12, 2) NOT GLOB '*[^0-9]*'
            AND substr(opened_at, 15, 2) NOT GLOB '*[^0-9]*'
            AND substr(opened_at, 18, 2) NOT GLOB '*[^0-9]*'
            AND strftime(
                '%Y-%m-%dT%H:%M:%SZ',
                julianday(opened_at)
            ) = opened_at
        ) AS opened_at_is_valid,
        (
            resolved_at IS NOT NULL
            AND length(resolved_at) = 20
            AND resolved_at GLOB '????-??-??T??:??:??Z'
            AND substr(resolved_at, 1, 4) NOT GLOB '*[^0-9]*'
            AND substr(resolved_at, 6, 2) NOT GLOB '*[^0-9]*'
            AND substr(resolved_at, 9, 2) NOT GLOB '*[^0-9]*'
            AND substr(resolved_at, 12, 2) NOT GLOB '*[^0-9]*'
            AND substr(resolved_at, 15, 2) NOT GLOB '*[^0-9]*'
            AND substr(resolved_at, 18, 2) NOT GLOB '*[^0-9]*'
            AND strftime(
                '%Y-%m-%dT%H:%M:%SZ',
                julianday(resolved_at)
            ) = resolved_at
        ) AS resolved_at_is_valid
    FROM incidents
),
resolution_durations AS (
    SELECT
        incident_key,
        CASE
            WHEN status = 'Resolved'
                AND opened_at_is_valid
                AND resolved_at_is_valid
                AND julianday(resolved_at) >= julianday(opened_at)
            THEN
                (julianday(resolved_at) - julianday(opened_at)) * 24.0
        END AS resolution_hours
    FROM timestamp_checks
)
SELECT
    COUNT(*) AS total_incidents,
    COUNT(resolution_hours) AS resolved_incidents_with_valid_timestamps,
    ROUND(AVG(resolution_hours), 2) AS average_resolution_hours,
    ROUND(MIN(resolution_hours), 2) AS minimum_resolution_hours,
    ROUND(MAX(resolution_hours), 2) AS maximum_resolution_hours,
    COUNT(*) - COUNT(resolution_hours) AS excluded_incidents
FROM resolution_durations;
