# ITSM Data Warehouse Business Requirements

## Document purpose and status

This document describes the business needs and initial requirements for a
learning-project IT Service Management (ITSM) data warehouse. It is intended to
guide the conceptual, logical, and physical data models and later implementation
work.

The project uses only synthetic data representing the ITSM operations of a
fictional company. No real company, employee, customer, incident, or client
information is to be used. The initial SQLite schema, synthetic CSV datasets,
Python data validator and loader, and four SQL analytics queries have been
implemented. Dimensional modelling and other enhancements remain planned; this
document records current scope and outstanding requirements.

Rules labelled **Proposed business rule** are initial recommendations for
discussion. Items labelled **Open question** require a decision before the
affected model or calculation is finalized. A later implementation choice,
such as a table layout or SQLite data type, is not automatically a business
rule.

## 1. Business Problem

Operational ticket systems are designed primarily to record and manage current
work. Their records may change as incidents are reassigned, priorities are
updated, or tickets are resolved. Different records may also use different
definitions for elapsed time, SLA eligibility, or change success.

Relying only on operational ticket records can therefore make historical
analysis difficult. It may be hard to answer consistently how many incidents
occurred in a period, how quickly they were resolved, whether applicable service
targets were met, or which services and assignment groups were involved.
Information about incidents, service targets, configuration items, groups, and
changes may also be stored separately.

A structured warehouse can bring selected records together under documented
definitions, preserve useful historical context, and support repeatable
reporting. For this learning project, the warehouse will demonstrate these
ideas on a deliberately small, synthetic dataset rather than represent a
production ITSM platform.

## 2. Business Objectives

The proposed warehouse should:

1. Organize synthetic ITSM data in a documented relational and dimensional
   model.
2. Support consistent analysis of incidents, SLA measurements, changes,
   configuration items (CIs), and assignment groups.
3. Make the definitions, populations, and formulas behind reported measures
   understandable and testable.
4. Support historical analysis, including monthly trends and, subject to
   design confirmation, changes in descriptive dimension attributes over time.
5. Identify missing, invalid, duplicate, or unmatched source information rather
   than silently treating it as valid.
6. Provide a small, reproducible learning implementation using Python, SQLite,
   and SQL that can run on Windows 11 with 8 GB of RAM.
7. Demonstrate documentation, data lineage, and automated validation suitable
   for an entry-level data modeller portfolio.

## 3. Stakeholders

The following are fictional stakeholder roles, not real people or
organizations:

| Stakeholder role | Interest in the warehouse |
| --- | --- |
| IT operations manager | Understand incident demand, priority mix, resolution performance, and operational trends. |
| Service delivery manager | Review service-level performance and compare SLA compliance across relevant groups, priorities, or services. |
| Incident manager | Understand incident volumes, open and resolved work, assignment patterns, and resolution times. |
| Change manager | Review change volumes and the rate of changes classified as failed. |
| Configuration manager | Understand which CIs are associated with incidents and changes and identify missing or unmatched CI references. |
| Data analyst | Answer business questions using consistent definitions and trace measures to their source information. |
| Data modeller / project owner | Define clear entities, relationships, history, and data-quality rules for the learning project. |

## 4. Business Questions

The completed warehouse should be able to answer the following questions,
subject to the agreed definitions and availability of source data:

1. How many incidents were reported in a selected date range or calendar month?
2. How many incidents remain unresolved, and how many were resolved in a
   selected period?
3. How are incidents distributed across the valid priority levels?
4. Which assignment groups received the most incidents during a selected
   period?
5. What is the SLA breach rate for incidents with an eligible, valid SLA
   measurement?
6. How does SLA compliance vary by priority, assignment group, or applicable
   SLA target?
7. What is the average elapsed resolution time for incidents resolved in a
   selected period?
8. Which CIs are associated with the largest number of incidents?
9. How many changes were raised, and how many were classified as failed, in
   each month?
10. What is the change failure rate for the agreed population of completed
    changes?
