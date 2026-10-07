# NEXORA-8: Proof-Carrying AI Software Engineering Agent

An AI software engineering agent that reads an existing Python codebase, fixes bugs or adds small features, and verifies that the changes do not introduce regressions by comparing test results before and after the modification.

Built for **HackNex 2026 (Internal Qualifier)** under **Problem Statement HNX26PSI09: AI Software Engineering Agent**, Division of Computer Science and Engineering, Karunya Institute of Technology and Sciences.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Project Overview](#2-project-overview)
3. [Objectives](#3-objectives)
4. [Proposed Solution](#4-proposed-solution)
5. [Key Features](#5-key-features)
6. [System Architecture](#6-system-architecture)
7. [System Workflow](#7-system-workflow)
8. [Technology Stack](#8-technology-stack)
9. [AI/ML Methodology](#9-aiml-methodology)
10. [Dataset](#10-dataset)
11. [Project Structure](#11-project-structure)
12. [Installation](#12-installation)
13. [Usage](#13-usage)
14. [Results and Evaluation](#14-results-and-evaluation)
15. [Expected Outcome](#15-expected-outcome)
16. [Future Scope](#16-future-scope)
17. [Team Members](#17-team-members)
18. [Project Status](#18-project-status)

---

## 1. Problem Statement

Real-world software repositories consist of thousands of lines of code distributed across backend and frontend modules, databases, APIs, tests, configuration files, and documentation. Making changes safely requires developers to understand the existing codebase, identify the correct files and functions, implement the requested modification, and verify that previously working functionality has not been affected.

Most AI-based coding tools focus on generating code or modifying existing code but do not provide sufficient evidence that the changes preserve existing functionality. AI-generated changes may introduce incorrect imports, undefined functions, invalid code, or unintended behavioural changes.

The problem is to develop an AI Software Engineering Agent that can understand an existing Python codebase, identify the relevant components, implement a requested bug fix or small feature, and verify the modification through automated testing without introducing regressions or hallucinated APIs.

---

## 2. Project Overview

NEXORA-8 is a command-line AI Software Engineering Agent designed to safely modify existing Python repositories.

The system accepts two primary inputs:

- A Python repository containing a pytest test suite
- A task description specifying a bug fix or feature request

The agent produces:

- A patched copy of the repository
- A before-and-after test comparison
- New tests covering the implemented change
- An evidence report containing the root cause, modified files, test results, retries, and generated diff

The original repository is never directly modified. All changes are performed inside an isolated sandbox environment.

---

## 3. Objectives

- Automatically understand an unseen Python codebase, including files, functions, classes, imports, and tests.
- Identify the appropriate files and functions for a requested modification.
- Perform small, targeted, and minimal code changes.
- Verify that all previously passing tests continue to pass after modification.
- Detect and block hallucinated imports, functions, and undefined names.
- Generate meaningful tests for newly implemented changes.
- Provide an evidence-based explanation of the identified problem and implemented solution.
- Safely roll back changes when the modification cannot be verified.

---

## 4. Proposed Solution

NEXORA-8 treats the Large Language Model as an untrusted component and places deterministic verification mechanisms around it.

The core principle is:

> **The LLM proposes; deterministic verification components approve.**

The system operates through the following stages:

1. A baseline test run records the exact state of the repository before modification.
2. A code analyzer creates a structural map of the repository and identifies files relevant to the requested task.
3. The LLM generates a plan containing the suspected root cause and target files.
4. The LLM generates small search-and-replace patches instead of rewriting entire files.
5. A hallucination guard validates syntax, undefined names, and import resolution.
6. The verifier executes the test suite and compares the results against the baseline.
7. If a regression is detected, the failure information is provided to the LLM for another attempt.
8. If the maximum retry limit is reached without successful verification, the system rolls back the changes.
9. New tests are generated and verified to fail before the fix and pass after the fix.
10. An evidence report containing the complete verification information is generated.

---

## 5. Key Features

| Feature | Description |
|---|---|
| Sandboxed Execution | Performs modifications on a temporary copy without changing the original repository. |
| Baseline Snapshot | Records the pass/fail state of the complete test suite before modification. |
| Code Mapping and Retrieval | Uses Python AST analysis to identify relevant files, classes, functions, and imports. |
| Minimal Patches | Uses targeted search-and-replace edits to keep changes small and reviewable. |
| Hallucination Guard | Detects invalid syntax, undefined names, and unresolved imports. |
| Regression Detection | Identifies tests that passed before modification but fail after the change. |
| Automatic Rollback | Restores the repository to the previous valid state when verification fails. |
| Test Generation | Generates and validates tests for the implemented modification. |
| Evidence Report | Provides root-cause analysis, code changes, test comparisons, retries, and generated tests. |

---

## 6. System Architecture

```mermaid
flowchart TD
    A["User: Repository Path + Task"] --> B["Sandbox: Copy Repository"]
    B --> C["Baseline Test Run"]
    B --> D["Code Analyzer: AST Map + Retrieval"]
    D --> E["Planner: LLM"]
    E --> F["Patcher: LLM"]
    F --> G["Hallucination Guard"]
    G -->|"Invalid"| F
    G -->|"Valid"| H["Verifier: Compare Tests"]
    C --> H
    H -->|"Regression"| F
    H -->|"Retries Exhausted"| R["Rollback"]
    H -->|"No Regression"| I["Test Generator: LLM"]
    I --> J["Evidence Report + Diff"]