<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-08-24T23:09:00Z" />
  <input_reports>
    <report path="bids-recon_clean_20260824_204500.md" mode="clean" key_items="9" />
  </input_reports>
  <notes>
    The clean report stated F2 removes "8 tests." Actual count is 10 (6 for assert_deface_tools, 4 for _resolve_flirt). All 10 test functions that exercise the two dead functions are removed. The user's approved direction (remove all tests for both dead functions) is unchanged; only the count was inaccurate. Expected suite count after build: 611 - 7 (test_versions.py) - 10 (test_deface.py dead-function tests) = 594.
  </notes>
  <changes>
    <change id="C1" priority="P2" source_item="F4, F5">
      <file path="fmri_bids_recon/sidecar.py" action="modify" />
      <description>Add description_stem(), _SBREF_SUFFIX_RE, and nifti_stem() to sidecar.py. Prerequisite for C2-C5 which route existing call sites through these shared helpers.</description>
      <spec>
1. Add `import re` after line 9 (`import json`).
2. Append after the modality_token function (after line 335):

```python
_SBREF_SUFFIX_RE = re.compile(r"[_\s]*sbref\s*$", re.IGNORECASE)


def description_stem(desc: str) -> str:
    """Strip trailing _SBRef (case-insensitive) and whitespace."""
    return _SBREF_SUFFIX_RE.sub("", desc).lower().strip()


def nifti_stem(path: Path) -> str:
    """Return the bare stem of a NIfTI path with .nii.gz/.nii removed."""
    name = path.name
    if name.endswith(".nii.gz"):
        return name[:-7]
    if name.endswith(".nii"):
        return name[:-4]
    return path.stem
```
      </spec>
      <dependencies>none</dependencies>
      <risk>low — pure addition, no behavioral change, no existing code altered</risk>
      <rollback>Remove the appended functions and the `import re` line.</rollback>
    </change>

    <change id="C2" priority="P2" source_item="F3, F4, F5, F6">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>Consolidates four findings in stage2_classify.py: remove SEVERITY_HIGH dead import (F3), route _description_stem through sidecar.description_stem (F4), route _bval_path through sidecar.nifti_stem (F5), precompute position_by_sn dict (F6).</description>
      <spec>
1. Line 11: remove `import re` (sole consumer was _SBREF_SUFFIX_RE, now in sidecar.py).
2. Line 17: add `description_stem, nifti_stem` to sidecar import:
   `from .sidecar import Series, modality_token, description_stem, nifti_stem`
3. Line 19: remove `SEVERITY_HIGH` from warnings import:
   `from .warnings import graded_warning, SEVERITY_LOW, SEVERITY_MEDIUM`
4. Remove lines 69-74 (_SBREF_SUFFIX_RE compile and _description_stem function). These are replaced by the sidecar.py helpers from C1.
5. Replace _bval_path function (lines 101-108) with:
   ```python
   def _bval_path(s: Series):
       """Return the .bval companion path for a series."""
       return s.nifti_path.parent / (nifti_stem(s.nifti_path) + ".bval")
   ```
6. After line 174 (`by_time: list[Series] = sorted(...)`), insert:
   `position_by_sn = {t.series_number: i for i, t in enumerate(by_time)}`
7. Rule 5 (lines 267-271): replace the `next(...)` generator expression with:
   `_r5_pos = position_by_sn.get(s.series_number)`
   (Remove the 4-line generator; one line replaces it.)
8. Rule 5 body: replace `_description_stem(` with `description_stem(` at the two call sites (lines 275, 276).
9. Rule 9 (lines 312-315): replace the `next(...)` generator expression with:
   `pos = position_by_sn.get(s.series_number)`
   (Remove the 3-line generator; one line replaces it.)
10. Rule 9 body: replace `_description_stem(` with `description_stem(` at line 318.
      </spec>
      <dependencies>C1</dependencies>
      <risk>medium — four changes in the classifier, but each is behavior-preserving (1:1 substitution or dead-import removal); position_by_sn is a precomputed index with identical lookup semantics</risk>
      <rollback>Restore the removed functions and imports; revert position_by_sn to inline generators.</rollback>
    </change>

    <change id="C3" priority="P2" source_item="F4">
      <file path="fmri_bids_recon/labels.py" action="modify" />
      <description>Route the inline SBRef stem normalization through sidecar.description_stem (F4). Removes the duplicated _SBREF_SUFFIX_RE from labels.py.</description>
      <spec>