11. How do incident volumes, SLA breach rates, and average resolution times
    change from month to month?
12. Which incidents or changes have missing, invalid, or unmatched assignment
    group or CI references?
13. How many incidents have no eligible SLA measurement, and why are they
    excluded from SLA compliance calculations?

## 5. Scope

### 5.1 Included in the first version

- Synthetic data representing a fictional company's ITSM operations.
- Five synthetic source datasets are implemented under `data/raw/`: incidents,
  SLA measurements, changes, configuration items, and assignment groups.
- A relational model and SQLite schema are implemented; dimensional modelling
  and a star schema remain planned.
- Incident, SLA, change, CI, and assignment-group reporting within the limits of
  the available synthetic data.
- Basic data profiling and validation, including identifier, reference, and
  timestamp checks.
- Candidate KPIs defined in this document, once their business rules and
  populations are confirmed.
- Python, SQLite, and SQL are used for source validation, database loading, and
  analytics.
- Documentation of business definitions, data structures, lineage, and
  architecture as the project progresses.
- Automated tests for agreed data and calculation rules.

### 5.2 Explicitly out of scope for the first version

- Connection to a real ticketing platform or other production system.
- Use, collection, or processing of real personal, company, customer, employee,
  incident, or client data.
- Production-grade scheduling, orchestration, cloud hosting, or high-volume
  distributed processing.
- Real-time dashboards, alerting, or operational ticket updates.
- Financial, asset-cost, workforce, customer satisfaction, or problem-management
  analytics unless separately approved as future work.
- Predictive analytics, machine learning, or automated incident prioritization.
- A claim that the project meets production security, availability, or
  regulatory requirements.

## 6. Source Data

These synthetic source datasets are implemented as CSV files under `data/raw/`.
Their current columns and file layout are reflected in those files and the
physical model; some business semantics and data rules remain open questions.

| Dataset | Business purpose | Expected information |
| --- | --- | --- |
| `incidents` | Describe reported IT incidents and their lifecycle so incident volume, priority, ownership, and resolution can be analyzed. | A unique incident identifier; reported, updated, and, where applicable, resolved timestamps; priority; status; assignment-group reference; optional CI reference; and descriptive synthetic attributes needed for analysis. |
| `sla_records` | Record the SLA measurement or measurements associated with an incident, allowing eligible performance to be compared with the applicable target. | A record identifier or other agreed key; incident reference; SLA name or type; applicable target duration; measured elapsed duration; measurement status or outcome if available; and measurement-period timestamps or other context needed to interpret the measurement. |
| `changes` | Describe planned or completed changes to IT services or CIs and support analysis of change outcomes. | A unique change identifier; opened, planned, and completed timestamps as applicable; status; outcome or failure classification; optional CI reference; and other synthetic attributes needed to group changes. |
| `configuration_items` | Describe the fictional technology or service components that incidents and changes may affect. | A unique CI identifier; CI name; CI type or category, such as application, server, or database; lifecycle or status information; and any agreed descriptive attributes. |
| `assignment_groups` | Identify the fictional teams responsible for incident work and support group-level reporting. | A unique group identifier; group name; group type or service area if useful; and effective or lifecycle information if historical group changes are to be represented. |

## 7. Business Definitions

These definitions are proposed for the learning project and must be confirmed
where noted in the open questions.

