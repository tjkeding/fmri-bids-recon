<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-08-26T15:24:36Z" />
  <input_reports>
    <report path="bids-recon_brainstorm_20260826_134759.md" mode="brainstorm" key_items="15" />
    <report path="bids-recon_cr_20260826_150650.md" mode="cr" key_items="9" />
  </input_reports>
  <changes>

    <change id="C1" priority="P0" source_item="brainstorm:D1, cr:F1/F2/F3/F4">
      <file path="fmri_bids_recon/sidecar.py" action="modify" />
      <description>Expand Series dataclass with vendor normalization and fields required by downstream vendor-aware classification, GRE support, and absent-PE detection.</description>
      <spec>
1. Add a module-level helper `_normalize_vendor(manufacturer: str | None) -> str | None`:
   - If manufacturer is None or empty, return None.
   - lower = manufacturer.strip().lower()
   - If "siemens" in lower: return "siemens"
   - If "ge" in lower: return "ge"
   - If "philips" in lower: return "philips"
   - Else: return None

2. Add fields to Series dataclass (after `raw`, before `software_versions`):
   - vendor: str | None = None              # normalized: "siemens", "ge", "philips", or None
   - echo_number: int | None = None         # DICOM EchoNumber (for GRE phase/magnitude discrimination)
   - phase_encoding_axis: str | None = None # dcm2niix PhaseEncodingAxis (axis only, no polarity)
   - sequence_name: str | None = None       # DICOM SequenceName (0018,0024)

3. Update load_series() Series construction (around line 290) to populate new fields:
   - vendor=_normalize_vendor(raw.get("Manufacturer")),
   - echo_number=(int(raw["EchoNumber"]) if raw.get("EchoNumber") is not None else None),
   - phase_encoding_axis=raw.get("PhaseEncodingAxis"),
   - sequence_name=raw.get("SequenceName"),

4. Do NOT remove modality_token(). It remains as a public API; canonical_modality() (C2) will call it internally for the raw-token fallback path.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - additive fields with defaults; no existing behavior altered</risk>
      <rollback>git checkout fmri_bids_recon/sidecar.py</rollback>
    </change>

    <change id="C2" priority="P0" source_item="brainstorm:D4/D5/D6/D7/D8/D9, cr:F1/F4">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>Implement vendor-aware classification helpers: canonical_modality() with context-gated GE dispatch (CR F1), layered _is_epi() with physics-primary Philips detection (CR F4), and vendor-dispatched _is_spin_echo() (D8).</description>
      <spec>
1. Add import of SEVERITY_HIGH to the existing warnings import line.

2. Implement `canonical_modality(s: Series) -> str` (new function, placed after _description_anat_hint):
   Canonical token vocabulary: FMRI, DIFFUSION, MAGNITUDE, PHASE, ASL, SE_EPI, EPI, DERIVED, OTHER.

   raw_tok = modality_token(s)  # existing function, returns s.image_type[2] or "OTHER"

   if s.vendor == "siemens":
       _SIEMENS_MAP = {"FMRI": "FMRI", "DIFFUSION": "DIFFUSION", "M": "MAGNITUDE",
                       "P": "PHASE", "ASL": "ASL"}
       return _SIEMENS_MAP.get(raw_tok, raw_tok)

   elif s.vendor == "ge":
       if raw_tok == "EPI":
           if "EP" in s.scanning_sequence and "GR" in s.scanning_sequence:
               return "FMRI"    # EP\GR = BOLD EPI
           # EP\SE: context-gated (CR F1) - return SE_EPI, not DIFFUSION
           if "EP" in s.scanning_sequence and "SE" in s.scanning_sequence:
               return "SE_EPI"
           return "EPI"         # bare EP, no refinement
       elif raw_tok == "OTHER":
           if "EP" in s.scanning_sequence and "SE" in s.scanning_sequence:
               return "SE_EPI"  # GE DWI tensor: IT[2]=OTHER, SS=EP\SE
           return "OTHER"
       return raw_tok

   elif s.vendor == "philips":
       _PHILIPS_MAP = {"T2": "FMRI", "T1": "MAGNITUDE", "M": "MAGNITUDE",
                       "DIFFUSION": "DIFFUSION", "PHASE MAP": "PHASE",
                       "PERFUSION": "ASL"}
       return _PHILIPS_MAP.get(raw_tok, raw_tok)

   else:  # unknown vendor
       _FALLBACK_MAP = {"M": "MAGNITUDE", "P": "PHASE"}
       return _FALLBACK_MAP.get(raw_tok, raw_tok)

