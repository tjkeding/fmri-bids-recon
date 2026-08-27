<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-08-24T17:32:24Z" />
  <input_reports>
    <report path="bids-recon_brainstorm_20260824_171259.md" mode="brainstorm" key_items="14" />
  </input_reports>
  <changes>

    <!-- ================================================================== -->
    <!-- FILE: warnings.py                                                   -->
    <!-- ================================================================== -->

    <change id="C1" priority="P1" source_item="T3">
      <file path="fmri_bids_recon/warnings.py" action="modify" />
      <description>Add user_facing key to graded_warning return dict. Completes the cross-pipeline four-key contract {severity, code, message, user_facing}.</description>
      <spec>
        In graded_warning() (line 29-33), add `"user_facing": user_facing` to the return dict:

        ```python
        return {
            "severity": severity,
            "code": code,
            "message": message,
            "user_facing": user_facing,
        }
        ```
      </spec>
      <dependencies>none</dependencies>
      <risk>low - additive dict key; no existing consumer accesses user_facing so no breakage</risk>
      <rollback>Remove the "user_facing" key from the return dict.</rollback>
    </change>

    <change id="C2" priority="P1" source_item="T4">
      <file path="fmri_bids_recon/warnings.py" action="modify" />
      <description>Add module-level warning accumulator with get_warnings()/clear_warnings() API. graded_warning() auto-appends each return dict to the accumulator.</description>
      <spec>
        1. After the severity constants (after line 14), add:

        ```python
        _WARNING_ACCUMULATOR: list[dict] = []


        def get_warnings() -> list[dict]:
            return list(_WARNING_ACCUMULATOR)


        def clear_warnings() -> None:
            _WARNING_ACCUMULATOR.clear()
        ```

        2. In graded_warning(), assign the return dict to a local variable, append it to _WARNING_ACCUMULATOR, then return it:

        ```python
        def graded_warning(
            logger: logging.Logger,
            severity: str,
            code: str,
            message: str,
            *,
            user_facing: bool = False,
        ) -> dict:
            level = logging.WARNING if user_facing else logging.INFO
            prefix = f"[{severity}:{code}]"
            full_message = f"{prefix} {message}"
            logger.log(level, full_message)
            result = {
                "severity": severity,
                "code": code,
                "message": message,
                "user_facing": user_facing,
            }
            _WARNING_ACCUMULATOR.append(result)
            return result
        ```
      </spec>
      <dependencies>C1</dependencies>
      <risk>low - accumulator is append-only; existing consumers continue to use the return value unchanged</risk>
      <rollback>Remove _WARNING_ACCUMULATOR, get_warnings(), clear_warnings(), and the append call.</rollback>
    </change>

    <!-- ================================================================== -->
    <!-- FILE: stage2_classify.py                                            -->
    <!-- ================================================================== -->

    <change id="C3" priority="P1" source_item="T5/C1, T5/C6">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>Add _SCOUT_KEYWORDS module constant and _is_epi_bold_physics() helper function for vendor-agnostic BOLD inference.</description>
      <spec>
        1. After _bval_exists/_has_nonzero_bval helpers (after line 126), add the _SCOUT_KEYWORDS constant and _is_epi_bold_physics helper:

        ```python
        _SCOUT_KEYWORDS = frozenset({"scout", "localizer", "survey", "3-plane", "3plane"})


        def _is_epi_bold_physics(s: Series) -> bool:
            return (
                s.mr_acquisition_type == "2D"
                and "EP" in s.scanning_sequence
                and s.n_volumes >= 10
                and not _bval_exists(s)
            )
        ```
      </spec>
      <dependencies>none</dependencies>
      <risk>low - new private symbols; no existing code affected until C4-C9 consume them</risk>
      <rollback>Remove both definitions.</rollback>
    </change>

    <change id="C4" priority="P1" source_item="T5/C6">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>Rule 2: add multi-signal scout/localizer detection for GE and Philips scanners. Three detection signals: (1) existing Siemens DIS2D check, (2) LOCALIZER token in ImageType, (3) description keyword match with physics confirmation.</description>
      <spec>
        Replace the current Rule 2 block (lines 174-181) with:

        ```python
        # Rule 2: DROP_SCOUT
        # Signal 1: Siemens DIS2D mosaic scout
        if (
            "DIS2D" in s.image_type_text
            and s.mr_acquisition_type == "2D"
            and s.multiband_factor is None
        ):
            roles[s.series_number] = Role.DROP_SCOUT
            continue

        # Signal 2: LOCALIZER token in ImageType (vendor-agnostic)
        if "LOCALIZER" in s.image_type:
            roles[s.series_number] = Role.DROP_SCOUT
            continue

        # Signal 3: description keyword match with physics guard
        desc_lower = s.description.lower()
        if any(kw in desc_lower for kw in _SCOUT_KEYWORDS):
            if s.mr_acquisition_type == "2D" and s.n_volumes <= 3:
                roles[s.series_number] = Role.DROP_SCOUT
                continue
        ```

        Note: Signal 1 is the existing check, preserved verbatim. Signals 2 and 3 are new.
      </spec>
      <dependencies>C3 (_SCOUT_KEYWORDS)</dependencies>
      <risk>medium - new scout detection could catch non-scout series if description contains "scout" or "localizer" as a substring. The physics guard (2D + n_volumes <= 3) mitigates this: real BOLD/DWI series have n_volumes >> 3.</risk>
      <rollback>Revert to the original single-signal DIS2D check.</rollback>
    </change>

    <change id="C5" priority="P1" source_item="T5/C2">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>Rule 3: add physics pass-through for EPI BOLD. When _is_epi_bold_physics matches, pass through instead of raising NavigatorDropError. Preserves the halt for genuinely aberrant non-EPI-BOLD multi-volume series.</description>
      <spec>
        Replace the Rule 3 block (lines 183-194) with:

        ```python
        # Rule 3: DROP_NAVIGATOR
        if s.n_volumes > 1 and tok not in {"FMRI", "DIFFUSION"}:
            if "EP" in s.scanning_sequence:
                if _is_epi_bold_physics(s):
                    pass
                else:
                    raise NavigatorDropError(
                        f"Series {s.series_number} is multi-volume EPI physics "
                        f"(ImageType[2]={tok!r}, SoftwareVersions={s.software_versions!r}) "
                        f"and would be dropped as a navigator; halting for adjudication.",
                        context={"series_number": s.series_number,
                                 "image_type": list(s.image_type),
                                 "software_versions": s.software_versions})
            else:
                roles[s.series_number] = Role.DROP_NAVIGATOR
                continue
        ```

        When _is_epi_bold_physics matches (2D EPI, n_volumes >= 10, no bval): execution falls through to Rule 4+, where Rule 8 (broadened in C7) classifies it as BOLD. When the physics check fails: NavigatorDropError halts for manual adjudication (preserving the existing safety). Non-EPI multi-volume series are still dropped as navigators (the else branch).
      </spec>
      <dependencies>C3 (_is_epi_bold_physics)</dependencies>
      <risk>medium - EPI series that pass the physics check but are not genuine BOLD would fall through to downstream rules. The n_volumes >= 10 threshold and downstream volume-count guard mitigate this.</risk>
      <rollback>Revert to the original conditional that raises unconditionally for EP series.</rollback>
    </change>

    <change id="C6" priority="P1" source_item="T5/C3">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>Rule 5: broaden FMAP_FUNC from tok == "FMRI" to vendor-agnostic EPI detection. A functional fieldmap is a single-volume spin-echo EPI that is not diffusion.</description>
      <spec>
        Replace the Rule 5 condition (lines 231-232) `tok == "FMRI"` with:

        ```python
        # Rule 5: FMAP_FUNC
        if (
            tok != "DIFFUSION"
            and "EP" in s.scanning_sequence
            and _is_spin_echo(s)
            and "GR" not in s.scanning_sequence
            and s.n_volumes == 1
        ):
            roles[s.series_number] = Role.FMAP_FUNC
            continue
        ```

        The change replaces `tok == "FMRI"` with `tok != "DIFFUSION" and "EP" in s.scanning_sequence`. This catches functional fieldmaps on GE (tok="OTHER") and Philips/Siemens-pre-XA (tok="M") while preserving the exclusion of diffusion fieldmaps (handled by Rule 6).
      </spec>
      <dependencies>none</dependencies>
      <risk>low - the additional guards (_is_spin_echo, no GR, n_volumes==1) are unchanged; only the token guard is broadened</risk>
      <rollback>Revert tok condition to `tok == "FMRI"`.</rollback>
    </change>

    <change id="C7" priority="P1" source_item="T5/C4">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>Rule 8: broaden BOLD from tok == "FMRI" to include physics-based BOLD inference.</description>
      <spec>
        Replace the Rule 8 condition (line 261) with:

        ```python
        # Rule 8: BOLD
        if (tok == "FMRI" or _is_epi_bold_physics(s)) and s.n_volumes > 1:
            roles[s.series_number] = Role.BOLD
            continue
        ```

        The `tok == "FMRI"` path is preserved for backward compatibility with Siemens XA data. The `_is_epi_bold_physics(s)` path adds vendor-agnostic BOLD detection (2D EPI, n_volumes >= 10, no bval).
      </spec>
      <dependencies>C3 (_is_epi_bold_physics)</dependencies>
      <risk>low - the physics check is strictly narrower than the original (adds n_volumes >= 10 and no-bval constraints)</risk>
      <rollback>Revert to `tok == "FMRI" and s.n_volumes > 1`.</rollback>
    </change>

    <change id="C8" priority="P1" source_item="T5/C5">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>Merge Rules 9 and 9b into a single vendor-agnostic SBRef rule. Entry condition: single-volume EPI (any ImageType[2] token). Look-ahead determines SBREF vs DWI_SBREF.</description>
      <spec>
        Replace Rules 9 and 9b (lines 265-306) with a single merged rule:

        ```python
        # Rule 9: SBRef (functional or diffusion)
        if s.n_volumes == 1 and "EP" in s.scanning_sequence:
            pos = next(
                (i for i, t in enumerate(by_time) if t.series_number == s.series_number),
                None,
            )
            if pos is not None and pos + 1 < len(by_time):
                nxt = by_time[pos + 1]
                same_stem = _description_stem(s.description) == _description_stem(nxt.description)
                if same_stem:
                    nxt_tok = modality_token(nxt)
                    if (nxt_tok == "FMRI" or _is_epi_bold_physics(nxt)) and nxt.n_volumes > 1:
                        roles[s.series_number] = Role.SBREF
                        continue
                    if nxt_tok == "DIFFUSION" and _bval_exists(nxt):
                        roles[s.series_number] = Role.DWI_SBREF
                        continue
        ```

        Changes from original:
        - Entry guard: `s.n_volumes == 1 and "EP" in s.scanning_sequence` replaces `tok == "FMRI" and s.n_volumes == 1` (Rule 9) and `tok == "M" and s.n_volumes == 1 and "EP" in s.scanning_sequence` (Rule 9b).
        - BOLD look-ahead: `(nxt_tok == "FMRI" or _is_epi_bold_physics(nxt)) and nxt.n_volumes > 1` replaces `nxt_tok == "FMRI" and nxt.n_volumes > 1`.
        - DWI look-ahead: unchanged from Rule 9b.
        - Single pos lookup shared between both branches (eliminates duplicated chronological search).
      </spec>
      <dependencies>C3 (_is_epi_bold_physics)</dependencies>
      <risk>medium - broader entry guard catches more single-volume EPI series. Mitigated by the same_stem + next-series look-ahead: only classifies as SBRef when the next chronological series with matching description is BOLD or DWI.</risk>
      <rollback>Restore separate Rule 9 and Rule 9b blocks.</rollback>
    </change>

    <change id="C9" priority="P1" source_item="T5/C7">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>Guard the NORM/ND twin resolution pass with Siemens-specific detection (skip when no NORM tokens present). Add a duplicate modality guard for T1W/T2W that emits a graded_warning when more than one series of the same modality survives after all classification.</description>
      <spec>
        1. Add SEVERITY_HIGH to the existing import from .warnings (line 19):
        ```python
        from .warnings import graded_warning, SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH
        ```

        2. Replace the NORM/ND pass (lines 311-377) with a guarded version:

        ```python
        # ------------------------------------------------------------------
        # Anatomical NORM / ND twin resolution pass (Siemens-specific)
        # ------------------------------------------------------------------
        has_norm = any("NORM" in s.image_type_text for s in series)
        if has_norm:
            for suffix, drop_role in (
                (Role.T1W, Role.DROP_ANAT_ND_T1W),
                (Role.T2W, Role.DROP_ANAT_ND_T2W),
            ):
                seen_sn: set[int] = set()
                anat_series: list[Series] = []
                for s in series:
                    if s.series_number not in seen_sn and roles.get(s.series_number) == suffix:
                        anat_series.append(s)
                        seen_sn.add(s.series_number)

                if len(anat_series) < 2:
                    for s in anat_series:
                        if "NORM" not in s.image_type_text:
                            flags.append(
                                graded_warning(
                                    _logger, SEVERITY_LOW, "UNCLASSIFIED_SERIES",
                                    f"Series {s.series_number} ({suffix.value}) has no "
                                    f"NORM reconstruction and no ND twin; manual review required.",
                                )
                            )
                    continue

                by_geometry: dict[tuple[int, int, int], list[Series]] = {}
                for s in anat_series:
                    by_geometry.setdefault(s.matrix, []).append(s)

                for geometry, group in by_geometry.items():
                    if len(group) < 2:
                        s = group[0]
                        if "NORM" not in s.image_type_text:
                            flags.append(
                                graded_warning(
                                    _logger, SEVERITY_LOW, "NAVIGATOR_CANDIDATE",
                                    f"Series {s.series_number} ({suffix.value}) has no "
                                    f"NORM reconstruction and no ND twin at geometry "
                                    f"{geometry}; manual review required.",
                                )
                            )
                        continue

                    norm_members = [s for s in group if "NORM" in s.image_type_text]
                    nd_members = [s for s in group if "NORM" not in s.image_type_text]

                    if norm_members and nd_members:
                        for s in nd_members:
                            roles[s.series_number] = drop_role
                    elif not norm_members:
                        for s in group:
                            flags.append(
                                graded_warning(
                                    _logger, SEVERITY_MEDIUM, "AMBIGUOUS_CLASSIFICATION",
                                    f"Series {s.series_number} ({suffix.value}) is in a "
                                    f"paired group at geometry {geometry} but no NORM "
                                    f"reconstruction found; manual review required.",
                                )
                            )

        # ------------------------------------------------------------------
        # Duplicate modality guard (vendor-agnostic)
        # ------------------------------------------------------------------
        for role_check in (Role.T1W, Role.T2W):
            count = sum(1 for r in roles.values() if r == role_check)
            if count > 1:
                flags.append(
                    graded_warning(
                        _logger, SEVERITY_MEDIUM, "DUPLICATE_MODALITY",
                        f"{count} series classified as {role_check.value} after "
                        f"classification; only one expected per session. "
                        f"Manual review recommended.",
                    )
                )
        ```

        The NORM/ND pass body is IDENTICAL to the original; only the outer `if has_norm:` guard and indentation change. The duplicate modality guard is new code placed after the NORM/ND block (runs unconditionally).
      </spec>
      <dependencies>none (uses existing graded_warning import; add SEVERITY_HIGH to import line)</dependencies>
      <risk>low - the NORM/ND pass body is unchanged; only the entry guard is new. The duplicate modality guard is advisory (medium severity, non-blocking).</risk>
      <rollback>Remove the `if has_norm:` guard (unindent NORM/ND body); remove the duplicate modality guard block.</rollback>
    </change>

    <!-- ================================================================== -->
    <!-- FILE: stage1_convert.py                                             -->
    <!-- ================================================================== -->

    <change id="C10" priority="P1" source_item="T5/C8">
      <file path="fmri_bids_recon/stage1_convert.py" action="modify" />
      <description>Add dcm2niix -i y flag to skip truly single-slice 2D images, derived images, and localizer images at conversion time. Safe for all multi-slice BOLD data.</description>
      <spec>
        In convert_to_staging(), add `-i y` to the dcm2niix command (lines 86-94). Insert after the `-ba n` pair:

        ```python
        cmd = [
            dcm2niix,
            "-ba", "n",
            "-i", "y",
            "-b", "y",
            "-z", "y",
            "-f", "%s_%d",
            "-o", str(staging),
            str(source),
        ]
        ```

        Add an inline comment alongside the existing flags block (lines 81-84):
        ```
        # -i  y : ignore derived/localizer/single-slice images
        ```
      </spec>
      <dependencies>none</dependencies>
      <risk>low - -i y only skips truly single-slice 2D (xyzDim[3] < 2 AND mosaicSlices < 2), derived, and localizer images. Confirmed safe for multi-slice BOLD by dcm2niix source code analysis.</risk>
      <rollback>Remove `-i y` from the cmd list.</rollback>
    </change>

    <!-- ================================================================== -->
    <!-- FILE: pipeline.py                                                   -->
    <!-- ================================================================== -->

    <change id="C11" priority="P1" source_item="T4 (pipeline-side)">
      <file path="fmri_bids_recon/pipeline.py" action="modify" />
      <description>Adopt warning accumulator in pipeline.py: import get_warnings/clear_warnings, call clear_warnings() at pipeline entry, replace all_review_flags with get_warnings() for status determination and BidsReconResult.warnings. Remove manual all_review_flags accumulation (lines 135, 203, 298).</description>
      <spec>
        1. Update import (line 36):
        ```python
        from .warnings import graded_warning, get_warnings, clear_warnings
        ```

        2. Add clear_warnings() at pipeline entry, immediately after line 121 (`effective_config_path = ...`):
        ```python
        effective_config_path = config_path or config.config_path
        clear_warnings()
        ```

        3. Remove the `all_review_flags` initialization at line 135. The line `all_review_flags: list[dict] = []` is deleted entirely.

        4. Remove `all_review_flags.extend(review_flags)` at line 203.

        5. At the BIDS validation section (lines 297-305), remove the `all_review_flags.append(...)` wrapper. The graded_warning call auto-appends to the accumulator:
        ```python
        if errors_found:
            graded_warning(
                logger, "high", "BIDS_VALIDATION_ERRORS",
                f"BIDS validation found {len(errors_found)} error(s): "
                f"{'; '.join(f.message for f in errors_found[:3])}"
                + (f" (+{len(errors_found) - 3} more)" if len(errors_found) > 3 else ""),
            )
        ```

        6. Replace status determination (line 323):
        ```python
        all_warnings = get_warnings()
        status = "warning" if any(w["severity"] == "high" for w in all_warnings) else "success"
        ```

        7. Replace BidsReconResult construction (lines 325-334), using `all_warnings`:
        ```python
        return BidsReconResult(
            status=status,
            manifest_path=manifest_path,
            output_dir=bids_root / "derivatives" / "fmri-bids-recon",
            warnings=all_warnings,
            participants_processed=participants_processed,
            bids_validation_errors=error_count,
            bids_validation_warnings=warning_count,
            tool_report=tool_report,
        )
        ```
      </spec>
      <dependencies>C2 (get_warnings, clear_warnings must exist in warnings.py)</dependencies>
      <risk>low - all graded_warning calls throughout the pipeline auto-append to the accumulator; get_warnings() collects them all. The per-participant review_flags lists remain for intermediate JSON serialization (unchanged).</risk>
      <rollback>Restore all_review_flags initialization, extend, and append calls; remove get_warnings/clear_warnings import and calls.</rollback>
    </change>

    <change id="C12" priority="P1" source_item="T6/C1">
      <file path="fmri_bids_recon/pipeline.py" action="modify" />
      <description>Filter fieldmap targets by volume-count exclusion set. Prevents excluded calibration/auto-align scans from appearing as fieldmap targets.</description>
      <spec>
        Replace the targets line (line 178) with an exclusion-filtered version. Build the exclusion set from check_volume_counts' excluded list:

        ```python
        excluded_sns = {e.series.series_number for e in excluded}
        targets = [
            (series_map[sn], role)
            for sn, role in roles.items()
            if role in (Role.BOLD, Role.DWI, Role.SBREF, Role.DWI_SBREF)
            and sn not in excluded_sns
        ]
        ```

        The `excluded` variable is already available from line 169 (`surviving, excluded, vol_updates, vol_flags = check_volume_counts(...)`). The Excluded dataclass (runs.py:23) has a `.series` attribute with `.series_number`.
      </spec>
      <dependencies>none (uses existing variables)</dependencies>
      <risk>low - strictly removes series that were already excluded by volume-count validation</risk>
      <rollback>Remove the excluded_sns line and the `and sn not in excluded_sns` filter.</rollback>
    </change>

    <change id="C13" priority="P1" source_item="T6/C2">
      <file path="fmri_bids_recon/pipeline.py" action="modify" />
      <description>No-fieldmaps early-out: when pair_fieldmaps returns empty, skip map_fieldmaps, construct empty Mapping, emit graded_warning, and set all fieldmap-related guard_log entries to True (vacuously satisfied).</description>
      <spec>
        1. Add Mapping to the stage3_map import (line 23):
        ```python
        from .stage3_map import order_series, pair_fieldmaps, map_fieldmaps, Mapping
        ```

        2. Replace the map_fieldmaps call (line 179) with a guarded version:
        ```python
        if not pairs:
            graded_warning(
                logger, "medium", "NO_FIELDMAP_SERIES",
                "No fieldmap series found; proceeding without fieldmap correction.",
            )
            mapping = Mapping(pairs=[], pair_to_targets={})
            guard_log["opposite_pe_within_pair"] = True
            guard_log["dir_label_pe_agreement"] = True
            guard_log["fieldmap_target_geometry_match"] = True
            guard_log["pe_axis_target_match"] = True
            guard_log["association_unambiguous"] = True
            guard_log["no_orphan_pairs"] = True
        else:
            mapping = map_fieldmaps(pairs, targets, ordered, guard_log)
        ```

        The 6 guard_log entries are set to True because the fieldmap guards are vacuously satisfied when no fieldmap pairs exist. Without these entries, assert_guards_executed() would raise GuardError on any session without fieldmaps. The 7th fieldmap guard (fieldmap_pairing_unambiguous) is already set True by pair_fieldmaps when fmaps is empty (stage3_map.py:268-269).
      </spec>
      <dependencies>C2 (graded_warning auto-append), C12 (targets filtering should precede this logically, both in same file)</dependencies>
      <risk>medium - sessions without fieldmaps now proceed instead of halting. The graded_warning (medium severity) ensures visibility. If fieldmaps are genuinely expected but missing, the NO_FIELDMAP_SERIES warning alerts the user.</risk>
      <rollback>Remove the `if not pairs:` guard and Mapping import; restore direct `mapping = map_fieldmaps(...)` call.</rollback>
    </change>

    <!-- ================================================================== -->
    <!-- FILE: stage3_map.py                                                 -->
    <!-- ================================================================== -->

    <change id="C14" priority="P1" source_item="T6/C3">
      <file path="fmri_bids_recon/stage3_map.py" action="modify" />
      <description>Soften per-target FieldmapCoverageError to graded_warning. When a target has no geometry-compatible fieldmap pair, emit a high-severity warning and continue processing remaining targets instead of halting.</description>
      <spec>
        1. Add graded_warning import (after line 12):
        ```python
        from .warnings import graded_warning
        ```

        2. Replace the FieldmapCoverageError raise at lines 485-495 with:
        ```python
        if not eligible:
            candidate_pairs = [
                {
                    "pair_index": i,
                    "run_index": pairs[i].run_index,
                    "modality": pairs[i].modality,
                    "series": [pairs[i].member_a.series_number, pairs[i].member_b.series_number],
                    "failures": result.failures,
                }
                for i, result in checks
                if not result.compatible
            ]
            graded_warning(
                logger, "high", "FIELDMAP_COVERAGE_GAP",
                f"Series {s.series_number} (description={s.description!r}, "
                f"modality={modality!r}) has no geometry-compatible fieldmap pair. "
                f"Candidate diagnostics: {candidate_pairs}",
            )
            continue
        ```

        The `continue` skips to the next target instead of halting. The candidate_pairs diagnostic info is preserved in the warning message (previously in the error context).
      </spec>
      <dependencies>none</dependencies>
      <risk>medium - genuine fieldmap coverage errors now produce a warning instead of a halt. The high-severity graded_warning triggers exit code 3 (status="warning") via the pipeline's status determination, ensuring visibility.</risk>
      <rollback>Restore the FieldmapCoverageError raise.</rollback>
    </change>

    <change id="C15" priority="P1" source_item="T6/C4">
      <file path="fmri_bids_recon/stage3_map.py" action="modify" />
      <description>Soften orphan fieldmap pair check to graded_warning. When a fieldmap pair has no assigned targets, emit a medium-severity warning instead of halting.</description>
      <spec>
        Replace the FieldmapCoverageError raise at lines 533-544 with:

        ```python
        for i, p in enumerate(pairs):
            if not pair_to_targets[i]:
                graded_warning(
                    logger, "medium", "ORPHAN_FIELDMAP_PAIR",
                    f"Fieldmap pair (run_index={p.run_index}, modality={p.modality!r}, "
                    f"series_a={p.member_a.series_number}, "
                    f"series_b={p.member_b.series_number}) has no assigned targets.",
                )
        ```

        The guard_log["no_orphan_pairs"] = True at line 546 remains unchanged (the guard executed; it just emitted a warning instead of halting).
      </spec>
      <dependencies>C14 (graded_warning import added in same file)</dependencies>
      <risk>low - orphan fieldmap pairs are a configuration anomaly, not a data integrity issue. Medium severity is appropriate.</risk>
      <rollback>Restore the FieldmapCoverageError raise.</rollback>
    </change>

  </changes>

  <execution_order>
    C1, C2 (warnings.py: return dict + accumulator)
    C3 (stage2_classify.py: helpers and constants)
    C4 (stage2_classify.py: Rule 2 multi-signal scout)
    C5 (stage2_classify.py: Rule 3 physics pass-through)
    C6 (stage2_classify.py: Rule 5 broadened)
    C7 (stage2_classify.py: Rule 8 broadened)
    C8 (stage2_classify.py: Rules 9/9b merged)
    C9 (stage2_classify.py: NORM/ND guard + duplicate modality guard)
    C10 (stage1_convert.py: dcm2niix -i y flag)
    C11 (pipeline.py: accumulator consumer)
    C12 (pipeline.py: filter fieldmap targets)
    C13 (pipeline.py: no-fieldmaps early-out)
    C14 (stage3_map.py: soften per-target coverage gap)
    C15 (stage3_map.py: soften orphan pair check)
  </execution_order>

  <build_dispatch_groups>
    Group A (warnings.py): C1 + C2
    Group B (stage2_classify.py): C3 + C4 + C5 + C6 + C7 + C8 + C9
    Group C (stage1_convert.py): C10
    Group D (pipeline.py): C11 + C12 + C13
    Group E (stage3_map.py): C14 + C15

    All 5 groups edit non-overlapping files. Build-phase dispatch: all groups parallel in a single batch.
  </build_dispatch_groups>
</implement_plan>
