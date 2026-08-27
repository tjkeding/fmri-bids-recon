<implement_plan>
  <meta project="fmri-bids-recon" mode="implement" submodule="plan" timestamp="2026-08-27T19:12:54Z" />
  <input_reports>
    <report path="fmri-bids-recon_brainstorm_20260827_190941.md" mode="brainstorm" key_items="5" />
  </input_reports>
  <changes>
    <change id="C1" priority="P0" source_item="T1/A4 decision item 1">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>Add DROP_CALIBRATION to the Role enum. Insert after DROP_ANAT_ND_T2W, before UNCLASSIFIED.</description>
      <spec>
In the Role(StrEnum) class (line 22-40), add:

    DROP_CALIBRATION = "drop_calibration"

after the line `DROP_ANAT_ND_T2W = "drop_anat_nd_t2w"` (line 39) and before `UNCLASSIFIED = "unclassified"` (line 40).
      </spec>
      <dependencies>none</dependencies>
      <risk>low - enum addition, no existing code references this value</risk>
      <rollback>Remove the enum member</rollback>
    </change>

    <change id="C2" priority="P0" source_item="T1/A4 decision items 2-5">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>Add post-classification PE axis validation pass after the NORM/ND twin resolution pass. For each FMAP_FUNC series, check if its PE axis matches the PE axis of at least one BOLD series; for each FMAP_DWI series, check against DWI series. If no target series of the relevant modality exist, skip the check. Demote non-matching series to DROP_CALIBRATION with a graded_warning at medium severity.</description>
      <spec>
After the NORM/ND twin resolution pass (after the DUPLICATE_MODALITY check ending at line 486, before `return roles, flags` at line 488), insert a new section:

    # ------------------------------------------------------------------
    # Calibration sequence exclusion pass (PE axis validation)
    # ------------------------------------------------------------------
    bold_pe_axes: set[str] = set()
    dwi_pe_axes: set[str] = set()
    for s in series:
        r = roles.get(s.series_number)
        if r == Role.BOLD and s.pe_axis is not None:
            bold_pe_axes.add(s.pe_axis)
        elif r == Role.DWI and s.pe_axis is not None:
            dwi_pe_axes.add(s.pe_axis)

    for s in series:
        r = roles.get(s.series_number)
        if r == Role.FMAP_FUNC:
            if not bold_pe_axes:
                continue
            if s.pe_axis is not None and s.pe_axis not in bold_pe_axes:
                roles[s.series_number] = Role.DROP_CALIBRATION
                flags.append(
                    graded_warning(
                        _logger, SEVERITY_MEDIUM, "CALIBRATION_PE_AXIS_MISMATCH",
                        f"Series {s.series_number} classified as FMAP_FUNC but "
                        f"its PE axis '{s.pe_axis}' does not match any BOLD "
                        f"series PE axis {bold_pe_axes}; demoted to "
                        f"DROP_CALIBRATION.",
                    )
                )
        elif r == Role.FMAP_DWI:
            if not dwi_pe_axes:
                continue
            if s.pe_axis is not None and s.pe_axis not in dwi_pe_axes:
                roles[s.series_number] = Role.DROP_CALIBRATION
                flags.append(
                    graded_warning(
                        _logger, SEVERITY_MEDIUM, "CALIBRATION_PE_AXIS_MISMATCH",
                        f"Series {s.series_number} classified as FMAP_DWI but "
                        f"its PE axis '{s.pe_axis}' does not match any DWI "
                        f"series PE axis {dwi_pe_axes}; demoted to "
                        f"DROP_CALIBRATION.",
                    )
                )

Note: `s.pe_axis` is the polarity-stripped PE axis property from Sidecar (returns first char of PhaseEncodingDirection, e.g. 'j' for both 'j' and 'j-'). It is already accessible on Series objects via the inherited Sidecar.pe_axis property.
      </spec>
      <dependencies>C1</dependencies>
      <risk>low - follows existing NORM/ND pass pattern; operates on already-classified roles; empty-target bypass prevents false demotion</risk>
      <rollback>Remove the inserted section</rollback>
    </change>

    <change id="C3" priority="P1" source_item="T1/A4 decision item 6">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>Add secondary compound keyword guard for defense-in-depth. After the PE axis validation pass (C2), add a keyword-based guard that catches calibration sequences sharing PE axis with targets. Requires compound match: keyword in description AND single-volume AND description stem differs from all target modality series.</description>
      <spec>
Add a module-level constant after _SCOUT_KEYWORDS (line 187):

_CALIBRATION_KEYWORDS = frozenset({"setter", "prescan"})