3. Replace existing `_is_spin_echo(s: Series) -> bool` with vendor-dispatched version:
   if s.vendor == "siemens":
       # Check 1: SE in ScanningSequence
       if "SE" in s.scanning_sequence:
           return True
       # Check 2: _se in PulseSequenceDetails
       psd = s.raw.get("PulseSequenceDetails", "")
       if isinstance(psd, str) and "_se" in psd.lower():
           return True
       # Check 3: "epse" in SequenceName (replaces SS-absent check per D8)
       sn = s.sequence_name or ""
       if "epse" in sn.lower():
           return True
       return False
   else:
       # GE, Philips, Unknown: SE in ScanningSequence only
       return "SE" in s.scanning_sequence

4. Implement `_is_epi(s: Series) -> bool` (new function, replaces raw "EP" checks):
   if s.vendor in ("siemens", "ge"):
       return "EP" in s.scanning_sequence

   elif s.vendor == "philips":
       # CR F4: layered detection. Primary: physics-based.
       etl = s.raw.get("EchoTrainLength")
       has_ees = (s.raw.get("EffectiveEchoSpacing") is not None
                  or s.raw.get("EstimatedEffectiveEchoSpacing") is not None)
       if etl is not None and int(etl) > 10 and has_ees:
           return True
       # Secondary: SequenceName corroboration
       sn = (s.sequence_name or "").lower()
       if any(tok in sn for tok in ("epi", "dwi", "grase")):
           return True
       # Fallback: medium-severity graded_warning if inconclusive and EPI-like TR
       if has_ees:
           graded_warning(_logger, SEVERITY_MEDIUM, "PHILIPS_EPI_INCONCLUSIVE",
               f"Series {s.series_number}: Philips EPI detection inconclusive "
               f"(EchoTrainLength={etl}, SequenceName={s.sequence_name!r}). "
               f"EstimatedEffectiveEchoSpacing present suggests EPI.")
           return True
       return False

   else:  # unknown vendor
       return "EP" in s.scanning_sequence
      </spec>
      <dependencies>C1</dependencies>
      <risk>medium - new classification logic; must preserve Siemens behavior exactly while adding GE/Philips paths</risk>
      <rollback>git checkout fmri_bids_recon/stage2_classify.py</rollback>
    </change>

    <change id="C3" priority="P0" source_item="brainstorm:D10/D13/D15, cr:F1/F2">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>Add new Role enum members, add Rule 2 negative guard for GRE fieldmaps (CR F2), add Rule 3.5 for GRE phase classification, and update all classification rules to use canonical_modality() and _is_epi() instead of modality_token() and raw EP checks.</description>
      <spec>
1. Add to Role enum (after FMAP_DWI):
   FMAP_GRE_PHASE = "fmap_gre_phase"
   FMAP_GRE_MAG = "fmap_gre_mag"

2. In classify(), replace `tok = modality_token(s)` with `tok = canonical_modality(s)`.

3. Rule 2 (DIS2D scout detection, lines 174-180): Add negative guard per CR F2.
   BEFORE the DIS2D check, add:
   ```
   _is_gre_fieldmap_candidate = (
       "GR" in s.scanning_sequence
       and ("PHASE" in s.image_type or s.echo_number is not None)
   )
   ```
   Change the DIS2D condition to:
   ```
   if (
       "DIS2D" in s.image_type_text
       and s.mr_acquisition_type == "2D"
       and s.multiband_factor is None
       and not _is_gre_fieldmap_candidate
   ):
   ```

4. Rule 3 (DROP_NAVIGATOR, lines 195-209): Replace `tok not in {"FMRI", "DIFFUSION"}` with `tok not in {"FMRI", "DIFFUSION", "SE_EPI"}` to handle GE's context-gated token. Replace `"EP" in s.scanning_sequence` with `_is_epi(s)`.

