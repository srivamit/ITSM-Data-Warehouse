-- Business question: How many incidents are assigned to each support group?
-- Use a LEFT JOIN so support groups with no incidents are included.
SELECT
    ag.group_name,
    COUNT(i.incident_key) AS incident_count
FROM assignment_groups AS ag
LEFT JOIN incidents AS i
    ON i.assignment_group_key = ag.assignment_group_key
GROUP BY
    ag.assignment_group_key,
    ag.group_name
ORDER BY
    incident_count DESC;
