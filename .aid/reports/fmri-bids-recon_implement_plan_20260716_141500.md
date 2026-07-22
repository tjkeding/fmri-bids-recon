<implement_plan>
  <meta project="fmri-bids-recon" mode="implement" submodule="plan" timestamp="2026-07-16T14:15:00Z" />

  <input_reports>
    <report path="memory/project_redesign_spec.md" mode="brainstorm" key_items="3" />
    <report path="fmri-bids-recon_implement_build_20260716_101352.md" mode="implement" key_items="2" />
  </input_reports>

  <baseline>
    First successful validation in this project's history, established during planning.
    output tree. Result: 8 errors, 237 warnings, exit code 16, well-formed 99 KB JSON.
    Prior runs were never validated: the npm bids-validator 1.14.13 line was archived
    read-only on 2025-12-11 and crashes in both environments.
  </baseline>

  <locked_decisions>
    All resolved with the user during planning. Zero decision gates remain (Gate 1 satisfied).
    1. hpc/ deleted in full, including Apptainer.def. environment.yml at repo root is the
       single setup path.
    2. Legacy heudiconv-era scripts fmri-bids-recon.sh and bids-heuristic-bw.py deleted.
    3. Scope: D1-D6 plus all validator errors plus our-fault warnings, EXCLUDING documentation
       content (README, Authors, License, GeneratedBy, HEDVersion, SourceDatasets, and the
       task-description metadata TaskDescription/Instructions/CogAtlasID/CogPOID).
    4. SIDECAR_DENY_LIST: remove the five scanner/site fields. Patient fields left exactly
       as-is; out of scope for this redesign (no bearing on either acceptance criterion).
    5. Validator distribution: pip bids-validator-deno==3.0.0. Not npm, not Deno-from-source.
  </locked_decisions>

  <changes>

    <change id="C1" priority="P0" source_item="D1">
      <file path="fmri_bids_recon/config.py" action="modify" />
      <description>
        Reduce StudyConfig to the six-field schema. Everything else is derived or deleted.
      </description>
      <spec>
        StudyConfig fields, exactly six:
          bids_root: Path
          staging_root: Path
          dicom_root: Path              # raw DICOM root
          dicom_pattern: str            # per-subject/session path pattern under dicom_root
          subjects: list[str]           # subject ID list
          sessions: list[str]           # session list

        Delete: study_name, sourcedata_root, participants, task_registry from the config
        surface. Derive:
          sourcedata_root  -> bids_root / "sourcedata"
          study_name       -> bids_root.name
          task_registry    -> persisted to a sidecar registry file next to the config
                              (unchanged save_registry mechanics; no longer a config field)

        dicom_pattern supports {sub} and {ses} placeholders, resolved per (subject, session)
        via str.format. Resolved path = dicom_root / dicom_pattern.format(sub=..., ses=...).

        Participant expansion: the cross product subjects x sessions. For each pair, resolve
        the DICOM path. If the resolved path does NOT exist, log an INFO-level notice naming
        the pair and the resolved path, and SKIP it. This replaces the current hard
        FileNotFoundError. Rationale: the six-field config expresses an intended cohort, and
        a partially-collected cohort is the normal case, not an error condition. An empty
        result set after expansion (no pair resolved) IS an error: raise ConfigError.

        Retain from current load_config: BIDS label validation (^[a-zA-Z0-9]+$) for subjects;
        session padding validation (^[0-9]{2,}$); the staging_root-inside-bids_root rejection
        (concurrency hazard). Duplicate sub+ses is now structurally impossible (cross product
        of two lists), so drop that check; instead reject duplicate entries WITHIN subjects
        or WITHIN sessions.
      </spec>
      <dependencies>none</dependencies>
      <risk>medium - every call site reading config.participants / config.sourcedata_root /
        config.study_name / config.task_registry must be updated. Grep before editing.</risk>
      <rollback>Revert config.py; the six-field YAML is additive to disk, no data migration.</rollback>
    </change>

    <change id="C2" priority="P0" source_item="D3">
      <file path="fmri_bids_recon/__main__.py" action="modify" />
      <description>
        Collapse three subcommands into one config-only invocation running convert, assemble,
        and deface end to end. LOCKED verbatim by the user: "1 config, 1 Python command with
        1 argument (the config)."
      </description>
      <spec>
        Delete _build_parser's subparsers entirely (p_convert, p_assemble, p_deface) and the
        dispatch dict in main(). New parser: exactly one positional argument, `config`
        (path). No flags. No --participant, no --session, no --tool, no phase field.

        New main() flow:
          config = load_config(args.config)
          for each resolved (sub, ses):   # from C1's expansion
              convert
          assemble          # all participants, as today
          deface            # tool selection is no longer a flag; hardcode pydeface

        Deface tool: the --tool flag offered pydeface|afni_refacer. With no flags permitted,
        pydeface is the tool. Remove the afni_refacer branch.

        CRITICAL STRUCTURAL FIX (D4, and the direct cause of the user's "non-error error"):
        the current order commits output before the check fires --
            274 result = assemble(...)
            280 render(...)
            290 write_conversion_report(...)
            299 update_manifest(status="assembled")
            311 assert_guards_executed(...)
            312 run_bids_validator(...)   <- raises AFTER the data is written
        Reorder so that every genuine pipeline invariant is checked BEFORE any write:
            1. assert_guards_executed(combined_guard_log)   # invariant; halt before write
            2. assemble / render / write_conversion_report / update_manifest(status="assembled")
            3. save_registry(config, args.config)
            4. run_bids_validator(...)                      # post-hoc report; never a guard
            5. update_manifest(status="validated") iff the validator returned zero errors
            6. generate_cubids_report(...)
        save_registry MUST move ahead of the validator call. Today it sits at line 316, after
        the raise at 312, so the task registry was never persisted on any historical run --
        this silently breaks cross-subject label stability.
      </spec>
      <dependencies>C1, C3, C4</dependencies>
      <risk>high - this is the pipeline's control flow. The reorder changes which failures
        are recoverable. Mitigated by the fact that the current order is provably wrong.</risk>
      <rollback>Revert __main__.py.</rollback>
    </change>

    <change id="C3" priority="P0" source_item="D4">
      <file path="fmri_bids_recon/errors.py" action="modify" />
      <description>
        Rewrite the error taxonomy along the four categories the user specified, and remove
        the orphaned OrderingError.
      </description>
      <spec>
        Four categories, each with distinct semantics and distinct operator-facing behavior:

        1. GuardError(BidsReconError) -- PIPELINE-INVARIANT VIOLATION.
           A precondition the pipeline itself guarantees was broken. Halts BEFORE any output
           is written. Traceback is appropriate: this is a bug or corrupt input, and the
           stack is diagnostic. Exit 1.
           Members: VersionFloorError, AnatSuffixError, PhaseEncodingError,
           FieldmapGeometryError, FieldmapCoverageError, LabelCollisionError,
           EmptyLabelError, LabelDriftError, TaskRenameError, PhysioAssociationError,
           PhysioParseError, ConversionError, NavigatorDropError.

        2. SpecFinding -- POST-HOC SPEC-CHECK RESULT. NOT an exception. A dataclass.
           The validator's verdict about a tree that is already written. Reported legibly,
           no traceback, no stack. Carries: severity, code, location, message.
           Exit 3 if any severity=="error" findings exist; exit 0 otherwise.
           DELETE ValidationError entirely -- its docstring ("bids-validator exited with a
           non-zero return code") encodes exactly the miscategorization that produced the
           user's misleading error. A spec finding is not a pipeline invariant.

        3. ToolUnavailableError(BidsReconError) -- TOOL COULD NOT RUN.
           An external tool crashed, is absent, or returned an unparseable result. This is
           NOT a pass. Fails loudly. Message states plainly that the dataset is UNCHECKED,
           never that it is valid. Exit 4.
           Rationale: the C5 guard treated "the validator broke" as "skip validation and
           continue," which manufactured a green run on an unchecked tree.

        4. ReviewFlag -- ADVISORY, non-blocking. Unchanged. Exit 0.

        Delete OrderingError: orphaned since the order_series guard was removed on 2026-07-15;
        referenced nowhere in fmri_bids_recon/.

        Keep BidsReconError as the root with its context dict.
      </spec>
      <dependencies>none</dependencies>
      <risk>medium - ValidationError deletion and OrderingError deletion both need call-site
        sweeps. Both are narrow: ValidationError appears only in stage6_validate.py.</risk>
      <rollback>Revert errors.py.</rollback>
    </change>

    <change id="C4" priority="P0" source_item="D6">
      <file path="fmri_bids_recon/stage6_validate.py" action="modify" />
      <description>
        Replace the crash-signature guard with a well-formed-result discriminator, switch to
        the pip-installed validator, and drop the two stale guard names.
      </description>
      <spec>
        Delete the C5 guard at lines 113-130 in full. It signature-matched ONE crash string
        (empty stdout + "esm.js" in stderr[:200]) and fell through on the server's different
        crash (Ajv strict mode, exit 3, version banner on stdout), reporting a broken tool as
        a dataset failure.

        run_bids_validator(bids_root: Path) -> list[SpecFinding]:
          Invoke: [ "bids-validator-deno", "--json", "-o", <tmpfile>, str(bids_root) ]
          Write to a NamedTemporaryFile rather than reading stdout. Verified during planning:
          the validator writes a well-formed JSON result to -o while returning a NON-ZERO
          exit (16 on the reference tree, from the binary directly, not a conda artifact).

          DISCRIMINATOR -- do NOT branch on returncode. Exit codes are undocumented in the
          CLI reference and the tracker carries a "validator crash returns zero exit code"
          defect, so the exit code is unreliable in BOTH directions. The robust signal is
          whether a well-formed result exists:
            - FileNotFoundError on the binary        -> raise ToolUnavailableError
            - outfile missing / empty                -> raise ToolUnavailableError
            - json.JSONDecodeError on the outfile    -> raise ToolUnavailableError
            - parsed dict lacks the "issues" key     -> raise ToolUnavailableError
            - parses with "issues"                   -> a VERDICT; return findings
          Every ToolUnavailableError message must say the dataset is UNCHECKED and include
          the captured stderr tail. Never warn-and-return; never treat unchecked as passed.

          Parse: result["issues"]["issues"] is a list of records with keys code, severity,
          location, and optionally subCode, issueMessage, rule, line. Map each to a
          SpecFinding. result["issues"]["codeMessages"] maps code -> human-readable text;
          use it for the operator-facing report.

        Caller (C2) renders findings as a legible table, no traceback. Errors set exit 3.

        ALL_GUARD_NAMES: remove "ordering_agreement" (guard deleted 2026-07-15) and
        "physio_geometry_agreement" (name does not match any guard the physio module logs).
        Leaves 12 entries. assert_guards_executed is otherwise unchanged and remains a
        genuine invariant check -- it stays, and per C2 it now runs BEFORE the writes.

        generate_cubids_report is already correctly non-blocking; leave it alone.
      </spec>
      <dependencies>C3</dependencies>
      <risk>low - the discriminator was exercised against real output during planning; the
        99 KB result parsed and the key path result["issues"]["issues"] is confirmed.</risk>
      <rollback>Revert stage6_validate.py; re-add the two guard names.</rollback>
    </change>

    <change id="C5" priority="P0" source_item="D5">
      <file path="fmri_bids_recon/physio.py" action="modify" />
      <description>
        Revert the two guard downgrades from the 2026-07-16 build. They converted hard
        failures into silent data loss.
      </description>
      <spec>
        Restore both fatal raises.

        associate_physio (~lines 510-519): restore
            if log.acq_info is None:
                raise PhysioAssociationError(
                    f"Physio log {log!r} has no ACQUISITION_INFO block; cannot verify run geometry.",
                    context={"physio_series": log.series_number,
                             "bold_series": best_bold.series_number},
                )
        Delete the warning + result[...] = log + continue.

        write_physio (~lines 596-603): restore
            if sample_time_ticks is None:
                raise PhysioParseError(
                    f"No channel in {run_prefix} reports a positive SampleTime; "
                    "cannot derive SamplingFrequency.",
                    context={"channels": list(log.channels)},
                )
        Delete the warning + return [].

        Rationale, recorded so this is not re-downgraded: all six physio logs on real XA30
        data failed BOTH guards. Six-for-six is a broken parser, not missing data. The prior
        test report classified the guards as "too strict" and that classification was ported
        without challenge. Before the downgrade the pipeline halted and said physio was
        broken; after it, the pipeline warned and shipped an incomplete dataset. The
        downgraded warnings were also indistinguishable from "the parser recognised nothing,"
        which is the diagnostic the operator actually needs.

        Also replace the two function-local `import logging as _logging` statements with the
        module-level `logger` convention used by every other module in the package.
      </spec>
      <dependencies>C3</dependencies>
        and intended behavior: it surfaces the parser defect the downgrade concealed. See
        known_consequences below; this is why the physio parser fix is sequenced next.</risk>
      <rollback>Re-apply the warnings. Do not do this without diagnosing the parser first.</rollback>
    </change>

    <change id="C6" priority="P0" source_item="validator-errors">
      <file path="fmri_bids_recon/stage4_assemble.py" action="modify" />
      <description>
        Four fixes: acq_time normalization, TaskName injection, deny-list correction, and a
        sessions.json sidecar. Together these clear 7 of the 8 validator errors and 122 of
        the warnings.
      </description>
      <spec>
        (a) acq_time zero-padding -- clears TSV_VALUE_INCORRECT_TYPE (1 error).
            Root cause established during planning: dcm2niix itself emits an unpadded
            seconds field when seconds < 10. Digits-redacted format census over the staging
            sidecars: 'DDDD-DD-DDTDD:DD:DD.DDDDDD' x271 (well-formed) vs
            'DDDD-DD-DDTDD:DD:D.DDDDDD' x61 (malformed, 18%). Our code passes it through
            verbatim at lines 286, 301, 317, 343 via series.raw.get("AcquisitionDateTime").
            Fix: at each of the four sites, normalize before writing:
                _parse_acquisition_datetime(raw).isoformat()  when the key is present,
                "n/a" otherwise.
            _parse_acquisition_datetime is ALREADY imported at line 16 and already parses the
            unpadded form correctly (strptime's %S accepts a single digit); .isoformat()
            always zero-pads. Guard the parse: on failure, emit "n/a" rather than propagating
            a malformed string.

        (b) TaskName -- clears SIDECAR_KEY_REQUIRED x6 (6 errors) and TaskName
            SIDECAR_KEY_RECOMMENDED x12.
            BIDS REQUIRES TaskName in every func sidecar. dcm2niix does not write it and
            neither do we, so all six BOLD runs are currently non-compliant.
            Fix: when writing a func sidecar (bold or sbref), inject
                data["TaskName"] = <task label>
            The task label is the same one already used to build the filename entity
            task-<label> (from the task registry / labels stage). Source it from there so the
            sidecar and the filename cannot drift; do not re-derive it from the description.

        (c) SIDECAR_DENY_LIST -- clears 120 SIDECAR_KEY_RECOMMENDED warnings.
            Remove exactly these five entries from the frozenset at lines 30-50:
                "InstitutionName", "InstitutionAddress", "InstitutionalDepartmentName",
                "StationName", "DeviceSerialNumber"
            Leave every other entry untouched, including all patient fields.
            Established during planning: these five ARE present in the raw DICOMs, and we
            already pass dcm2niix -ba n specifically to preserve them, then delete them
            ourselves at assembly. Per the user's PHI doctrine, scanner and site metadata is
            not PHI; the PHI boundary is the collaboration surface, not the pipeline's output
            on the secure server. BIDS recommends all five.

        (d) sessions.json sidecar -- clears TSV_ADDITIONAL_COLUMNS_UNDEFINED x2.
            sub-<X>_sessions.tsv carries `wave` and `age` columns with no sidecar defining
            them. Write sub-<X>_sessions.json alongside it:
                {"wave": {"Description": "Study wave identifier."},
                 "age":  {"Description": "Age at scan.", "Units": "years"}}
            Use the existing atomic JSON writer at line 122.
      </spec>
      <dependencies>C1</dependencies>
      <risk>medium - (b) requires the task label at sidecar-write time; confirm it is in
        scope at that call site before wiring. (a) and (c) are low risk and mechanical.</risk>
      <rollback>Revert stage4_assemble.py. The deny-list change is a one-line frozenset edit.</rollback>
    </change>

    <change id="C7" priority="P0" source_item="validator-errors">
      <file path="fmri_bids_recon/__main__.py" action="modify" />
      <description>
        Relocate manifest.tsv out of the BIDS root. Clears NOT_INCLUDED (1 error).
      </description>
      <spec>
        Line 223 currently: manifest_path = Path(config.bids_root) / "manifest.tsv"
        BIDS does not permit an arbitrary manifest.tsv at the dataset root; the validator
        reports NOT_INCLUDED.
        New: manifest_path = Path(config.bids_root) / "derivatives" / "fmri-bids-recon" / "manifest.tsv"
        This is the directory the pipeline already owns and already writes conversion reports
        into, so it needs no new tree. mkdir(parents=True, exist_ok=True) before first write.

        Migration: if a manifest.tsv exists at the old root path, move it to the new location
        on first run and log the move at INFO. Do not silently create a second manifest and
        strand the first -- that would break should_skip and silently re-convert everything.
        The move is a destructive-adjacent operation on a pre-existing file: per project
        policy the build phase must obtain explicit user approval before performing it.
      </spec>
      <dependencies>C2</dependencies>
      <risk>medium - manifest location drives should_skip / resumability. A stranded manifest
        means silent full re-conversion. The migration step is the mitigation.</risk>
      <rollback>Revert the path constant; move manifest.tsv back to the root.</rollback>
    </change>

    <change id="C8" priority="P0" source_item="D2">
      <file path="environment.yml" action="modify" />
      <description>
        Replace the dead npm validator with the pip wheel and drop the Node dependency.
      </description>
      <spec>
        Remove: `- nodejs=20` from dependencies.
        Add under pip: `- bids-validator-deno==3.0.0`
        Rewrite the header comment: `conda env create -f environment.yml` is now the complete
        and only setup step. Delete the reference to hpc/setup_env.sh (that file is deleted
        by C9).

        Verified during planning: `pip install bids-validator-deno==3.0.0` resolves and pulls
        `deno-2.9.3` as a platform wheel (38 MB), bundling the runtime. No Node, no npm, no
        global install, no separate Deno install. It provides the `bids-validator-deno`
        console script on PATH inside the env.

        Leave the numpy==1.26.4 cap and its comment intact: still required by the cubids 1.1.0
        ceiling. bids-validator-deno is a bundled binary wheel with no numpy dependency, so it
        does not interact with that cap.

        Rationale for the version move: the pinned bids-validator@1.14.13 is from the npm 1.x
        line, which now lives in bids-standard/legacy-validator, is documented as "not updated
        anymore," and was ARCHIVED READ-ONLY on 2025-12-11. It is not misconfigured; it is
        abandoned. Both observed crashes were that tool dying.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - additive pip pin; exercised locally during planning.</risk>
      <rollback>Restore nodejs=20; remove the pip line.</rollback>
    </change>

    <change id="C9" priority="P1" source_item="D2">
      <file path="hpc/" action="delete" />
      <file path="RUNBOOK.md" action="delete" />
      <file path="fmri-bids-recon.sh" action="delete" />
      <file path="bids-heuristic-bw.py" action="delete" />
      <description>
        Remove all SLURM/HPC packaging and the superseded heudiconv-era scripts.
      </description>
      <spec>
        Delete in full:
          hpc/convert_array.sbatch     - SLURM array
          hpc/assemble.sbatch          - SLURM
          hpc/setup_env.sh             - its only content beyond `conda env create` is the
                                         npm install of the archived validator; C8 makes the
                                         whole file redundant
          hpc/Apptainer.def            - user-approved deletion; once the validator is a pip
                                         wheel there is no non-Python dependency left for a
                                         container to solve
          hpc/                         - the now-empty directory
          RUNBOOK.md                   - SLURM-oriented end to end; superseded by the
                                         single-command invocation from C2
          fmri-bids-recon.sh                - heudiconv-era, superseded by the fmri_bids_recon package
          bids-heuristic-bw.py         - heudiconv heuristic, superseded

        Verified: no Python module imports or references any of these. The only SLURM
        references outside hpc/ are in RUNBOOK.md (deleted here) and in explanatory comments
        inside tests/ (prose only, no executable dependency).

        EVERY deletion in this change requires explicit per-invocation user approval per
        project policy. The build phase must present the list and obtain approval before
        removing anything. Do not batch-approve.
      </spec>
      <dependencies>C8</dependencies>
      <risk>low - nothing imports these. C8 must land first so the environment remains
        buildable at every commit.</risk>
      <rollback>Restore from the user's backups; these files are not reconstructible from
        the working tree once removed.</rollback>
    </change>

    <change id="C10" priority="P1" source_item="D4">
      <file path="fmri_bids_recon/__main__.py" action="modify" />
      <description>
        Operator-facing output and exit codes matching the C3 taxonomy. This is the change
        that removes the "non-error errors."
      </description>
      <spec>
        Exit codes:
          0  success; no spec errors; advisory warnings permitted
          1  GuardError            - pipeline invariant violated; traceback shown
          2  ConfigError           - malformed config / no participants resolved
          3  spec findings present - validator reported >=1 severity=="error"
          4  ToolUnavailableError  - a tool could not run; dataset UNCHECKED

        Rendering rules, one per category:
          GuardError           -> logger.error + full traceback. This is a bug; the stack is
                                  the diagnostic.
          SpecFinding list     -> a legible table grouped by severity then code, using
                                  codeMessages for the explanation and location for the file.
                                  NO traceback. Header must state plainly what happened, e.g.
                                  "BIDS validation completed: N errors, M warnings." Never
                                  the word "Failed" for a completed check that produced a
                                  verdict -- the user's objection was precise: an ERROR line
                                  reading "bids-validator failed" while the tree was in fact
                                  written and largely correct is incoherent output.
          ToolUnavailableError -> logger.error stating the tool, the failure, and explicitly
                                  that the dataset is UNCHECKED. Never imply validity.
          ReviewFlag           -> logger.warning, exit unaffected.

        The physio non-fatal wrapper at lines 142-158 stays as-is: it re-raises GuardError and
        warns otherwise, which is already correct under the new taxonomy.
      </spec>
      <dependencies>C2, C3, C4</dependencies>
      <risk>low - output formatting and exit-code mapping.</risk>
      <rollback>Revert __main__.py.</rollback>
    </change>

  </changes>

  <execution_order>C8, C1, C3, C4, C5, C6, C7, C2, C10, C9</execution_order>
  <execution_order_rationale>
    C8 first so the environment is buildable throughout. C1 (config) and C3 (errors) are the
    two foundations every other change imports. C4/C5/C6/C7 are independent module-level edits
    that depend only on those foundations and touch disjoint files, so they may be dispatched
    in parallel. C2 and C10 both rewrite __main__.py and must be serialized after everything
    they orchestrate. C9 (deletions) last, so the tree stays working until the end and the
    deletions are trivially abandonable if anything upstream stalls.
  </execution_order_rationale>

  <projected_outcome>
    Against acceptance criterion (1), no errors: all 8 clear. TSV_VALUE_INCORRECT_TYPE via
    C6a, SIDECAR_KEY_REQUIRED x6 via C6b, NOT_INCLUDED via C7. Projected errors: 0.

    Against acceptance criterion (2), no warnings except those appropriate for missing data:
    237 -> ~103. Cleared: 120 institution/device (C6c), TaskName x12 (C6b), sessions columns
    x2 (C6d). The ~103 residual, itemized honestly:

      SequenceName x24              genuinely absent. Verified: tag (0018,0024) is absent from
                                    all 22 series. XA30 enhanced DICOM carries
                                    PulseSequenceName (0018,9005) instead.
      PulseSequenceType x24         dcm2niix does not emit this BIDS field.
      PartialFourierDirection x17   dcm2niix emits PartialFourier but not the direction.
      TaskDescription / Instructions / CogAtlasID / CogPOID x24
                                    user-descoped: requires human-authored content.
      EVENTS_TSV_MISSING x4         appropriate; no events data for emotionalnback. Correctly
                                    silent for rest.
      README / NO_AUTHORS / TOO_FEW_AUTHORS x3, JSON_KEY_RECOMMENDED x4
                                    user-descoped as documentation.
      ParallelReductionFactorOutOfPlane x2, SpoilingType x1
                                    not emitted by dcm2niix.

    Every residual is either genuinely-missing source data or an explicit user descope. None
    is a silent failure. This satisfies criterion (2) as scoped, but it is ~103 warnings and
    not zero, so the projection is stated rather than implied.
  </projected_outcome>

  <known_consequences>
    PhysioAssociationError on the first log lacking an ACQUISITION_INFO block. This is
    correct: the downgrade concealed a parser defect that fails six-for-six on real XA30
    data, which is a parser bug, not missing data.

    This means the redesign as specified does NOT by itself produce a clean end-to-end run.
    The physio parser must be diagnosed and fixed for the acceptance criteria to be met. That
    diagnosis is deliberately NOT in this plan: its scope depends on what the parser is
    actually doing, which is unknown until the private element (7fe1,1010) block split is
    dumped for the SN=21 log. The diagnostic was offered earlier and has not been run.

    This is surfaced as a scope decision for the user, not self-classified as out of scope.
    The user has stated physio FILES are not a deliverable ("I don't give a flying f about the
    physio files, just get me reconstructed scans") while also requiring that warnings be
    honest. Those two constraints are compatible in more than one way, and the choice is the
    user's:
      (i)  diagnose and fix the parser;
           it and the guards stay hard for studies that do enable it;
      (iii) keep the guards hard and let the run halt until (i) happens.
    Option (ii) is the only one that satisfies both stated constraints without a parser fix.
  </known_consequences>

  <testing_note>
    Per skill constraints /implement does not run tests. Tests WILL break: C1 changes the
    config schema that tests/test_config.py asserts against; C2 removes the subcommands that
    tests/test_cli_integration.py drives; C3 deletes ValidationError, which
    tests/test_validate.py imports. tests/bids_recon_patched/ is a stale copy of the package
    and will diverge further. Route to /test after build.
  </testing_note>
</implement_plan>
</content>
</invoke>
