-- Business question: What percentage of change requests were successful?
-- Treat only the stored outcomes 'Successful' and 'Failed' as known outcomes.
-- Missing or other outcome values are reported as unknown, not as success or
-- failure. Calculate the success rate over known outcomes only.
WITH outcome_counts AS (
    SELECT
        COUNT(*) AS total_change_requests,
        COUNT(CASE
            WHEN outcome_classification = 'Successful' THEN 1
        END) AS successful_changes,
        COUNT(CASE
            WHEN outcome_classification = 'Failed' THEN 1
        END) AS failed_changes,
        COUNT(CASE
            WHEN outcome_classification IS NULL
                OR outcome_classification NOT IN ('Successful', 'Failed')
            THEN 1
        END) AS unknown_outcomes
    FROM change_requests
)
SELECT
    total_change_requests,
    successful_changes,
    failed_changes,
    unknown_outcomes,
    ROUND(
        100.0 * successful_changes
        / NULLIF(successful_changes + failed_changes, 0),
        2
    ) AS change_success_rate_percent
FROM outcome_counts;
