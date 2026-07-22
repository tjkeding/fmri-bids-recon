<implement_report>
  <meta project="fmri-bids-recon" mode="implement" submodule="build" timestamp="2026-07-15T23:39:46Z" />
  <spec_ref>fmri-bids-recon_implement_plan_20260715_193946.md</spec_ref>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage3_map.py" lines_changed="20" />
      </files_modified>
      <notes>
        order_series body replaced with the single statement
        `return sorted(series, key=lambda s: s.acquisition_datetime)`; the pairwise
        SeriesNumber/AcquisitionDateTime monotonicity loop and the raise OrderingError block were
        removed. Signature `def order_series(series: list[Series]) -> list[Series]:` is unchanged, so
        all inline call sites (tests and the __main__.py convert composition) are unaffected. Docstring
        reworded to sort-only, Raises/OrderingError section removed, Notes paragraph added documenting
        AcquisitionDateTime as the authoritative anchor and the expected non-chronological SeriesNumber
        on Siemens XA30. `OrderingError` removed from the `from .errors import (...)` block (now unused
        in this module); PhaseEncodingError, FieldmapGeometryError, FieldmapCoverageError retained.
        errors.py, __main__.py, and all tests untouched, per spec. Verified against the on-disk file.
      </notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>1</total_changes>
    <completed>1</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <next_steps>
    Re-run the single subject: `python -m fmri_bids_recon convert --config <yaml> --participant T002 --session 01`
    then `python -m fmri_bids_recon assemble --config <yaml>`. Separately, run /test to re-express the now-obsolete
    test tests/test_map.py::test_acquisition_time_disagreeing_with_series_number_raises (contract changed by
    explicit user decision: an ordering disagreement is no longer fatal); the re-expressed test should assert
    that order_series returns strict acquisition_datetime order even when SeriesNumber disagrees. The unused
    OrderingError class remains defined in errors.py for tomorrow's guard redesign to dispose of.
  </next_steps>
</implement_report>
