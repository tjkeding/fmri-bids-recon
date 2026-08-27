<brainstorm_report>
  <meta project="bids-recon" mode="brainstorm" timestamp="2026-08-13T16:06:53Z" />
  <context_files>
    <file path="TODO_fmri-bids-recon_20260812_132545.md" relevance="Orchestrator-generated harmonization TODO; source of all 7 discussion topics" />
    <file path="fmri_bids_recon/__main__.py" relevance="CLI entry point, exit codes, logging setup, pipeline orchestration; refactoring target for T5/T2/T3" />
    <file path="fmri_bids_recon/config.py" relevance="StudyConfig dataclass, load_config(), save_registry(); refactoring target for T4" />
    <file path="fmri_bids_recon/versions.py" relevance="Current dcm2niix floor-check; replaced by ToolSuiteRegistry in T1" />
    <file path="fmri_bids_recon/errors.py" relevance="Exception hierarchy including ReviewFlag (retired in T3) and VersionFloorError (replaced in T1)" />
    <file path="pyproject.toml" relevance="Package metadata, dependencies, requires-python; target for T6 pytest markers" />
    <file path="/Volumes/Backup Plus/Yale Research Faculty/projects/fmri-preproc/fmri_preproc/preproc_utils.py" relevance="Established graded_warning() function and severity taxonomy adopted in T3" />
    <file path="/Volumes/Backup Plus/Yale Research Faculty/projects/fmri-preproc/fmri_preproc/integrity.py" relevance="SEVERITY_WARN/SEVERITY_CRITICAL constants and severity-by-code pattern adopted in T3" />
  </context_files>
  <topics>
    <topic id="T5" title="Python API (load_and_validate + run + BidsReconResult)">
      <summary>Restructure __main__.py from a monolithic CLI handler into a programmatic API with two public functions: load_and_validate() for config loading with optional subject filtering, and run() for pipeline execution returning a typed BidsReconResult. CLI main() becomes a thin wrapper.</summary>
      <research>No external research required. Design informed by the orchestrator's cross-reference contract (subprocess invocation via conda run, --config and --subject arguments) and the current codebase structure.</research>
      <approaches>
        <approach id="A1" label="Approved design" feasibility="high" risk="low">
          <description>
            Two public functions:
            - load_and_validate(config_path: str | Path, *, subject: str | None = None) -> StudyConfig
            - run(config: StudyConfig) -> BidsReconResult

            BidsReconResult dataclass:
            - status: str ("success" | "warning" | "error")
            - manifest_path: Path
            - warnings: list[dict] (graded_warning output dicts)
            - participants_processed: list[str]
            - bids_validation_errors: int
            - bids_validation_warnings: int
            - tool_report: ToolReport (from T1)

            Design decisions:
            - exit_code dropped from BidsReconResult (redundant with exception handling; main() maps exceptions to exit codes)
            - Explicit subject: str | None parameter instead of **overrides (type-safe, matches the orchestrator's single-subject-per-invocation pattern)
            - CLI accepts both positional CONFIG (backward compat) and --config (orchestrator contract), plus new --subject
            - Preflight (tool version checking from T1) is internal to run()
            - run() does NOT call logging setup; that is the caller's responsibility
          </description>
          <pros>Clean separation of concerns; type-safe API; backward-compatible CLI; orchestrator can call programmatically or via subprocess</pros>
          <cons>Dual-form CLI adds parser complexity (minor)</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Approved by user. Explicit subject parameter over **overrides; exit_code excluded from result; preflight internal to run(); logging setup stays in main().</decision>
    </topic>

    <topic id="T4" title="Config Schema Versioning + 3-Stage Pipeline">
      <summary>Add schema_version field to StudyConfig and refactor the monolithic load_config() into three private stages (load raw YAML, validate, resolve to typed dataclass) with load_and_validate() as the sole public entry point.</summary>
      <research>No external research required. Design follows additive-growth policy already established by physio and deface field additions.</research>
      <approaches>
        <approach id="A1" label="Approved design" feasibility="high" risk="low">
          <description>
            schema_version: str field on StudyConfig, defaulting to "1.0.0" when absent from YAML. Absent-version configs load silently (additive-growth policy); orchestrator treats absent-version as oldest schema.

            Three private stages:
            - _load_raw(path: Path) -> dict: read YAML, return raw dict
            - _validate_raw(raw: dict) -> dict: schema validation, type checks, required field enforcement
            - _resolve_config(validated: dict, *, subject: str | None = None) -> StudyConfig: construct dataclass, resolve paths, expand participants, apply subject filter

            load_and_validate() is the sole public entry point, calling all three stages. Intermediate stages are private (underscore-prefixed), preserving the option to promote them later as a non-breaking change.
          </description>
          <pros>Testability (stages testable independently); clean public API; no commitment to intermediate-stage contracts</pros>
          <cons>Intermediate stages not directly accessible to external consumers (acceptable since no consumer needs them)</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Approved by user. schema_version defaults to "1.0.0" when absent. Three private stages; load_and_validate() is public. Subject filter lives in _resolve_config().</decision>
    </topic>

    <topic id="T2" title="Exit Code Alignment">
      <summary>Audit exit code semantics against the orchestrator's 5-code contract. Current mapping is already correct: the one apparent mismatch (code 3 for BIDS validation errors) aligns with the contract's "completed with warnings" semantics because BIDS validation is a post-hoc conformance check, not a data integrity check.</summary>
      <research>No external research required. Analysis based on the current __main__.py exit code mapping and the orchestrator's contract specification.</research>
      <approaches>
        <approach id="A1" label="Option A: Current mapping is correct (approved)" feasibility="high" risk="low">
          <description>
            Current exit code mapping already matches the contract:
            - 0 = Success (proceed)
            - 1 = GuardError (pipeline invariant violation; stop, do not retry)
            - 2 = ConfigError, BidsReconError, generic Exception (config/input validation; stop, user must fix)
            - 3 = BIDS validation errors found (completed with warnings; proceed, flag for QC)
            - 4 = ToolUnavailableError (external tool unavailable; stop, environment issue)

            Code 3 rationale: the pipeline's 14-guard system is the authoritative correctness check. BIDS validation is a downstream conformance check. The manifest tracks "assembled" vs "validated" status, and BidsReconResult provides granular validation counts (bids_validation_errors, bids_validation_warnings) so the orchestrator can make its own proceed/halt decision.

            sys.exit() is already confined to main() (all 11 call sites). No changes needed.
          </description>
          <pros>No code changes required; existing semantics are defensible; BidsReconResult gives orchestrator full decision authority</pros>
          <cons>Generic BidsReconError and unhandled Exception both map to code 2, which overloads that code; flagged as a future cross-module alignment item</cons>
        </approach>
        <approach id="A2" label="Option B: BIDS errors to code 1" feasibility="high" risk="medium">
          <description>Move BIDS validation errors to exit code 1 (invariant violation). More conservative but potentially too aggressive for spec-level issues.</description>
          <pros>Stricter quality gate</pros>
          <cons>BIDS "errors" include spec-level alternatives (e.g., B0FieldSource vs IntendedFor) that are valid but flagged by some validators; would cause unnecessary pipeline halts</cons>
        </approach>
        <approach id="A3" label="Option C: Split errors/warnings" feasibility="high" risk="medium">
          <description>BIDS validation errors to code 1, BIDS validation warnings to code 3. Most precise but most disruptive.</description>
          <pros>Finest-grained mapping</pros>
          <cons>Any BIDS error halts the orchestrator, which is disruptive for benign spec-level issues</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Approved by user. Current exit code mapping is correct. No code changes needed beyond documenting the mapping. BidsReconResult provides granular validation counts for orchestrator decision-making.</decision>
    </topic>

    <topic id="T1" title="Software Version Verification (Class A/B Pins + ToolSuiteRegistry)">
      <summary>Replace the current dcm2niix floor-check with a tools.lock.yaml lockfile and ToolSuiteRegistry pattern supporting Class A (exact match) and Class B (minimum floor) pin semantics, with standalone fallback behavior.</summary>
      <research>No external research required. Design informed by the orchestrator's cross-environment alignment contract and the current versions.py implementation.</research>
      <approaches>
        <approach id="A1" label="Approved design" feasibility="high" risk="low">
          <description>
            tools.lock.yaml at project root:
            - dcm2niix: Class A (exact match). Rationale: output format changes between versions affect downstream processing.
            - pydeface (when config.deface: true): Class B (minimum floor). Stable API, optional dependency.
            - flirt/FSL (when config.deface: true): Class A (declarative only). The FSL version is session-global (module load); bids-recon cannot independently control it. Lockfile entry serves as a declaration ("tested with FSL X.X.X"). Mismatch produces a warning, not an error.

            Standalone vs orchestrator behavior:
            - Standalone (default): Class A mismatches produce a warning, falling back to floor-check behavior. Preserves usability on HPC clusters where sysadmins update tools independently.
            - Under orchestrator (--strict-versions flag or environment variable): Class A mismatches raise ToolVersionError. The orchestrator's master lockfile is the system-level authority.

            Implementation:
            - preflight_tool_environments(config: StudyConfig) -> ToolReport function
            - ToolReport dataclass with per-tool ToolStatus entries (name, pinned_version, found_version, pin_class, status, message)
            - Called from run() before any processing
            - tool_report included in BidsReconResult
            - versions.py retired; VersionFloorError replaced by ToolVersionError
            - assert_deface_tools() in deface.py absorbed into the registry
          </description>
          <pros>Unified tool-checking; orchestrator gets exact-match control; standalone usability preserved; declarative FSL entry avoids false errors</pros>
          <cons>Two behavioral modes (strict vs lenient) add conditional logic</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Approved by user. Class A for dcm2niix with standalone fallback. Class B for pydeface. FSL declarative (warning only). preflight_tool_environments() internal to run(). ToolReport in BidsReconResult.</decision>
    </topic>

    <topic id="T3" title="Logging Harmonization">
      <summary>Adopt the fmri-preproc graded_warning() function and "warn"/"strong" severity taxonomy. Replace ReviewFlag with plain dicts. Add setup_logging() factory and --log-file CLI argument.</summary>
      <research>Read fmri-preproc source (preproc_utils.py:graded_warning, integrity.py:SEVERITY_WARN/SEVERITY_CRITICAL) to adopt the established severity taxonomy rather than inventing a new one.</research>
      <approaches>
        <approach id="A1" label="Approved design" feasibility="high" risk="medium">
          <description>
            3.1 Logging factory:
            - _setup_logging(log_file: Path | None = None) private function in __main__.py
            - Console handler: StreamHandler(sys.stderr) at INFO
            - File handler (when --log-file provided): FileHandler at DEBUG
            - Format: %(asctime)s [%(levelname)s] %(name)s: %(message)s
            - Date format: %Y-%m-%dT%H:%M:%S (already matches)
            - Idempotent (check for existing handlers before adding)
            - run() does NOT call this; main() calls it before run()

            3.2 CLI argument:
            - --log-file PATH added to _build_parser()
            - Passed to _setup_logging()

            3.3 ReviewFlag migration:
            - Adopt graded_warning() verbatim from fmri-preproc:
              graded_warning(logger, severity, code, message, *, user_facing=False) -> dict
            - Severity taxonomy: SEVERITY_WARN = "warn", SEVERITY_CRITICAL = "strong"
            - Log line format: [severity:code] message
            - Log level controlled by user_facing (True -> WARNING, False -> INFO), NOT by severity
            - Returns {"severity": ..., "code": ..., "message": ...}

            Warning code assignments:
            - UNCLASSIFIED_SERIES (classify.py:325): warn
            - NAVIGATOR_CANDIDATE (classify.py:349): warn
            - AMBIGUOUS_CLASSIFICATION (classify.py:374): warn
            - VOLUME_COUNT_MISMATCH (runs.py:119): warn
            - VOLUME_COUNT_DRIFT (runs.py:177): warn
            - PATIENT_ID_WARNING (assemble.py:380): strong

            Migration impact:
            - ReviewFlag class in errors.py: retired
            - json_intermediate.py: custom ReviewFlag serializer replaced by plain dict pass-through
            - report.py: updated to consume list[dict] instead of list[ReviewFlag]
            - BidsReconResult.warnings: list[dict]
          </description>
          <pros>Cross-module consistency with fmri-preproc; plain dicts simplify serialization; greppable log format</pros>
          <cons>6 files, ~10 call sites to migrate; ReviewFlag retirement touches the serialization layer</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Approved by user. Adopt fmri-preproc graded_warning() and "warn"/"strong" severity taxonomy verbatim. PATIENT_ID_WARNING at "strong", all others at "warn". ReviewFlag retired.</decision>
    </topic>

    <topic id="T6" title="Test Taxonomy Markers">
      <summary>Add the 8-level pytest test taxonomy markers to pyproject.toml and apply them at function level across the existing test suite.</summary>
      <research>No external research required. Taxonomy defined by the orchestrator's harmonization contract.</research>
      <approaches>
        <approach id="A1" label="Approved design" feasibility="high" risk="low">
          <description>
            Add [tool.pytest.ini_options] to pyproject.toml with all 8 markers:
            - level0_unit: Pure-function unit tests
            - level1_internal_integration: Cross-function integration within a module
            - level2_tool_equivalence: Verify tool wrapper output matches known reference
            - level3_checkpoint: Checkpoint/resume round-trip (registered but empty; bids-recon has no checkpoint/resume)
            - level4_stage_integration: Single pipeline stage end-to-end
            - level5_adversarial: Edge cases, malformed input, boundary conditions
            - level6_cross_stage: Multi-stage integration
            - level7_pipeline: Full pipeline end-to-end

            Apply markers at function level (not file level) for precise selective test runs.

            File-level heuristic for implementation-time guidance:
            - test_config.py, test_labels.py, test_runs.py, test_sidecar.py, test_tsv.py, test_json_intermediate.py, test_manifest.py, test_report.py, test_sanitize_sys_path.py: primarily level0_unit
            - test_config_template_and_subjects_file.py: level0_unit, level1_internal_integration
            - test_versions.py, test_deface.py: level2_tool_equivalence
            - test_classify.py, test_convert.py, test_assemble.py, test_render.py, test_validate.py: level4_stage_integration
            - test_physio.py, test_map.py: level0_unit, level1_internal_integration
            - test_adversary_matrix.py: level5_adversarial
            - test_guard_coverage.py: level6_cross_stage
            - test_cli_integration.py: level7_pipeline
          </description>
          <pros>Enables selective CI runs; taxonomy-complete registration; function-level precision</pros>
          <cons>~374 individual marker decisions at implementation time (one-time cost)</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Approved by user. All 8 markers registered. Function-level assignment. Level 3 empty. Per-function mapping at implementation time using file-level heuristic as guide.</decision>
    </topic>

    <topic id="T7" title="Python Version Floor (Verification Only)">
      <summary>requires-python = ">=3.12" in pyproject.toml already satisfies the orchestrator contract. No changes needed.</summary>
      <research>None required. Direct verification of pyproject.toml.</research>
      <approaches>
        <approach id="A1" label="Already compliant" feasibility="high" risk="low">
          <description>pyproject.toml line 9: requires-python = ">=3.12". Verified correct.</description>
          <pros>No work required</pros>
          <cons>None</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Verified. No changes needed.</decision>
    </topic>
  </topics>
  <action_items>
    <item priority="P0" target_mode="implement" description="Python API: extract load_and_validate() and run() from main(); create BidsReconResult dataclass; refactor main() to thin CLI wrapper with --config, --subject, and --log-file arguments (T5, T4, T3.1, T3.2)" />
    <item priority="P0" target_mode="implement" description="Config 3-stage pipeline: refactor load_config() into _load_raw(), _validate_raw(), _resolve_config(); add schema_version field to StudyConfig (T4)" />
    <item priority="P0" target_mode="implement" description="Version verification: create tools.lock.yaml, implement preflight_tool_environments() with ToolReport/ToolStatus dataclasses, retire versions.py, absorb assert_deface_tools(), add --strict-versions flag (T1)" />
    <item priority="P0" target_mode="implement" description="Logging harmonization: implement graded_warning() with warn/strong severity, migrate 6 ReviewFlag sites (10 instantiations), retire ReviewFlag class, simplify json_intermediate.py serialization (T3.3)" />
    <item priority="P0" target_mode="implement" description="Exit code documentation: document the 5-code contract mapping in __main__.py and/or a dedicated section of the codebase docs (T2)" />
    <item priority="P1" target_mode="test" description="Test taxonomy: add [tool.pytest.ini_options] markers to pyproject.toml, assign function-level markers across all ~374 test functions (T6)" />
    <item priority="P1" target_mode="test" description="Test coverage for new API: unit tests for load_and_validate(), run(), BidsReconResult, preflight_tool_environments(), graded_warning(), config 3-stage pipeline" />
  </action_items>
  <next_steps>The recommended downstream mode is /implement (plan phase first). The action items have natural dependency ordering: T4 (config refactoring) and T3 (logging/graded_warning) are prerequisites for T5 (Python API), since run() returns BidsReconResult containing warnings (graded_warning dicts) and tool_report. T1 (version verification) is independent of T4/T3 and can be built in parallel or sequentially. T2 (exit codes) requires no code changes, only documentation. T6 (test taxonomy) is independent and can be done after or in parallel with the main implementation. A single /implement plan should sequence the builds to respect these dependencies.</next_steps>
</brainstorm_report>
