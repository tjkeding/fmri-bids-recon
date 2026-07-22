<implement_plan>
  <meta project="fmri-bids-recon" mode="implement" submodule="plan" timestamp="2026-07-17T19:27:32Z" />
  <input_reports>
    <report path="fmri-bids-recon_test_20260717_185304.md" mode="test" key_items="2" />
  </input_reports>

  <assumptions_resolved>
    <resolution id="R1" question="SBRef with no geometry-compatible pair: silent skip or pipeline halt?" decision="Silent skip with logging.warning() that includes per-pair diagnostics. The parent BOLD's association is unaffected; halting on passenger geometry mismatch is disproportionate." source="User adjudication (AskUserQuestion, this session)" />
    <resolution id="R2" question="Which candidate pair(s) to cite in FieldmapCoverageError when no pair is geometry-eligible?" decision="All pairs, each with its per-criterion failure list." source="User adjudication (AskUserQuestion, this session)" />
    <resolution id="R3" question="Separate diagnostic function vs. result object for _geometry_compatible?" decision="Replace with a GeometryResult dataclass returned by _geometry_check. All call sites updated to use .compatible." source="User adjudication (AskUserQuestion, this session)" />
  </assumptions_resolved>

  <changes>

    <change id="C1" priority="P2" source_item="P2 action item (per-criterion geometry diagnostics)">
      <file path="fmri_bids_recon/stage3_map.py" action="modify" />
      <file path="tests/conftest.py" action="modify" />
      <file path="tests/test_map.py" action="modify" />
      <description>Replace the boolean-returning _geometry_compatible with a GeometryResult dataclass and _geometry_check function that returns both a compatibility verdict and per-criterion failure reasons. Update all call sites. Add per-pair diagnostics to FieldmapCoverageError when no eligible pair exists.</description>
      <spec>
1. Add a new dataclass after the existing FieldmapPair/Mapping definitions in fmri_bids_recon/stage3_map.py:

       @dataclass
       class GeometryResult:
           compatible: bool
           failures: list[str]

2. Rename _geometry_compatible to _geometry_check. Change return type from bool to GeometryResult. Preserve the existing None guard as an early return, but report which fields are None in the failures list:

       if any None fields detected:
           return GeometryResult(
               compatible=False,
               failures=["None geometry field(s): a.image_position, b.pe_axis, ..."],
           )

   For the 5 criteria (image_position per axis, affine rotation block, voxel_sizes per axis, matrix exact equality, pe_axis identity): collect ALL failures into a list instead of returning False on first failure. Each failure string is a human-readable diagnostic including the criterion name, observed delta, and tolerance exceeded. Examples:

       "image_position[0]: delta=118.100 mm > tol=0.100 mm"
       "affine[1][2]: delta=0.003000 > tol=0.001000"
       "voxel_sizes[2]: delta=0.500 mm > tol=0.100 mm"
       "matrix: (96, 96, 72) != (64, 64, 40)"
       "pe_axis: 'i' != 'j'"

   Return:
       GeometryResult(compatible=len(failures) == 0, failures=failures)

   Preserve the existing docstring structure; update return-type documentation and the Returns section to describe GeometryResult.

3. Update the two call sites in fmri_bids_recon/stage3_map.py:

   a. pair_fieldmaps union-find (current line 244):
      BEFORE: if _geometry_compatible(series_list[i], series_list[j]):
      AFTER:  if _geometry_check(series_list[i], series_list[j]).compatible:

   b. map_fieldmaps eligibility filter (current lines 421-424): replace the list comprehension with a two-step pattern that preserves check results for diagnostic use in the error path:

      checks = [(i, _geometry_check(p.member_a, s)) for i, p in enumerate(pairs)]
      eligible = [i for i, result in checks if result.compatible]

4. In the existing "if not eligible:" error path (current line 429), build a candidate_pairs diagnostic list from the non-compatible check results and add it to the FieldmapCoverageError context dict:

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

   Add "candidate_pairs": candidate_pairs to the existing context dict in the FieldmapCoverageError constructor call. Do not alter the error message string itself (it remains useful as the top-level summary).

