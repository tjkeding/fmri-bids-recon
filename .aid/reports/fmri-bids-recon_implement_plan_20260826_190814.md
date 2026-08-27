<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-08-26T19:08:14Z" />
  <input_reports>
    <report path="bids-recon_test_20260826_190136.md" mode="test" key_items="3" />
  </input_reports>
  <changes>
    <change id="C1" priority="P0" source_item="action_items[0]: stage4_assemble.py fieldmap wiring-defect guard">
      <file path="fmri_bids_recon/stage4_assemble.py" action="modify" />
      <description>Restore GuardError for fieldmap series absent from both the paired-unit lookup AND the unpaired-fieldmap list. The current code `continue`s past any FMAP_FUNC/FMAP_DWI series not in fmap_unit_lookup without distinguishing (a) legitimate CR F3/F7 degradation (series is in unpaired_fmaps) from (b) a wiring defect (series never entered group_fieldmaps() at all). Case (b) silently drops the series with no BIDS file, no sourcedata copy, and no error.</description>
      <spec>
1. After the fmap_unit_lookup construction (line 196) and before the _write_gre_output helper (line 197), add:
   unpaired_sns: set[int] = {s.series_number for s in unpaired_fmaps}

2. Replace lines 391-394 (the `if snum not in fmap_unit_lookup:` block inside `elif role in (Role.FMAP_FUNC, Role.FMAP_DWI):`) from:
   if snum not in fmap_unit_lookup:
       # Unpaired ...
       continue
   to:
   if snum not in fmap_unit_lookup:
       if snum in unpaired_sns:
           continue
       raise GuardError(
           f"Fieldmap series {snum} (role={role.name}) is absent from both "
           f"the paired-unit lookup and the unpaired-fieldmap list; this "
           f"indicates a wiring defect in the grouping stage.",
           context={
               "guard": "fieldmap_pair_complete",
               "series_number": snum,
               "role": role.name,
           },
       )
      </spec>
      <dependencies>none</dependencies>
      <risk>low - single conditional branch addition in an existing guard site; proof test already written and expected to pass after this change</risk>
      <rollback>Revert the two edits: remove the unpaired_sns set construction, restore the unconditional continue</rollback>
    </change>
    <change id="C2" priority="P1" source_item="action_items[1]: report.py dir-label formatting regression">
      <file path="fmri_bids_recon/report.py" action="modify" />
      <description>Fix the fieldmap-mapping-table row to independently dir-prefix each direction label ("dir-PA/dir-AP") instead of joining them under one shared prefix ("dir-PA/AP"). The regression was introduced during the C4 deviation when PE_DIRECTION_TO_LABEL conversion replaced direct dir_a/dir_b fields.</description>
      <spec>
Replace line 179 from:
   unit_label = f"dir-{'/'.join(anatomical_labels)}, run-{unit.run_index:02d}"
to:
   unit_label = f"{'/'.join(f'dir-{l}' for l in anatomical_labels)}, run-{unit.run_index:02d}"
      </spec>
      <dependencies>none</dependencies>
      <risk>low - single string formatting fix; proof test already written and expected to pass after this change</risk>
      <rollback>Revert the one-line format string change</rollback>
    </change>
    <change id="C3" priority="P1" source_item="action_items[2]: stage3_map.py timestamp-tie detection in group_fieldmaps()">
      <file path="fmri_bids_recon/stage3_map.py" action="modify" />
      <description>Add timestamp-tie detection within each modality sub-group in group_fieldmaps(). Two fieldmap members with identical AcquisitionDateTime have no principled consecutive-pairing order (which becomes member 0 vs. member 1 is arbitrary), making the pairing non-deterministic. This restores fieldmap_pairing_unambiguous as an independently triggerable guard, per explicit user adjudication during /test design.</description>
      <spec>
Insert after the odd-count check (after line 404: `members = members[:-1]`) and before the pairing loop (line 406: `for i in range(0, len(members), 2):`), add a consecutive-timestamp-tie check:

            for k in range(len(members) - 1):
                if members[k].acquisition_datetime == members[k + 1].acquisition_datetime:
                    raise PhaseEncodingError(
                        f"Fieldmap series {members[k].series_number} and "
                        f"{members[k + 1].series_number} share identical "
                        f"AcquisitionDateTime "
                        f"({members[k].acquisition_datetime}); "
                        f"consecutive-pairing order is arbitrary.",
                        context={
                            "modality": modality,
                            "series_a": members[k].series_number,
                            "series_b": members[k + 1].series_number,
                            "acquisition_datetime": str(
                                members[k].acquisition_datetime
                            ),
                        },
                    )

The loop variable is `k` (not `i`) to avoid shadowing the outer pairing loop variable.

Guard-log interaction: the existing `guard_log["fieldmap_pairing_unambiguous"] = True` at line 466 is reached only when no PhaseEncodingError was raised in the preceding code, which is correct. The new raise site fires before the pairing loop, so the guard_log entry is never set when the guard fires, consistent with the other two PE guards (opposite_pe_within_pair, dir_label_pe_agreement).
      </spec>
      <dependencies>none</dependencies>
      <risk>low - new raise site in an existing guard's logical scope; proof test already written and expected to pass after this change</risk>
      <rollback>Remove the inserted timestamp-tie check block</rollback>
    </change>
  </changes>
  <execution_order>C1, C2, C3</execution_order>
</implement_plan>
