<brainstorm_report>
  <meta project="bids-recon" mode="brainstorm" timestamp="2026-08-18T14:00:00Z" />
  <context_files>
    <file path="HARMONIZE_fmri-bids-recon_20260816_212459.md" relevance="Orchestrator-generated second-round harmonization report; source of all 6 discussion topics" />
    <file path="bids-recon_brainstorm_20260813_160653.md" relevance="Prior brainstorm (round 1 harmonization); locked decisions for the Python API, config pipeline, tool registry, and logging framework that this round refines" />
    <file path="fmri_bids_recon/warnings.py" relevance="Current graded_warning() implementation and SEVERITY_WARN/SEVERITY_CRITICAL constants; refactoring target for H2" />
    <file path="fmri_bids_recon/tool_registry.py" relevance="Current preflight_tool_environments() reading tools.lock.yaml; refactoring target for H1 and H5" />
    <file path="fmri_bids_recon/pipeline.py" relevance="BidsReconResult dataclass and run() function; refactoring target for H2 halt elevations and H4 output_dir" />
    <file path="fmri_bids_recon/__main__.py" relevance="Exit code mapping in main(); refactoring target for H2c and H3" />
    <file path="fmri_bids_recon/stage2_classify.py" relevance="3 graded_warning call sites (UNCLASSIFIED_SERIES, NAVIGATOR_CANDIDATE, AMBIGUOUS_CLASSIFICATION); severity reclassification target for H2b" />
    <file path="fmri_bids_recon/runs.py" relevance="2 graded_warning call sites (VOLUME_COUNT_MISMATCH, VOLUME_COUNT_DRIFT); VOLUME_COUNT_MISMATCH elevated to halt for H2" />
    <file path="fmri_bids_recon/stage4_assemble.py" relevance="UNPAIRED_FIELDMAP graded_warning call site (elevated to halt) and patient_id_warnings plain-string list (migrated to graded_warning + halt) for H2" />
    <file path="fmri_bids_recon/stage6_validate.py" relevance="ALL_GUARD_NAMES list; target for new guard registrations (fieldmap_pair_complete, patient_id_unique) for H2" />
    <file path="tools.lock.yaml" relevance="Current lockfile with schema_version/tools keys; refactoring target for H1 and H5" />
    <file path="pyproject.toml" relevance="Package metadata; target for H6a pytest marker registration" />
  </context_files>
  <topics>
    <topic id="H1" title="tools.lock.yaml Schema Alignment">
      <summary>Rename lockfile keys to match the cross-module schema used by fmri-preproc and fmri-first-level-proc: schema_version to lockfile_version, tools: to binaries:. Update tool_registry.py to read the new keys.</summary>
      <research>No external research required. Mechanical rename to match established cross-module convention.</research>
      <approaches>
        <approach id="A1" label="Direct rename (approved)" feasibility="high" risk="low">
          <description>
            1. tools.lock.yaml: rename schema_version to lockfile_version, rename tools: to binaries:. All per-tool structure (pin_class, version, binary, version_flag, conditional, enforcement) preserved unchanged.
            2. tool_registry.py:145: change lock_data.get("tools", {}) to lock_data.get("binaries", {}).
            3. No code change needed for the lockfile_version key itself (field loaded into dict but never accessed by name in current code).
            4. Downstream: 31 existing tests in test_tool_registry.py use inline YAML fixtures with the old keys; these will be updated during /test design phase.
          </description>
          <pros>Exact parity with sister modules; no behavioral change; mechanical</pros>
          <cons>Test fixture updates needed (handled in /test)</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Approved by user. Direct rename with no behavioral change.</decision>
    </topic>

    <topic id="H2" title="graded_warning Severity Vocabulary + Halt Elevations">
      <summary>Replace the warn/strong severity vocabulary with low/medium/high. Reclassify all call sites. Elevate three warnings (VOLUME_COUNT_MISMATCH, UNPAIRED_FIELDMAP, PATIENT_ID_WARNING) to halt conditions (GuardError). Migrate patient_id_warnings from plain strings to graded_warning(). Change exit code 3 gating to union of BIDS validation errors OR high-severity graded_warnings.</summary>
      <research>No external research required. All decisions are internal codebase semantics informed by the pipeline's guard architecture and the orchestrator's exit code contract.</research>
      <approaches>
        <approach id="A1" label="Approved design" feasibility="high" risk="medium">
          <description>
            H2a: Severity vocabulary replacement in warnings.py:
            - Remove SEVERITY_WARN = "warn" and SEVERITY_CRITICAL = "strong"
            - Add SEVERITY_LOW = "low", SEVERITY_MEDIUM = "medium", SEVERITY_HIGH = "high"

            H2b: Per-call-site reclassification and halt elevations:

            | Call Site | Code | New Severity | Halt? | Guard Name |
            |---|---|---|---|---|
            | stage2_classify.py:330 | UNCLASSIFIED_SERIES | low | No | n/a |
            | stage2_classify.py:350 | NAVIGATOR_CANDIDATE | low | No | n/a |
            | stage2_classify.py:370 | AMBIGUOUS_CLASSIFICATION | medium | No | n/a |
            | runs.py:123 | VOLUME_COUNT_MISMATCH | high | Yes | exact_volume_counts (existing) |
            | runs.py:182 | VOLUME_COUNT_DRIFT | high | No | n/a |
            | stage4_assemble.py:384 | UNPAIRED_FIELDMAP | high | Yes | fieldmap_pair_complete (new) |
            | stage4_assemble.py:527-538 | PATIENT_ID_WARNING | high | Yes | patient_id_unique (new) |

            For the three halt elevations:
            - VOLUME_COUNT_MISMATCH: change check_volume_counts() to raise GuardError instead of returning graded_warning(). Uses existing guard name exact_volume_counts in ALL_GUARD_NAMES.
            - UNPAIRED_FIELDMAP: add fieldmap_pair_complete to ALL_GUARD_NAMES. Raise GuardError when an unpaired fieldmap is detected instead of graded_warning().
            - PATIENT_ID_WARNING: migrate from plain list[str] on AssemblyResult to graded_warning() at SEVERITY_HIGH. Add patient_id_unique to ALL_GUARD_NAMES. Raise GuardError when multiple distinct PatientID values found in one session.

            H2c: Exit code 3 gating (Option C, union):
            ```python
            has_high_warnings = any(w['severity'] == 'high' for w in result.warnings)
            if result.status == "warning" or has_high_warnings:
                sys.exit(3)
            ```
            Both BIDS validation errors and high-severity graded_warnings trigger exit code 3. Preserves backward compatibility while adding severity-driven triggering.

            Note: the three halted conditions (VOLUME_COUNT_MISMATCH, UNPAIRED_FIELDMAP, PATIENT_ID_WARNING) will raise GuardError (exit code 1) before reaching the exit code 3 gate. The exit code 3 union gate catches the remaining high-severity warning (VOLUME_COUNT_DRIFT) and BIDS validation errors.
          </description>
          <pros>Unified severity taxonomy across modules; dangerous conditions halt immediately rather than risking unnoticed warnings; exit code 3 union preserves backward compatibility for BIDS validation errors while adding severity-driven triggering</pros>
          <cons>Three conditions that previously allowed the pipeline to continue now halt it; users must resolve these before processing can complete. This is the intended behavioral change per user decision.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Approved by user. Three-level vocabulary (low/medium/high). Three halt elevations (VOLUME_COUNT_MISMATCH, UNPAIRED_FIELDMAP, PATIENT_ID_WARNING). VOLUME_COUNT_DRIFT stays at high with no halt. Patient_id_warnings migrated to graded_warning(). Exit code 3 union (Option C).</decision>
    </topic>

    <topic id="H3" title="Exit Code 5 Reservation">
      <summary>Document exit code 5 (Model error, reserved, not raised by bids-recon) in the main() docstring. No code changes.</summary>
      <research>No external research required. Docstring-only change.</research>
      <approaches>
        <approach id="A1" label="Docstring update (approved)" feasibility="high" risk="low">
          <description>
            Add to __main__.py:main() docstring:
            5 = Model error (reserved; not raised by bids-recon)
          </description>
          <pros>Completes the 6-code contract documentation; no code change</pros>
          <cons>None</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Approved by user. Docstring-only addition.</decision>
    </topic>

    <topic id="H4" title="BidsReconResult output_dir Field">
      <summary>Add output_dir: Path field to BidsReconResult, set to bids_root / "derivatives" / "fmri-bids-recon" explicitly in pipeline.py:run().</summary>
      <research>No external research required. Field addition to match orchestrator contract.</research>
      <approaches>
        <approach id="A1" label="Explicit construction (approved)" feasibility="high" risk="low">
          <description>
            Add output_dir: Path field to BidsReconResult dataclass in pipeline.py.
            Set to bids_root / "derivatives" / "fmri-bids-recon" in the BidsReconResult construction at pipeline.py:314-322, using the bids_root variable already in scope at line 125.
            Explicit construction rather than manifest_path.parent derivation for self-documenting contract.
            status vocabulary ("success" / "warning") already matches the unified contract; no change needed.
          </description>
          <pros>Self-documenting; no coupling to manifest location; bids_root already in scope</pros>
          <cons>None</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Approved by user. Explicit construction from bids_root.</decision>
    </topic>

    <topic id="H5" title="Python Pin in tools.lock.yaml">
      <summary>Add python: "3.12.13" to tools.lock.yaml as a top-level key. Add runtime validation in preflight_tool_environments() using sys.version_info with Class B (floor) semantics.</summary>
      <research>No external research required. Version determined from runtime check (Python 3.12.13).</research>
      <approaches>
        <approach id="A1" label="Declarative pin with runtime floor check (approved)" feasibility="high" risk="low">
          <description>
            Lockfile addition:
            - python: "3.12.13" as top-level key in tools.lock.yaml (not under binaries:)

            Runtime validation in preflight_tool_environments():
            - Read python field from lockfile
            - Compare sys.version_info against pinned version using Class B (floor) semantics
            - No subprocess probe needed; uses sys.version_info directly
            - Report as ToolStatus entry in ToolReport.tools["python"]
            - Lenient mode: floor violation warns
            - Strict mode (--strict-versions): floor violation raises ToolVersionError (exit code 4)
            - Patch-level updates (3.12.13 to 3.12.14) pass; minor-version mismatches (3.11.x vs 3.12.x) fail

            Rationale for runtime check: external libraries and HPC module loads can reset Python paths, causing a different Python interpreter to run than the conda environment specifies. The _sanitize_sys_path() guard addresses import-path contamination but not interpreter-binary substitution.
          </description>
          <pros>Catches interpreter-binary substitution that _sanitize_sys_path() cannot; consistent reporting through ToolReport; no external probe needed</pros>
          <cons>Adds one special-case path in preflight_tool_environments() for a non-binary tool (minor complexity)</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Approved by user. Runtime Class B floor check via sys.version_info.</decision>
    </topic>

    <topic id="H6" title="Testing Marker Taxonomy">
      <summary>Register the 8-level pytest marker taxonomy in pyproject.toml. Defer per-function marker assignment to /test design phase.</summary>
      <research>No external research required. Taxonomy defined by the orchestrator's harmonization contract and locked in the prior brainstorm (2026-08-13, T6).</research>
      <approaches>
        <approach id="A1" label="Split registration and labeling (approved)" feasibility="high" risk="low">
          <description>
            H6a (in /implement build, alongside H1-H5):
            Add [tool.pytest.ini_options] to pyproject.toml with all 8 markers:
            - level0_unit: Pure-function unit tests
            - level1_internal_integration: Cross-function integration within a module
            - level2_tool_equivalence: Verify tool wrapper output matches known reference
            - level3_checkpoint: Checkpoint/resume round-trip
            - level4_stage_integration: Single pipeline stage end-to-end
            - level5_adversarial: Edge cases, malformed input, boundary conditions
            - level6_cross_stage: Multi-stage integration
            - level7_pipeline: Full pipeline end-to-end

            H6b (deferred to /test design phase):
            Per-function marker assignment across the full test suite. Deferred because the test suite will be in flux during /implement (new tests for H2 severity changes, halt elevations, H4 output_dir, H5 Python check, H1 fixture updates). Labeling is most efficient after the suite stabilizes.
          </description>
          <pros>Registration is trivial and belongs with the code changes; labeling benefits from a stable test suite; clean separation of concerns</pros>
          <cons>Markers registered but not yet applied until /test (pytest will emit "unknown marker" warnings in the interim, suppressed by the ini_options registration)</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Approved by user. Split: 6.1 in /implement, 6.2 in /test.</decision>
    </topic>
  </topics>
  <action_items>
    <item priority="P0" target_mode="implement" description="H1: Rename tools.lock.yaml keys (schema_version to lockfile_version, tools: to binaries:). Update tool_registry.py:145 to read binaries: instead of tools:." />
    <item priority="P0" target_mode="implement" description="H2a: Replace severity constants in warnings.py (SEVERITY_WARN/SEVERITY_CRITICAL removed; SEVERITY_LOW/SEVERITY_MEDIUM/SEVERITY_HIGH added). Update all 6 existing graded_warning() call sites with new severity assignments (UNCLASSIFIED_SERIES=low, NAVIGATOR_CANDIDATE=low, AMBIGUOUS_CLASSIFICATION=medium, VOLUME_COUNT_MISMATCH=high, VOLUME_COUNT_DRIFT=high, UNPAIRED_FIELDMAP=high)." />
    <item priority="P0" target_mode="implement" description="H2b halt elevations: Convert VOLUME_COUNT_MISMATCH (runs.py) to raise GuardError (existing guard exact_volume_counts). Convert UNPAIRED_FIELDMAP (stage4_assemble.py) to raise GuardError (new guard fieldmap_pair_complete in ALL_GUARD_NAMES). Migrate patient_id_warnings (stage4_assemble.py) from plain list[str] to graded_warning() at SEVERITY_HIGH, then raise GuardError (new guard patient_id_unique in ALL_GUARD_NAMES)." />
    <item priority="P0" target_mode="implement" description="H2c: Update exit code 3 gating in __main__.py to union: trigger on result.status == 'warning' OR any(w['severity'] == 'high' for w in result.warnings)." />
    <item priority="P0" target_mode="implement" description="H3: Add exit code 5 reservation to main() docstring: '5 = Model error (reserved; not raised by bids-recon)'." />
    <item priority="P0" target_mode="implement" description="H4: Add output_dir: Path field to BidsReconResult. Set to bids_root / 'derivatives' / 'fmri-bids-recon' in pipeline.py:run()." />
    <item priority="P0" target_mode="implement" description="H5: Add python: '3.12.13' to tools.lock.yaml. Add runtime Class B floor check in preflight_tool_environments() using sys.version_info, reporting as ToolReport.tools['python']." />
    <item priority="P0" target_mode="implement" description="H6a: Add [tool.pytest.ini_options] to pyproject.toml with the 8-level marker taxonomy." />
    <item priority="P1" target_mode="test" description="H1 downstream: Update 31 test_tool_registry.py inline YAML fixtures from schema_version/tools to lockfile_version/binaries." />
    <item priority="P1" target_mode="test" description="H2 downstream: Add tests for new severity constants, halt-condition GuardError raises, patient_id_warnings migration, and exit code 3 union gating." />
    <item priority="P1" target_mode="test" description="H4 downstream: Add test verifying BidsReconResult.output_dir is set correctly." />
    <item priority="P1" target_mode="test" description="H5 downstream: Add tests for Python version floor check in preflight_tool_environments()." />
    <item priority="P1" target_mode="test" description="H6b: Per-function marker assignment across the full test suite (deferred from /implement to /test design phase)." />
  </action_items>
  <next_steps>The recommended downstream mode is /implement (plan phase). The action items have a natural dependency ordering: H2a (severity constants) must precede H2b (halt elevations use the new constants) and H2c (exit code 3 union references severity values). H1 (lockfile rename) and H5 (Python pin) are logically grouped since they modify the same two files (tools.lock.yaml and tool_registry.py). H3 (docstring), H4 (output_dir), and H6a (pyproject.toml markers) are independent. A single /implement plan should sequence the builds to respect these dependencies. After /implement, /test should cover the new behavior (halt conditions, exit code union, Python floor check) and perform H6b (per-function marker assignment).</next_steps>
</brainstorm_report>
