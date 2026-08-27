<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-08-24T20:15:00Z" />
  <input_reports>
    <report path="bids-recon_test_20260824_192120.md" mode="test" key_items="1" />
  </input_reports>
  <changes>
    <change id="C1" priority="P0" source_item="action_items[0]: Rule 5/Rule 9 ordering conflict">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>Make Rule 5 context-aware by adding a DWI look-ahead inside the rule body. The broadened physics gate (tok != "DIFFUSION", SE, EP, no GR, n_volumes == 1) is preserved as-is; only the interior classification logic changes. The rule now handles ALL single-volume spin-echo EPI classification:

1. DWI look-ahead: locate the current series in by_time, inspect the next chronologically-adjacent series, and check whether it shares the same description stem, carries a DIFFUSION modality token, and has a .bval companion. If all three conditions hold, classify as DWI_SBREF and continue.

2. Default: classify as FMAP_FUNC and continue.

Physics justification: the gate admits exactly two possible roles for a single-volume SE EPI (excluding tok="DIFFUSION", which is handled by Rule 6). A series matching this gate is either a functional fieldmap or a diffusion single-band reference. The DWI look-ahead eliminates the latter; the remaining possibility is FMAP_FUNC. This is not a guess: it is the only classification consistent with the physics-defined role space.

Vendor coverage: on Siemens XA30 (tok="FMRI"), FMAP_FUNC fires via the default path. On E11 (tok="M"), GE (tok="OTHER"), and Philips (tok="M"), FMAP_FUNC fires identically because the gate does not discriminate on tok beyond excluding "DIFFUSION". On any platform where a DWI SBRef has the same physics (tok="M", SE, EP, n_volumes=1), the look-ahead catches it. The Rule 5 broadening from T5/C3 is fully preserved.

Rule 9 impact: SE EPIs no longer reach Rule 9 (they are fully handled by Rule 5). Rule 9 continues to handle gradient-echo single-volume EPIs (functional SBRefs with scanning_sequence=("EP","GR"), and the rare gradient-echo DWI SBRef). This is correct because functional SBRefs match their BOLD's gradient-echo physics, not spin-echo.</description>
      <spec>File: fmri_bids_recon/stage2_classify.py
Location: lines 259-268 (Rule 5 block)

Replace the current Rule 5 body:

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

With:

        # Rule 5: single-volume spin-echo EPI (FMAP_FUNC or DWI_SBREF)
        if (
            tok != "DIFFUSION"
            and "EP" in s.scanning_sequence
            and _is_spin_echo(s)
            and "GR" not in s.scanning_sequence
            and s.n_volumes == 1
        ):
            _r5_pos = next(
                (i for i, t in enumerate(by_time)
                 if t.series_number == s.series_number),
                None,
            )
            if _r5_pos is not None and _r5_pos + 1 &lt; len(by_time):
                _r5_nxt = by_time[_r5_pos + 1]
                if (
                    _description_stem(s.description)
                    == _description_stem(_r5_nxt.description)
                    and modality_token(_r5_nxt) == "DIFFUSION"
                    and _bval_exists(_r5_nxt)
                ):
                    roles[s.series_number] = Role.DWI_SBREF
                    continue
            roles[s.series_number] = Role.FMAP_FUNC
            continue

Functions referenced (all already defined in scope): _description_stem, modality_token, _bval_exists. Variable by_time is the chronologically sorted series list computed at line 174. The underscore-prefixed locals (_r5_pos, _r5_nxt) avoid confusion with Rule 9's identically-structured look-ahead (which uses pos, nxt).

Behavioral trace for each case:

(a) tok="FMRI", SE, EP, single-volume, no DWI follows:
    Gate passes. Look-ahead: no DWI match. Default: FMAP_FUNC. (unchanged from current behavior)

(b) tok="FMRI", SE, EP, single-volume, DWI follows (same stem):
    Gate passes. Look-ahead: DWI match. DWI_SBREF. (edge case, unlikely: fieldmap and DWI protocols rarely share a description stem)

(c) tok="M", SE, EP, single-volume, DWI follows (same stem):
    Gate passes. Look-ahead: DWI match. DWI_SBREF. (fixes test 1: currently misclassified as FMAP_FUNC)

