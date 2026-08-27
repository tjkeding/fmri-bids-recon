<clean_report>
  <meta project="bids-recon" mode="clean" timestamp="2026-08-24T20:45:00Z" />
  <scope>Full production package fmri_bids_recon/ (23 modules, 5769 LOC). Configuration files (pyproject.toml, tools.lock.yaml) read for cross-reference. Test suite consulted only to verify no consumer relies on symbols proposed for removal. Sandbox backups and the tools/simulated_bids generator were out of scope (not part of the shipped pipeline).</scope>
  <research_conducted>None. All findings derive from static analysis of the codebase: AST-based unused-import detection (stdlib ast, since no linter is installed in the environment), grep-based consumer/reference checks against production and tests, and manual data-flow tracing. No external literature or web research was required; every finding is grounded in local code evidence.</research_conducted>
  <metrics>
    <loc>5769</loc>
    <files>23</files>
    <avg_complexity>Low-to-moderate. The two highest-complexity functions are stage2_classify.classify() (ten ordered rules plus a NORM/ND twin-resolution pass) and stage3_map.map_fieldmaps() (two selection passes); neither exceeds reasonable cyclomatic bounds, though map_fieldmaps carries the duplication noted in F7.</avg_complexity>
  </metrics>
  <findings>
    <finding id="F1" severity="major" category="redundancy">
      <location file="fmri_bids_recon/versions.py" lines="1-83" />
      <description>The entire versions.py module (DCM2NIIX_VERSION_FLOOR, parse_dcm2niix_version, assert_dcm2niix_version) is dead production code, superseded by tool_registry.preflight_tool_environments(). No production module imports it; the version floor it hardcodes duplicates the dcm2niix pin in tools.lock.yaml (two sources of truth). Its companion exception VersionFloorError (errors.py:51-57) is documented "deprecated, retained for test compat" and is raised only by this dead module. The only consumer is test_versions.py (7 tests).</description>
      <current>versions.py performs standalone dcm2niix version probing/parsing/comparison; tool_registry.py independently performs the same probing driven by tools.lock.yaml. The dcm2niix floor "1.0.20260416" is stated in both versions.py and tools.lock.yaml.</current>
      <proposed>Remove versions.py, VersionFloorError, and test_versions.py. Repoint the dcm2niix_version_floor entry in test_guard_coverage.py to engine_module="tool_registry" and error=ToolVersionError. Leaves tools.lock.yaml as the single source of truth for the dcm2niix floor.</proposed>
      <literature>N/A (local-only finding).</literature>
      <impact>Removes 83 lines of dead production code, 90 lines of dead tests, one deprecated exception class, and a duplicated version constant with drift risk (single source of truth for the dcm2niix floor).</impact>
    </finding>
    <finding id="F2" severity="minor" category="redundancy">
      <location file="fmri_bids_recon/deface.py" lines="35-59" />
      <description>assert_deface_tools() is documented "Called at pipeline startup when config.deface is True" but is never called in production (pipeline.py:309 calls only deface(config); __main__ never references it). Its startup pre-flight job is already performed by preflight_tool_environments() (pipeline.py:124), which probes pydeface and flirt via the conditional:deface entries in tools.lock.yaml and raises ToolVersionError (exit 4) before any DICOM processing. No correctness gap exists; the function is strictly redundant. Its only distinctive value is a more actionable FSLDIR-specific error hint.</description>
      <current>assert_deface_tools() and _resolve_flirt() duplicate the FSLDIR/bin/flirt then PATH resolution already implemented in tool_registry._resolve_binary("flirt", ...). Sole consumers are 8 tests in test_deface.py.</current>
      <proposed>Remove assert_deface_tools() and _resolve_flirt() and their 8 tests. Fold the FSLDIR-specific hint ("Set the FSLDIR environment variable ...") into tool_registry's flirt "not found on PATH" error message so the actionable guidance is preserved at the single live gate.</proposed>
      <literature>N/A (local-only finding).</literature>
      <impact>Removes ~26 lines of dead production code plus its helper and 8 tests; preserves the better error message at the one place the check actually runs.</impact>
    </finding>
    <finding id="F3" severity="minor" category="redundancy">
      <location file="fmri_bids_recon/stage2_classify.py, report.py, stage3_map.py, stage4_assemble.py, stage5_render.py" lines="multiple" />
      <description>Six genuine dead imports and three stale/misleading noqa:F401 markers, verified against the full test suite (no external consumer of any re-export). Dead imports: SEVERITY_HIGH (stage2_classify:19), json (report:10), FieldmapPair (report:16), modality_token re-export (stage3_map:12), RegistryDelta re-export (stage4_assemble:24), PE_DIRECTION_TO_LABEL re-export (stage5_render:14). Stale noqa markers (the symbol is actually used, so F401 would never fire): field (stage3_map:10), the stage4_assemble:21 group, and stage5_render:14 after its dead symbol is removed. The "re-exported per spec" comments assert a contract no importer honors.</description>
      <current>Import lists carry unused symbols; noqa:F401 markers suppress warnings that either would not fire (used symbols) or mask genuinely dead re-exports no module consumes.</current>
      <proposed>Drop the six dead symbols from their import lists (removing the RegistryDelta line entirely), and remove the three stale noqa markers so the remaining used symbols stand without suppression.</proposed>
      <literature>N/A (local-only finding).</literature>
      <impact>Pure hygiene; zero behavioral change, zero risk (no consumers). Corrects noqa markers that misrepresent used symbols as re-exported dead weight.</impact>
    </finding>
    <finding id="F4" severity="minor" category="redundancy">
      <location file="fmri_bids_recon/stage2_classify.py, labels.py" lines="stage2_classify:69,72-74; labels:38,376" />
      <description>The _SBREF_SUFFIX_RE regex (r"[_\s]*sbref\s*$", IGNORECASE) is compiled identically in two modules, and the three-step stem normalization (sub then lower then strip) is duplicated: stage2_classify._description_stem() vs the inline set comprehension at labels.py:376. The two stems gate coupled decisions on the same descriptions (classifier SBRef look-ahead vs the LabelCollisionError injectivity guard), so drift between the copies could cause a false-positive halt or a false-negative collision.</description>
      <current>Two independent compilations of the identical regex and two independent implementations of the identical stem transformation.</current>
      <proposed>Promote a public description_stem() plus the compiled regex into sidecar.py (the shared low-level module both already import from), and route both stage2_classify and labels through it. Cycle-free (sidecar imports neither module); behavior-preserving (transformation is byte-identical at both sites).</proposed>
      <literature>N/A (local-only finding).</literature>
      <impact>Single source of truth for the SBRef stem, removing a drift hazard on a correctness-relevant guard.</impact>
    </finding>
    <finding id="F5" severity="minor" category="redundancy">
      <location file="fmri_bids_recon/stage2_classify.py, stage4_assemble.py, stage5_render.py" lines="stage2_classify:101-108; stage4_assemble:65-72; stage5_render:79-101" />
      <description>The ".nii.gz"/".nii" double-extension stripping kernel is implemented three times (_bval_path, _nifti_filestem, _sidecar_path), with divergent fallback semantics for non-NIfTI names: _bval_path keeps the full name (foo.txt then foo.txt.bval) while the other two fall back to Path.stem (foo.txt then foo). Unreachable with real dcm2niix inputs, but a latent inconsistency; _bval_path and the stage4 DWI companion-copy block also construct the same series' .bval path by two different code paths.</description>
      <current>Three copies of the stem-stripping rule that already disagree on the fallback edge case.</current>
      <proposed>Add a single nifti_stem(path) to sidecar.py (colocated with F4's description_stem), standardizing the fallback on Path.stem, and route all three call sites through it. Adopts the Path.stem fallback everywhere (a theoretical behavior change on an unreachable path for _bval_path), which is the more sensible of the two behaviors.</proposed>
      <literature>N/A (local-only finding).</literature>
      <impact>Removes ~20 lines of triplicated logic and eliminates the divergent-fallback latent inconsistency; single construction path for companion file paths.</impact>
    </finding>
    <finding id="F6" severity="style" category="maintainability">
      <location file="fmri_bids_recon/stage2_classify.py" lines="267-271, 312-315" />
      <description>Rule 5 and Rule 9 each contain the identical next((i for i,t in enumerate(by_time) if t.series_number == s.series_number), None) linear scan inside the per-series loop, giving O(n^2). At the ABCD/XA30 target scale (~20-60 series/session) this is microseconds and wholly dominated by dcm2niix conversion and NIfTI copy I/O, so there is no measurable wall-clock benefit. The genuine value is deduplication of the twice-written lookup and correct O(n) complexity.</description>
      <current>Two identical linear position lookups run per series iteration.</current>
      <proposed>Precompute position_by_sn = {t.series_number: i for i, t in enumerate(by_time)} once after by_time is sorted; Rule 5 and Rule 9 both read position_by_sn.get(s.series_number). Behavior-identical (series_number is unique within a session).</proposed>
      <literature>N/A (local-only finding).</literature>
      <impact>Clarity and deduplication (two sites to one); incidental O(n^2) to O(n) with no practical wall-clock effect at target scale. Framed honestly as a maintainability change, not a performance fix.</impact>
    </finding>
    <finding id="F7" severity="minor" category="redundancy">
      <location file="fmri_bids_recon/stage3_map.py" lines="462-523, 541-606" />
      <description>map_fieldmaps() duplicates its full pair-selection kernel between the target pass and the passenger (SBRef) pass: identical geometry-checks/eligible computation, an identical _time_dist closure defined twice (498-504 and 577-583), and an identical single-or-nearest-with-tie block. The d0 == d1 tie check is the association_unambiguous guard, so the duplication means the passenger pass could drift from the target pass it mirrors. Only the no-eligible handling (high graded_warning + guard flags vs best-effort logger.warning) and the tie error prefix ("Series" vs "SBRef series") legitimately differ.</description>
      <current>~50 lines of near-identical selection logic, with the ambiguity guard written twice.</current>
      <proposed>Extract a module-level _select_pair(s, pairs, kind) helper performing geometry checks, eligibility, single-or-nearest selection, and the tie FieldmapCoverageError (kind supplies the message noun). Each caller keeps its own distinct no-eligible branch using the returned checks. The d0 == d1 exact-float-equality semantics are preserved unchanged (any revisit is separate scope).</proposed>
      <literature>N/A (local-only finding).</literature>
      <impact>Collapses ~50 duplicated lines to one ~18-line helper and gives the association_unambiguous tie guard a single definition.</impact>
    </finding>
    <finding id="F8" severity="minor" category="redundancy">
      <location file="fmri_bids_recon/errors.py" lines="20, 121-128" />
      <description>The ReviewFlag exception class is documented "Retained for backward compatibility with existing tests" but no test references it; the only occurrences are its own definition and the module-docstring listing. Production uses warnings.graded_warning() (plain dicts). The stated justification for retention is false.</description>
      <current>Dead deprecated exception class with an inaccurate retention rationale.</current>
      <proposed>Remove the ReviewFlag class (121-128) and its module-docstring entry (line 20). Coordinate the errors.py module-docstring header edit with F1's removal of the VersionFloorError line (line 5), since both touch the same header block (lines 1-22).</proposed>
      <literature>N/A (local-only finding).</literature>
      <impact>Removes 8 lines of dead code and an inaccurate docstring claim. API-surface reduction is theoretical only: the class is never raised, so no external catcher could ever receive it.</impact>
    </finding>
    <finding id="F9" severity="minor" category="maintainability">
      <location file="fmri_bids_recon/pipeline.py" lines="217-220, 259, 281-284" />
      <description>hasattr(registry_delta, 'new_entries') duck-typing guards a dict-shape branch that is unreachable and latently incorrect. resolve_labels() always returns a RegistryDelta (labels.py:292,392); it round-trips through json_intermediate as a RegistryDelta (registered dataclass); the intermediate key is always written (line 231), so the get(..., {}) default at 259 never fires. Both else branches (220, 284) are dead. The Phase 1 else is also wrong if reached: merged_registry.update(registry_delta) on a plain dict would merge the wrong shape into the registry.</description>
      <current>Two shape-guards on a value that is always a RegistryDelta on every live path; the dict-shape fallback would corrupt the registry rather than protect it if reached.</current>
      <proposed>Line 217-220 to unconditional merged_registry.update(registry_delta.new_entries); line 259 default to intermediate.get('registry_delta') or RegistryDelta() (add RegistryDelta to the labels import); line 281-284 to unconditional new_tasks comprehension. Behavior-identical on all live paths.</proposed>
      <literature>N/A (local-only finding).</literature>
      <impact>Removes dead-and-incorrect defensive scaffolding and makes the RegistryDelta contract explicit and type-consistent. Lowest-confidence finding of the nine; user accepted removal over retaining the defensive branches.</impact>
    </finding>
  </findings>
  <summary>
    <critical_count>0</critical_count>
    <major_count>1</major_count>
    <total_findings>9</total_findings>
    <overall_assessment>needs_minor_work</overall_assessment>
  </summary>
  <action_items>
    <item priority="P1" target_mode="implement" finding_ref="F1" description="Remove versions.py, VersionFloorError, and test_versions.py; repoint the dcm2niix_version_floor guard in test_guard_coverage.py to tool_registry/ToolVersionError. tools.lock.yaml becomes the single source of truth for the dcm2niix floor." />
    <item priority="P2" target_mode="implement" finding_ref="F2" description="Remove assert_deface_tools() and _resolve_flirt() and their 8 tests; fold the FSLDIR-specific hint into tool_registry's flirt not-found error message." />
    <item priority="P2" target_mode="implement" finding_ref="F3" description="Remove 6 dead imports (SEVERITY_HIGH, report.json, report.FieldmapPair, stage3_map.modality_token, stage4_assemble.RegistryDelta, stage5_render.PE_DIRECTION_TO_LABEL) and 3 stale noqa:F401 markers (stage3_map:10, stage4_assemble:21, stage5_render:14)." />
    <item priority="P2" target_mode="implement" finding_ref="F4" description="Promote description_stem() plus the SBRef regex into sidecar.py; route stage2_classify._description_stem and labels.py:376 through it." />
    <item priority="P2" target_mode="implement" finding_ref="F5" description="Add sidecar.nifti_stem(path) with a Path.stem fallback; route _bval_path, _nifti_filestem, and _sidecar_path through it (standardizes _bval_path's unreachable fallback on Path.stem)." />
    <item priority="P2" target_mode="implement" finding_ref="F6" description="Precompute position_by_sn once in classify(); Rule 5 and Rule 9 read from it instead of re-scanning by_time. Deduplication/clarity change, not a performance fix." />
    <item priority="P2" target_mode="implement" finding_ref="F7" description="Extract _select_pair(s, pairs, kind) in stage3_map.py; both passes of map_fieldmaps() use it, giving the association_unambiguous tie guard a single definition. Preserve d0==d1 float-equality semantics." />
    <item priority="P2" target_mode="implement" finding_ref="F8" description="Remove the ReviewFlag class and its docstring entry; coordinate the errors.py header edit with F1's VersionFloorError removal." />
    <item priority="P2" target_mode="implement" finding_ref="F9" description="Remove the two dead hasattr(registry_delta,'new_entries') branches in pipeline.py; make the Phase 3 default a RegistryDelta() and add RegistryDelta to the labels import." />
  </action_items>
</clean_report>
