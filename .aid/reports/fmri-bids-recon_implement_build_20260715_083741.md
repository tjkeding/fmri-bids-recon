<implement_report>
  <meta project="fmri-bids-recon" mode="implement" submodule="build" timestamp="2026-07-15T12:37:41Z" />
  <spec_ref>fmri-bids-recon_implement_plan_20260714_192820.md</spec_ref>
  <changes_applied>

    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/errors.py" anchor="class NavigatorDropError(GuardError):" />
      </files_modified>
      <notes>Added three blocking exception subclasses (conversion failure, physio parse failure, dropped-navigator EPI) under the blocking-guard branch of the hierarchy, each with a single-line docstring matching the sibling pattern, and refreshed the module docstring hierarchy listing. No behavior beyond class definition.</notes>
    </change>

    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage3_map.py" anchor="bids_relative_paths: dict[int, str] = field(default_factory=dict)" />
      </files_modified>
      <notes>Added the subject-relative output-path registry field to the mutable mapping dataclass, keyed by series number, defaulting to an empty dict. This is the shared channel that lets the render stage locate emitted files without recomputing layout.</notes>
    </change>

    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" anchor="DWI_SBREF = &quot;dwi_sbref&quot;" />
      </files_modified>
      <notes>Added the diffusion single-band-reference member to the role enumeration, used by both the new classification rule and the diffusion-directory assembly branch.</notes>
    </change>

    <change id="C4" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/sidecar.py" anchor="software_versions: str | None = None" />
      </files_modified>
      <notes>Appended a nullable software-version field to the frozen series dataclass as its final attribute and populated it during series loading from the corresponding sidecar tag. Supports the fail-loud navigator guard's ability to identify the acquisition software line.</notes>
    </change>

    <change id="C5" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage4_assemble.py" anchor="mapping.bids_relative_paths[snum] = dest.relative_to(sub_dir).as_posix()" />
      </files_modified>
      <notes>Six coordinated edits: every emitting branch now records the subject-relative output path into the shared mapping registry; anatomical run indices, single-band-reference run indices inherited from the parent functional series, and diffusion phase-encoding direction labels plus diffusion run indices are all applied; orphan fieldmaps are routed to an unpaired-fieldmap source-data location with a non-blocking review flag; and a dedicated diffusion single-band-reference branch emits into the diffusion directory with the reference suffix. Deviation: the orphan-fieldmap review flag is constructed with the code carried in its context mapping rather than a dedicated keyword, because the non-blocking review-flag class inherits the base two-argument message/context constructor. This preserves the intended payload and matches the same adaptation applied to the ambiguous-volume flag.</notes>
    </change>

    <change id="C6" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage5_render.py" anchor="rel = mapping.bids_relative_paths.get(target.series_number)" />
      </files_modified>
      <notes>Both the intended-for loop and the field-source loop now resolve each target's on-disk location through the shared mapping registry and skip targets with no recorded path, replacing the prior recomputation that produced incorrect linkage. The four-argument render signature and the three path/identifier helpers are unchanged.</notes>
    </change>

    <change id="C7" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" anchor="from .errors import AnatSuffixError, NavigatorDropError, ReviewFlag" />
      </files_modified>
      <notes>Two rule changes in the classifier: the navigator-drop rule now raises the blocking dropped-navigator exception when the series carries an echo-planar scanning sequence before it would otherwise silently drop the series, and a new rule placed ahead of the unclassified fallthrough detects diffusion single-band-reference series by temporal adjacency and stem match to a diffusion parent and assigns the new diffusion reference role. Bundled with the enum addition into a single file dispatch.</notes>
    </change>

    <change id="C8" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/__main__.py" anchor="from .stage6_validate import assert_guards_executed, run_bids_validator, generate_cubids_report, ALL_GUARD_NAMES" />
      </files_modified>
      <notes>Convert-command cluster: physio logs are now parsed per file from the source DICOM index by SOP class rather than from a directory scan (the physio raw-data objects are skipped by the converter and reachable only through the index), associated against surviving functional series into a mapping keyed by series number; the surrounding exception handler was narrowed so a genuinely absent physio warns while blocking-guard subclasses re-raise; the guard log now records every registered guard name; the dead demographics local and its pickle key were removed; and the intermediate hand-off was extended with the series map and the unclassified series list. Bundled into the single orchestration-file dispatch.</notes>
    </change>

    <change id="C9" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/__main__.py" anchor="config.task_registry.clear()" />
      </files_modified>
      <notes>Assemble-command cluster: the unpickle block was extended with the series map, unclassified list, excluded list, and volume updates; the registry merge now reads the delta's new-entries mapping and the volume updates rather than treating the delta dataclass as a mapping; the assemble, render, per-session conversion-report, and cubids-report calls were all corrected to their true signatures with the demographics argument dropped; the conversion report was moved inside the per-participant loop; and the registry is persisted by mutating the config's task registry in place before saving. Bundled into the single orchestration-file dispatch.</notes>
    </change>

    <change id="C10" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/__main__.py" anchor="for bold_snum, log in physio_pairs.items():" />
      </files_modified>
      <notes>Physio-write cluster: the write loop now iterates the association mapping's items and calls the writer with the log, the constructed run prefix, the functional output directory, and the corresponding functional series, replacing the prior incorrect iteration. Bundled into the single orchestration-file dispatch.</notes>
    </change>

    <change id="C11" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/labels.py" anchor="label_match = (new_label == old_label)" />
      </files_modified>
      <notes>The rename guard now evaluates against the persisted task registry rather than only session-local signatures, so a description recorded in the persisted registry under a different label than the incoming session raises the rename exception. Deviation from the literal spec approach: the agent achieved the persisted-registry comparison by adding an explicit label-equality condition alongside the existing acquisition-signature intersection, because the session-local signature index does not contain signatures for descriptions absent from the current session. This strengthens rather than weakens the guard and satisfies the acceptance criterion; flagged here for review because it introduces a new comparison branch rather than only swapping the comparison source.</notes>
    </change>

    <change id="C12" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/runs.py" anchor="ambiguous_volume_mode" />
      </files_modified>
      <notes>The volume-count check now detects a tie between candidate volume modes, retains all functional runs, and emits a non-blocking review flag without writing a registry entry. Deviation: the review flag's code is carried in its context mapping rather than a dedicated keyword, because the non-blocking review-flag class inherits the base two-argument message/context constructor. The spec explicitly licensed adapting the constructor call when the signature differs; the payload is preserved.</notes>
    </change>

    <change id="C13" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage1_convert.py" anchor="from .errors import ConversionError" />
      </files_modified>
      <notes>The conversion stage now clears the contents of the staging leaf (not the leaf directory itself) before invoking the converter, logs the cleanup, captures the converter's exit status and streams, and raises the blocking conversion exception on a nonzero return while preserving the captured standard-error output on the staging result. Added the standard-library filesystem and logging imports and a module logger.</notes>
    </change>

    <change id="C14" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/physio.py" anchor="from .errors import PhysioAssociationError, PhysioParseError" />
      </files_modified>
      <notes>Physio association now selects the latest functional series preceding the log with a nearest-series fallback and raises the association exception when no acquisition context is available; the written start time is expressed on the physiological-unit clock via a new seconds-since-midnight helper anchored to the acquisition datetime; and the writer raises the blocking parse exception on a non-positive sample time, a pulse/respiration rate disagreement, or a recording-window-versus-expected-duration mismatch.</notes>
    </change>

    <change id="C15" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/manifest.py" anchor="from .errors import ValidationError" />
      </files_modified>
      <notes>The manifest update now raises the validation exception at entry when the supplied status is not a member of the recognized status set, enforcing the manifest status vocabulary at the write boundary.</notes>
    </change>

    <change id="C16" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/deface.py" anchor="if output_path.exists()" />
      </files_modified>
      <notes>The defacing step now appends the output path only when it actually exists on disk and otherwise emits a warning, preventing a nonexistent path from being recorded as a produced artifact.</notes>
    </change>

    <change id="C17" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/tsv.py" anchor="bids_recon_" />
      </files_modified>
      <notes>The tabular-file lock path is now derived from a truncated hash of the resolved target path placed in the system temporary directory, so distinct targets take distinct locks, and the lock is removed in the finally block regardless of outcome. Added the standard-library hashing import.</notes>
    </change>

    <change id="C18" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage6_validate.py" anchor="raise ValidationError" />
      </files_modified>
      <notes>The external-validator invocation is now wrapped so a missing validator executable is re-raised as the validation exception with the original cause chained, converting a silent tool-absence into an explicit, attributable failure.</notes>
    </change>

    <change id="C19" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/report.py" anchor="datetime.now(timezone.utc).isoformat(timespec='seconds')" />
      </files_modified>
      <notes>The report timestamp now uses a timezone-aware current-time call, replacing the deprecated naive utc call while retaining the trailing zulu marker in the rendered string. Removes the deprecation warning emitted during the report tests.</notes>
    </change>

  </changes_applied>
  <summary>
    <total_changes>19</total_changes>
    <completed>19</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
    <files_touched>16</files_touched>
    <deviations>3</deviations>
  </summary>
  <next_steps>Recommended: run /test to validate all changes. The completion criterion for this work is a green suite with zero expected-failure and zero unexpectedly-passing markers; that verification runs under /test, not here. Five of the adjudicated behaviors (the two physio guards, the staging cleanup, the manifest status enforcement, the navigator fail-loud path, and the diffusion single-band-reference routing) are not yet pinned by dedicated strict expected-failure tests and need new test coverage authored in the design phase.</next_steps>
</implement_report>
