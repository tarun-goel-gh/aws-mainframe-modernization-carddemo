# Invoice Generation — Requirements

## Global Preconditions

- All operations require valid input data and appropriate authorization.
- Processing constraints and scheduling dependencies are documented in the Job Dependencies section.

## 1. Billing Event Selection

As a billing operator, I want posted billing events selected for the current cycle so that only
settled activity reaches the invoice extract.

### Requirements

REQ-F-001: [Event-driven] When the invoice cycle job starts, the system shall read the billing event
file in ascending account order and select only events whose posted indicator is set.

REQ-F-002: [Unwanted] If a billing event carries a posted indicator that is neither set nor clear,
the system shall reject the event and write it to the exception report.

REQ-F-003: [State-driven] While the cycle-open flag is clear, the system shall not select any
billing event for invoicing.

## 2. Invoice Totalling

As a billing operator, I want per-account totals computed so that the invoice reflects the full
cycle.

### Requirements

REQ-F-004: [Ubiquitous] The system shall accumulate the net amount of every selected billing event
into the account invoice total.

REQ-F-005: [Unwanted] If the accumulated invoice total would exceed the invoice amount field
capacity, the system shall abort the cycle with a size-error condition rather than truncate.

REQ-F-006: [Optional] Where an account carries a credit adjustment, the system shall subtract the
adjustment before writing the invoice total.

REQ-N-001: [Ubiquitous] The system shall complete a full invoice cycle within the batch window
allotted to the billing schedule.

## Job Dependencies

- The invoice cycle runs after payment posting has completed for the same business date.
