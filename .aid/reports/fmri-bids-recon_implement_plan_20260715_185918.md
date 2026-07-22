<implement_plan>
  <meta project="fmri-bids-recon" mode="implement" submodule="plan" timestamp="2026-07-15T22:59:18Z" />
  <input_reports>
    <report path="(none; change specified directly from deployment troubleshooting)" mode="n/a" key_items="1" />
  </input_reports>
  <changes>
    <change id="C1" priority="P0" source_item="direct user instruction">
      <file path="environment.yml" action="modify" />
      <description>The pip pin numpy==2.2.3 is unsatisfiable alongside cubids==1.1.0, which constrains numpy to &lt;=1.26.4 (via its datalad dependency chain). Conda env creation fails at the pip stage with ResolutionImpossible. Repin numpy to 1.26.4, the highest version satisfying every constraint simultaneously.</description>
      <spec>In the `pip:` block of environment.yml, replace the single line `      - numpy==2.2.3` with `      - numpy==1.26.4   # capped at cubids 1.1.0 ceiling (&lt;=1.26.4); pipeline uses only basic numpy APIs`. Preserve the six-space indentation of the list item so it remains a child of the `pip:` key. Change no other dependency line, no channel, no key. numpy 1.26.4 ships a cp312 manylinux wheel, so it installs under the pinned python=3.12. Constraint satisfaction: nibabel==5.3.2 requires numpy&gt;=1.22 (ok); pydicom==3.0.1 has no hard numpy bound (ok); cubids==1.1.0 requires numpy&lt;=1.26.4 (ok, equal); the package's only numpy usage is fmri_bids_recon/physio.py (np.array, np.zeros, np.float32), none of which is a numpy-2.x-only API (ok).</spec>
      <dependencies>none</dependencies>
      <risk>low - single pin decrement within a well-understood constraint window; no source code changes; the affected numpy APIs are stable across 1.22 through 2.x.</risk>
      <rollback>Revert the line to `      - numpy==2.2.3`. (Restores the prior unsatisfiable state; only meaningful if the numpy ceiling source, cubids, is later removed.)</rollback>
    </change>
  </changes>
  <execution_order>C1</execution_order>
</implement_plan>