1. Remove line 38: `_SBREF_SUFFIX_RE = re.compile(r"[_\s]*sbref\s*$", re.IGNORECASE)`
2. Add import after line 16 (`from .sidecar import Series`... wait, labels.py does not import from sidecar. Add a new import line after the existing imports block (after line 17)):
   `from .sidecar import description_stem`
3. Line 376: replace `{_SBREF_SUFFIX_RE.sub("", d).lower().strip() for d in descs}` with `{description_stem(d) for d in descs}`.
Note: `import re` remains in labels.py (lines 36-37 still use _RE_SPLIT and _RE_ALPHANUM).
      </spec>
      <dependencies>C1</dependencies>
      <risk>low — 1:1 behavioral substitution on a guard-bearing path (LabelCollisionError injectivity check), verified byte-identical transformation</risk>
      <rollback>Restore _SBREF_SUFFIX_RE and inline stem normalization; remove sidecar import.</rollback>
    </change>

    <change id="C4" priority="P2" source_item="F3, F5">
      <file path="fmri_bids_recon/stage4_assemble.py" action="modify" />
      <description>Route _nifti_filestem through sidecar.nifti_stem (F5) and remove dead RegistryDelta import + stale noqa (F3).</description>
      <spec>
1. Line 19: add `nifti_stem` to sidecar import:
   `from .sidecar import Series, _parse_acquisition_datetime, nifti_stem`
2. Line 21: remove `# noqa: F401` (all three symbols Mapping, FieldmapPair, PE_DIRECTION_TO_LABEL are used in the module body):
   `from .stage3_map import Mapping, FieldmapPair, PE_DIRECTION_TO_LABEL`
3. Remove line 24 entirely: `from .labels import RegistryDelta  # noqa: F401` (dead import, no consumer).
4. Remove the _nifti_filestem function (lines 65-72).
5. Line 339: replace `_nifti_filestem(series.nifti_path)` with `nifti_stem(series.nifti_path)`.
      </spec>
      <dependencies>C1</dependencies>
      <risk>low — 1:1 substitution at one call site; dead import removal with no consumer</risk>
      <rollback>Restore _nifti_filestem function and RegistryDelta import; revert sidecar import.</rollback>
    </change>

    <change id="C5" priority="P2" source_item="F3, F5">
      <file path="fmri_bids_recon/stage5_render.py" action="modify" />
      <description>Route _sidecar_path through sidecar.nifti_stem (F5) and remove dead PE_DIRECTION_TO_LABEL import + stale noqa (F3).</description>
      <spec>
1. Line 14: remove PE_DIRECTION_TO_LABEL (dead, not referenced in the module body) and the noqa marker:
   `from .stage3_map import Mapping, FieldmapPair`
2. Add import after line 14:
   `from .sidecar import nifti_stem`
3. Replace the _sidecar_path function (lines 79-101) with:
   ```python
   def _sidecar_path(nii_path: Path) -> Path:
       """Return the sidecar JSON path corresponding to a NIfTI file path."""
       return nii_path.parent / f"{nifti_stem(nii_path)}.json"
   ```
   Call sites at lines 159 and 172 remain unchanged (they call _sidecar_path, which now delegates to nifti_stem internally).
      </spec>
      <dependencies>C1</dependencies>
      <risk>low — 1:1 behavioral substitution; _sidecar_path's public interface is unchanged, only its implementation is simplified</risk>
      <rollback>Restore the original _sidecar_path body and PE_DIRECTION_TO_LABEL import.</rollback>
    </change>

    <change id="C6" priority="P2" source_item="F3">
      <file path="fmri_bids_recon/report.py" action="modify" />
      <description>Remove two dead imports from report.py (F3): json (unused after prior refactor) and FieldmapPair (no reference in module body).</description>
      <spec>
1. Remove line 10: `import json` (dead, no call site in report.py).
2. Line 16: remove FieldmapPair from the stage3_map import:
   `from .stage3_map import Mapping`
      </spec>
      <dependencies>none</dependencies>
      <risk>low — pure dead-import removal with no consumer</risk>
      <rollback>Restore both imports.</rollback>
    </change>

    <change id="C7" priority="P2" source_item="F3, F7">
      <file path="fmri_bids_recon/stage3_map.py" action="modify" />
      <description>Remove dead modality_token import + stale field noqa (F3) and extract _select_pair helper (F7) to eliminate the duplicated selection kernel + tie guard in map_fieldmaps().</description>
      <spec>