(d) tok="M", SE, EP, single-volume, no DWI follows:
    Gate passes. Look-ahead: no match (lone series, or next series not DWI). Default: FMAP_FUNC. (E11/GE/Philips fieldmap classification: currently FMAP_FUNC, remains FMAP_FUNC)

(e) tok="OTHER", SE, EP, single-volume, no DWI follows:
    Gate passes. Look-ahead: no match. Default: FMAP_FUNC. (GE fieldmap classification: currently FMAP_FUNC, remains FMAP_FUNC)

(f) tok="DIFFUSION", SE, EP, single-volume:
    Gate fails (tok=="DIFFUSION"). Skips Rule 5 entirely, reaches Rule 6 (FMAP_DWI). (unchanged)

No existing PASSING test is affected: the fmap_func factory uses tok="FMRI" (case a); the sbref factory uses scanning_sequence=("EP","GR") which fails the "GR not in" gate; the dwi/fmap_dwi factories use tok="DIFFUSION" which fails the tok != "DIFFUSION" gate.</spec>
      <dependencies>none</dependencies>
      <risk>low - single-block edit within one rule; all six behavioral cases traced; no other rule's gate or classification is modified</risk>
      <rollback>Revert lines 259-282 to the pre-edit form (the two-line body: roles assignment + continue)</rollback>
    </change>
    <change id="C2" priority="P0" source_item="action_items[0]: Rule 5/Rule 9 ordering conflict (test contract update)">
      <file path="tests/test_classify.py" action="modify" />
      <description>Update test_a_single_volume_epi_with_no_following_dwi_is_unclassified to reflect the revised contract. With the context-aware Rule 5, a lone single-volume SE EPI with tok="M" is classified as FMAP_FUNC (the only remaining possibility after the DWI look-ahead finds no match), not UNCLASSIFIED.

Disposition change: the original product-bug disposition assumed the test contract was authoritative and the code was wrong. The deeper analysis revealed that the test was written against pre-broadening behavior (where tok="M" skipped Rule 5 entirely). With the broadened, context-aware Rule 5, FMAP_FUNC is the correct classification: the physics signature admits only FMAP_FUNC or DWI_SBREF, and the look-ahead eliminates DWI_SBREF. Reclassifying the disposition to obsolete-test (the broadening changed the intended contract for this case) per user approval of the merger approach.

Three changes to the test:
1. Rename from test_a_single_volume_epi_with_no_following_dwi_is_unclassified to test_a_lone_single_volume_spin_echo_epi_is_a_functional_fieldmap.
2. Update the comment to reflect the physics rationale.
3. Change the assertion from Role.UNCLASSIFIED to Role.FMAP_FUNC.</description>
      <spec>File: tests/test_classify.py
Location: lines 363-372

Replace:

def test_a_single_volume_epi_with_no_following_dwi_is_unclassified(make_series):
    # Symmetry with the SBRef contract: a diffusion reference is defined by the DWI
    # that follows it. A lone single-volume EPI magnitude series is not a reference
    # to anything, so it falls through to UNCLASSIFIED rather than emitting a _sbref
    # under dwi/ with no acquisition to accompany it.
    ref = make_series(29, "STUDY_dwi", scanning_sequence=("EP", "SE"))

    roles, _ = classify([ref])

    assert roles[29] == Role.UNCLASSIFIED

With:

def test_a_lone_single_volume_spin_echo_epi_is_a_functional_fieldmap(make_series):
    # A single-volume SE EPI whose DWI look-ahead finds no diffusion successor
    # classifies as FMAP_FUNC: the physics gate (SE, EP, no GR, n_volumes=1)
    # admits only FMAP_FUNC or DWI_SBREF, and the look-ahead eliminates the latter.
    ref = make_series(29, "STUDY_dwi", scanning_sequence=("EP", "SE"))

    roles, _ = classify([ref])

    assert roles[29] == Role.FMAP_FUNC

No cascading references: this test is not referenced by test_guard_coverage.py or any other structural inventory. The rename is self-contained.</spec>
      <dependencies>C1</dependencies>
      <risk>low - assertion and name change on a single test; no guard roster reference; no import dependency</risk>
      <rollback>Revert the test function to its original name, comment, and assertion</rollback>
    </change>
  </changes>
  <execution_order>C1, C2</execution_order>
</implement_plan>