5. Update comment/docstring references to the old function name (_geometry_compatible) to _geometry_check:
   - fmri_bids_recon/stage3_map.py: docstrings at current lines 192, 296, 420
   - tests/conftest.py: comment at line 50
   - tests/test_map.py: comments at lines 140, 154, 209, 369, 386
      </spec>
      <dependencies>none</dependencies>
      <risk>low - the function is tested indirectly through all pairing and geometry-guard tests (9 pairing tests, 3 geometry-guard tests, the SBRef coverage test, and the geometry-mismatch-splits-to-singletons test all exercise _geometry_compatible via pair_fieldmaps or map_fieldmaps); the short-circuit to collect-all change does not alter boolean semantics; comment-reference updates are mechanical</risk>
      <rollback>Revert the function rename and dataclass addition; restore _geometry_compatible.</rollback>
    </change>

    <change id="C2" priority="P0" source_item="P0 action item (SBRef B0FieldSource passenger gap)">
      <file path="fmri_bids_recon/stage3_map.py" action="modify" />
      <description>Add a "passenger pass" after the orphan check in map_fieldmaps that processes Role.SBREF and Role.DWI_SBREF targets through geometry-eligibility and nearest-in-time assignment, appending them to pair_to_targets so render() writes their B0FieldSource. SBRef targets do not count toward orphan coverage (the orphan check runs before the passenger pass). A passenger with no geometry-compatible pair is a silent skip with a logging.warning() that includes per-pair diagnostics from _geometry_check.</description>
      <spec>
1. At the top of fmri_bids_recon/stage3_map.py, add:
       import logging
   After the module docstring (before the existing imports), add:
       logger = logging.getLogger(__name__)

2. Inside map_fieldmaps, define a passenger role-to-modality dict adjacent to the existing _ROLE_TO_MODALITY (current line 405):
       _SBREF_MODALITY: dict[Role, str] = {Role.SBREF: "func", Role.DWI_SBREF: "dwi"}

3. After guard_log["no_orphan_pairs"] = True (current line 490), before the return statement, add the passenger pass:

       # Passenger pass: assign SBRef/DWI_SBREF targets to geometry-compatible
       # pairs for B0FieldSource metadata, without affecting orphan coverage.
       for s, role in targets_sorted:
           modality = _SBREF_MODALITY.get(role)
           if modality is None:
               continue

           checks = [(i, _geometry_check(p.member_a, s)) for i, p in enumerate(pairs)]
           eligible = [i for i, result in checks if result.compatible]

           if not eligible:
               diagnostics = [
                   {
                       "pair_index": i,
                       "run_index": pairs[i].run_index,
                       "modality": pairs[i].modality,
                       "series": [
                           pairs[i].member_a.series_number,
                           pairs[i].member_b.series_number,
                       ],
                       "failures": result.failures,
                   }
                   for i, result in checks
                   if not result.compatible
               ]
               logger.warning(
                   "SBRef series %d (%s) has no geometry-compatible fieldmap "
                   "pair; B0FieldSource will not be assigned. "
                   "Per-pair diagnostics: %s",
                   s.series_number,
                   s.description,
                   diagnostics,
               )
               continue

           if len(eligible) == 1:
               chosen = eligible[0]
           else:
               def _time_dist(pair_idx: int) -> float:
                   p = pairs[pair_idx]
                   pair_dt = max(
                       p.member_a.acquisition_datetime,
                       p.member_b.acquisition_datetime,
                   )
                   return abs((s.acquisition_datetime - pair_dt).total_seconds())

               sorted_eligible = sorted(eligible, key=_time_dist)
               d0 = _time_dist(sorted_eligible[0])
               d1 = _time_dist(sorted_eligible[1])
               if d0 == d1:
                   raise FieldmapCoverageError(
                       f"SBRef series {s.series_number} "
                       f"(description={s.description!r}) has a time-distance "
                       f"tie between eligible fieldmap pairs "
                       f"{sorted_eligible[0]} and {sorted_eligible[1]}; "
                       f"association is ambiguous.",
                       context={
                           "series_number": s.series_number,
                           "description": s.description,
                           "tied_pair_indices": [
                               sorted_eligible[0],
                               sorted_eligible[1],
                           ],
                       },
                   )
               chosen = sorted_eligible[0]

           pair_to_targets[chosen].append(s)

4. No changes to stage5_render.py: B0FieldSource is written for any Series in pair_to_targets (lines 166-176). No changes to stage4_assemble.py: bids_relative_paths is already populated for SBREF (line 350) and DWI_SBREF (line 410).
      </spec>
      <dependencies>C1 (uses _geometry_check and GeometryResult for per-pair diagnostics in the logging.warning call)</dependencies>
      <risk>low - the passenger pass is structurally isolated after the orphan check and cannot affect justifier-pass behavior or orphan coverage accounting; the orphan check (which enforces SBRef-not-justifier) runs before the passenger pass executes; the existing test_an_sbref_does_not_count_as_coverage passes unchanged because the orphan check raises FieldmapCoverageError before the passenger pass runs</risk>
      <rollback>Remove the passenger-pass block, the _SBREF_MODALITY dict, and the import logging / logger lines.</rollback>
    </change>

  </changes>

  <execution_order>C1, C2 (sequential; both modify fmri_bids_recon/stage3_map.py)</execution_order>

</implement_plan>
