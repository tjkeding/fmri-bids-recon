<implement_report>
  <meta project="bids-recon" mode="implement" submodule="build" timestamp="2026-07-17T08:56:20-04:00" />
  <spec_ref>bids-recon_implement_plan_20260717_082844.md</spec_ref>

  <pre_build>
    <plan_discipline_gate result="pass">
      Scanned the spec for decision-gate indicators. One hit, at line 248, was the word "open"
      used as a verb ("these index or open paths directly"), not an unresolved decision. No
      conditional gates, no pending markers, no unapproved assumptions. Spec accepted.
    </plan_discipline_gate>
    <environment_preflight result="pass">
      Python 3.12.13, numpy 2.5.1, nibabel 5.4.2 in the bids-recon conda environment. These are
      the same versions the plan-phase nibabel probes were run against. No packages required
      installation; no environment mutation was requested or performed.
    </environment_preflight>
    <backup>
      Path: sandbox/backups/pre_implement_20260717_082844/
      Taken before the first edit. The project is not a git repository, so this is the only
      rollback mechanism that exists. SHA-256 of the pre-build originals:
        adversaries.py  e3d3594adbf7a9ef271142ed2ee02903989f5de7762cdc03dcc4db563dd82171
        manifest.py     6fb34eff1bcb731e6611b67d9628bb661dd54cb02df91688cd707e8872b5db0f
        modalities.py   d9e42f09a84ae6b7d384820b47fc316aab772316b4445295b58859fbff0d4435
    </backup>
  </pre_build>

  <execution_order_deviation user_decision="modify">
    The spec's execution_order contradicted its own dependencies fields: the A19 inversion and
    the A25 repoint both call the requirement helper, but were ordered ahead of the change that
    defines it. Final state is identical under either order, because Python resolves the name at
    call time and no code runs between changes; the exposure was that a halt mid-chain would
    leave the package raising NameError on those two adversaries. Surfaced to the user, who
    approved reordering the adversary-module chain so the guard helpers land before their two
    consumers. No change's content was altered. Order executed:

      int16 baseline and helper consolidation
      -> direct-construction routing
      -> duplicate-key reorder and post-condition check
      -> requirement-guard sweep
      -> dtype-mixing inversion
      -> duplicate-run repoint
      (manifest descriptions dispatched in parallel throughout; disjoint file)
  </execution_order_deviation>

  <changes_applied>

    <change id="C1" priority="P0" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/modalities.py" lines_changed="27" />
        <file path="tools/simulated_bids/adversaries.py" lines_changed="18" />
      </files_modified>
      <notes>
        Applied as specified. The int16 storage baseline with per-image scl_slope/scl_inter is
        in place, the 12-bit quantization constant was added, and set_data_dtype was correctly
        omitted per the spec directive. The two byte-identical helper copies were removed from
        the adversary module and are now imported from the modality module; no call site needed
        textual change. Verified independently against all nine acceptance criteria (see
        post_build_verification). The one residual risk flagged in the plan, that the
        sform/qform/pixdim4 calls might disturb the slope set by set_slope_inter, is disproved:
        slope and inter both survive and the raw stored range lands exactly on [0, 4095].
      </notes>
    </change>

    <change id="C5" priority="P1" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/adversaries.py" lines_changed="14" />
      </files_modified>
      <notes>
        Applied as specified. All three direct-construction sites now route through the shared
        writer. The truncation adversary's second write call for its extra run was correctly
        left untouched and its image binding remains in scope. The orientation adversary
        regained its header repetition time, per the user's explicit decision to fix both the
        dtype drift and the undeclared pixdim regression rather than the dtype alone.
      </notes>
    </change>

    <change id="C6" priority="P1" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/adversaries.py" lines_changed="31" />
      </files_modified>
      <notes>
        Applied as specified. The duplicate-key adversary now sits at the tail of its subject's
        list with the explanatory comment above it, its post-condition verifier exists, and the
        dispatcher runs the naming-convention-keyed post-condition pass after the full
        application loop. Verified the resulting order is A2, A6, A12, A19, A23, A15.
      </notes>
    </change>

    <change id="C3" priority="P0" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/adversaries.py" lines_changed="118" />
      </files_modified>
      <notes>
        Applied as specified; the broadest change in the set. The three requirement helpers were
        added, and guards were applied across 24 adversaries: named-path guards on 6,
        collection guards on 15, recursive-collection guards on 3, plus content-filter
        tracking raises on the two adversaries that filter by content rather than by path, and
        the minimum-two-sidecar requirement on the mixed-identifier adversary. The four
        already-loud adversaries were left untouched, confirmed by body-level diff against the
        backup. Independently verified: zero residual silent existence guards remain anywhere
        in the module, and all 28 adversaries are accounted for (24 guarded, 4 already loud).
        No spurious hard failure was introduced; the module imports cleanly.
      </notes>
    </change>

    <change id="C2" priority="P1" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/adversaries.py" lines_changed="12" />
      </files_modified>
      <notes>
        Applied as specified. The dtype-mixing adversary now casts rest run-01 to float32
        against the int16 baseline, inverting its former polarity, and its matrix details dict
        inverted with it so the declaration matches the code. Verified this is the only float32
        write in the module.
      </notes>
    </change>

    <change id="C4" priority="P0" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/adversaries.py" lines_changed="10" />
      </files_modified>
      <notes>
        Applied as specified. The duplicate-run adversary now sources rest run-02, decoupling it
        from the adversary that removes rest run-01 on the same session, so matrix order no
        longer determines whether it materializes. Every source path is guarded. The subject's
        matrix order was correctly left unchanged, per the spec's directive that reordering
        would leave the coupling latent for a future edit to reintroduce. The agent noted the
        guard was already present, which is expected: the guard sweep had already converted this
        function's body under the reordered execution sequence.
      </notes>
    </change>

    <change id="C7" priority="P2" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/manifest.py" lines_changed="3" />
      </files_modified>
      <notes>
        Applied as specified. The orphan-file adversary's description now declares both orphan
        classes (the SBRef pair and the image-less BOLD sidecar) rather than only the former.
      </notes>
    </change>

    <change id="C8" priority="P2" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/manifest.py" lines_changed="4" />
      </files_modified>
      <notes>
        Applied as specified. The missing-modality adversary's description now covers both of
        its branches and scopes the dangling-pointer consequence to the diffusion branch only,
        so it does not misdescribe the subject that takes the anatomical branch. The
        dtype-mixing description was reviewed and correctly left unchanged: it names both dtypes
        without asserting which run holds which, so it survives the polarity inversion.
      </notes>
    </change>

  </changes_applied>

  <post_build_verification>
    Static and unit-level only. The generator was NOT run and no test suite was executed;
    both belong to the post-build smoke loop and to /test respectively.

    Return-claim verification (every agent claim checked against disk, not accepted on report):
      - All declared anchors present in the target files.
      - Zero local copies of the two consolidated helpers remain in the adversary module; the
        writer resolves to the modality module at runtime.
      - set_data_dtype absent from the modality module, per the spec directive.
      - Exactly one direct image construction remains in the adversary module, and it is the
        one the plan expects.
      - Zero residual silent existence guards module-wide.
      - Body-level diff confirms the already-loud adversaries were not touched.

    Storage-baseline acceptance criteria, all 9 PASS:
      on-disk dtype int16; dataobj.slope finite and != 1.0; dataobj.inter finite; raw stored
      range within [0, 4095]; round-trip error <= one quantization step; pixdim[4] preserved;
      sform_code == 1; qform_code == 1; float32 escape hatch functional.
      Measured: raw range [0, 4095], slope 6.29358e-04, inter -5.42786e-01.
      Read via dataobj.slope, not header["scl_slope"], per the plan's finding that the array
      proxy consumes the header scaling on load and would produce a false negative.

    Integration:
      - py_compile passes on all package modules.
      - All modules import cleanly, including the new adversary-to-modality edge.
      - Diff vs backup: adversaries.py 223 diff lines, modalities.py 27, manifest.py 7.
  </post_build_verification>

  <summary>
    <total_changes>8</total_changes>
    <completed>8</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>

  <next_steps>
    1. Fix the three known checker bugs in sandbox/verify_dataset.py before any re-run: the
       first check targets the wrong task; the second filters out the very file its adversary
       creates; the third assumes 2-space JSON indent where the actual indent is 4. The checker
       must additionally read dtype via dataobj.slope rather than the header field. These bugs
       are why the prior run reported 27/28 with one false failure class.
    2. Re-run the reduced-scale smoke loop and the corrected verifier. The bar is 28/28, not
       27/28. The guard sweep means any adversary that fails to materialize now raises by name
       rather than reporting success, so a clean run is materially stronger evidence than before.
    3. /test for the generator package. No tests were run during this build.
    4. /brainstorm for cohort design: the second clean dataset, and subject/session re-sizing
       for both datasets under a disk budget. The storage-baseline change roughly halves the
       adversarial dataset's footprint, which is direct input to that budget.
  </next_steps>
</implement_report>