| Term | Proposed definition |
| --- | --- |
| Incident | An unplanned interruption to, or reduction in the quality of, an IT service that is recorded for investigation and restoration. |
| Priority | A business classification indicating the relative urgency or impact of an incident. The set of valid values and their ordering must be agreed; the project should not assume a priority scale without documenting it. |
| Assignment group | A team responsible for handling an incident at a recorded point in its lifecycle. Whether the source represents only current ownership or ownership history is not yet decided. |
| Configuration item (CI) | A managed technology or service component, such as a fictional application, server, or database, that may be related to an incident or change. |
| SLA target | The applicable agreed maximum elapsed duration for a defined service-level measurement and eligible population. Targets may differ by incident or measurement context; identical targets must not be assumed for all incidents. |
| SLA breach | An eligible SLA measurement for which actual SLA elapsed time exceeds the applicable SLA target, subject to the agreed business rules. The boundary condition, clock rules, and treatment of incomplete measurements must be confirmed. |
| Resolution time | Elapsed time between the agreed incident start event and its valid resolution event. Whether this means calendar time or SLA/business time, and how pauses or reopenings affect it, must be confirmed. |
| Change request | A recorded proposal or authorization to modify an IT service, CI, or related environment. |
| Failed change | A change classified as failed according to an agreed outcome rule, for example an unsuccessful implementation or a change requiring rollback. The authoritative source field or classification must be confirmed. |

## 8. Business Rules

The rules below are initial proposals for discussion. They express business
expectations, not decisions about table names, keys, SQLite column types, or
other implementation details.

### 8.1 Proposed business rules

1. **Incident identifier:** Every incident must have a non-null identifier that
   is unique within the agreed source dataset and warehouse scope. Duplicate
   identifiers must be reported for investigation, not silently merged.
2. **Priority:** Each incident priority must map to a documented valid priority
   value. Unknown or blank values must be identified and not silently assigned
   a priority.
3. **Assignment-group reference:** A populated incident assignment-group
   reference should match a known assignment group. Missing and unmatched
   references must be distinguished in data-quality results. Whether a group is
   mandatory for every incident remains to be confirmed.
4. **CI reference:** A populated incident or change CI reference should match a
   known configuration item. A missing CI must not be treated as a failed
   reference; a populated but unmatched CI reference should be flagged.
5. **Timestamps:** Timestamps used for duration calculations must be parseable
   and comparable under one agreed timezone convention. A resolution timestamp
   must not precede the incident start timestamp. Invalid or contradictory
   timestamps must be reported and excluded from affected duration measures.
6. **Resolved incidents:** An incident counts as resolved only when it meets
   the agreed resolved-status and resolution-timestamp rules. An unresolved
   incident must not be included in resolved-incident counts or resolution-time
   averages.
7. **SLA measurements:** An SLA record must identify its incident and the
   applicable target and actual elapsed measurement, or an agreed reason why
   these are unavailable. Multiple SLA records per incident may be valid; the
   grain and rule for selecting or aggregating measurements must be agreed.
8. **SLA breach comparison:** For an eligible and complete SLA measurement,
   compare actual elapsed time with the applicable target. A breach is when
   actual elapsed time exceeds that target, subject to agreed boundary,
   pause, reset, and calendar rules. Do not apply a single assumed target to
   every incident.
9. **Failed changes:** A change counts as failed only when its outcome meets the
   approved failure classification. Open, cancelled, or otherwise ineligible
   changes must not be implicitly classified as successful or failed.
10. **Historical attributes:** If group or CI descriptions can change and
    historical reporting is required, reports should use the description valid
    for the relevant event date. Whether to maintain this history (including
    SCD Type 2) must be confirmed before model design.

### 8.2 Decisions requiring confirmation

The following are not established business rules yet:

- The allowed priority values, ordering, and handling of emergency or
  unassigned priority.
- Whether every incident must have an assignment group and whether group
  transfers are tracked historically.
- Whether an incident can be related to zero, one, or multiple CIs; likewise
  for a change.
- Whether the incident source contains one current row per incident or
  multiple lifecycle events or snapshots.
- The incident start event, statuses that count as resolved, and treatment of
  reopened incidents.
- The SLA measurement grain, eligibility criteria, applicable target source,
  and handling of multiple measurements.
- Whether SLA clocks use calendar time or business time, and the treatment of
  pauses, exclusions, resets, and exact equality to the target.
- The source-of-truth timezone and whether timestamps include offsets.
- The outcomes that qualify as failed, and the denominator population for
  change failure rate.
