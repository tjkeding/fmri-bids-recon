<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-09-15T13:00:00Z" />
  <input_reports>
    <report path="bids-recon_brainstorm_20260915_120000.md" mode="brainstorm" key_items="3" />
  </input_reports>
  <changes>
    <change id="C1" priority="P0" source_item="T5: exact_volume_counts guard crash on 2-run tie">
      <file path="fmri_bids_recon/runs.py" action="modify" />
      <description>Add a 2-run tied-mode branch to check_volume_counts that accepts the longer run and excludes the shorter, instead of raising GuardError. Preserves GuardError for n_runs > 2 ties.</description>
      <spec>
In check_volume_counts (runs.py), replace the unconditional GuardError at lines 122-133 with a conditional:

Current code (lines 121-133):
```python
            if len(top) > 1 and top[0][1] == top[1][1]:
                raise GuardError(
                    f"Task {task_label!r}: no unique modal volume count among "
                    f"{sorted(set(counts))} ({n_runs} runs). Cannot determine "
                    f"expected volume count; manual review required.",
                    context={
                        "guard": "exact_volume_counts",
                        "task_label": task_label,
                        "counts": sorted(set(counts)),
                        "n_runs": n_runs,
                    },
                )
            else:
                mode_count: int = top[0][0]
```

Replacement:
```python
            if len(top) > 1 and top[0][1] == top[1][1]:
                if n_runs == 2:
                    mode_count = max(counts)
                    review_flags.append(
                        graded_warning(
                            _logger, SEVERITY_HIGH, "ABORTED_RUN_DETECTED",
                            f"Task {task_label!r}: 2 runs with different volume "
                            f"counts {sorted(set(counts))}. Accepted the "
                            f"{mode_count}-volume run and excluded the other as "
                            f"a probable aborted acquisition. Manual review "
                            f"recommended.",
                            user_facing=True,
                        )
                    )
                else:
                    raise GuardError(
                        f"Task {task_label!r}: no unique modal volume count among "
                        f"{sorted(set(counts))} ({n_runs} runs). Cannot determine "
                        f"expected volume count; manual review required.",
                        context={
                            "guard": "exact_volume_counts",
                            "task_label": task_label,
                            "counts": sorted(set(counts)),
                            "n_runs": n_runs,
                        },
                    )
            else:
                mode_count: int = top[0][0]
```

No new imports required: SEVERITY_HIGH and graded_warning are already imported (line 17), and review_flags is already in scope (line 81).

The downstream loop (lines 137-164) uses mode_count for accept/exclude decisions; no changes needed there since mode_count is now defined in both the n_runs==2 branch and the else branch.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - narrow scope (single branch addition), no new imports, no signature changes</risk>
      <rollback>Revert the conditional to the original unconditional GuardError</rollback>
    </change>
    <change id="C2" priority="P1" source_item="T2: DistortionMap SBRef disposition">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>Add _has_nonzero_bval guard to DWI_SBREF look-ahead in Rule 5 and Rule 9. When the next series is DIFFUSION/SE_EPI with .bval but all b-values are zero, route the SBRef to UNCLASSIFIED instead of DWI_SBREF (Rule 5/9) or FMAP_FUNC (Rule 5 default).</description>
      <spec>
Two edit sites within classify() in stage2_classify.py:

**Edit 1: Rule 5 DWI_SBREF branch (lines 356-362)**

Current code:
```python
        if (
            description_stem(s.description)
            == description_stem(_r5_nxt.description)
            and canonical_modality(_r5_nxt) in ("DIFFUSION", "SE_EPI")
            and _bval_exists(_r5_nxt)
        ):
            roles[s.series_number] = Role.DWI_SBREF
            continue
```

Replacement:
```python
        if (
            description_stem(s.description)
            == description_stem(_r5_nxt.description)
            and canonical_modality(_r5_nxt) in ("DIFFUSION", "SE_EPI")
            and _bval_exists(_r5_nxt)
        ):
            if _has_nonzero_bval(_r5_nxt):
                roles[s.series_number] = Role.DWI_SBREF
                continue
            else:
                roles[s.series_number] = Role.UNCLASSIFIED
                continue
```

**Edit 2: Rule 9 DWI_SBREF branch (lines 405-407)**