5. Add Rule 3.5 (GRE phase classification, inserted AFTER Rule 3, BEFORE Rule 4):
   ```
   # Rule 3.5: GRE fieldmap phase image
   if (
       tok == "PHASE"
       and not _is_epi(s)
       and "GR" in s.scanning_sequence
   ):
       roles[s.series_number] = Role.FMAP_GRE_PHASE
       continue
   ```

6. Rule 4 (T1W/T2W, lines 212-243): Replace `"EP" not in s.scanning_sequence` with `not _is_epi(s)`. Replace `tok == "M"` with `tok in ("M", "MAGNITUDE")` to handle canonical tokens.

7. Rule 5 (SE-EPI fieldmap, lines 246-265):
   Replace `tok != "DIFFUSION"` with `tok not in ("DIFFUSION", "SE_EPI") or (tok == "SE_EPI" and s.raw.get("DiffusionDirectionality") is None and not _bval_exists(s))`.
   This is the CR F1 context-gated dispatch: SE_EPI tokens pass Rule 5 only when no diffusion indicators are present.
   Replace `"EP" in s.scanning_sequence` with `_is_epi(s)`.
   Replace `"GR" not in s.scanning_sequence` with `"GR" not in s.scanning_sequence` (unchanged).
   Replace `modality_token(_r5_nxt) == "DIFFUSION"` with `canonical_modality(_r5_nxt) in ("DIFFUSION", "SE_EPI")`.

8. Rule 6 (FMAP_DWI, lines 268-275):
   Replace `tok == "DIFFUSION"` with `tok in ("DIFFUSION", "SE_EPI")`.
   Add: for SE_EPI tokens, require diffusion indicators: `and (tok == "DIFFUSION" or (tok == "SE_EPI" and (s.raw.get("DiffusionDirectionality") is not None or _bval_exists(s))))`.
   Replace `"GR" not in s.scanning_sequence` with `"GR" not in s.scanning_sequence` (unchanged).

9. Rule 7 (DWI, lines 278-285):
   Replace `tok == "DIFFUSION"` with `tok in ("DIFFUSION", "SE_EPI")`.

10. Rule 8 (BOLD, lines 288-290):
    Replace `tok == "FMRI"` with `tok == "FMRI"` (unchanged for Siemens; FMRI is the canonical token).
    The `_is_epi_bold_physics(s)` fallback handles GE/Philips.
    Update `_is_epi_bold_physics` to use `_is_epi(s)` instead of `"EP" in s.scanning_sequence`.

11. Rule 9 (SBRef, lines 293-305):
    Replace `"EP" in s.scanning_sequence` with `_is_epi(s)`.
    Replace `modality_token(nxt)` with `canonical_modality(nxt)`.
    Update FMRI check: `nxt_tok == "FMRI"` already works.
    Update DIFFUSION check: `nxt_tok in ("DIFFUSION", "SE_EPI")`.

12. Update import line: add `canonical_modality` if it is defined in this module (it is, per C2). Remove `modality_token` from the sidecar import if no longer needed locally. Actually, canonical_modality calls modality_token internally, so keep the import.
      </spec>
      <dependencies>C1, C2</dependencies>
      <risk>high - touches every classification rule; regression risk across all modalities</risk>
      <rollback>git checkout fmri_bids_recon/stage2_classify.py</rollback>
    </change>

    <change id="C4" priority="P0" source_item="brainstorm:D12, cr:F3/F6/F7">
      <file path="fmri_bids_recon/stage3_map.py" action="modify" />
      <description>Generalize FieldmapPair to FieldmapUnit with paired/single modes. Replace odd-count PhaseEncodingError with unified vendor-independent graded_warning. Implement absent-PE detection with high-severity warning and Tier 3 routing. Use voxel-space PE labels in warnings.</description>
      <spec>
1. Replace FieldmapPair dataclass with FieldmapUnit:
   ```
   @dataclass
   class FieldmapUnit:
       members: list[Series]  # 1 (single mode) or 2 (paired mode)
       modality: str           # "func" or "dwi"
       mode: str               # "paired" or "single"
       run_index: int
       dir_labels: list[str]   # 1 or 2 BIDS dir- labels (voxel-space: "j", "j-", etc.)
   ```
   Note: dir_labels use voxel-space notation (CR F6). PE_DIRECTION_TO_LABEL remains for assembly-time conversion to anatomical labels for BIDS entity naming.

