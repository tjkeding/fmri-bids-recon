<implement_report>
  <meta project="bids-recon" mode="implement" submodule="build" timestamp="2026-08-24T17:54:12Z" />
  <spec_ref>bids-recon_implement_plan_20260824_173224.md</spec_ref>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/warnings.py" lines_changed="4" />
      </files_modified>
      <notes>Added user_facing key to graded_warning return dict (4-key schema).</notes>
    </change>
    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/warnings.py" lines_changed="18" />
      </files_modified>
      <notes>Added module-level _WARNING_ACCUMULATOR with get_warnings()/clear_warnings() API. Rewrote graded_warning() to append to accumulator before returning.</notes>
    </change>
    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" lines_changed="11" />
      </files_modified>
      <notes>Added _SCOUT_KEYWORDS frozenset and _is_epi_bold_physics() helper with n_volumes >= 10 threshold.</notes>
    </change>
    <change id="C4" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" lines_changed="20" />
      </files_modified>
      <notes>Rule 2 expanded to three detection signals: Siemens DIS2D mosaic, LOCALIZER token in ImageType, description keyword match with physics guard.</notes>
    </change>
    <change id="C5" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" lines_changed="16" />
      </files_modified>
      <notes>Rule 3 rewritten with physics pass-through: _is_epi_bold_physics falls through to Rule 4+; non-matching EPI raises NavigatorDropError; non-EPI dropped as navigator.</notes>
    </change>
    <change id="C6" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" lines_changed="3" />
      </files_modified>
      <notes>Rule 5 broadened from tok=="FMRI" to tok!="DIFFUSION" and "EP" in scanning_sequence.</notes>
    </change>
    <change id="C7" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" lines_changed="2" />
      </files_modified>
      <notes>Rule 8 broadened to include _is_epi_bold_physics fallback alongside tok=="FMRI".</notes>
    </change>
    <change id="C8" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" lines_changed="17" />
      </files_modified>
      <notes>Rules 9/9b merged into single vendor-agnostic SBRef rule with look-ahead determining SBREF vs DWI_SBREF.</notes>
    </change>
    <change id="C9" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" lines_changed="15" />
      </files_modified>
      <notes>NORM/ND pass wrapped in has_norm Siemens guard. Duplicate modality guard added unconditionally after NORM/ND block. SEVERITY_HIGH added to import.</notes>
    </change>
    <change id="C10" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage1_convert.py" lines_changed="3" />
      </files_modified>
      <notes>Added -i y flag to dcm2niix invocation (ignore derived/localizer/single-slice images) with comment.</notes>
    </change>
    <change id="C11" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/pipeline.py" lines_changed="12" />
      </files_modified>
      <notes>Adopted warning accumulator: imported get_warnings/clear_warnings, added clear_warnings() at entry, removed all_review_flags, unwrapped BIDS validation graded_warning, status determined via get_warnings().</notes>
    </change>
    <change id="C12" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/pipeline.py" lines_changed="6" />
      </files_modified>
      <notes>Fieldmap targets filtered by excluded_sns set (series excluded by volume-count check).</notes>
    </change>
    <change id="C13" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/pipeline.py" lines_changed="14" />
      </files_modified>
      <notes>No-fieldmaps early-out: when pairs is empty, emits NO_FIELDMAP_SERIES graded_warning, constructs empty Mapping, sets 6 guard_log entries vacuously True.</notes>
    </change>
    <change id="C14" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage3_map.py" lines_changed="8" />
      </files_modified>
      <notes>Per-target FieldmapCoverageError replaced with FIELDMAP_COVERAGE_GAP graded_warning (high severity) + continue. Candidate diagnostics preserved in message.</notes>
    </change>
    <change id="C15" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage3_map.py" lines_changed="6" />
      </files_modified>
      <notes>Orphan fieldmap pair FieldmapCoverageError replaced with ORPHAN_FIELDMAP_PAIR graded_warning (medium severity). guard_log entries unchanged.</notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>15</total_changes>
    <completed>15</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <next_steps>Recommended: run /test to validate all changes.</next_steps>
</implement_report>
