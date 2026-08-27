<implement_report>
  <meta project="bids-recon" mode="implement" submodule="build" timestamp="2026-07-16T16:35:00-05:00" />
  <spec_ref>bids-recon_implement_plan_20260716_150000.md</spec_ref>

  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/__init__.py" lines_changed="0" />
        <file path="tools/simulated_bids/config.py" lines_changed="105" />
        <file path="tools/simulated_bids/noise.py" lines_changed="57" />
      </files_modified>
      <notes>All three files created as specified. Empty package marker, SCANNER/acquisition params/demographics constants in config.py, structured_noise_3d and structured_noise_4d in noise.py.</notes>
    </change>

    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/modalities.py" lines_changed="195" />
      </files_modified>
      <notes>generate_t2w implemented following generate_t1w pattern with T2W_PARAMS, as specified for the ellipsis stub. All 11 functions present.</notes>
    </change>

    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/adversaries.py" lines_changed="410" />
      </files_modified>
      <notes>All 28 apply_A{n} functions implemented. ADVERSARY_MATRIX verbatim. A11 confirmed to use PatientSex (deny-listed), not InstitutionName. apply_adversaries dispatcher present.</notes>
    </change>

    <change id="C4" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/scaffold.py" lines_changed="56" />
        <file path="tools/simulated_bids/__main__.py" lines_changed="83" />
      </files_modified>
      <notes>Four scaffold functions and four-phase generation flow in __main__.py. CLI accepts output_dir positional arg and --seed option.</notes>
    </change>

    <change id="C5" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/manifest.py" lines_changed="78" />
      </files_modified>
      <notes>ADVERSARY_DESCRIPTIONS with all 28 entries. write_manifest generates README.md with modality inventory table, adversary matrix table, per-subject detail section, and generation instructions.</notes>
    </change>
  </changes_applied>

  <post_build_verification>
    - All 8 files pass AST syntax check (Python 3.12.13 via bids-recon conda env)
    - All modules import cleanly from tools.simulated_bids
    - ADVERSARY_MATRIX covers all 28 adversary types (A1-A28) across 9 subjects
    - A11 details confirmed: {"field": "PatientSex", "value": "F"}
    - InstitutionName in SCANNER: "Simulated Brain Institute" (fabricated, non-traceable)
    - N_SUBJECTS=10, SESSIONS=["ses-01","ses-02","ses-03"], DEMOGRAPHICS=10 entries
  </post_build_verification>

  <summary>
    <total_changes>5</total_changes>
    <completed>5</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>

  <next_steps>
    Run the generator: conda run -n bids-recon python -m tools.simulated_bids ~/simulated-bids-dataset/
    Then recommend /test to validate the generated package.
  </next_steps>
</implement_report>