2. Update Mapping dataclass:
   - Replace `pairs: list[FieldmapPair]` with `units: list[FieldmapUnit]`
   - Replace `pair_to_targets: dict[int, list[Series]]` with `unit_to_targets: dict[int, list[Series]]`
   - Add `unpaired_fmaps: list[Series]` for Tier 3 routing (absent-PE or unmatchable)

3. Rewrite pair_fieldmaps() -> group_fieldmaps():
   Signature: `group_fieldmaps(fmaps: list[tuple[Series, Role]], ordered: list[Series], guard_log: dict) -> tuple[list[FieldmapUnit], list[Series]]`
   Returns (units, unpaired_fmaps).

   a. Geometry grouping via union-find (unchanged algorithm).

   b. Absent-PE detection (CR F3): Before modality split, check each fieldmap's phase_encoding_direction.
      If phase_encoding_direction is None:
      - If phase_encoding_axis is not None: emit graded_warning(SEVERITY_HIGH, "ABSENT_PE_DIRECTION",
        f"Series {s.series_number}: PhaseEncodingDirection absent "
        f"(PhaseEncodingAxis={s.phase_encoding_axis!r} present without polarity). "
        f"Cannot verify opposite-PE pairing. Route to sourcedata/unpaired_fmap. "
        f"To enable fieldmap correction, add PhaseEncodingDirection to the sidecar "
        f"manually or use a controlled-vocabulary protocol naming convention.")
      - Route to unpaired_fmaps list. Do NOT include in modality sub-groups.

   c. Within each geometry group, split by modality and sort by acquisition_datetime.

   d. Even-count: pair consecutively into FieldmapUnit(mode="paired", members=[a, b], ...).
      Opposite-PE validation unchanged (still raises PhaseEncodingError for non-opposite pairs).

   e. Odd-count (CR F7): emit graded_warning(SEVERITY_HIGH, "ODD_FIELDMAP_COUNT",
      f"Geometry group contains {len(members)} {modality} fieldmap series "
      f"(series: {[s.series_number for s in members]}). Cannot form balanced "
      f"opposite-PE pairs. Paired fieldmaps assigned where possible; "
      f"remainder routed to sourcedata/unpaired_fmap.")
      Pair as many as possible (len-1 if odd); route the remainder to unpaired_fmaps.
      This replaces the PhaseEncodingError raise.

   f. For paired units, dir_labels stores voxel-space PE directions (e.g., ["j", "j-"]),
      NOT anatomical labels. PE_DIRECTION_TO_LABEL conversion happens at assembly time.

4. Update map_fieldmaps() to use FieldmapUnit instead of FieldmapPair:
   - Accept `units: list[FieldmapUnit]` instead of `pairs: list[FieldmapPair]`.
   - Geometry check uses units[i].members[0] as the reference series.
   - Return Mapping with unit_to_targets and unpaired_fmaps.

5. Update _select_pair -> _select_unit (rename, same logic but on FieldmapUnit).
      </spec>
      <dependencies>C1, C3</dependencies>
      <risk>high - replaces core pairing logic; all downstream consumers (stage4) must update</risk>
      <rollback>git checkout fmri_bids_recon/stage3_map.py</rollback>
    </change>

    <change id="C5" priority="P1" source_item="brainstorm:D15/D16/D17, cr:F5/F8">
      <file path="fmri_bids_recon/stage3_map.py" action="modify" />
      <description>Implement GRE fieldmap grouping with geometry-primary magnitude rescue, explicit BIDS case determination, and relaxed geometry check for GRE-to-EPI target association.</description>
      <spec>
1. Add GREFieldmapSet dataclass:
   ```
   @dataclass
   class GREFieldmapSet:
       phase_series: list[Series]     # 1 (Case 1/3) or 2 (Case 2)
       magnitude_series: list[Series] # 1-2 magnitude companions
       bids_case: int                 # 1, 2, 3, or 0 (indeterminate)
       run_index: int
       targets: list[Series]          # assigned BOLD/DWI targets
   ```

