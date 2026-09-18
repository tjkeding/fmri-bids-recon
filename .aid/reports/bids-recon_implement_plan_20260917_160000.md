<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-09-17T16:00:00Z" />
  <input_reports>
    <report path="bids-recon_cr_20260917_145553.md" mode="cr" key_items="9" />
  </input_reports>
  <design_principles>
    Backward compatibility strategy: function-level defaults preserve OLD behavior for test compatibility. Config-level defaults implement NEW behavior. Pipeline call sites pass config values, overriding function defaults. This means:
    - resolve_labels(rename_detection="strict") by default at function level; config.rename_detection="warn" by default
    - check_volume_counts(registry_mode="strict") by default at function level; config.registry_mode="advisory" by default
    - classify() uses expanded keyword/token frozensets as function defaults (superset of old values; no old keywords removed)
    Existing tests that call functions without new parameters get old behavior. The config-driven defaults are the behavioral migration path.
  </design_principles>
  <changes>
    <change id="C1" priority="P1" source_item="CR F1: config schema">
      <file path="fmri_bids_recon/config.py" action="modify" />
      <description>Add 7 config fields to StudyConfig dataclass and the 3-stage loading pipeline (_validate_raw, _resolve_config). All fields are optional with documented defaults.</description>
      <spec>
        1. StudyConfig dataclass (after line 144, after task_registry field):
           Add 7 fields with dataclass defaults:
             scout_keywords: list[str] = field(default_factory=lambda: [
                 "scout", "localizer", "survey", "3-plane", "3plane",
                 "aascout", "aahscout", "locator", "scanogram",
                 "plan scan", "planscan", "topogram",
             ])
             calibration_keywords: list[str] = field(default_factory=lambda: [
                 "setter", "prescan", "_cal_", "calibration", "coilsurv",
             ])
             norm_tokens: list[str] = field(default_factory=lambda: [
                 "NORM", "PURE", "SCIC", "CLEAR",
             ])
             expected_anat_count: dict[str, int] | None = None
             registry_mode: str = "advisory"
             label_freeze_mode: str = "frozen"
             rename_detection: str = "warn"

        2. _validate_raw (after line 248, after schema_version parsing):
           Parse each field from raw dict with defaults. Validate enum fields:
             scout_keywords = list(raw.get("scout_keywords", [...default...]))
             calibration_keywords = list(raw.get("calibration_keywords", [...default...]))
             norm_tokens = list(raw.get("norm_tokens", ["NORM", "PURE", "SCIC", "CLEAR"]))
             expected_anat_count_raw = raw.get("expected_anat_count")
             expected_anat_count = None
             if expected_anat_count_raw is not None:
                 expected_anat_count = {str(k).upper(): int(v) for k, v in expected_anat_count_raw.items()}
             registry_mode = str(raw.get("registry_mode", "advisory"))
             if registry_mode not in ("advisory", "strict"):
                 raise ValueError(...)
             label_freeze_mode = str(raw.get("label_freeze_mode", "frozen"))
             if label_freeze_mode not in ("frozen", "re-derive"):
                 raise ValueError(...)
             rename_detection = str(raw.get("rename_detection", "warn"))
             if rename_detection not in ("strict", "warn", "off"):
                 raise ValueError(...)
           Add all 7 fields to the return dict (line 282-292).

        3. _resolve_config (line 378-391):
           Pass 7 fields through to StudyConfig constructor from validated dict.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - additive fields with defaults; no existing logic affected</risk>
      <rollback>Remove fields from StudyConfig, _validate_raw return dict, and _resolve_config constructor call</rollback>
    </change>

    <change id="C2" priority="P0" source_item="CR F3/brainstorm T1: excluded-series crash fix">
      <file path="fmri_bids_recon/pipeline.py" action="modify" />
      <file path="fmri_bids_recon/stage4_assemble.py" action="modify" />
      <description>Defense in depth: (1) remove excluded BOLD series from roles dict before saving to intermediate JSON, (2) add skip-excluded guard at top of assembly loop.</description>
      <spec>
        1. pipeline.py, Phase 1, after check_volume_counts and before intermediate dict (between lines 204 and 258):
           Insert:
             excluded_sns = {e.series.series_number for e in excluded}
             for sn in excluded_sns:
                 if sn in roles:
                     del roles[sn]

        2. stage4_assemble.py, assemble() function, per-series loop (line 314):
           Build excluded series_number set and add early continue:
             excluded_sns = {e.series.series_number for e in excluded}
           Change loop body opening:
             for snum, role in roles.items():
                 if snum in excluded_sns:
                     continue
                 series = series_map[snum]
      </spec>
      <dependencies>none</dependencies>
      <risk>low - removes crash path; excluded series already routed via separate excluded list</risk>
      <rollback>Remove the del loop in pipeline.py; remove the excluded_sns guard in stage4_assemble.py</rollback>
    </change>

    <change id="C3" priority="P1" source_item="CR F2/brainstorm T2: configurable norm tokens">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>Define _has_norm_token helper checking both image_type_text and image_type. Replace all bare "NORM" checks in the NORM/ND twin resolution pass with calls to this helper parameterized by the norm_tokens keyword argument.</description>
      <spec>
        1. Add module-level default frozenset (near line 189):
             _DEFAULT_NORM_TOKENS = frozenset({"NORM", "PURE", "SCIC", "CLEAR"})

        2. Define helper (near line 190):
             def _has_norm_token(s: Series, tokens: frozenset[str]) -> bool:
                 for tok in tokens:
                     if tok in s.image_type_text:
                         return True
                     if tok in s.image_type:
                         return True
                 return False

        3. Add norm_tokens keyword parameter to classify() signature:
             def classify(
                 series: list[Series],
                 *,
                 ...,
                 norm_tokens: frozenset[str] = _DEFAULT_NORM_TOKENS,
                 ...,
             ) -> tuple[dict[int, Role], list[dict]]:

        4. Replace bare "NORM" checks in the NORM/ND pass:
           Line 428: any("NORM" in s.image_type_text for s in series)
             -> any(_has_norm_token(s, norm_tokens) for s in series)
           Line 444: "NORM" not in s.image_type_text
             -> not _has_norm_token(s, norm_tokens)
           Line 464: "NORM" not in s.image_type_text
             -> not _has_norm_token(s, norm_tokens)
           Line 476: [s for s in group if "NORM" in s.image_type_text]
             -> [s for s in group if _has_norm_token(s, norm_tokens)]
           Line 477: [s for s in group if "NORM" not in s.image_type_text]
             -> [s for s in group if not _has_norm_token(s, norm_tokens)]
      </spec>
      <dependencies>C1</dependencies>
      <risk>low - default includes "NORM"; Siemens behavior unchanged; new tokens only activate on GE/Philips data</risk>
      <rollback>Remove helper; restore bare "NORM" string checks</rollback>
    </change>

    <change id="C4" priority="P1" source_item="CR F3/brainstorm T3a: spin-echo PSD token fix">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>Fix _is_spin_echo PSD false positive on Siemens sequences containing "_se" as a substring (e.g. "_sense", "_sensePA"). Replace substring check with token-boundary check.</description>
      <spec>
        Line 123, inside _is_spin_echo, Siemens branch:
          OLD: if isinstance(psd, str) and "_se" in psd.lower():
          NEW: if isinstance(psd, str) and "se" in psd.lower().split("_"):
      </spec>
      <dependencies>none</dependencies>
      <risk>low - targeted fix within Siemens vendor branch; split("_") preserves "se" detection while excluding "_sense" etc.</risk>
      <rollback>Revert to substring check</rollback>
    </change>

    <change id="C5" priority="P1" source_item="CR F1/brainstorm T3b: two-key anatomical calibration gate">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>Add a post-NORM/ND calibration pass for T1W/T2W that requires BOTH (a) expected_anat_count exceeded AND (b) calibration keyword match with description_stem mismatch before demoting to DROP_CALIBRATION. When only count is exceeded without keyword match, elevate the existing DUPLICATE_MODALITY warning to HIGH severity.</description>
      <spec>
        1. Add expected_anat_count keyword parameter to classify() signature:
             def classify(
                 series: list[Series],
                 *,
                 ...,
                 expected_anat_count: dict[str, int] | None = None,
             ) -> tuple[dict[int, Role], list[dict]]:

        2. Build a series_number-to-Series lookup at the top of classify() (before the main loop, after line 238):
             sn_to_series = {s.series_number: s for s in series}

        3. Insert new pass after the DUPLICATE_MODALITY check (after line 504, before the calibration PE axis pass at line 508). Replace the existing DUPLICATE_MODALITY check (lines 494-504) with the two-key logic:

           if expected_anat_count is not None:
               for suffix, role_str in ((Role.T1W, "T1W"), (Role.T2W, "T2W")):
                   expected = expected_anat_count.get(role_str)
                   if expected is None:
                       continue
                   anat_sns = [sn for sn, r in roles.items() if r == suffix]
                   if len(anat_sns) <= expected:
                       continue
                   # Count exceeds expectation: collect non-keyword stems
                   non_kw_stems: set[str] = set()
                   for sn in anat_sns:
                       s = sn_to_series[sn]
                       if not any(kw in s.description.lower() for kw in calibration_keywords):
                           non_kw_stems.add(description_stem(s.description))
                   for sn in list(anat_sns):
                       s = sn_to_series[sn]
                       if any(kw in s.description.lower() for kw in calibration_keywords):
                           stem = description_stem(s.description)
                           if stem not in non_kw_stems:
                               roles[sn] = Role.DROP_CALIBRATION
                               flags.append(graded_warning(
                                   _logger, SEVERITY_HIGH, "ANAT_CALIBRATION_DEMOTION",
                                   f"Series {sn} ({role_str}) matches calibration keyword "
                                   f"and count ({len(anat_sns)}) exceeds expected ({expected}); "
                                   f"demoted to DROP_CALIBRATION.",
                               ))
                   # Re-check: if still over count after demotions and no keyword matches found
                   remaining = sum(1 for sn, r in roles.items() if r == suffix)
                   if remaining > expected:
                       flags.append(graded_warning(
                           _logger, SEVERITY_HIGH, "DUPLICATE_MODALITY",
                           f"{remaining} series classified as {suffix.value} after "
                           f"calibration demotion; expected {expected}. Manual review recommended.",
                       ))
           else:
               # No expected_anat_count configured: preserve current DUPLICATE_MODALITY warning
               for role_check in (Role.T1W, Role.T2W):
                   count = sum(1 for r in roles.values() if r == role_check)
                   if count > 1:
                       flags.append(graded_warning(
                           _logger, SEVERITY_MEDIUM, "DUPLICATE_MODALITY",
                           f"{count} series classified as {role_check.value} after "
                           f"classification; only one expected per session. "
                           f"Manual review recommended.",
                       ))
      </spec>
      <dependencies>C1, C3 (two-key gate runs after NORM/ND pass which uses norm_tokens)</dependencies>
      <risk>medium - new logic path; when expected_anat_count is None (default), falls through to current behavior. Requires test coverage for all gate branches.</risk>
      <rollback>Remove the two-key gate block; restore original lines 494-504</rollback>
    </change>

    <change id="C6" priority="P1" source_item="CR F1: config-driven scout keywords">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>Replace _SCOUT_KEYWORDS frozenset with a configurable parameter. Existing module-level default expands to 12 entries (cross-vendor coverage).</description>
      <spec>
        1. Replace _SCOUT_KEYWORDS (line 188) with expanded default:
             _DEFAULT_SCOUT_KEYWORDS = frozenset({
                 "scout", "localizer", "survey", "3-plane", "3plane",
                 "aascout", "aahscout", "locator", "scanogram",
                 "plan scan", "planscan", "topogram",
             })
           Remove the old: _SCOUT_KEYWORDS = frozenset({"scout", "localizer", "survey", "3-plane", "3plane"})

        2. Replace _CALIBRATION_KEYWORDS (line 189) with expanded default:
             _DEFAULT_CALIBRATION_KEYWORDS = frozenset({
                 "setter", "prescan", "_cal_", "calibration", "coilsurv",
             })
           Remove the old: _CALIBRATION_KEYWORDS = frozenset({"setter", "prescan"})

        3. Add keyword parameters to classify() signature:
             def classify(
                 series: list[Series],
                 *,
                 scout_keywords: frozenset[str] = _DEFAULT_SCOUT_KEYWORDS,
                 calibration_keywords: frozenset[str] = _DEFAULT_CALIBRATION_KEYWORDS,
                 norm_tokens: frozenset[str] = _DEFAULT_NORM_TOKENS,
                 expected_anat_count: dict[str, int] | None = None,
             ) -> tuple[dict[int, Role], list[dict]]:

        4. Update usage in Rule 2 Signal 3 (line 273):
             OLD: if any(kw in desc_lower for kw in _SCOUT_KEYWORDS):
             NEW: if any(kw in desc_lower for kw in scout_keywords):

        5. Update usage in calibration keyword guard (line 566):
             OLD: if not any(kw in desc_lower for kw in _CALIBRATION_KEYWORDS):
             NEW: if not any(kw in desc_lower for kw in calibration_keywords):
      </spec>
      <dependencies>C1</dependencies>
      <risk>low - superset of old keywords; all old matches still match; new matches only activate on non-Siemens data</risk>
      <rollback>Restore _SCOUT_KEYWORDS and _CALIBRATION_KEYWORDS frozensets; revert classify() signature</rollback>
    </change>

    <change id="C7" priority="P1" source_item="CR F4: label freeze mode">
      <file path="fmri_bids_recon/labels.py" action="modify" />
      <description>Add label_freeze_mode parameter to resolve_labels. When "frozen" (function default): current behavior. When "re-derive": re-derive labels fresh; emit HIGH warning on drift instead of LabelDriftError halt.</description>
      <spec>
        1. Add parameter to resolve_labels signature (line 203):
             def resolve_labels(
                 series_by_role: dict[int, tuple[Series, Role]],
                 registry: dict[str, TaskRegistryEntry],
                 *,
                 label_freeze_mode: str = "frozen",
                 rename_detection: str = "strict",
             ) -> tuple[dict[int, str], RegistryDelta]:

        2. Import graded_warning at top of labels.py:
             from .warnings import graded_warning, SEVERITY_HIGH

        3. Refactor the registry-hit branch (lines 294-313):
             for desc in unique_descs:
                 if desc in registry:
                     if label_freeze_mode == "frozen":
                         # Current behavior: frozen label reuse + drift guard
                         frozen_label = registry[desc].label
                         stored_prefix = registry[desc].prefix if registry[desc].prefix is not None else prefix
                         re_derived = derive_task_label(desc, stored_prefix)
                         if re_derived != frozen_label:
                             raise LabelDriftError(...)
                         desc_to_label[desc] = frozen_label
                     else:
                         # "re-derive": fresh derivation, registry for consistency warning only
                         re_derived = derive_task_label(desc, prefix)
                         frozen_label = registry[desc].label
                         if re_derived != frozen_label:
                             delta.warnings.append(
                                 f"Label drift: '{desc}' re-derives to '{re_derived}' "
                                 f"(registry: '{frozen_label}'). Using re-derived label."
                             )
                             graded_warning(
                                 logging.getLogger(__name__), SEVERITY_HIGH,
                                 "LABEL_DRIFT_ADVISORY",
                                 f"SeriesDescription '{desc}' re-derives to '{re_derived}' "
                                 f"but registry records '{frozen_label}'. "
                                 f"label_freeze_mode='re-derive': using '{re_derived}'.",
                             )
                         desc_to_label[desc] = re_derived
                 else:
                     # ... existing auto-derive logic unchanged ...
      </spec>
      <dependencies>C1</dependencies>
      <risk>medium - function default "frozen" preserves old behavior; "re-derive" is new path activated only via config. Needs test coverage for the advisory branch.</risk>
      <rollback>Remove label_freeze_mode parameter; restore unconditional frozen-label branch</rollback>
    </change>

    <change id="C8" priority="P1" source_item="CR F4: rename detection mode">
      <file path="fmri_bids_recon/labels.py" action="modify" />
      <description>Add rename_detection parameter to resolve_labels. When "strict" (function default): current behavior (TaskRenameError halt). When "warn": emit HIGH warning, continue. When "off": skip rename detection entirely.</description>
      <spec>
        1. Parameter already added in C7 spec (rename_detection: str = "strict").

        2. Wrap the rename detection loop (lines 330-365):
             if rename_detection != "off":
                 for old_desc in old_registry_descs:
                     old_label = registry[old_desc].label
                     old_sigs = set(all_sig_by_desc.get(old_desc, set()))
                     stored_sig = getattr(registry[old_desc], "signature", None)
                     if stored_sig is not None:
                         old_sigs.add(stored_sig)
                     sig_match = bool(new_sigs & old_sigs)
                     label_match = (new_label == old_label)
                     if sig_match or label_match:
                         if rename_detection == "strict":
                             raise TaskRenameError(...)
                         else:
                             # "warn": advisory, continue processing
                             delta.warnings.append(
                                 f"Possible rename: '{desc}' -> '{old_desc}' "
                                 f"({'signature match' if sig_match else 'label match'})."
                             )
                             graded_warning(
                                 logging.getLogger(__name__), SEVERITY_HIGH,
                                 "TASK_RENAME_ADVISORY",
                                 f"New description '{desc}' (label '{new_label}') "
                                 f"{'shares acquisition signature with' if sig_match else 'derives same label as'} "
                                 f"old registry description '{old_desc}' (label '{old_label}'). "
                                 f"rename_detection='warn': processing continues.",
                             )
      </spec>
      <dependencies>C1, C7 (signature shared)</dependencies>
      <risk>medium - function default "strict" preserves old behavior; "warn" is new path. Config default "warn" changes upgrade behavior (see design principles note above).</risk>
      <rollback>Remove rename_detection parameter; restore unconditional TaskRenameError raise</rollback>
    </change>

    <change id="C9" priority="P2" source_item="CR F3/brainstorm T4: registry volume enforcement mode">
      <file path="fmri_bids_recon/runs.py" action="modify" />
      <description>Add registry_mode parameter to check_volume_counts. When "strict" (function default): current exact-match exclusion. When "advisory": emit HIGH warning instead of excluding; series passes to surviving list.</description>
      <spec>
        1. Add parameter to check_volume_counts signature (line 44):
             def check_volume_counts(
                 bolds: list[tuple[Series, str]],
                 registry: dict[str, TaskRegistryEntry],
                 *,
                 registry_mode: str = "strict",
             ) -> tuple[...]:

        2. Refactor known-series enforcement (lines 101-114):
             for series, task_label in known:
                 expected = registry[series.description].expected_volumes
                 if series.n_volumes == expected:
                     surviving_bolds.append((series, task_label))
                 else:
                     if registry_mode == "strict":
                         excluded_list.append(Excluded(
                             series=series, task_label=task_label,
                             observed_volumes=series.n_volumes,
                             expected_volumes=expected,
                         ))
                     else:
                         # "advisory": warn but do not exclude
                         surviving_bolds.append((series, task_label))
                         review_flags.append(graded_warning(
                             _logger, SEVERITY_HIGH, "REGISTRY_VOLUME_MISMATCH",
                             f"Task {task_label!r} series {series.series_number}: "
                             f"n_volumes={series.n_volumes} vs registry expected "
                             f"{expected}. registry_mode='advisory': series retained.",
                             user_facing=True,
                         ))
      </spec>
      <dependencies>C1</dependencies>
      <risk>medium - function default "strict" preserves old behavior for tests; config default "advisory" relaxes enforcement for pipeline runs</risk>
      <rollback>Remove registry_mode parameter; restore unconditional exclusion</rollback>
    </change>

    <change id="C10" priority="P1" source_item="CR F1: config field wiring">
      <file path="fmri_bids_recon/pipeline.py" action="modify" />
      <description>Wire config fields to the refactored function signatures at all Phase 1 call sites.</description>
      <spec>
        1. classify() call (line 189):
             OLD: roles, review_flags = classify(all_series)
             NEW: roles, review_flags = classify(
                 all_series,
                 scout_keywords=frozenset(config.scout_keywords),
                 calibration_keywords=frozenset(config.calibration_keywords),
                 norm_tokens=frozenset(config.norm_tokens),
                 expected_anat_count=config.expected_anat_count,
             )

        2. resolve_labels() call (line 195):
             OLD: labels_dict, registry_delta = resolve_labels(series_by_role, config.task_registry)
             NEW: labels_dict, registry_delta = resolve_labels(
                 series_by_role, config.task_registry,
                 label_freeze_mode=config.label_freeze_mode,
                 rename_detection=config.rename_detection,
             )

        3. check_volume_counts() call (line 201):
             OLD: surviving, excluded, vol_updates, vol_flags = check_volume_counts(bolds, config.task_registry)
             NEW: surviving, excluded, vol_updates, vol_flags = check_volume_counts(
                 bolds, config.task_registry,
                 registry_mode=config.registry_mode,
             )
      </spec>
      <dependencies>C1, C3, C5, C6, C7, C8, C9</dependencies>
      <risk>low - wiring only; all new parameters have function-level defaults so pipeline works even if wiring is partially applied</risk>
      <rollback>Revert to single-line calls without keyword arguments</rollback>
    </change>
  </changes>
  <execution_order>C1, C2, C4, C6, C3, C5, C7, C8, C9, C10</execution_order>
  <notes>
    Behavioral migration: config defaults for registry_mode ("advisory") and rename_detection ("warn") differ from the old implicit behavior ("strict" for both). Existing installations that upgrade without adding these fields to their config YAML will see:
    (1) Volume count mismatches that previously excluded series will now produce HIGH warnings instead.
    (2) Rename detection that previously halted will now produce HIGH warnings instead.
    These are deliberate relaxations per the CR's design principle that cross-participant state should inform but not block per-participant processing. Sites that require strict enforcement can set registry_mode: "strict" and rename_detection: "strict" in their config YAML. Document this in the changelog as a behavioral change.

    Test coverage: all 10 changes need /test coverage. In particular:
    - C1: config field parsing, validation of enum values, defaults when fields omitted
    - C2: regression test confirming no KeyError when excluded BOLD is in roles
    - C3: NORM/ND pass with GE PURE token, with Philips CLEAR token, with mixed tokens
    - C4: PSD strings containing "_sense", "_sensePA" no longer false-positive
    - C5: two-key gate branches (both keys met, only count exceeded, count at or below, null expected_anat_count)
    - C6: non-Siemens scout descriptions ("Locator", "Scanogram", "Plan Scan") correctly detected
    - C7: label_freeze_mode="re-derive" produces warning instead of LabelDriftError
    - C8: rename_detection="warn" produces warning instead of TaskRenameError; "off" skips entirely
    - C9: registry_mode="advisory" produces warning instead of exclusion
    - C10: integration test confirming config values flow through to classification, labeling, volume checks

    C3, C5, and C6 all modify the classify() signature. The final classify() signature after all three:
      def classify(
          series: list[Series],
          *,
          scout_keywords: frozenset[str] = _DEFAULT_SCOUT_KEYWORDS,
          calibration_keywords: frozenset[str] = _DEFAULT_CALIBRATION_KEYWORDS,
          norm_tokens: frozenset[str] = _DEFAULT_NORM_TOKENS,
          expected_anat_count: dict[str, int] | None = None,
      ) -> tuple[dict[int, Role], list[dict]]:

    C7 and C8 both modify the resolve_labels() signature. The final resolve_labels() signature after both:
      def resolve_labels(
          series_by_role: dict[int, tuple[Series, Role]],
          registry: dict[str, TaskRegistryEntry],
          *,
          label_freeze_mode: str = "frozen",
          rename_detection: str = "strict",
      ) -> tuple[dict[int, str], RegistryDelta]:
  </notes>
</implement_plan>
