<implement_report>
  <meta project="fmri-bids-recon" mode="implement" submodule="build" timestamp="2026-07-17T19:54:12Z" />
  <spec_ref>fmri-bids-recon_implement_plan_20260717_192732.md</spec_ref>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage3_map.py" lines_changed="~90" />
        <file path="tests/conftest.py" lines_changed="1" />
        <file path="tests/test_map.py" lines_changed="5" />
      </files_modified>
      <notes>Replaced the boolean-returning geometry-compatibility check with a GeometryResult dataclass (compatible, failures) returned by the renamed _geometry_check function. All five geometry criteria (image_position, affine rotation block, voxel_sizes, matrix, pe_axis) now collect into a single failures list instead of short-circuiting on the first mismatch. Both call sites (the union-find grouping step in pair_fieldmaps and the eligibility filter in map_fieldmaps) were updated to the .compatible accessor. The no-eligible-pair error path in map_fieldmaps now attaches a candidate_pairs diagnostic list (per-pair run index, modality, member series numbers, and failure strings) to the FieldmapCoverageError context. All docstring and comment references to the old function name were updated across the three affected files. Independently verified by reading the modified file in full; no deviations from the tech spec.</notes>
    </change>
    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage3_map.py" lines_changed="~70" />
      </files_modified>
      <notes>Added a module-level logger and a passenger-assignment pass to map_fieldmaps, inserted immediately after the orphan-coverage check completes and before the function returns. The passenger pass iterates SBRef and DWI-SBRef targets, evaluates geometry eligibility against all pairs via the geometry-diagnostic function from the companion change, and assigns each passenger to its geometry-compatible pair so that the rendering stage writes its B0FieldSource metadata. A passenger with no geometry-compatible pair is skipped without raising, and a warning is logged with the same per-pair diagnostics used in the justifier-pass error path. A time-distance tie among multiple eligible pairs raises FieldmapCoverageError, mirroring the justifier pass's tie-handling. Because the passenger pass runs strictly after the orphan check, a passenger assignment can never retroactively satisfy orphan coverage for its pair. Independently verified by reading the modified file in full; no deviations from the tech spec. No changes were required to the rendering or assembly stages, since both already handle any series present in the pair-to-targets mapping.</notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>2</total_changes>
    <completed>2</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <next_steps>Recommended: run /test to validate all changes.</next_steps>
</implement_report>