- Whether deleted, cancelled, duplicate, test, or invalid source records are
  excluded, retained with a quality status, or both.
- Whether historical group and CI attributes are needed and for which reporting
  dates.

## 9. KPIs

The following are candidate KPIs. Each formula depends on the relevant business
rules being confirmed. The project should publish the numerator, denominator,
and exclusions alongside each rate or average so that the result is
interpretable.

| KPI | Candidate formula | Population and handling |
| --- | --- | --- |
| Total incidents | Count of distinct valid incident identifiers. | Incidents reported in the selected reporting period, based on the agreed reporting date. Records with missing or duplicate identifiers are excluded from the distinct count and reported as data-quality exceptions. |
| Resolved incidents | Count of distinct incidents meeting the agreed resolved-status and valid-resolution-timestamp rules. | Incidents resolved in the selected period, based on the agreed resolution date. Open incidents and incidents without a valid resolution timestamp are not counted as resolved; exceptions should be reported. |
| SLA breach rate | Eligible SLA measurements classified as breached ÷ all eligible, complete SLA measurements × 100. | Use the agreed SLA measurement grain and period. Exclude ineligible or incomplete measurements from both numerator and denominator, and report their counts separately. Compare each measurement with its own applicable target. |
| Average resolution time | Sum of valid resolution durations ÷ count of incidents with a valid duration. | Incidents resolved in the selected period. Exclude unresolved incidents and records with missing, invalid, or contradictory start/resolution timestamps. State whether duration is calendar or business time once decided. |
| Change failure rate | Failed changes ÷ eligible completed changes × 100. | Use only the agreed completed-change population and failure definition. Exclude open, cancelled, or otherwise ineligible changes from both numerator and denominator; report excluded counts separately. |

### 9.1 Missing values and KPI eligibility

- A missing value is not automatically zero, success, failure, or compliance.
- A record that does not meet a KPI's eligibility rules is excluded from that
  KPI's numerator and denominator, but should remain visible in data-quality or
  eligibility reporting where practical.
- Invalid identifiers, priorities, timestamps, targets, or references must not
  be silently repaired with invented business values.
- A rate with a zero eligible denominator should be reported as not available
  (or an agreed equivalent), not as 0%.
- KPI reports should make the selected reporting period and date field clear.
- Rates and averages should expose their counts so small or empty populations
  are not misleading.

## 10. Functional Requirements

The completed system must satisfy these testable requirements:

| ID | Requirement |
| --- | --- |
| FR-01 | The system must accept the five agreed synthetic source datasets: incidents, SLA records, changes, configuration items, and assignment groups. |
| FR-02 | The system must validate required identifiers for presence and uniqueness according to the agreed source and warehouse scope, and report violations. |
| FR-03 | The system must validate incident priority values against a documented, agreed list and report unknown or missing values. |
| FR-04 | The system must check populated assignment-group and CI references against their corresponding synthetic datasets and distinguish missing from unmatched references. |
| FR-05 | The system must validate timestamp parsing and agreed chronological rules, and identify invalid records before duration KPIs are calculated. |
| FR-06 | The system must identify resolved incidents according to the approved status and timestamp rules and calculate resolution time only for eligible records. |
| FR-07 | The system must determine SLA breach status by comparing actual elapsed measurement with the applicable target for each eligible measurement, using the approved comparison and clock rules. |
| FR-08 | The system must support multiple SLA records per incident if that source grain is approved, without silently double-counting incidents in incident-level KPIs. |
| FR-09 | The system must classify failed changes using the approved change-outcome rule and calculate change failure rate using the approved denominator. |
| FR-10 | The system must calculate the approved candidate KPIs for a selected reporting period and expose the population counts and exclusions used. |
| FR-11 | The system must support monthly reporting for incident volume and the agreed SLA, resolution, and change measures. |
| FR-12 | The system must allow analysis by agreed dimensions such as priority, assignment group, CI, change outcome, and reporting month where source data supports them. |
| FR-13 | The system must produce understandable data-quality results for the validation rules, including enough detail to identify the affected synthetic records. |
| FR-14 | The system must provide documentation connecting business terms and KPIs to their source data and modeled representations. |
| FR-15 | The system must include automated tests for the agreed validation and KPI rules, including boundary cases such as a measurement equal to its target once that behavior is decided. |

