# AI Development Log

This document discloses the use of AI-assisted development tools in the creation of the **fmri-bids-recon** analysis pipeline, in accordance with emerging best practices for transparency in scientific software development.

---

## 1. Purpose

This document provides a structured disclosure of AI tool usage during the development of the fmri-bids-recon pipeline. The disclosure follows the AI Disclosure (AID) Framework (Weaver, 2025) and adheres to recommendations for responsible AI use in scientific computing (Bridgeford et al., 2025; Nussberger et al., 2024; Jamieson et al., 2024). The intent is to ensure that reviewers, collaborators, and end users can assess the nature and extent of AI involvement in the development process.

## 2. Scope

AI assistance was utilized for **DICOM-to-BIDS reconstruction pipeline development**, encompassing:

- Code architecture and design (pipeline staging model, guard system, geometry-primary fieldmap association)
- Statistical methodology review and validation (geometry tolerance calibration, volume-count enforcement, acquisition-signature drift detection)
- Implementation of pipeline modules (7 pipeline stages, 14 integrity guards, configuration loading, task registry persistence)
- Test suite development and validation (423 tests covering unit, integration, edge-case, and guard-coverage scenarios)
- Documentation authoring and refinement

AI was **not** used for:

- Running the pipeline against real imaging data
- Interpreting scientific results from pipeline outputs
- Making domain-specific methodological decisions (e.g., selection of fieldmap association strategy, guard severity classifications, or study-specific analytical choices)

The fmri-bids-recon pipeline is a preprocessing tool that converts raw DICOM acquisitions into BIDS-compliant datasets. All methodological decisions governing the pipeline's behavior (guard thresholds, classification rules, geometry tolerances, and the faithful-reconstruction philosophy) were made by the researcher. The pipeline's application to real imaging data and the interpretation of its outputs are entirely human-directed activities outside the scope of AI assistance.

## 3. Tools Used

Development utilized **Claude Code** (Anthropic), employing two model tiers:

| Model | Use Case | Tasks |
|-------|----------|-------|
| Claude Opus 4 | Analytical and review | Critical review of statistical methods, brainstorming sessions, code quality audits, risk assessment, and architectural decisions |
| Claude Sonnet 4 | Implementation | Code generation, test implementation, documentation drafting, and file management |

This dual-model approach ensured that analytical depth (Opus) was applied to decisions with statistical or methodological consequences, while implementation efficiency (Sonnet) was used for well-specified coding tasks under explicit human direction.

## 4. Development Workflow

The pipeline was developed through an iterative, mode-based workflow with the following stages:

1. **Brainstorm** -- Structured discussion of design decisions, trade-offs, and alternative approaches. Sessions covered: pipeline architecture (staging model, atomic writes, resumability), fieldmap association strategy (geometry-primary vs. temporal-primary), guard system design (blocking vs. advisory severity), and the faithful-reconstruction philosophy. Every brainstorm session produced a report with explicit decision records (accepted, rejected, deferred).

2. **Critical Review (CR)** -- Formal review of the codebase for statistical correctness, robustness, reproducibility, and defensive coding practices. Findings included: geometry tolerance calibration against empirical within-block and nearest-block deltas, sidecar field handling edge cases, and guard coverage completeness. Each finding was classified by severity (P0/P1/P2) and required explicit human triage (accept, reject, or modify).

3. **Implement (Plan + Build)** -- Implementation proceeded in two sub-phases: (a) a technical specification mapping each approved change to specific code modifications with risk assessment, and (b) execution of the specification. All plans required human approval before code generation began.

4. **Test** -- Comprehensive test suite development covering unit tests for all public functions, integration tests for pipeline stage wiring (AST-based call-site binding verification), edge-case tests (empty inputs, boundary values, type mismatches), and guard-coverage tests (structural verification that every named guard has both a raise site in the engine and a test that drives it to violation). Tests were designed prior to implementation where feasible (test-first methodology).

5. **Clean** -- Code quality review for consistency, style, and maintainability.

6. **Document** -- Authoring and updating of user-facing documentation (README, RUNBOOK, INPUT_SPECIFICATION) and machine-readable technical specifications.

Key properties of this workflow:

- All decisions required **explicit human approval** before implementation.
- The pipeline was developed with a **test-first** approach.
- Every statistical and algorithmic choice was subjected to **formal critical review**, with findings documented and triaged individually.

