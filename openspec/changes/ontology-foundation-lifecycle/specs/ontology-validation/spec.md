## Purpose

Validate candidate business knowledge using evidence, calibrated evaluation and prioritized expert review while preserving corrections for future assessment.

## ADDED Requirements

### Requirement: Evidence-based relationship assessment
The system SHALL evaluate schema and type compatibility, key compatibility and value consistency, semantic similarity, value overlap, referential profiles, existing constraints, freshness and contradictory evidence. Each assessment SHALL expose signal availability, supporting evidence and scoring method version without treating missing signals as positive evidence.

#### Scenario: Contradictory values despite similar names
- **WHEN** similarly named fields have compatible types but contradictory key-value profiles
- **THEN** the assessment retains the contradiction and does not accept the mapping based on names alone

### Requirement: Calibrated risk-based acceptance
The system SHALL calibrate relationship scores against reviewed examples and retain evaluation dataset and calibration versions. Automatic acceptance SHALL require validated representative-case precision, an explicit low-risk policy and no blocking contradictions. Uncalibrated scores SHALL be labelled uncalibrated and SHALL NOT authorize automatic acceptance.

#### Scenario: No reviewed examples
- **WHEN** a candidate has strong heuristic evidence but lacks applicable calibration evidence
- **THEN** its calibrated score is unavailable and it remains subject to review

#### Scenario: High-impact candidate
- **WHEN** a candidate exceeds a score threshold but affects high-impact constraints or workflows
- **THEN** the applicable risk policy routes it to expert review

### Requirement: Expert review and labelled corrections
Authorized experts SHALL accept, reject, correct or merge mappings using current evidence. The system SHALL preserve original model output, evidence, expert changes, reviewer identity, reason and validation outcome as versioned evaluation data. Stale review submissions SHALL be rejected.

#### Scenario: Expert corrects a predicate
- **WHEN** an expert corrects a suggested business relationship using its current revision
- **THEN** both the immutable original suggestion and expert correction are retained and the resulting mapping is revalidated

#### Scenario: Evidence changed before review
- **WHEN** a reviewer submits a decision after supporting evidence changed
- **THEN** the decision fails with a conflict and the current evidence is returned for renewed review

### Requirement: Review prioritization and evaluation metrics
The review interface SHALL show candidate mappings, evidence, scores, conflicts and downstream dependencies, prioritizing uncertainty, impact, risk and dependency count. Metrics SHALL report unresolved mappings, reviewed precision, false positives, correction rates, drift and downstream failures with denominators and unavailable states.

#### Scenario: Prioritized work queue
- **WHEN** an uncertain candidate affects many workflows and another affects none
- **THEN** the queue exposes their impact evidence and prioritizes them according to its versioned policy

#### Scenario: Insufficient evaluation labels
- **WHEN** no reviewed outcomes exist for an assessment version
- **THEN** precision and false-positive metrics show unavailable rather than fabricated success rates
