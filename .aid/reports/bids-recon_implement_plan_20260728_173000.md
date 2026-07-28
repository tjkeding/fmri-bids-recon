<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-07-28T17:30:00-04:00" />
  <input_reports>
    <report path="bids-recon_test_20260728_170800.md" mode="test" key_items="1" />
  </input_reports>
  <changes>
    <change id="C1" priority="P0" source_item="test_report/action_items/item[@priority='P0']">
      <file path="fmri_bids_recon/physio.py" action="modify" />
      <description>Fix _load_native_channel()'s label-parsing regex to support compound (underscored) channel labels. The current regex `_recording-([^_]+)_physio\.json$` uses a character class that excludes underscores, so it cannot match dcm2niix's real `external_trigger` channel label. This halts the entire pipeline on any physio-enabled run against ABCD/XA30 data (PhysioParseError is a GuardError subclass, re-raised at the top level with exit code 1).</description>
      <spec>
        File: fmri_bids_recon/physio.py
        Line: 81

        Current:
            m = re.search(r"_recording-([^_]+)_physio\.json$", name)

        Replace with:
            m = re.search(r"_recording-(.+)_physio\.json$", name)

        Rationale: greedy `.+` is unambiguous here because `_physio.json` is a fixed literal suffix that appears exactly once at the end of every dcm2niix native physio sidecar filename. The regex engine's greedy-then-backtrack behavior guarantees the capture group consumes everything between `_recording-` and the final `_physio.json`, correctly handling both single-token labels (cardiac, respiratory) and compound labels (external_trigger).

        No other lines in physio.py change. No other files change.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - single character-class substitution on one line; 12 existing tests (11 in test_physio.py, 1 in test_cli_integration.py) are already pinned to the correct post-fix behavior and will pass once this lands with no test changes needed</risk>
      <rollback>Revert line 81 to `r"_recording-([^_]+)_physio\.json$"`</rollback>
    </change>
  </changes>
  <execution_order>C1</execution_order>
</implement_plan>
