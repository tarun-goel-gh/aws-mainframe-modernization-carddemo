# Payment Posting — Requirements

## Global Preconditions

- All operations require valid input data and appropriate authorization.

## 1. Payment Capture

As a service agent, I want a payment captured against an account so that the balance reflects it
immediately.

### Requirements

REQ-F-001: [Event-driven] When the agent submits a payment amount, the system shall validate that the
amount is numeric and greater than zero before posting.

REQ-F-002: [Unwanted] If the account is not found on the balance file, the system shall reject the
payment and display an account-not-found message without altering any record.

## 2. Balance Update

As a service agent, I want the posted payment reflected in the account balance so that the customer
sees the correct figure.

### Requirements

REQ-F-003: [Ubiquitous] The system shall subtract the posted payment amount from the account
outstanding balance.

REQ-F-004: [Unwanted] If the balance file record is held by another task, the system shall abandon
the update and report a contention condition rather than wait indefinitely.

## Job Dependencies

- Payment posting is online and has no batch predecessor.
