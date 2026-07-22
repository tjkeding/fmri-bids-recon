<implement_report>
  <meta project="fmri-bids-recon" mode="implement" submodule="build" timestamp="2026-07-17T13:00:57-04:00" />
  <spec_ref>fmri-bids-recon_implement_plan_20260717_124134.md</spec_ref>

  <pre_build>
    <plan_discipline_gate result="pass">
      Scanned the spec for decision-gate indicators. No user-decision gates. The "either"/"may choose"
      hits are bounded build-agent latitude with stated defaults (the missing-datetime exception type
      defaults to reusing ConversionError) or scope-discipline instructions, not unresolved decisions.
    </plan_discipline_gate>
    <environment_preflight result="pass">
      nibabel 5.4.2, numpy 2.5.1 in the fmri-bids-recon env; no new packages required. dcm2niix
      v1.0.20260416 present (used to clear the geometry verification gate during the plan phase).
    </environment_preflight>
    <backup>
      sandbox/backups/pre_implement_20260717_124134/ (five files), taken before the first edit.
      SHA-256 of originals:
        __main__.py         2e4110c851e89a9fe3ec08382806c6d4d499580e172748262dbaf663e83eaffb
        config.py           25e77fe4d96d1938b80da46f3c1548feb64fa890e69a3bf4300db4f997cc2828
        sidecar.py          e63f3bad993fe6f0a006204113282ca8f2894bb587cb33547b727b77565fd1c5
        stage3_map.py       03ff22484f1fa9581425c955d7d79e512746b37cbd9082b7dc85e3bf2cac99e8
        stage6_validate.py  007983336e0799a9162f5f7b896bb0da6cd3bc27a33708272b8f026da697157d
    </backup>
  </pre_build>

  <changes_applied>

    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/sidecar.py" lines_changed="33" />
      </files_modified>
      <notes>
        Added affine, image_position, voxel_sizes (all defaulted, appended after software_versions to
        preserve positional constructor calls) and a pe_axis property to the frozen Series dataclass;
        load_series now populates the three geometry fields from the NIfTI affine and header zooms.
        Verified: a loaded Series carries the 4x4 affine, image_position equal to the affine
        translation, voxel_sizes, and pe_axis polarity-stripped ('j-' -> 'j').
      </notes>
    </change>

    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage6_validate.py" lines_changed="15" />
        <file path="fmri_bids_recon/__main__.py" lines_changed="17" />
      </files_modified>
      <notes>
        The guard registry dropped the two obsolete fieldmap guards and added the four new association
        guards (14 total). The guard log now initializes all-False and is threaded into the two
        fieldmap functions; the seven fieldmap guards self-record inside the redesigned association,
        and the seven non-fieldmap guards are recorded at their post-return call sites in the driver.
        The prior hardcoded all-True construction is removed. Verified: registry correct, all-False
        init present, both call sites thread the log, all-True gone. Note the intermediate state after
        this change but before the association redesign is intentionally non-runnable (the driver
        passes the log to functions that do not yet accept it); the next change closes it.
      </notes>
    </change>

    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage3_map.py" lines_changed="419" />
        <file path="fmri_bids_recon/config.py" lines_changed="9" />
      </files_modified>
      <notes>
        The core redesign. Replaced the acquisition-order association with geometry-primary grouping:
        a compatibility helper compares affine translation, the 3x3 rotation block, voxel sizes,
        matrix, and PE axis within jitter-sized tolerances (position 0.1 mm, orientation 1e-4, voxel
        1e-3 mm). Pairing partitions fieldmaps into geometry groups (union-find) and forms opposite-PE
        pairs, raising on an ambiguous group rather than silently dropping an odd member. Assignment
        gives each target its geometry-compatible pair (single -> direct; multiple -> nearest-in-time,
        with a time tie raising), then a hard orphan check. Every uncertainty raises a GuardError
        (halt). The Mapping and FieldmapPair interfaces are preserved, so the assembly and render
        stages are untouched. The agent leaked one line of prose before its JSON return (a protocol
        slip); the structured return was intact and the work correct.

        VERIFIED END-TO-END on the real target subject, converted with the pipeline's own dcm2niix
        flags (-ba n), with genuine acquisition timestamps and no test shims: three fieldmap pairs
        form; the two functional fieldmap pairs carry identical protocol names and are separated into
        the enback block (-> its two runs) and the rest block (-> its four runs) by GEOMETRY ALONE;
        the diffusion pair maps to the diffusion run; all seven fieldmap guards record. This is the
        association acceptance criterion met on actual data.
      </notes>
    </change>

    <change id="C4" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/__main__.py" lines_changed="1" />
      </files_modified>
      <notes>
        The fieldmap-association target set now includes the single-band reference roles alongside BOLD
        and DWI. Under geometry grouping an SBRef shares its BOLD's prescription and associates with the
        same pair; the render stage writes the association metadata onto SBRef sidecars via its existing
        uniform target loop. No SBRef-specific logic added.
      </notes>
    </change>

    <change id="C5" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/sidecar.py" lines_changed="(included in C1 count)" />
      </files_modified>
      <notes>
        A missing or unparseable AcquisitionDateTime in load_series now raises a typed, contextual
        GuardError (reusing the existing ConversionError, per the spec's default) naming the sidecar and
        raw value, instead of a bare ValueError. Verified: an empty AcquisitionDateTime raises
        ConversionError naming the sidecar.
      </notes>
    </change>

    <change id="C6" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage6_validate.py" lines_changed="(included in C3 count)" />
      </files_modified>
      <notes>
        The BIDS-validator wrapper now guards the nested issues-block access: a non-dict or
        inner-key-missing shape raises ToolUnavailableError (dataset UNCHECKED) rather than an uncaught
        KeyError/TypeError. Verified via static inspection and py_compile.
      </notes>
    </change>

  </changes_applied>

  <post_build_verification>
    - All eight package modules pass py_compile; fmri_bids_recon.__main__ imports (full pipeline wiring
      resolves the guard_log threading between the driver and the redesigned association).
    - Association acceptance criterion met end-to-end on the real target subject with the pipeline's
      own dcm2niix flags and real timestamps (see the C2 note).
    - Diff vs backup: stage3_map.py 419, sidecar.py 33, __main__.py 17, stage6_validate.py 15,
      config.py 9.
    - No tests were run (implement does not test); six test files encode the old behavior and will
      need redesign under /test.
  </post_build_verification>

  <investigation_note>
    During verification a converted subject appeared to lack AcquisitionDateTime entirely, which would
    have halted the pipeline at load_series. This was traced to the verification conversion omitting the
    -ba n flag: the dcm2niix default (-ba y) anonymizes and suppresses that key. The pipeline's own
    stage1_convert uses -ba n, which the code documents as REQUIRED for exactly this reason. Re-converting
    with -ba n restored AcquisitionDateTime, and the end-to-end verification then passed with genuine
    timestamps. Recorded so the false alarm is not mistaken for a real defect: there is no
    missing-timestamp problem in the pipeline's real conversion path.
  </investigation_note>

  <summary>
    <total_changes>6</total_changes>
    <completed>6</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>

  <next_steps>
    Recommended: /test to redesign the six affected test files (test_map.py, test_assemble.py,
    test_render.py, test_guard_coverage.py, test_report.py, tests/conftest.py) around the geometry-based
    association, the new Series geometry fields, and the real meta-guard; then run the suite. Separately,
    the deferred simulated-dataset harmonization (SBRef association in the clean generator) can now be
    actioned against fmri-bids-recon_implement_plan_20260717_101506.md, since the pipeline is built.
  </next_steps>
</implement_report>
