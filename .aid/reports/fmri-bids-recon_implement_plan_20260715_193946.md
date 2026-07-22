<implement_plan>
  <meta project="fmri-bids-recon" mode="implement" submodule="plan" timestamp="2026-07-15T23:39:46Z" />
  <input_reports>
    <report path="(none — change specified directly by user)" mode="direct" key_items="1" />
  </input_reports>
  <changes>
    <change id="C1" priority="P0" source_item="direct-user-directive">
      <file path="fmri_bids_recon/stage3_map.py" action="modify" />
      <description>
        Remove the invalid SeriesNumber/AcquisitionDateTime monotonicity guard from order_series.
        SeriesNumber is not chronological on Siemens XA30 (derived/secondary series are numbered
        higher than earlier-acquired primaries), so the fatal OrderingError raised when the two
        ordering signals disagree encodes a false assumption contradicted by the project's own
        representative raw data. AcquisitionDateTime is the sole authoritative chronological anchor
        and is already the only key used by every downstream temporal consumer (pair_fieldmaps
        re-sorts by acquisition_datetime; map_fieldmaps assigns nearest-preceding by
        acquisition_datetime). Per explicit user directive, AcquisitionDateTime is treated as the
        single ordering anchor with no cross-check against any other field.
      </description>
      <spec>
        Function: def order_series(series: list[Series]) -> list[Series]  (signature UNCHANGED; still
        returns a bare list[Series], preserving all inline call sites and the production composition).

        Body: replace the entire current body (the `sorted_by_dt = sorted(...)` assignment, the
        `for i in range(len(sorted_by_dt) - 1): ...` loop, the nested `if a.acquisition_datetime <
        b.acquisition_datetime:` / `if a.series_number > b.series_number:` guard, the
        `raise OrderingError(...)` block, and the final `return sorted_by_dt`) with a single
        statement:
            return sorted(series, key=lambda s: s.acquisition_datetime)

        Docstring: keep the one-line summary reworded to reflect sort-only behavior; keep the
        Returns section (list sorted ascending by acquisition_datetime); REMOVE the `Raises
        OrderingError` section; add a short Notes sentence stating that AcquisitionDateTime is the
        authoritative chronological anchor and SeriesNumber is NOT chronological on Siemens XA30, so a
        SeriesNumber/AcquisitionDateTime disagreement is expected and is not treated as an error.

        Import block: in the `from .errors import (...)` statement at the top of the module, REMOVE
        the `OrderingError,` entry (now unused in this module). Leave PhaseEncodingError,
        FieldmapGeometryError, and FieldmapCoverageError in place.

        Do NOT modify __main__.py. Do NOT modify errors.py (leave the OrderingError class defined).
        Do NOT modify any test. Do NOT touch any other function in stage3_map.py.
      </spec>
      <dependencies>none</dependencies>
      <risk>
        low - Signature and return type are unchanged, so the ~40 inline call sites in tests and the
        production composition in __main__.py (order_series feeding pair_fieldmaps/map_fieldmaps) are
        unaffected. The only behavioral change is that the previously-fatal ordering disagreement no
        longer raises. Downstream fieldmap logic already orders exclusively by acquisition_datetime,
        so mapping correctness is unchanged. One existing test (tests/test_map.py::
        test_acquisition_time_disagreeing_with_series_number_raises) asserts the removed raise and
        will fail; this is an obsolete-test disposition (contract changed by explicit user decision),
        to be re-expressed via /test, not handled here. OrderingError becomes an unused class in
        errors.py; its definition is intentionally left in place for tomorrow's guard redesign.
      </rollback>
      <rollback>
        Restore order_series to its prior body (re-add the sorted_by_dt assignment, the pairwise
        monotonicity loop, and the raise OrderingError block) and re-add `OrderingError,` to the
        `from .errors import (...)` block. Single-file, self-contained revert.
      </rollback>
    </change>
  </changes>
  <execution_order>C1</execution_order>
</implement_plan>