1. Line 10: remove the noqa comment (field IS used by the Mapping dataclass):
   `from dataclasses import dataclass, field`
2. Line 12: remove modality_token (dead, no consumer re-imports from stage3_map):
   `from .sidecar import Series`
3. Add a module-level helper before map_fieldmaps() (approximately line 460):
   ```python
   def _select_pair(
       s: Series,
       pairs: list[FieldmapPair],
       eligible: list[int],
       kind: str,
   ) -> int:
       """Select the nearest-in-time eligible pair, raising on a tie."""
       if len(eligible) == 1:
           return eligible[0]

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
               f"{kind} {s.series_number} (description={s.description!r}) has "
               f"a time-distance tie between eligible fieldmap pairs "
               f"{sorted_eligible[0]} and {sorted_eligible[1]}; "
               f"association is ambiguous.",
               context={
                   "series_number": s.series_number,
                   "description": s.description,
                   "tied_pair_indices": [sorted_eligible[0], sorted_eligible[1]],
               },
           )
       return sorted_eligible[0]
   ```
4. Target pass (lines 494-521): replace the entire `if len(eligible) == 1` / `else` block with:
   `chosen = _select_pair(s, pairs, eligible, "Series")`
5. Passenger pass (lines 574-604): replace the entire `if len(eligible) == 1` / `else` block with:
   `chosen = _select_pair(s, pairs, eligible, "SBRef series")`