Current code:
```python
            if nxt_tok in ("DIFFUSION", "SE_EPI") and _bval_exists(nxt):
                roles[s.series_number] = Role.DWI_SBREF
                continue
```

Replacement:
```python
            if nxt_tok in ("DIFFUSION", "SE_EPI") and _bval_exists(nxt):
                if _has_nonzero_bval(nxt):
                    roles[s.series_number] = Role.DWI_SBREF
                    continue
                else:
                    roles[s.series_number] = Role.UNCLASSIFIED
                    continue
```

No new imports: _has_nonzero_bval is already defined in the same module (lines 176-186). UNCLASSIFIED is already a member of the Role enum (line 41).
      </spec>
      <dependencies>none</dependencies>
      <risk>low - uses existing helper, no new imports, no signature changes. Both edits follow identical pattern.</risk>
      <rollback>Remove the inner if/else and restore direct DWI_SBREF assignment</rollback>
    </change>
    <change id="C3" priority="P1" source_item="T1: DWI run-index assignment and SBRef pairing">
      <file path="fmri_bids_recon/stage4_assemble.py" action="modify" />
      <description>Replace global DWI run-index assignment with per-dir-entity grouping and DWI_SBREF-to-parent-DWI temporal pairing, mirroring the BOLD SBRef pairing pattern at lines 294-313.</description>
      <spec>
Replace lines 254-258 in the assemble() function:

Current code:
```python
    dwi_snums = sorted(
        [sn for sn, r in roles.items() if r in (Role.DWI, Role.DWI_SBREF)],
        key=_acq_sort_key,
    )
    dwi_run_index: dict[int, int] = {sn: i + 1 for i, sn in enumerate(dwi_snums)}
```

Replacement:
```python
    dwi_by_dir: dict[str, list[int]] = {}
    for sn, r in roles.items():
        if r == Role.DWI:
            dir_label = PE_DIRECTION_TO_LABEL.get(
                series_map[sn].phase_encoding_direction or "")
            if dir_label is not None:
                dwi_by_dir.setdefault(dir_label, []).append(sn)

    dwi_run_index: dict[int, int] = {}
    for dir_label, snums in dwi_by_dir.items():
        ordered = sorted(snums, key=_acq_sort_key)
        for idx, sn in enumerate(ordered, start=1):
            dwi_run_index[sn] = idx

    for sn, r in roles.items():
        if r == Role.DWI_SBREF:
            sbref_s = series_map[sn]
            dir_label = PE_DIRECTION_TO_LABEL.get(
                sbref_s.phase_encoding_direction or "")
            if dir_label is None:
                dwi_run_index[sn] = 1
                continue
            sbref_key = _acq_sort_key(sn)
            dwi_snums_same_dir = sorted(
                dwi_by_dir.get(dir_label, []),
                key=_acq_sort_key,
            )
            parent_dwi_snum = next(
                (dsn for dsn in dwi_snums_same_dir
                 if _acq_sort_key(dsn) > sbref_key),
                dwi_snums_same_dir[0] if dwi_snums_same_dir else None,
            )
            dwi_run_index[sn] = (
                dwi_run_index[parent_dwi_snum]
                if parent_dwi_snum is not None else 1
            )
```

No new imports needed. PE_DIRECTION_TO_LABEL is already imported (line 21). _acq_sort_key is defined in the same function scope (lines 235-241). series_map is a function parameter.

The DWI assembly block (lines 315-335) uses dwi_run_index[snum] and the DWI_SBREF assembly block (lines 337-356) uses dwi_run_index.get(snum, 1); both continue to work correctly with the new per-dir-entity indices.
      </spec>
      <dependencies>C2 (logical: C2 ensures only genuine DWI SBRefs reach this code; no code-level dependency)</dependencies>
      <risk>low - mirrors validated BOLD SBRef pairing pattern, no new imports, no signature changes</risk>
      <rollback>Revert to the original 5-line global indexing block</rollback>
    </change>
    <change id="C4" priority="P1" source_item="Participant/session context in all log and error messages">
      <file path="fmri_bids_recon/pipeline.py" action="modify" />
      <file path="fmri_bids_recon/__main__.py" action="modify" />
      <description>Inject participant/session context into all log messages emitted within the per-participant processing loop, using contextvars.ContextVar and a custom logging.Formatter subclass. Messages from downstream modules (runs.py, stage2_classify.py, warnings.py, labels.py, etc.) gain [sub-X ses-Y] context transparently. Outside the participant loop, the context fields are absent and the log format omits them gracefully.</description>
      <spec>
