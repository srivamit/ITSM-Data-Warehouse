-- Business question: What percentage of SLA measurements breached their targets?
-- Count NULL breach indicators as unknown, not as breaches or successful outcomes.
-- Calculate the breach rate among measurements with a known indicator (0 or 1).
SELECT
    COUNT(*) AS total_sla_measurements,
    COUNT(CASE WHEN breach_indicator = 1 THEN 1 END) AS confirmed_breaches,
    COUNT(CASE WHEN breach_indicator = 0 THEN 1 END) AS met_sla_target,
    COUNT(CASE WHEN breach_indicator IS NULL THEN 1 END) AS unknown_outcomes,
    ROUND(
        100.0 * COUNT(CASE WHEN breach_indicator = 1 THEN 1 END)
        / NULLIF(COUNT(breach_indicator), 0),
        2
    ) AS breach_rate_percent
FROM sla_measurements;