## 11. Non-Functional Requirements

- **Data quality:** Validation rules must be documented, repeatable, and
  explicit about which records are accepted, rejected, flagged, or excluded
  from a measure.
- **Reproducibility:** Given the same synthetic input data and agreed rules,
  repeated runs should produce the same documented results. Any randomness in
  future synthetic data generation should be controllable and documented.
- **Documentation:** Business definitions, assumptions, KPI formulas, source
  fields, model decisions, and lineage should be written in clear language
  suitable for a beginner to explain.
- **Maintainability:** Use a simple, understandable structure and naming
  conventions. Keep business logic visible and testable, and avoid unnecessary
  dependencies or infrastructure.
- **Privacy:** Use only synthetic fictional data. Do not add real names,
  contact details, credentials, client records, or identifiable real incident
  descriptions.
- **Lightweight execution:** The first version should run locally on Windows 11
  with 8 GB RAM using Python, SQLite, and SQL, without requiring a server
  cluster or cloud platform.
- **Portability:** Instructions should make the project usable from its
  documented folder structure on a typical Windows development environment.
- **Transparency:** Reports should disclose relevant date filters, KPI
  populations, exclusions, and unresolved assumptions rather than hide them.

## 12. Assumptions and Open Questions

The following assumptions are provisional and must be confirmed before the
database schema and detailed model are designed:

1. **Reporting purpose:** Is the main reporting lens based on incident opened
   date, resolved date, SLA measurement date, or more than one date role?
2. **Incident grain:** Is there one source row per incident, or must the model
   represent status and assignment changes over time?
3. **Incident identity:** Are incident identifiers unique across the complete
   source history, or only within a source system or time period?
4. **Priority scale:** What are the valid values and ordering, and can priority
   change after an incident is opened?
5. **Resolution:** Which statuses count as resolved, what event starts the
   resolution clock, and how should reopened incidents be treated?
6. **Time convention:** Which timezone should timestamps use, and are values
   stored with an offset? Should elapsed time use calendar time or working
   schedules?
7. **Assignment history:** Is the current assignment group sufficient, or must
   the warehouse retain each group responsible during an incident's lifecycle?
8. **CI relationships:** Can an incident or change relate to multiple CIs? If
   so, how should that relationship be represented and counted?
9. **SLA grain and eligibility:** Is there one SLA measurement per incident,
   or can different SLA types, stages, or repeated measurements exist? Which
   incidents and measurements are eligible?
10. **SLA targets and clocks:** Where does the applicable target come from, can
    it vary by priority or service, how are pauses/exclusions/resets handled,
    and is a measurement exactly equal to its target compliant or breached?
11. **Change failure:** Which statuses are complete, which outcomes constitute
    failure, and should cancelled or backed-out changes be in the denominator?
12. **Monthly trends:** Should a monthly total use the date an item was opened,
    resolved, measured, or completed? Which date should each KPI use?
13. **Source quality:** How should duplicates, deleted records, test records,
    and missing reference records be handled: rejected, retained with a quality
    status, or both?
14. **History requirements:** Do assignment-group and CI names or attributes
    need historical versions for accurate past reporting, potentially using
    SCD Type 2?
15. **Synthetic data scale:** What small but useful record counts and date span
    should be used for demonstrations and tests?
16. **Implementation boundaries:** Should the first ETL load rebuild the
    warehouse from scratch, append new data, or support repeatable incremental
    loads? This is an implementation decision that affects design but is not
    itself a business definition.

These questions should be answered or explicitly deferred before the related
schema elements and KPI calculations are treated as finalized.