Then, immediately after the PE axis validation pass from C2 (still before `return roles, flags`), insert:

    # ------------------------------------------------------------------
    # Calibration sequence exclusion pass (description keyword guard)
    # ------------------------------------------------------------------
    bold_stems: set[str] = set()
    dwi_stems: set[str] = set()
    for s in series:
        r = roles.get(s.series_number)
        if r == Role.BOLD:
            bold_stems.add(description_stem(s.description))
        elif r == Role.DWI:
            dwi_stems.add(description_stem(s.description))

    for s in series:
        r = roles.get(s.series_number)
        if r not in (Role.FMAP_FUNC, Role.FMAP_DWI):
            continue
        desc_lower = s.description.lower()
        if not any(kw in desc_lower for kw in _CALIBRATION_KEYWORDS):
            continue
        if s.n_volumes != 1:
            continue
        stem = description_stem(s.description)
        target_stems = bold_stems if r == Role.FMAP_FUNC else dwi_stems
        if stem not in target_stems:
            roles[s.series_number] = Role.DROP_CALIBRATION
            flags.append(
                graded_warning(
                    _logger, SEVERITY_MEDIUM, "CALIBRATION_KEYWORD_MATCH",
                    f"Series {s.series_number} (role={r.value}) matches "
                    f"calibration keyword in description "
                    f"{s.description!r} and its description stem "
                    f"does not match any target series; demoted to "
                    f"DROP_CALIBRATION.",
                )
            )

Note: description_stem is already imported (line 16). The compound match requirement (keyword AND single-volume AND stem mismatch) narrows false-positive surface. Series already demoted to DROP_CALIBRATION by C2's PE axis check will have r != FMAP_FUNC/FMAP_DWI and be skipped by the `if r not in ...` guard.
      </spec>
      <dependencies>C1, C2</dependencies>
      <risk>low - keyword guard is defense-in-depth; compound match prevents false positives; operates after PE axis pass so already-demoted series are skipped</risk>
      <rollback>Remove the constant and the inserted section</rollback>
    </change>

    <change id="C4" priority="P1" source_item="T1/A4 decision item 7">
      <file path="fmri_bids_recon/stage4_assemble.py" action="modify" />
      <description>Verify and update the DROP_* comment in stage4_assemble.py to explicitly list DROP_CALIBRATION. The existing fallthrough behavior at line 400 already silently discards all unhandled DROP_* roles, so DROP_CALIBRATION is functionally covered. This change makes the coverage explicit in the comment.</description>
      <spec>
At line 400, change:

        # Role.DROP_DERIVED, DROP_SCOUT, DROP_NAVIGATOR: silently discarded.

to:

        # Role.DROP_DERIVED, DROP_SCOUT, DROP_NAVIGATOR, DROP_CALIBRATION:
        # silently discarded.
      </spec>
      <dependencies>C1</dependencies>
      <risk>low - comment-only change</risk>
      <rollback>Revert the comment</rollback>
    </change>

    <change id="C5" priority="P0" source_item="T1/A4 decision item 2 (docstring update)">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>Update the classify() docstring to document the new calibration sequence exclusion pass alongside the existing NORM/ND pass.</description>
      <spec>
At lines 1-7, change the module docstring from:

"""Stage 2: series classification for fmri-bids-recon.

Assigns a :class:`Role` to every :class:`~fmri_bids_recon.sidecar.Series` loaded
from the staging directory. Classification applies ten ordered rules with
first-match-wins semantics, followed by an anatomical NORM/ND twin resolution
pass.
"""

to:

"""Stage 2: series classification for fmri-bids-recon.

Assigns a :class:`Role` to every :class:`~fmri_bids_recon.sidecar.Series` loaded
from the staging directory. Classification applies ten ordered rules with
first-match-wins semantics, followed by an anatomical NORM/ND twin resolution
pass and a calibration sequence exclusion pass.
"""

Similarly, update the classify() function docstring (lines 207-211) from:

    Rules are evaluated in order; the first matching rule wins.  After the
    initial per-series pass, an anatomical NORM/ND twin resolution pass
    demotes ND reconstructions to ``DROP_ANAT_ND_T1W`` / ``DROP_ANAT_ND_T2W``
    where a NORM partner with identical matrix geometry exists.

to:

    Rules are evaluated in order; the first matching rule wins.  After the
    initial per-series pass, an anatomical NORM/ND twin resolution pass
    demotes ND reconstructions to ``DROP_ANAT_ND_T1W`` / ``DROP_ANAT_ND_T2W``
    where a NORM partner with identical matrix geometry exists.  A subsequent
    calibration sequence exclusion pass demotes FMAP_FUNC/FMAP_DWI series
    whose PE axis does not match any target series of the corresponding
    modality to ``DROP_CALIBRATION``.
      </spec>
      <dependencies>C1</dependencies>
      <risk>low - docstring-only change</risk>
      <rollback>Revert the docstring</rollback>
    </change>
  </changes>
  <execution_order>C1, C5, C2, C3, C4</execution_order>
</implement_plan>
