<implement_report>
  <meta project="fmri-bids-recon" mode="implement" submodule="build" timestamp="2026-07-15T12:39:48Z" />
  <spec_ref>fmri-bids-recon_implement_plan_20260715_105745.md</spec_ref>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage5_render.py" lines_changed="8" />
      </files_modified>
      <notes>The fieldmap-member loop in render() now resolves each member's BIDS sidecar via mapping.bids_relative_paths.get(member.series_number), skips members with no mapping entry, and no longer references the nonexistent staging-tree attribute. IntendedFor and B0FieldIdentifier are still written to each resolved member sidecar. Verified present at stage5_render.py:155-158; no member-attribute path access remains.</notes>
    </change>
    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage4_assemble.py" lines_changed="17" />
      </files_modified>
      <notes>Errors import extended to include PhaseEncodingError (line 23). Both the diffusion and diffusion single-band-reference branches replace the unknown-direction fallback with a None-check that raises PhaseEncodingError (a GuardError subclass), carrying series_number, phase_encoding_direction, and role.name in context (raises at lines 351 and 384). No unknown-direction label fallback remains for diffusion series.</notes>
    </change>
    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/config.py" lines_changed="12" />
        <file path="fmri_bids_recon/labels.py" lines_changed="8" />
      </files_modified>
      <notes>TaskRegistryEntry gained a trailing optional signature field (config.py:46). load_config reconstructs the signature tuple with the matrix as an inner tuple from the optional YAML list and passes it to the constructor (config.py:241). save_registry serializes the signature as a list and omits the key when None (config.py:284). resolve_labels populates the signature at new-entry registration from the description's acquisition-signature set (labels.py:326), and the rename guard augments the old-description signature set with the stored registry signature before computing the signature match (labels.py:345-347). Backward-compatible: legacy entries without a stored signature default to None and the guard falls back to the label match.</notes>
    </change>
    <change id="C4" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/tsv.py" lines_changed="4" />
      </files_modified>
      <notes>Removed the lockfile-unlink try/except from the finally clause of upsert_tsv, leaving only the flock release and file close (tsv.py:109). The lockfile now persists in the system temp directory so contending processes contend on the same inode; no BIDS-tree artifact is introduced.</notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>4</total_changes>
    <completed>4</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <verification>
    All five edited modules byte-compile under the project interpreter. Anchor strings from each agent return were confirmed present on disk at the reported lines. No tests were run (testing is out of scope for implement mode).
  </verification>
  <next_steps>Recommended: run /test. The strict-xfail markers guarding the render, diffusion-direction, and rename fixes will now report XPASS(strict)=FAILED until /test removes the obsolete markers; the rename fix additionally requires the conftest registry_entry fixture to supply a matching stored signature before its test flips to pass. The physio integration xfail remains deferred and needs a runtime traceback (pytest --runxfail) to determine whether the residual fault is a product defect or a fixture inconsistency before a fix is specified. The lockfile-persistence change has no guarding test; a concurrency regression test for upsert_tsv is recommended.</next_steps>
</implement_report>
