<implement_plan>
  <meta project="fmri-bids-recon" mode="implement" submodule="plan" timestamp="2026-07-16T12:00:00-04:00" />
  <input_reports>
    <report path="tests/fmri-bids-recon_test_report_20260716.md" mode="test" key_items="9" />
  </input_reports>
  <changes>

    <change id="C1" priority="P0" source_item="Bug 1">
      <file path="fmri_bids_recon/sidecar.py" action="modify" />
      <description>
        Add backslash-delimited string splitting to `_to_str_tuple`. dcm2niix on
        Siemens XA30 encodes multi-value DICOM fields as backslash-delimited
        strings (e.g. "GR\\IR") rather than JSON arrays. The function currently
        treats these as single tokens. All downstream classification depends on
        correct tuple parsing.
      </description>
      <spec>
        In `_to_str_tuple` (lines 148-165), inside the `isinstance(value, str)`
        branch (line 163), insert a backslash check before the single-string
        return (line 164):

        ```python
        # BEFORE (lines 163-164):
            if isinstance(value, str):
                return (value,)

        # AFTER:
            if isinstance(value, str):
                if "\\" in value:
                    return tuple(value.split("\\"))
                return (value,)
        ```

        No other changes to this file.
      </spec>
      <dependencies>None</dependencies>
      <risk>low - additive guard; single-value strings without backslashes are unaffected</risk>
      <rollback>Revert the two-line addition inside `_to_str_tuple`.</rollback>
    </change>

    <change id="C2" priority="P0" source_item="Bugs 2, 3, 4, 5">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>
        Four independent classification fixes grouped for atomicity: (a) add
        `_is_spin_echo` helper and use it in Rule 5 for XA30 spin-echo
        detection; (b) add `_bval_path`/`_has_nonzero_bval` helpers and use them
        in Rule 6 for XA30 diffusion fieldmap detection; (c) add
        `_description_stem` helper and use it in Rules 9/9b for SBRef suffix
        stripping; (d) add SeriesNumber deduplication guard in the classify loop
        and NORM/ND twin resolution pass to handle vNav setter series with many
        sidecars per SeriesNumber.
      </description>
      <spec>
        **C2-imports**: Add `import re` after line 9 (after `from __future__
        import annotations`).

        **C2-helpers**: Replace the existing `_bval_exists` function (lines
        62-81) and add new helpers in the Internal helpers section (between
        `_description_anat_hint` ending at line 59 and the Public API section
        at line 84). The final helper block should contain, in order:

        1. `_SBREF_SUFFIX_RE` regex constant:
           ```python
           _SBREF_SUFFIX_RE = re.compile(r"[_\s]*sbref\s*$", re.IGNORECASE)
           ```

        2. `_description_stem(desc: str) -> str`: strips trailing _SBRef
           suffix via `_SBREF_SUFFIX_RE.sub("", desc).lower().strip()`.

        3. `_is_spin_echo(s: Series) -> bool`: checks three indicators in
           priority order: (i) `"SE" in s.scanning_sequence`; (ii) `"_se"` in
           `s.raw.get("PulseSequenceDetails", "")` (lowercased); (iii) `"SS"`
           absent from `SequenceVariant` tokens (parsing backslash-delimited
           strings). Returns True if any indicator fires.

        4. `_bval_path(s: Series)`: derives the .bval companion path from
           `s.nifti_path` by stripping .nii.gz or .nii and appending .bval.

        5. `_bval_exists(s: Series) -> bool`: returns `_bval_path(s).exists()`.

        6. `_has_nonzero_bval(s: Series) -> bool`: reads the .bval file content
           and returns True if any value exceeds zero. Returns False if the file
           does not exist or is unreadable.

        **C2-dedup** (Bug 5, part 1): At line 120, after `for s in series:`,
        insert `if s.series_number in roles: continue` before
        `tok = modality_token(s)` (line 121).

        **C2-rule5** (Bug 2): Lines 184-192, replace the Rule 5 condition:
        ```python
        # BEFORE:
            tok == "FMRI"
            and "SE" in s.scanning_sequence
            and "GR" not in s.scanning_sequence
            and s.n_volumes == 1

        # AFTER:
            tok == "FMRI"
            and _is_spin_echo(s)
            and "GR" not in s.scanning_sequence
            and s.n_volumes == 1
        ```

        **C2-rule6** (Bug 3): Lines 194-201, replace the Rule 6 condition:
        ```python
        # BEFORE:
            tok == "DIFFUSION"
            and "SE" in s.scanning_sequence
            and "GR" not in s.scanning_sequence
            and not _bval_exists(s)

        # AFTER:
            tok == "DIFFUSION"
            and "GR" not in s.scanning_sequence
            and s.n_volumes == 1
            and not _has_nonzero_bval(s)
        ```
        Removing `"SE" in s.scanning_sequence` is safe: `n_volumes == 1` and
        `not _has_nonzero_bval(s)` together are sufficient to identify diffusion
        fieldmaps on both VE11 and XA30.

        **C2-rule9** (Bug 4): Lines 232-238, replace the stem comparison block:
        ```python
        # BEFORE:
                same_stem = (
                    nxt.description.lower().strip()
                    == s.description.lower().strip()
                    or nxt.description.lower().startswith(
                        s.description.lower().rstrip("_- ")
                    )
                )

        # AFTER:
                same_stem = _description_stem(s.description) == _description_stem(nxt.description)
        ```

        **C2-rule9b** (Bug 4): Lines 259-265, identical replacement:
        ```python
        # BEFORE:
                same_stem = (
                    nxt.description.lower().strip()
                    == s.description.lower().strip()
                    or nxt.description.lower().startswith(
                        s.description.lower().rstrip("_- ")
                    )
                )

        # AFTER:
                same_stem = _description_stem(s.description) == _description_stem(nxt.description)
        ```

        **C2-normnd** (Bug 5, part 2): Line 284, replace the list comprehension:
        ```python
        # BEFORE:
        anat_series = [s for s in series if roles.get(s.series_number) == suffix]

        # AFTER:
        seen_sn: set[int] = set()
        anat_series: list[Series] = []
        for s in series:
            if s.series_number not in seen_sn and roles.get(s.series_number) == suffix:
                anat_series.append(s)
                seen_sn.add(s.series_number)
        ```
      </spec>
      <dependencies>C1</dependencies>
      <risk>medium - multiple changes in the core classifier, but each touches distinct code regions and is independently testable</risk>
      <rollback>Revert all changes in stage2_classify.py to restore VE11-only behavior.</rollback>
    </change>

    <change id="C3" priority="P0" source_item="Bug 6">
      <file path="fmri_bids_recon/labels.py" action="modify" />
      <description>
        Normalize descriptions by stripping the _SBRef suffix in the label
        collision guard. SBRef and BOLD for the same task have different
        SeriesDescriptions (e.g. "..._SBRef" and "...") that correctly derive
        the same label, but the collision guard treats them as distinct tasks.
      </description>
      <spec>
        Add a module-level regex constant before the collision check section
        (around line 368, before the `label_to_descs` dict construction):
        ```python
        _SBREF_SUFFIX_RE = re.compile(r"[_\s]*sbref\s*$", re.IGNORECASE)
        ```
        `re` is already imported at line 11.

        Modify the collision check (lines 373-380):
        ```python
        # BEFORE:
        for label, descs in label_to_descs.items():
            if len(descs) > 1:
                raise LabelCollisionError(
                    f"Task label '{label}' is claimed by {len(descs)} distinct "
                    f"SeriesDescriptions: {descs}. Each description must produce a "
                    f"unique BIDS task label.",
                    context={"label": label, "descriptions": descs},
                )

        # AFTER:
        for label, descs in label_to_descs.items():
            if len(descs) > 1:
                stems = {_SBREF_SUFFIX_RE.sub("", d).lower().strip() for d in descs}
                if len(stems) > 1:
                    raise LabelCollisionError(
                        f"Task label '{label}' is claimed by {len(descs)} distinct "
                        f"SeriesDescriptions: {descs}. Each description must produce a "
                        f"unique BIDS task label.",
                        context={"label": label, "descriptions": descs},
                    )
        ```
      </spec>
      <dependencies>None</dependencies>
      <risk>low - only loosens the collision guard for the specific SBRef/BOLD pairing case</risk>
      <rollback>Remove _SBREF_SUFFIX_RE and the stem normalization; restore the direct len(descs) > 1 raise.</rollback>
    </change>

    <change id="C4" priority="P0" source_item="Bugs 7, 8">
      <file path="fmri_bids_recon/physio.py" action="modify" />
      <description>
        Downgrade two fatal guards to warnings: (a) missing ACQUISITION_INFO in
        `associate_physio` (XA30 physio logs lack this block); (b) missing
        positive SampleTime in `write_physio` (XA30 physio channels report
        SampleTime=0). VE11 data with valid ACQUISITION_INFO and SampleTime is
        unaffected (the warning path is never entered).
      </description>
      <spec>
        **C4a** (Bug 7): Lines 511-518 in `associate_physio`, replace the
        `raise PhysioAssociationError(...)` with:
        ```python
        if log.acq_info is None:
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "Physio log SN=%s has no ACQUISITION_INFO block; "
                "geometry verification skipped, pairing by temporal proximity only.",
                log.series_number,
            )
            result[best_bold.series_number] = log
            continue
        ```

        **C4b** (Bug 8): Lines 595-600 in `write_physio`, replace the
        `raise PhysioParseError(...)` with:
        ```python
        if sample_time_ticks is None:
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "Physio log for %s has no channel with a positive SampleTime; "
                "skipping physio file generation for this run.",
                run_prefix,
            )
            return []
        ```
      </spec>
      <dependencies>None</dependencies>
      <risk>low - both changes downgrade fatal errors to warnings for XA30-specific data characteristics only</risk>
      <rollback>Restore the raise statements.</rollback>
    </change>

    <change id="C5" priority="P1" source_item="Bug 9">
      <file path="fmri_bids_recon/stage6_validate.py" action="modify" />
      <description>
        Detect bids-validator startup crash (Node.js v25 incompatibility with
        bids-validator 1.5.3) and downgrade to a warning with upgrade guidance.
        This is an environment issue, not a pipeline logic bug, but the pipeline
        should provide actionable guidance rather than a cryptic ValidationError.
      </description>
      <spec>
        Lines 113-123 in `run_bids_validator`, insert a crash-detection guard
        before the existing `raise ValidationError(...)`:
        ```python
        # BEFORE:
        if result.returncode != 0:
            raise ValidationError(...)

        # AFTER:
        if result.returncode != 0:
            if not result.stdout.strip() and "esm.js" in result.stderr[:200]:
                logger.warning(
                    "bids-validator crashed (likely Node.js version incompatibility); "
                    "skipping spec-compliance validation. Install bids-validator >=2.0 "
                    "or use a compatible Node.js version.",
                )
                return
            raise ValidationError(...)
        ```
        Uses the module-level `logger` already defined at line 20.
      </spec>
      <dependencies>None</dependencies>
      <risk>low - only fires on the specific crash signature; normal validation failures still raise</risk>
      <rollback>Remove the crash-detection guard.</rollback>
    </change>

  </changes>
  <execution_order>C1, C2, C3, C4, C5</execution_order>
</implement_plan>
