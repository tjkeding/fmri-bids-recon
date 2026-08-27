<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-07-31T16:30:00-04:00" />
  <input_reports>
    <report path="bids-recon_run-local_20260731_161500.md" mode="run-local" key_items="1" />
  </input_reports>
  <changes>
    <change id="C1" priority="P2" source_item="run-local action item P2">
      <file path="sandbox/verify_dataset.py" action="modify" />
      <description>Fix sort key on line 271 to handle non-numeric check IDs. The current lambda `int(r[0][1:])` assumes all IDs are "A" followed by a number; the "INT" check ID (added in the prior implement build for intensity floor verification) crashes with ValueError. Replace with a key that sorts "A<n>" entries numerically first, then any other IDs lexicographically after.</description>
      <spec>Line 271: replace `key=lambda r: int(r[0][1:])` with `key=lambda r: (0, int(r[0][1:])) if r[0].startswith("A") else (1, r[0])`. This sorts all adversary checks (A1..A31) in numeric order, followed by any non-adversary checks (INT, etc.) in alphabetical order.</spec>
      <dependencies>none</dependencies>
      <risk>low - single expression change in a reporting-only code path; no effect on check logic</risk>
      <rollback>Revert the lambda to the original form</rollback>
    </change>
  </changes>
  <execution_order>C1</execution_order>
</implement_plan>