2. Implement `group_gre_fieldmaps(classified: dict[int, Role], series_map: dict[int, Series], guard_log: dict) -> tuple[list[GREFieldmapSet], list[Series]]`:
   Returns (gre_sets, unassociated_magnitudes).

   a. Collect all FMAP_GRE_PHASE series from classified.

   b. Geometry-primary magnitude rescue (CR F8):
      For each FMAP_GRE_PHASE series, find magnitude candidates:
      - Role is UNCLASSIFIED
      - "GR" in scanning_sequence
      - "PHASE" not in image_type
      - _geometry_check() compatible (position, orientation, voxel size, matrix)
      If multiple geometry-matched candidates: use series_number as tiebreaker (nearest).
      If no geometry match: emit graded_warning(SEVERITY_MEDIUM, "GRE_MAGNITUDE_MISSING", ...).
      Reclassify matched magnitudes as FMAP_GRE_MAG in classified dict.

   c. Group phase + rescued magnitude by geometry into fieldmap sets.

   d. Explicit BIDS case determination (CR F5):
      - Count phase series in the set.
      - If 2 phases with distinct EchoTime: bids_case = 2
      - If 1 phase with raw.get("EchoTime1") and raw.get("EchoTime2") both present: bids_case = 1
      - If 1 phase with raw.get("Units") == "Hz": bids_case = 3
      - Else: bids_case = 0 (indeterminate). Emit graded_warning(SEVERITY_HIGH, "GRE_CASE_INDETERMINATE",
        f"GRE fieldmap set (phase series {[s.series_number for s in phase_series]}) "
        f"cannot be classified as BIDS Case 1/2/3. Missing: EchoTime1+EchoTime2 "
        f"(Case 1), multiple phase outputs (Case 2), or Units='Hz' (Case 3). "
        f"Routing to sourcedata.")

3. Implement `_relaxed_geometry_check(a: Series, b: Series) -> GeometryResult`:
   Same as _geometry_check but:
   - Position and orientation: checked (same tolerances)
   - Voxel sizes: NOT checked (GRE/EPI resolution mismatch expected)
   - Matrix: NOT checked (same reason)
   - pe_axis: NOT checked (FUGUE is PE-direction-agnostic)

4. Implement `map_gre_fieldmaps(gre_sets: list[GREFieldmapSet], targets: list[tuple[Series, Role]], guard_log: dict) -> list[GREFieldmapSet]`:
   For each target (BOLD/DWI), find GRE sets whose phase_series[0] passes _relaxed_geometry_check against the target. Nearest-in-time selection for ties. Indeterminate sets (bids_case=0) are excluded from association.
      </spec>
      <dependencies>C3, C4</dependencies>
      <risk>medium - new grouping logic; tested against dcm_qa empirical data</risk>
      <rollback>git checkout fmri_bids_recon/stage3_map.py</rollback>
    </change>

    <change id="C6" priority="P1" source_item="brainstorm:D18, cr:F3/F5">
      <file path="fmri_bids_recon/stage4_assemble.py" action="modify" />
      <description>Add GRE fieldmap BIDS assembly paths for Cases 1-3, add sourcedata/unpaired_fmap routing for Tier 3 fieldmaps, and update SE-EPI assembly to use FieldmapUnit.</description>
      <spec>
1. Update imports: replace FieldmapPair with FieldmapUnit. Import GREFieldmapSet.

2. Update assemble() signature: add `gre_sets: list[GREFieldmapSet]` parameter and accept `unpaired_fmaps: list[Series]` parameter.

3. Update SE-EPI assembly block (lines 367-398):
   Replace fmap_pair_lookup with fmap_unit_lookup using FieldmapUnit.
   For paired units: assembly is identical to current FieldmapPair logic (dir-{label}_epi).
   For single units: route to sourcedata/unpaired_fmap instead of raising GuardError.
   Convert voxel-space dir_labels to anatomical labels at assembly time via PE_DIRECTION_TO_LABEL.

4. Add sourcedata/unpaired_fmap routing:
   For each series in unpaired_fmaps:
   ```
   sd_dest = sd_base / "unpaired_fmap" / series.nifti_path.name
   sd_dest.parent.mkdir(parents=True, exist_ok=True)
   shutil.copy2(series.nifti_path, sd_dest)
   sourcedata_files.append(sd_dest)
   ```

