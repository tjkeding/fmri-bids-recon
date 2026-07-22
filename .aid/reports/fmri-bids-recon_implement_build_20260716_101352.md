<implement_report>
  <meta project="fmri-bids-recon" mode="implement" submodule="build" timestamp="2026-07-16T10:13:52Z" />
  <spec_ref>fmri-bids-recon_implement_plan_20260716_120000.md</spec_ref>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/sidecar.py" lines_changed="4" />
      </files_modified>
      <notes>Backslash-delimited string splitting added to _to_str_tuple. When a string value contains literal backslash characters (e.g., "GR\\IR" from dcm2niix), the value is now split on backslash and returned as a tuple of tokens. This ensures downstream consumers (scanning_sequence, image_type, sequence_variant) receive multi-element tuples consistent with the JSON-array representation.</notes>
    </change>
    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" lines_changed="68" />
      </files_modified>
      <notes>Nine sub-changes applied: (1) added import re; (2) added _SBREF_SUFFIX_RE regex constant; (3) added _description_stem helper; (4) added _is_spin_echo helper with three-signal detection (SE in scanning_sequence, _se in PulseSequenceDetails, SS absent from SequenceVariant); (5) replaced _bval_exists with three-function decomposition (_bval_path, _bval_exists, _has_nonzero_bval); (6) added SeriesNumber dedup guard in classify loop; (7) Rule 5 updated to use _is_spin_echo(s); (8) Rule 6 updated to remove SE check and replace _bval_exists with n_volumes==1 and not _has_nonzero_bval; (9) Rules 9/9b updated to use _description_stem for stem comparison; (10) NORM/ND pass updated with deduplicating loop replacing list comprehension.</notes>
    </change>
    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/labels.py" lines_changed="5" />
      </files_modified>
      <notes>SBRef/BOLD collision guard normalization. Added _SBREF_SUFFIX_RE regex constant alongside existing module-level regex patterns. Modified collision check to compute stem set (stripping trailing _SBRef suffix, lowercasing, stripping whitespace) before raising LabelCollisionError, so that "task_SBRef" and "task" map to the same stem and do not trigger a false collision.</notes>
    </change>
    <change id="C4" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/physio.py" lines_changed="14" />
      </files_modified>
      <notes>Two guards downgraded from fatal to warning. (1) associate_physio: missing ACQUISITION_INFO block now logs a warning and pairs by temporal proximity (assigns result[best_bold.series_number] = log, continues loop) instead of raising PhysioAssociationError. (2) write_physio: missing SampleTime now logs a warning and returns empty list instead of raising PhysioParseError.</notes>
    </change>
    <change id="C5" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage6_validate.py" lines_changed="7" />
      </files_modified>
      <notes>bids-validator crash detection guard added before the generic ValidationError raise. When stdout is empty and "esm.js" appears in the first 200 characters of stderr (indicating a Node.js/ESM loader crash rather than a validation failure), the function logs a warning and returns gracefully instead of raising ValidationError.</notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>5</total_changes>
    <completed>5</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <next_steps>Recommended: run /test to validate all changes.</next_steps>
</implement_report>