**Edit 1: pipeline.py (ContextVar definition + set/clear)**

Add two module-level ContextVar declarations after the existing imports (after line 14, the last import block):

```python
from contextvars import ContextVar

_current_sub: ContextVar[str] = ContextVar("_current_sub", default="")
_current_ses: ContextVar[str] = ContextVar("_current_ses", default="")
```

In the Phase 1 per-participant loop (line 155: `for p in config.participants:`), immediately after `sub, ses = p.sub, p.ses` (line 156), set the context vars:

```python
        _sub_token = _current_sub.set(sub)
        _ses_token = _current_ses.set(ses)
```

At the end of the loop body (after line 257: `logger.info('convert complete: ...')`), reset them:

```python
        _current_sub.reset(_sub_token)
        _current_ses.reset(_ses_token)
```

Apply the same pattern to the Phase 3 per-participant loop (line 263: `for p in config.participants:`). After `sub, ses = p.sub, p.ses` in that loop, set the context vars; at the end of the loop body, reset them.

Export the ContextVars for use by __main__.py:

No `__all__` export needed; __main__.py imports them directly as `from .pipeline import _current_sub, _current_ses`.

**Edit 2: __main__.py (custom Formatter + format string)**

Replace the `_setup_logging` function (lines 28-49) with:

```python
from .pipeline import _current_sub, _current_ses


class _ParticipantFormatter(logging.Formatter):
    """Injects [sub-X ses-Y] when participant context is active."""

    def format(self, record: logging.LogRecord) -> str:
        sub = _current_sub.get("")
        ses = _current_ses.get("")
        if sub and ses:
            record.participant_ctx = f" [sub-{sub} ses-{ses}]"
        else:
            record.participant_ctx = ""
        return super().format(record)


def _setup_logging(log_file: Path | None = None) -> None:
    root = logging.getLogger()
    if root.handlers:
        return

    formatter = _ParticipantFormatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s%(participant_ctx)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    root.addHandler(console)

    if log_file is not None:
        file_handler = logging.FileHandler(str(log_file))
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    root.setLevel(logging.DEBUG)
```

The import `from .pipeline import _current_sub, _current_ses` is placed at module level, after the existing `from .pipeline import run` (line 21).

The format string changes from:
`"%(asctime)s [%(levelname)s] %(name)s: %(message)s"`
to:
`"%(asctime)s [%(levelname)s] %(name)s%(participant_ctx)s: %(message)s"`

The `%(participant_ctx)s` field is always set by _ParticipantFormatter.format(): either ` [sub-X ses-Y]` (with leading space) when inside a participant loop, or `""` (empty string) when outside. This means the format degrades gracefully: messages emitted before/after participant processing (tool registry checks, final summary) have no participant tag.

**Output examples:**

Inside participant loop:
```
2026-09-14T18:08:33 [ERROR] fmri_bids_recon.__main__ [sub-XXXX ses-01]: Pipeline invariant violated: Task '<task>': ...
2026-09-14T18:08:33 [INFO] fmri_bids_recon.stage2_classify [sub-XXXX ses-01]: [medium:DUPLICATE_MODALITY] 2 series classified as t1w ...
```

Outside participant loop (unchanged):
```
2026-09-14T18:03:32 [INFO] fmri_bids_recon.tool_registry: Tool python: ok (Python 3.12.13 meets floor 3.12.13)
```

No new third-party dependencies. `contextvars` is stdlib (Python 3.7+). The pipeline is documented as non-reentrant (single-threaded sequential), so the module-level ContextVar approach is safe.
      </spec>
      <dependencies>none (orthogonal to C1-C3; can be implemented in any order)</dependencies>
      <risk>low - stdlib only, no signature changes, no behavioral change to pipeline logic. Formatter subclass is a minimal override of format(). ContextVar reset via token ensures correct cleanup even if an exception is raised (the reset is best-effort; in practice, exceptions propagate to __main__.py's error handler which terminates the process).</risk>
      <rollback>Remove ContextVar declarations from pipeline.py, remove _ParticipantFormatter class from __main__.py, restore original format string</rollback>
    </change>
  </changes>
  <execution_order>C1, C2, C3, C4</execution_order>
</implement_plan>