5. Add GRE fieldmap assembly block (after SE-EPI block):
   For each GREFieldmapSet with bids_case > 0:
   fmap_dir = ses_dir / "fmap"
   fmap_dir.mkdir(parents=True, exist_ok=True)

   Case 1 (phasediff):
   - Phase: sub-{sub}_ses-{ses}_run-{run_idx:02d}_phasediff.nii.gz
   - Sidecar includes EchoTime1, EchoTime2 from raw
   - Magnitude1: sub-{sub}_ses-{ses}_run-{run_idx:02d}_magnitude1.nii.gz
   - Magnitude2 (if exists): sub-{sub}_ses-{ses}_run-{run_idx:02d}_magnitude2.nii.gz

   Case 2 (two-phase):
   - Phase1: sub-{sub}_ses-{ses}_run-{run_idx:02d}_phase1.nii.gz (with EchoTime)
   - Phase2: sub-{sub}_ses-{ses}_run-{run_idx:02d}_phase2.nii.gz (with EchoTime)
   - Magnitude1/2: same as Case 1

   Case 3 (direct B0):
   - Fieldmap: sub-{sub}_ses-{ses}_run-{run_idx:02d}_fieldmap.nii.gz (with Units: "Hz")
   - Magnitude: sub-{sub}_ses-{ses}_run-{run_idx:02d}_magnitude.nii.gz

   For indeterminate sets (bids_case=0): route all series to sourcedata/unclassified.

6. Add new Role handling in the per-series loop:
   FMAP_GRE_PHASE and FMAP_GRE_MAG are handled by the GREFieldmapSet assembly block (step 5), not the per-series loop. Add them to the set of roles that are silently skipped in the per-series loop (they are assembled set-wise, not series-wise).
      </spec>
      <dependencies>C4, C5</dependencies>
      <risk>medium - new assembly paths; no changes to existing SE-EPI assembly logic beyond FieldmapUnit adaptation</risk>
      <rollback>git checkout fmri_bids_recon/stage4_assemble.py</rollback>
    </change>

    <change id="C7" priority="P1" source_item="brainstorm:D14">
      <file path="fmri_bids_recon/config.py" action="modify" />
      <file path="fmri_bids_recon/labels.py" action="modify" />
      <description>Add prefix field to TaskRegistryEntry and update drift guard to use stored prefix instead of current session's prefix.</description>
      <spec>
1. config.py: Add field to TaskRegistryEntry (after `signature`):
   prefix: Optional[tuple] = None

2. labels.py resolve_labels() (around line 321): When creating a new TaskRegistryEntry, store the current prefix:
   delta.new_entries[desc] = TaskRegistryEntry(
       label=new_label,
       expected_volumes=None,
       first_seen=date.today().isoformat(),
       signature=next(iter(new_sigs)) if new_sigs else None,
       prefix=prefix,  # <-- new
   )

3. labels.py drift guard (around line 300): Use stored prefix when available:
   Replace:
       re_derived = derive_task_label(desc, prefix)
   With:
       stored_prefix = registry[desc].prefix if hasattr(registry[desc], "prefix") and registry[desc].prefix is not None else prefix
       re_derived = derive_task_label(desc, stored_prefix)
      </spec>
      <dependencies>none (independent of C1-C6)</dependencies>
      <risk>low - additive field with None default; backward-compatible with existing registries</risk>
      <rollback>git checkout fmri_bids_recon/config.py fmri_bids_recon/labels.py</rollback>
    </change>

  </changes>
  <execution_order>C1, C7, C2, C3, C4, C5, C6</execution_order>
  <notes>
    C1 and C7 have no dependencies and can execute in parallel.
    C2 depends on C1. C3 depends on C1+C2 (same file, sequential).
    C4 depends on C1+C3. C5 depends on C3+C4 (same file, sequential after C4).
    C6 depends on C4+C5.

    The pipeline.py orchestrator must be updated to pass new parameters (gre_sets, unpaired_fmaps) to assemble(). This is a wiring change that depends on C4+C5+C6 but is mechanical and included in C6's scope.

    CR F9 (warning accumulator) requires no implementation change.

    All changes require /test validation after build completes.
  </notes>
</implement_plan>