Note: d0 == d1 exact-float-equality semantics are preserved unchanged (per user's explicit approval).
      </spec>
      <dependencies>none</dependencies>
      <risk>medium — the tie guard (association_unambiguous) is now defined once; any misalignment in the extraction breaks fieldmap association correctness. The extraction is a mechanical refactor with identical semantics.</risk>
      <rollback>Inline the helper back into both call sites; restore imports.</rollback>
    </change>

    <change id="C8" priority="P1" source_item="F1, F8">
      <file path="fmri_bids_recon/versions.py" action="delete" />
      <file path="fmri_bids_recon/errors.py" action="modify" />
      <file path="tests/test_versions.py" action="delete" />
      <file path="tests/test_guard_coverage.py" action="modify" />
      <description>Remove the dead versions.py module, its companion test_versions.py (7 tests), and the deprecated VersionFloorError + ReviewFlag from errors.py (F1+F8). Repoint the dcm2niix_version_floor guard in test_guard_coverage.py to tool_registry/ToolVersionError.</description>
      <spec>
1. DELETE fmri_bids_recon/versions.py (83 lines). Superseded by tool_registry.py; tools.lock.yaml is the single source of truth for the dcm2niix floor.
2. DELETE tests/test_versions.py (92 lines, 7 test functions). Sole consumer of versions.py.
3. errors.py — remove VersionFloorError class (lines 51-57) and ReviewFlag class (lines 121-128).
4. errors.py — update the module docstring header (lines 1-22). Remove the `VersionFloorError  (deprecated, retained for test compat)` line (line 5) and the `ReviewFlag  (deprecated, replaced by warnings.graded_warning)` line (line 20). Resulting hierarchy:
   ```
   BidsReconError
       GuardError  (BLOCKING)
           AnatSuffixError
           PhaseEncodingError
           FieldmapCoverageError
           LabelCollisionError
           EmptyLabelError
           LabelDriftError
           TaskRenameError
           PhysioAssociationError
           ConversionError
           PhysioParseError
           NavigatorDropError
       ConfigError
       ToolUnavailableError
       ToolVersionError
   SpecFinding  (dataclass, not an exception)
   ```
5. test_guard_coverage.py — update imports (lines 27-37): remove `VersionFloorError` from the fmri_bids_recon.errors import block and add `ToolVersionError`.
6. test_guard_coverage.py — repoint the dcm2niix_version_floor entry (lines 69-71):
   FROM:
   ```python
   "dcm2niix_version_floor": Guard(
       "versions", VersionFloorError,
       "test_versions", "test_version_below_the_floor_raises_version_floor_error"),
   ```
   TO:
   ```python
   "dcm2niix_version_floor": Guard(
       "tool_registry", ToolVersionError,
       "test_tool_registry", "test_a_below_floor_version_raises_tool_version_error"),
   ```
   Verification: tool_registry.py line 237 contains `raise ToolVersionError(`, and test_tool_registry.py line 324 defines the proof test.
      </spec>
      <dependencies>none</dependencies>
      <risk>low — dead code removal; guard roster repoint verified: the engine source contains `raise ToolVersionError(` and the proof test exists at the named location</risk>
      <rollback>Restore versions.py, test_versions.py, VersionFloorError, ReviewFlag; revert guard coverage entry.</rollback>
    </change>

    <change id="C9" priority="P2" source_item="F2">
      <file path="fmri_bids_recon/deface.py" action="modify" />
      <file path="fmri_bids_recon/tool_registry.py" action="modify" />
      <file path="tests/test_deface.py" action="modify" />
      <description>Remove dead assert_deface_tools() and _resolve_flirt() from deface.py (F2). Fold the FSLDIR-specific hint into tool_registry's flirt not-found error. Remove the 10 companion tests (note: clean report stated 8, actual count is 10: 6 for assert_deface_tools, 4 for _resolve_flirt).</description>
      <spec>
1. deface.py — remove `import shutil` (line 13). After removing _resolve_flirt and assert_deface_tools, no shutil usage remains.
2. deface.py — remove the _resolve_flirt function (lines 22-32) and its blank-line separator.
3. deface.py — remove the assert_deface_tools function (lines 35-59) and its blank-line separator.
4. tool_registry.py — in the binary_path-is-None branch (lines 182-190), enhance the error message for flirt to include the FSLDIR hint:
   Replace lines 183-190 with:
   ```python
           msg = f"{spec['binary']} not found on PATH"
           if name == "flirt":
               msg += (
                   ". Set the FSLDIR environment variable"
                   " (e.g. via 'module load FSL')"
                   " or add FSL's bin directory to PATH."
               )
           report.tools[name] = ToolStatus(
               name=name,
               pinned_version=spec["version"],
               found_version=None,
               pin_class=spec["pin_class"],
               status="error",
               message=msg,
           )
   ```
5. test_deface.py — update the module-level import (line 26):
   `from fmri_bids_recon.deface import deface`
   (Remove `assert_deface_tools` from the import.)
6. test_deface.py — remove the entire assert_deface_tools test section (lines 249-338, 6 test functions) and the _resolve_flirt test section (lines 341-398, 4 test functions). Retain the _build_fsl_env section (starting at line 401) and all deface() tests above line 249.
      </spec>
      <dependencies>none</dependencies>
      <risk>low — dead function removal; the pre-flight job is already performed by tool_registry.preflight_tool_environments(). FSLDIR-specific hint is preserved at the live gate.</risk>
      <rollback>Restore the two functions, shutil import, test functions, and revert tool_registry message.</rollback>
    </change>

    <change id="C10" priority="P2" source_item="F9">
      <file path="fmri_bids_recon/pipeline.py" action="modify" />
      <description>Remove the dead + latently incorrect hasattr(registry_delta, 'new_entries') duck-typing in pipeline.py (F9). Make the RegistryDelta contract explicit.</description>
      <spec>
1. Line 22: add RegistryDelta to the labels import:
   `from .labels import resolve_labels, RegistryDelta`
2. Lines 217-220: replace the hasattr branch with the unconditional path:
   FROM:
   ```python
   if hasattr(registry_delta, 'new_entries'):
       merged_registry.update(registry_delta.new_entries)
   else:
       merged_registry.update(registry_delta)
   ```
   TO:
   ```python
   merged_registry.update(registry_delta.new_entries)
   ```
3. Line 259: replace the dict default with a RegistryDelta default:
   FROM: `registry_delta = intermediate.get('registry_delta', {})`
   TO: `registry_delta = intermediate.get('registry_delta') or RegistryDelta()`
4. Lines 281-284: replace the hasattr branch with the unconditional path:
   FROM:
   ```python
   if hasattr(registry_delta, 'new_entries'):
       new_tasks = {desc: e.label for desc, e in registry_delta.new_entries.items()}
   else:
       new_tasks = {}
   ```
   TO:
   ```python
   new_tasks = {desc: e.label for desc, e in registry_delta.new_entries.items()}
   ```
      </spec>
      <dependencies>none</dependencies>
      <risk>low — all live paths already return RegistryDelta; the removed else branches are dead and latently incorrect (would corrupt the registry if reached)</risk>
      <rollback>Restore hasattr guards and the dict default; remove RegistryDelta import.</rollback>
    </change>
  </changes>
  <execution_order>C1, then C2 through C10 in parallel (no file overlap between C2-C10)</execution_order>
</implement_plan>
