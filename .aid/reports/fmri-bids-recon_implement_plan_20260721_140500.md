<implement_plan>
  <meta project="fmri-bids-recon" mode="implement" submodule="plan" timestamp="2026-07-21T14:05:00-04:00" />
  <input_reports>
    <report path="fmri-bids-recon_test_20260721_175600.md" mode="test" key_items="2" />
  </input_reports>
  <changes>
    <change id="C1" priority="P1" source_item="test report action item 1">
      <file path="environment.yml" action="modify" />
      <description>Add pydeface to the pip dependencies in environment.yml. pydeface is not available on conda-forge; it must be added under the pip: subsection. The pipeline invokes pydeface at Phase 5 (deface.py line 82 via subprocess). While deface.py already handles FileNotFoundError gracefully (line 95, logs a warning and skips), having pydeface in environment.yml ensures the defacing step actually executes on real-data runs rather than silently skipping every anatomical. Pin to 2.1.0 (current PyPI release).</description>
      <spec>In environment.yml, add `- pydeface==2.1.0` to the pip: list, after the cubids entry (maintaining alphabetical-ish grouping of pipeline tools). No code changes needed; deface.py already handles the invocation correctly.</spec>
      <dependencies>none</dependencies>
      <risk>low - additive change to environment spec only; no code changes. pydeface 2.1.0 depends on nibabel and numpy, both already pinned in the environment. Existing conda environments will need `pip install pydeface==2.1.0` or recreation.</risk>
      <rollback>Remove the pydeface line from environment.yml.</rollback>
    </change>
    <change id="C2" priority="P2" source_item="test report action item 2">
      <file path="tests/test_map.py" action="modify" />
      <description>Add assertions on the candidate_pairs diagnostic content within FieldmapCoverageError.context for tests that exercise the geometry-mismatch and PE-axis-mismatch error paths. The implementation in stage3_map.py (lines 473-495) populates candidate_pairs with per-pair dicts containing pair_index, run_index, modality, series (list of two series numbers), and failures (list of per-criterion failure strings from GeometryResult). Three existing tests already capture the exception but assert only on series_number and modality, not on candidate_pairs.</description>
      <spec>
Extend three existing tests with candidate_pairs assertions:

1. test_a_target_with_no_geometry_compatible_pair_raises (line 285):
   - Assert `candidate_pairs` key is present in exc.value.context
   - Assert len(candidate_pairs) == 1 (one pair exists but is geometry-incompatible)
   - Assert candidate_pairs[0]["pair_index"] == 0
   - Assert len(candidate_pairs[0]["failures"]) > 0 (at least one failure criterion)
   - Assert any failure string contains "matrix" (the orphan_run has matrix=(64,64,40) vs the pair's (90,90,60))

2. test_a_phase_encoding_axis_mismatch_between_pair_and_target_raises (line 367):
   - Assert candidate_pairs is present and has length 1
   - Assert candidate_pairs[0]["pair_index"] == 0
   - Assert any failure string contains "pe_axis" (the run has PE direction "i-" vs pair's "j"/"j-")

3. test_a_matrix_mismatch_between_pair_and_target_raises (line 384):
   - Assert candidate_pairs is present and has length 1
   - Assert any failure string contains "matrix" (the run has matrix=(64,64,40))

Also extend test_a_func_pair_cannot_cover_a_diffusion_target (line 303):
   - Capture exc and assert candidate_pairs is present with length 1
   - Assert any failure string contains "image_position" (dwi and func have different positions, offset by 118mm)
      </spec>
      <dependencies>none</dependencies>
      <risk>low - additive assertions on existing passing tests. No existing assertions removed or weakened. Assertions strengthen postconditions by verifying diagnostic content that was previously untested.</risk>
      <rollback>Remove the added assertion lines from the four tests.</rollback>
    </change>
  </changes>
  <execution_order>C1, C2</execution_order>
</implement_plan>