## 5. Human Oversight

The researcher maintained full oversight and decision authority throughout the development process:

- **(a)** Defined all statistical methodology and analytical approach, including the geometry-primary fieldmap association strategy, the five-criterion geometry check, tolerance values calibrated against empirical DICOM data, and the faithful-reconstruction philosophy (no information filtering; de-identification is downstream).

- **(b)** Triaged every critical review finding with explicit accept/reject/modify decisions, documented in brainstorm reports with rationale for each determination. This included the decision to use 14 blocking integrity guards rather than advisory warnings, and the calibration of geometry tolerances against measured within-block and nearest-block position deltas.

- **(c)** Approved all implementation plans (technical specifications) before any code generation was executed. This included the recent package rename from bids-recon to fmri-bids-recon, the creation of pyproject.toml for pip-installable distribution, and the transition from PYTHONPATH invocation to console entry points.

- **(d)** Validated all test results and ensured test coverage aligned with the integrity guarantees required by the pipeline. The 423-test suite was reviewed for assertion strength (no weakened postconditions) and guard-coverage completeness (structural verification via source-file scanning).

- **(e)** Made all domain-specific decisions regarding pipeline architecture, algorithmic choices, and analytical strategy, including: the staging-then-commit execution model, the BIDS derivatives directory naming convention, the exit-code taxonomy, and the scope of each integrity guard.

## 6. Audit Trail

A complete record of the structured development process is available in the `.aid/reports/` directory within this repository. The audit trail includes:

- **Brainstorm reports** -- Records of design discussions, decision rationale, and trade-off analyses.
- **Critical review reports** -- Formal findings with severity classifications and human triage decisions.
- **Implementation plans** -- Technical specifications mapping approved changes to code modifications.
- **Implementation build reports** -- Records of executed changes with deviation notes.
- **Test reports** -- Test suite results and coverage summaries.
- **Code quality reviews** -- Clean-pass reports on style and consistency.
- **Documentation reports** -- Records of documentation updates and revisions.

The project-level configuration file used to guide AI interactions is preserved as `.aid/project_claude.md`.

Raw session transcripts are excluded for privacy reasons. The structured reports above capture all substantive technical decisions, rationale, and implementation details.

## 7. References

- Bridgeford, E. W., et al. (2025). Ten simple rules for AI-assisted coding in science. *arXiv preprint*, arXiv:2510.22254.

- Jamieson, A. J., et al. (2024). Protecting scientific integrity in an age of generative AI. *Proceedings of the National Academy of Sciences*, 121(41), e2407886121.

- Nussberger, A.-M., et al. (2024). Ten simple rules for using large language models in science. *PLOS Computational Biology*, 20(7), e1012291.

- Weaver, J. B. (2025). The AI Disclosure (AID) Framework. *arXiv preprint*, arXiv:2408.01904v2.

## Version History

| Date | Version | Summary |
|------|---------|---------|
| 2026-07-22 | 1.0.0 | Initial publication. Pipeline development complete (7 stages, 14 integrity guards, 409 tests). Package renamed to fmri-bids-recon with pip-installable distribution via pyproject.toml. Documentation suite: README, RUNBOOK, INPUT_SPECIFICATION. AID audit trail: 42 development reports covering brainstorm, critical review, implementation, testing, and documentation phases. |
| 2026-07-22 | 1.1.0 | Configuration ergonomics: renamed dicom_pattern to dicom_template with descriptive {subject}/{session} placeholders; added file-based subject roster input as alternative to inline YAML lists; updated documentation and example config. Test suite expanded from 409 to 418 tests. AID audit trail: 47 development reports. |
| 2026-07-24 | 1.2.0 | Deface bug fix: added `deface: bool` config toggle (default false) to make defacing opt-in; added `assert_deface_tools()` startup pre-flight check that verifies `pydeface` and FSL `flirt` are on PATH before any DICOM processing begins when `deface: true`; removed soft-degradation FileNotFoundError handler in favor of hard enforcement (both FileNotFoundError and CalledProcessError propagate); gated Phase 5 on `config.deface`; documented FSL as a conditional runtime dependency. Test suite expanded from 418 to 423 tests. AID audit trail: 52 development reports. |
