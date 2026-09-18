<implement_report>
  <meta project="bids-recon" mode="implement" submodule="build" timestamp="2026-09-17T16:15:00Z" />
  <spec_ref>bids-recon_implement_plan_20260917_160000.md</spec_ref>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/config.py" lines_changed="68" />
      </files_modified>
      <notes>Added 7 config fields (scout_keywords, calibration_keywords, norm_tokens, expected_anat_count, registry_mode, label_freeze_mode, rename_detection) to StudyConfig dataclass, _validate_raw parsing with enum validation, _validate_raw return dict, and _resolve_config constructor passthrough. Config-level defaults implement the new relaxed behavior: registry_mode="advisory", rename_detection="warn", label_freeze_mode="frozen".</notes>
    </change>

    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/pipeline.py" lines_changed="7" />
        <file path="fmri_bids_recon/stage4_assemble.py" lines_changed="3" />
      </files_modified>
      <notes>Defense-in-depth crash fix: (1) pipeline.py now deletes excluded BOLD series numbers from the roles dict before the intermediate JSON is built, preventing downstream consumers from referencing excluded series; (2) stage4_assemble.py adds an excluded_sns guard at the top of the per-series assembly loop as a secondary safety net. The excluded_sns computation was moved earlier in pipeline.py (before Stage 3) and the redundant re-computation at its old location was removed.</notes>
    </change>

    <change id="C4" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" lines_changed="1" />
      </files_modified>
      <notes>Fixed _is_spin_echo PSD false positive: replaced substring check `"_se" in psd.lower()` with token-boundary check `"se" in psd.lower().split("_")`, preventing sequences like "_sense" or "_sensePA" from triggering spin-echo detection.</notes>
    </change>

    <change id="C6" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" lines_changed="20" />
      </files_modified>
      <notes>Replaced _SCOUT_KEYWORDS (5 entries) with _DEFAULT_SCOUT_KEYWORDS (12 entries: added aascout, aahscout, locator, scanogram, plan scan, planscan, topogram). Replaced _CALIBRATION_KEYWORDS (2 entries) with _DEFAULT_CALIBRATION_KEYWORDS (5 entries: added _cal_, calibration, coilsurv). Added scout_keywords and calibration_keywords keyword-only parameters to classify() with the expanded frozensets as defaults. Updated both usage sites (scout check and calibration keyword guard) to reference the parameter variables.</notes>
    </change>

    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" lines_changed="25" />
      </files_modified>
      <notes>Added _DEFAULT_NORM_TOKENS frozenset (NORM, PURE, SCIC, CLEAR) and _has_norm_token(s, tokens) helper that checks both image_type_text and image_type fields. Added norm_tokens keyword-only parameter to classify(). Replaced all 5 bare "NORM" string checks in the NORM/ND twin resolution pass with _has_norm_token calls, enabling vendor-agnostic reconstruction variant detection (GE PURE, Philips CLEAR, Siemens SCIC).</notes>
    </change>

    <change id="C5" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" lines_changed="49" />
      </files_modified>
      <notes>Added expected_anat_count keyword-only parameter to classify() and sn_to_series lookup. Replaced the unconditional DUPLICATE_MODALITY warning with a two-key anatomical calibration gate: when expected_anat_count is configured and a modality's count exceeds its expectation, series matching a calibration keyword whose description stem does not match any non-keyword series are demoted to DROP_CALIBRATION. Residual over-counts after demotion produce a HIGH severity DUPLICATE_MODALITY warning. When expected_anat_count is None (default), the original MEDIUM severity DUPLICATE_MODALITY warning is preserved.</notes>
    </change>

    <change id="C7" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/labels.py" lines_changed="30" />
      </files_modified>
      <notes>Added label_freeze_mode keyword-only parameter to resolve_labels() (function default: "frozen"). Added logging and graded_warning imports. Bifurcated the registry-hit branch: "frozen" mode preserves the current LabelDriftError halt behavior; "re-derive" mode re-derives labels fresh using the current session's prefix, emits a HIGH severity LABEL_DRIFT_ADVISORY warning on drift instead of halting, and appends an advisory to delta.warnings.</notes>
    </change>

    <change id="C8" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/labels.py" lines_changed="97" />
      </files_modified>
      <notes>Added rename_detection keyword-only parameter to resolve_labels() (function default: "strict"). Wrapped the rename detection loop with an "off" guard. Bifurcated the match branch: "strict" mode preserves the current TaskRenameError halt; "warn" mode emits a HIGH severity TASK_RENAME_ADVISORY warning and appends an advisory to delta.warnings, allowing processing to continue.</notes>
    </change>

    <change id="C9" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/runs.py" lines_changed="26" />
      </files_modified>
      <notes>Added registry_mode keyword-only parameter to check_volume_counts() (function default: "strict"). Bifurcated the known-series enforcement block: "strict" mode preserves current exclusion behavior; "advisory" mode retains the series in the surviving list and emits a HIGH severity REGISTRY_VOLUME_MISMATCH warning with user_facing=True.</notes>
    </change>

    <change id="C10" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/pipeline.py" lines_changed="18" />
      </files_modified>
      <notes>Wired all 7 config fields to the 3 refactored call sites in pipeline.py Phase 1: classify() receives scout_keywords, calibration_keywords, norm_tokens, and expected_anat_count (converted to frozenset where needed); resolve_labels() receives label_freeze_mode and rename_detection; check_volume_counts() receives registry_mode. Config-level defaults now flow through to function calls, overriding function-level defaults that preserve backward compatibility for direct callers.</notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>10</total_changes>
    <completed>10</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <next_steps>Recommended: run /test to validate all changes. Key test coverage needed: config field parsing and enum validation (C1), excluded-series crash regression (C2), vendor-agnostic norm token detection (C3), PSD false-positive prevention (C4), two-key calibration gate branches (C5), cross-vendor scout/calibration keyword detection (C6), label drift advisory vs halt (C7), rename detection warn/off modes (C8), registry volume advisory vs exclusion (C9), and config-to-function wiring integration (C10).</next_steps>
</implement_report>
