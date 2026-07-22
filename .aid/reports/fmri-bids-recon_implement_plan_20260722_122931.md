<implement_plan>
  <meta project="fmri-bids-recon" mode="implement" submodule="plan" timestamp="2026-07-22T12:29:31Z" />
  <input_reports>
    <report path="fmri-bids-recon_test_20260722_120500.md" mode="test" key_items="2" />
  </input_reports>
  <changes>
    <change id="C1" priority="P2" source_item="test action item 1">
      <file path="fmri_bids_recon/stage4_assemble.py" action="modify" />
      <description>The assemble() function's docstring at line 140 still reads "writes scrubbed JSON sidecars". The module-level docstring was correctly updated during the prior implement build, but this function-level docstring was missed. Change "writes scrubbed JSON sidecars" to "writes JSON sidecars".</description>
      <spec>In fmri_bids_recon/stage4_assemble.py, line 140, replace the exact string "writes scrubbed JSON sidecars" with "writes JSON sidecars". No other changes to this file.</spec>
      <dependencies>none</dependencies>
      <risk>low - single word removal in a docstring, no behavioral change</risk>
      <rollback>Restore the word "scrubbed" to the docstring at line 140.</rollback>
    </change>
</changes>
  <execution_order>C1</execution_order>
</implement_plan>
