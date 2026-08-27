<implement_report>
  <meta project="bids-recon" mode="implement" submodule="build" timestamp="2026-08-25T00:05:59Z" />
  <spec_ref>bids-recon_implement_plan_20260824_230900.md</spec_ref>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/sidecar.py" lines_changed="12" />
      </files_modified>
      <notes>Promoted _SBREF_SUFFIX_RE, description_stem(), and nifti_stem() as shared helpers with import re added.</notes>
    </change>
    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" lines_changed="18" />
      </files_modified>
      <notes>Removed duplicated _SBREF_SUFFIX_RE and _description_stem; consolidated imports from sidecar; precomputed position_by_sn dict replacing O(n^2) inline generators in Rules 5 and 9.</notes>
    </change>
    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/labels.py" lines_changed="3" />
      </files_modified>
      <notes>Replaced inline _SBREF_SUFFIX_RE usage with imported description_stem.</notes>
    </change>
    <change id="C4" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage4_assemble.py" lines_changed="12" />
      </files_modified>
      <notes>Removed _nifti_filestem and stale RegistryDelta/noqa imports; replaced with nifti_stem from sidecar.</notes>
    </change>
    <change id="C5" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage5_render.py" lines_changed="4" />
      </files_modified>
      <notes>Removed dead PE_DIRECTION_TO_LABEL import; replaced _sidecar_path body with nifti_stem from sidecar.</notes>
    </change>
    <change id="C6" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/report.py" lines_changed="3" />
      </files_modified>
      <notes>Removed dead import json and dead FieldmapPair import.</notes>
    </change>
    <change id="C7" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage3_map.py" lines_changed="42" />
      </files_modified>
      <notes>Removed dead modality_token import and stale field noqa comment; extracted _select_pair() helper replacing duplicated selection kernel (target pass and passenger pass).</notes>
    </change>
    <change id="C8" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/errors.py" lines_changed="17" />
        <file path="tests/test_guard_coverage.py" lines_changed="4" />
      </files_modified>
      <notes>Removed VersionFloorError and ReviewFlag from errors.py (docstring and classes). Deleted fmri_bids_recon/versions.py (83 lines) and tests/test_versions.py (92 lines, 7 tests). Repointed dcm2niix_version_floor guard to tool_registry/ToolVersionError.</notes>
    </change>
    <change id="C9" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/deface.py" lines_changed="30" />
        <file path="fmri_bids_recon/tool_registry.py" lines_changed="8" />
        <file path="tests/test_deface.py" lines_changed="120" />
      </files_modified>
      <notes>Removed assert_deface_tools(), _resolve_flirt(), and import shutil from deface.py. Enhanced tool_registry.py binary-not-found message with FSLDIR hint for flirt. Removed 10 dead-function tests (6 assert_deface_tools + 4 _resolve_flirt) from test_deface.py.</notes>
    </change>
    <change id="C10" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/pipeline.py" lines_changed="8" />
      </files_modified>
      <notes>Added RegistryDelta import; replaced hasattr duck-typing with direct .new_entries access (Phase 1 and Phase 2); replaced empty-dict fallback with RegistryDelta() default.</notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>10</total_changes>
    <completed>10</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <next_steps>Recommended: run /test to validate all changes. Expected suite count: 611 - 7 (test_versions deleted) - 10 (assert_deface_tools + _resolve_flirt tests deleted) = 594.</next_steps>
</implement_report>
