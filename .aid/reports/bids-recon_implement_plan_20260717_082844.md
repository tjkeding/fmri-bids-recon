<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-07-17T08:28:44-04:00" />

  <input_reports>
    <report path="sandbox/runs/run_smoke_01/bids-recon_run-local_20260716_174110.md" mode="run-local" key_items="4" />
  </input_reports>

  <scope_note>
    The four action items in the input report are the mandate. Two additional changes (C6, C7)
    were surfaced to the user during planning as newly-observed defects of the same class as the
    reported A25 defect, and were explicitly approved for inclusion. No item is carried in from
    any other source. The input report's deferred_items and housekeeping_pending_approval
    sections are not implement action items and are not addressed here.

    Cohort design (a second clean dataset, and re-sizing subject/session counts for both under a
    disk budget) was raised by the user during planning and is routed to /brainstorm as separate
    work. Every change below is independent of N_SUBJECTS and SESSIONS, so none of them
    constrain or are constrained by that decision.
  </scope_note>

  <empirical_findings>
    Three nibabel behaviors were verified experimentally during planning rather than assumed,
    because the int16 change depends on them and a wrong assumption would silently produce
    unscaled data.

    F-A. After nib.load(), img.header["scl_slope"] reads NaN regardless of the on-disk value:
         the array proxy consumes the scaling. On-disk values must be read via
         img.dataobj.slope / img.dataobj.inter. Any verification of this change that inspects
         header["scl_slope"] will produce a false negative.

    F-B. Building Nifti1Image from an int16 array and then calling header.set_slope_inter()
         persists the slope/inter to disk correctly. Verified: raw stored range [0, 4095],
         dataobj.slope 6.29e-04, dataobj.inter -5.43e-01, round-trip max abs error 3.14e-04
         (= half a quantization step, as expected). This is the mechanism C1 uses.

    F-C. The apply_A4 pattern, Nifti1Image(float_data, affine, header) where header carries an
         int16 dtype, does NOT drift to float32. nibabel recomputes slope/inter and writes
         int16. Verified: on-disk dtype int16, round-trip max abs error 1.97e-05. A4 therefore
         needs no dtype rescue; it is included in C5 only for scaling-convention uniformity.

    Consequence: the dtype-drift surface is far smaller than the pre-planning inventory
    suggested. Only construction sites that pass NO header drift to float32. Those are A26 and
    A27, plus the two _save_nifti copies. A16/A17/A18 load-edit-save and preserve dtype.
  </empirical_findings>

  <changes>

    <change id="C1" priority="P0" source_item="P1 (F5): int16 + scl_slope/scl_inter baseline">
      <file path="tools/simulated_bids/modalities.py" action="modify" />
      <file path="tools/simulated_bids/adversaries.py" action="modify" />
      <description>
        Establish an int16 + scl_slope/scl_inter storage baseline for every NIfTI the generator
        writes, matching dcm2niix output. The current float32 baseline in range [-0.5, 2.4] with
        negative values is not faithful to magnitude MRI and roughly doubles dataset size
        (float32 Gaussian noise is nearly incompressible; measured gzip ratio 88.1%).

        modalities._save_nifti and adversaries._save_nifti are verbatim duplicates, as are
        modalities._make_affine and adversaries._make_affine. Editing two copies of the exact
        function whose divergence is the hazard under repair is self-defeating, so the
        adversaries.py copies are deleted and imported from modalities instead. This is the
        single structural refactor in this plan and it is confined to removing exact duplicates.
      </description>
      <spec>
        In tools/simulated_bids/modalities.py, add a module-level constant above _make_affine:

            # 12-bit quantization: matches the effective dynamic range of Siemens
            # magnitude reconstruction, which dcm2niix carries through to int16 +
            # scl_slope/scl_inter rather than rescaling to full int16 range.
            INT16_QUANT_LEVELS = 4095

        Replace _save_nifti (currently lines 22-30) with:

            def _save_nifti(data: np.ndarray, affine: np.ndarray, pixdim4: float,
                            out_path: Path, dtype=np.int16) -> None:
                """Write a NIfTI-1 image with sform_code=qform_code=1.

                Magnitude MRI is stored as int16 with per-image scl_slope/scl_inter,
                mirroring dcm2niix. dtype is a parameter solely so adversaries that
                declare a dtype defect can request float32; every other caller must
                use the int16 default.
                """
                data = np.asarray(data, dtype=np.float32)
                if dtype == np.int16:
                    dmin = float(data.min())
                    dmax = float(data.max())
                    slope = (dmax - dmin) / INT16_QUANT_LEVELS if dmax > dmin else 1.0
                    raw = np.rint((data - dmin) / slope).astype(np.int16)
                    img = nib.Nifti1Image(raw, affine)
                    img.header.set_slope_inter(slope, dmin)
                else:
                    img = nib.Nifti1Image(data.astype(dtype), affine)
                hdr = img.header
                hdr.set_sform(affine, code=1)
                hdr.set_qform(affine, code=1)
                hdr["pixdim"][4] = pixdim4
                nib.save(img, str(out_path))

        Do NOT call hdr.set_data_dtype(); the on-disk dtype is inferred from the array dtype,
        and an explicit call risks resetting the slope set by set_slope_inter. This ordering
        (construct from int16 array, then set_slope_inter, then sform/qform/pixdim4) is the
        verified-working sequence from finding F-B.

        In tools/simulated_bids/adversaries.py:
          - Delete the local _make_affine (lines 104-108) and the local _save_nifti
            (lines 111-119) in their entirety, along with the now-empty portion of the
            "Shared helpers" banner if no helpers remain above _load_json (keep the banner;
            _load_json, _save_json, and the new C3 helpers live under it).
          - Add to the existing import block, after `from .noise import ...`:
                from .modalities import _make_affine, _save_nifti
          - Leave every existing call site of _make_affine / _save_nifti textually unchanged;
            they resolve to the imported names.

        Import-cycle check: modalities imports only .config and .noise; adversaries importing
        modalities introduces no cycle. Import-order check: sandbox/smoke_run.py asserts that
        modalities is absent from sys.modules BEFORE it patches config, and only imports
        adversaries afterward, so the new adversaries -> modalities edge still resolves after
        the patch. Both invariants hold; no change to smoke_run.py is required.
      </spec>
      <dependencies>none</dependencies>
      <risk>
        medium - The quantization mechanism itself is empirically verified (finding F-B), so the
        residual risk is confined to the added sform/qform/pixdim4 calls disturbing the slope,
        which the probe did not exercise. Acceptance criteria below pin this. Secondary risk:
        the duplicate-helper deletion is textual and mechanical, but a missed call site would
        raise NameError at import, which fails loudly rather than silently.
      </risk>
      <rollback>Restore modalities.py and adversaries.py from the pre-build backup (see rollback_strategy).</rollback>
      <acceptance>
        Round-tripping any generated BOLD NIfTI satisfies all of: nib.load(p).get_data_dtype()
        == int16; p.dataobj.slope is finite and != 1.0; p.dataobj.inter is finite; the unscaled
        array's range is within [0, 4095]; get_fdata() recovers the pre-write float array to
        within one quantization step. Verify via dataobj.slope, NOT header["scl_slope"]
        (finding F-A).
      </acceptance>
    </change>

    <change id="C2" priority="P1" source_item="P1 (F5): invert A19 against an int16 baseline">
      <file path="tools/simulated_bids/adversaries.py" action="modify" />
      <description>
        A19 declares a mixed-dtype defect across runs. Under the old float32 baseline it cast
        run-01 to int16. Under the C1 int16 baseline that cast is a no-op, so the polarity must
        invert: run-01 becomes the float32 outlier and run-02 remains the int16 baseline. The
        ADVERSARY_MATRIX details dict is the machine-readable declaration of the defect and must
        invert with the code, or the manifest will assert the opposite of what is on disk.
      </description>
      <spec>
        Replace apply_A19 (currently lines 456-466) with:

            def apply_A19(out_dir: Path, sub: str, spec: dict) -> None:
                """Cast rest run-01 BOLD data to float32; run-02 remains int16."""
                for ses in spec["sessions"]:
                    func_dir = out_dir / sub / ses / "func"
                    p = _require(
                        func_dir / f"{sub}_{ses}_task-rest_run-01_bold.nii.gz", "A19")
                    img = nib.load(str(p))
                    data = img.get_fdata(dtype=np.float32)
                    _save_nifti(data, img.affine, BOLD_PARAMS["RepetitionTime"], p,
                                dtype=np.float32)

        In ADVERSARY_MATRIX, the A19 entry (lines 77-78) becomes:

            {"id": "A19", "sessions": ["ses-02"], "target": "mixed_dtype_across_runs",
             "details": {"run01_dtype": "float32", "run02_dtype": "int16"}},

        A19 is the ONLY image in the dataset permitted to be float32. Any other float32 NIfTI
        after this change is an undeclared outlier and indicates C1 or C5 was applied incompletely.
      </spec>
      <dependencies>C1 (requires the dtype parameter on _save_nifti), C3 (requires _require)</dependencies>
      <risk>low - Single function plus a two-key dict inversion, both fully specified.</risk>
      <rollback>Restore adversaries.py from the pre-build backup.</rollback>
      <acceptance>
        On sub-009/ses-02: rest run-01 BOLD has on-disk dtype float32; rest run-02 BOLD has
        on-disk dtype int16. No other NIfTI in the dataset is float32.
      </acceptance>
    </change>

    <change id="C3" priority="P0" source_item="P0 (F2): apply_adversaries must raise when a declared target is absent">
      <file path="tools/simulated_bids/adversaries.py" action="modify" />
      <description>
        The `applied` list returned by apply_adversaries is currently derived from "the function
        did not raise", not from "the defect materialized". Because nearly every adversary wraps
        its mutation in a silent existence guard (`if src.exists():`, `if sidecars:`, or an empty
        glob loop), an adversary whose declared target was removed by an earlier adversary
        degrades to a no-op and still reports as applied. That is the exact mechanism that
        produced the A25 defect and made it invisible to count-based checking.

        This change converts every silent guard that protects a DECLARED target into a loud
        failure. A count-based guard in the dispatcher would NOT catch A25 (it copied 3 of 4
        files, so any effect count was non-zero); the check must therefore be per-path and sit
        at the point of use.
      </description>
      <spec>
        Add to the "Shared helpers" section of adversaries.py, below _save_json:

            def _require(path: Path, aid: str) -> Path:
                """Return path, or raise if a declared adversary target is absent.

                An adversary whose declared target is missing must fail loudly. Silently
                degrading to a no-op while still reporting as applied is the defect class
                this guard exists to prevent.
                """
                if not path.exists():
                    raise RuntimeError(f"{aid}: declared target missing: {path}")
                return path


            def _require_glob(directory: Path, pattern: str, aid: str) -> list[Path]:
                """Return sorted glob matches, or raise if the pattern matches nothing."""
                matches = sorted(directory.glob(pattern))
                if not matches:
                    raise RuntimeError(
                        f"{aid}: declared target missing: {directory}/{pattern}")
                return matches


            def _require_rglob(directory: Path, pattern: str, aid: str) -> list[Path]:
                """Return sorted recursive glob matches, or raise if nothing matches."""
                matches = sorted(directory.rglob(pattern))
                if not matches:
                    raise RuntimeError(
                        f"{aid}: declared target missing: {directory}/**/{pattern}")
                return matches

        Apply across the adversary functions as follows. In every case the adversary's own ID
        string is passed as `aid`.

        Named-path guards -> replace `if p.exists():` with `p = _require(p, "A{n}")` and
        de-indent the body:
            A1 (line ~140, `if ses_dir.exists():`), A10 (~227), A14 (~372), A19 (~461),
            A21 (~289), A25 (~386).

        Collection guards -> replace `if sidecars:` / bare glob loops with _require_glob:
            A3, A5, A8, A9, A11 (~243, `if sidecars:`), A12, A13, A16, A17, A18, A20, A22,
            A23, A24, A26.

        Recursive collection guards -> _require_rglob:
            A2, A6, A15.

        Content-filter guards. Two adversaries filter matched files by content rather than by
        path. The filter itself is retained (it is the targeting mechanism, not a guard), but
        zero surviving matches must raise:
            A15: after the rglob loop, raise if no file received the substitution. Track with a
                 local counter and raise RuntimeError(f"A15: declared target missing: no sidecar
                 with RepetitionTime 0.8 under {ses_dir}") if it is zero.
            A22: `if "IntendedFor" in sc` -> track whether any sidecar carried the key; raise if
                 none did.

        Already-loud adversaries requiring no change: A4, A7, A27, A28 (these index or open
        paths directly and will raise on absence).

        A9 note: A9's two branches ("T2w" / "dwi" in target) are alternatives selected by the
        matrix `target` string, not optional paths. Each branch independently requires its own
        target to be present; a branch that matches nothing must raise.

        A6 note: A6 partitions the session's sidecars at `half = len(json_files) // 2`. Require
        at least two matches so both the id_a and id_b halves are non-empty; otherwise the
        declared mixed-PatientID defect does not materialize. Raise RuntimeError(f"A6: declared
        target missing: fewer than 2 sidecars under {ses_dir}") when len < 2.
      </spec>
      <dependencies>none (but must be applied AFTER C2/C5/C6 edits to avoid textual conflicts; see execution_order)</dependencies>
      <risk>
        high - This is the broadest change in the plan, touching roughly 25 functions. The
        failure mode is converting a legitimately-optional guard into a spurious hard failure,
        which would halt generation. Mitigation: every guard listed above protects a target the
        matrix DECLARES for that adversary, so absence is by definition a defect; and the
        smoke loop exercises all 28 adversaries across all 10 subjects, so a spurious raise
        surfaces immediately and loudly rather than silently. Note this change is expected to
        make generation FAIL until C4 lands, because A25's declared run-01 target is genuinely
        absent today; that failure is the correct behavior and is the proof the guard works.
      </risk>
      <rollback>Restore adversaries.py from the pre-build backup.</rollback>
      <acceptance>
        Generation completes with all 28 adversaries applied. Independently: temporarily
        repointing any single adversary at a non-existent target causes apply_adversaries to
        raise RuntimeError naming that adversary ID, rather than returning it in `applied`.
      </acceptance>
    </change>

    <change id="C4" priority="P0" source_item="P0 (F1): repoint A25 to copy rest run-02">
      <file path="tools/simulated_bids/adversaries.py" action="modify" />
      <description>
        A25 declares a duplicated rest run. It copies run-01 to run-04, but sub-008's matrix
        applies A14 first (index 2) and A25 later (index 4), both on ses-03; A14 unlinks the
        run-01 BOLD NIfTI, so A25's `if src.exists()` skips the image and copies only the
        sidecar. The result is run-04_bold.json with no image, while apply_adversaries still
        reports "A25" as applied. sub-008/ses-03 shows exactly the baseline 22 NIfTI because
        A14 removes one and the broken A25 adds one back, so the collision is invisible to
        count-based checking.

        Repointing A25 at run-02 decouples it from A14 entirely, so matrix ordering no longer
        matters for this pair. This is the instance fix; C3 is the class fix.
      </description>
      <spec>
        In apply_A25 (currently lines 376-387), change the source stem from run-01 to run-02 and
        replace the silent existence guard with the C3 requirement helper:

            def apply_A25(out_dir: Path, sub: str, spec: dict) -> None:
                """Copy rest run-02 NIfTI + sidecar (and SBRef) to run-04 (duplicate).

                Sources run-02, not run-01: A14 removes rest run-01 on the same session,
                and sourcing from it made A25's materialization depend on matrix order.
                """
                for ses in spec["sessions"]:
                    func_dir = out_dir / sub / ses / "func"
                    for suffix in ["_bold", "_sbref"]:
                        src_stem = f"{sub}_{ses}_task-rest_run-02{suffix}"
                        dst_stem = f"{sub}_{ses}_task-rest_run-04{suffix}"
                        for ext in [".nii.gz", ".json"]:
                            src = _require(func_dir / f"{src_stem}{ext}", "A25")
                            dst = func_dir / f"{dst_stem}{ext}"
                            shutil.copy2(str(src), str(dst))

        Do not reorder the sub-008 matrix; the repoint makes ordering irrelevant for this pair,
        and reordering would leave the run-01 coupling latent for a future edit to reintroduce.
      </spec>
      <dependencies>C3 (requires _require)</dependencies>
      <risk>
        low - The declared defect (a duplicated rest run at run-04) is unchanged; only its
        source changes. rest run-02 is present on sub-008/ses-03 and is touched by no other
        adversary assigned to that subject.
      </risk>
      <rollback>Restore adversaries.py from the pre-build backup.</rollback>
      <acceptance>
        sub-008/ses-03/func contains all four of run-04_bold.nii.gz, run-04_bold.json,
        run-04_sbref.nii.gz, run-04_sbref.json, and each is byte-identical to its run-02
        counterpart. rest run-01_bold.nii.gz remains absent (A14's declared defect).
      </acceptance>
    </change>

    <change id="C5" priority="P1" source_item="P1 (F5): int16 baseline; no undeclared dtype outliers">
      <file path="tools/simulated_bids/adversaries.py" action="modify" />
      <description>
        Three adversaries construct NIfTI images directly rather than through _save_nifti. A26
        and A27 pass no header, so under the C1 int16 baseline they would silently write float32
        and become undeclared dtype outliers, polluting A19's declared dtype-mixing defect. A4
        passes a header and was verified NOT to drift (finding F-C), but it lets nibabel
        auto-recompute scaling to full int16 range, giving it a different slope convention from
        every other image in the dataset; that is an undeclared property of the image, so it is
        routed through _save_nifti for uniformity.

        A26 additionally drops pixdim[4] from 0.8 to nibabel's default 1.0 because it builds
        without a header, corrupting the header TR even though A26's declared target is
        orientation only. The user approved fixing both the dtype and the pixdim[4] regression
        so that A26 materializes its declared defect and nothing else.
      </description>
      <spec>
        apply_A4 (lines ~320-327), truncation block. Replace:

            img = nib.load(str(bold_path))
            data = img.get_fdata(dtype=np.float32)[..., :truncated_vols]
            trunc_img = nib.Nifti1Image(data, img.affine, img.header)
            trunc_img.header.set_sform(img.header.get_sform(), code=1)
            trunc_img.header.set_qform(img.header.get_qform(), code=1)
            trunc_img.header["pixdim"][4] = BOLD_PARAMS["RepetitionTime"]
            nib.save(trunc_img, str(bold_path))

        with:

            img = nib.load(str(bold_path))
            data = img.get_fdata(dtype=np.float32)[..., :truncated_vols]
            _save_nifti(data, img.affine, BOLD_PARAMS["RepetitionTime"], bold_path)

        The subsequent `_save_nifti(data_full, img.affine, ...)` call for the extra run is
        already correct and inherits int16 from C1; leave it unchanged. `img` remains bound and
        in scope for that call.

        apply_A26 (lines ~475-482). Replace:

            new_img = nib.Nifti1Image(img.get_fdata(dtype=np.float32), affine)
            new_img.header.set_sform(affine, code=1)
            new_img.header.set_qform(affine, code=1)
            nib.save(new_img, str(p))

        with:

            _save_nifti(img.get_fdata(dtype=np.float32), affine,
                        BOLD_PARAMS["RepetitionTime"], p)

        apply_A27 (lines ~396-401). Replace:

            img = nib.Nifti1Image(data, affine)
            img.header.set_sform(affine, code=1)
            img.header.set_qform(affine, code=1)
            stem = f"{sub}_{ses}_localizer"
            nib.save(img, str(func_dir / f"{stem}.nii.gz"))

        with:

            stem = f"{sub}_{ses}_localizer"
            _save_nifti(data, affine, 1.0, func_dir / f"{stem}.nii.gz")

        pixdim4=1.0 for A27 preserves the current on-disk value exactly (nibabel's default for
        a header built without one). A27's localizer is 3D, so pixdim[4] is unused; passing 1.0
        keeps this change strictly a dtype fix and introduces no header delta.

        A7 and A13 already call the local _save_nifti and inherit int16 via the C1 import; no
        edit. A16/A17/A18 load-edit-save and preserve dtype; no edit.
      </spec>
      <dependencies>C1</dependencies>
      <risk>
        low - Three localized replacements, each substituting a verified-equivalent helper call
        for an inline construction that already set the same sform/qform. The A4 and A26
        replacements change the scaling convention and (for A26) restore pixdim[4]; both are
        the intended effect.
      </risk>
      <rollback>Restore adversaries.py from the pre-build backup.</rollback>
      <acceptance>
        Every NIfTI in the dataset has on-disk dtype int16 except sub-009/ses-02 rest run-01
        (A19's declared float32 outlier). sub-009/ses-02 rest run-01 header pixdim[4] == 0.8
        after A26 (note A19 and A26 both target sub-009 rest run-01 on ses-02; both write via
        _save_nifti with pixdim4=BOLD_PARAMS["RepetitionTime"], so the value is consistent
        regardless of which runs last).
      </acceptance>
    </change>

    <change id="C6" priority="P1" source_item="newly observed during planning; user-approved for inclusion">
      <file path="tools/simulated_bids/adversaries.py" action="modify" />
      <description>
        A15 injects a duplicate JSON key by raw text substitution, because json.dump cannot emit
        duplicate keys. Its effect is therefore erasable: any later adversary that json.load /
        json.dump's the same sidecar silently collapses the duplicate. A15 currently
        materializes only because it happens to sit at index 3 in sub-009's list while A6, which
        round-trips every sidecar in the session, sits at index 1. Reverse the two and A15 would
        vanish while still reporting as applied.

        This is the same defect class as A25 but a different mechanism: erasure-after-write
        rather than missing-target-before-write. C3's precondition guards do not catch it,
        because A15's write genuinely succeeds. It requires a post-condition check.

        Verified NOT at risk: fieldmap sidecars carry TR 4.2 and 7.033, never 0.8, so A15's
        content filter never matches them and A23 (which rewrites fmap sidecars on the same
        session) cannot collide with it. All ten injected duplicate keys land on func sidecars.
      </description>
      <spec>
        In ADVERSARY_MATRIX, move the A15 entry to the END of the sub-009 list, so the order
        becomes A2, A6, A12, A19, A23, A15. Add a comment immediately above the sub-009 list:

            # A15 MUST be applied last for this subject: it injects a duplicate JSON key
            # via raw text substitution, and any later adversary that json.load/json.dump's
            # the same sidecar (A6, A20, A21, A24) silently collapses it.

        Add a post-condition verifier below apply_A15:

            def _assert_A15_survived(out_dir: Path, sub: str, spec: dict) -> None:
                """Raise if A15's duplicate key did not survive the full adversary sequence.

                A15's effect is erasable by any later json round-trip, so a precondition
                guard is insufficient; only a post-condition check proves it materialized.
                """
                for ses in spec["sessions"]:
                    ses_dir = out_dir / sub / ses
                    if not any('"repetitiontime"' in p.read_text()
                               for p in sorted(ses_dir.rglob("*.json"))):
                        raise RuntimeError(
                            f"A15: effect erased after application under {ses_dir}; "
                            f"a later adversary collapsed the duplicate key")

        In apply_adversaries, run post-condition checks after the full per-spec loop completes,
        so erasure by a later adversary is caught:

            def apply_adversaries(out_dir: Path, sub: str) -> list[str]:
                """Apply all adversaries assigned to a subject. Returns list of applied IDs.

                Adversaries raise on a missing declared target (see _require), so a returned
                ID means the defect materialized, not merely that the function ran.
                """
                specs = ADVERSARY_MATRIX.get(sub, [])
                applied = []
                for spec in specs:
                    fn = globals()[f"apply_{spec['id']}"]
                    fn(out_dir, sub, spec)
                    applied.append(spec["id"])
                for spec in specs:
                    check = globals().get(f"_assert_{spec['id']}_survived")
                    if check is not None:
                        check(out_dir, sub, spec)
                return applied

        The post-condition pass is keyed by naming convention, so adding a checker for another
        adversary later requires no dispatcher edit. A15 is the only adversary that needs one
        today: it is the only one whose effect a subsequent json round-trip can erase.
      </spec>
      <dependencies>C3 (the _assert convention complements the _require guards; no textual overlap)</dependencies>
      <risk>
        low - The reorder is a list permutation within one subject, and the post-condition check
        is additive. A15 is verified to materialize today, so the assert should pass immediately;
        if it does not, that is a genuine finding rather than a regression from this change.
      </risk>
      <rollback>Restore adversaries.py from the pre-build backup.</rollback>
      <acceptance>
        Generation completes without raising. sub-009/ses-01 func sidecars still contain the
        literal '"repetitiontime"' duplicate key after all six of the subject's adversaries have
        been applied.
      </acceptance>
    </change>

    <change id="C7" priority="P2" source_item="P2 (F3): A14 manifest description must declare both orphan classes">
      <file path="tools/simulated_bids/manifest.py" action="modify" />
      <description>
        A14 removes the rest run-01 BOLD NIfTI. Its manifest description declares only the
        orphaned SBRef, but the removal also leaves run-01_bold.json as an orphaned sidecar with
        no image. The user's locked decision is to keep the behavior and declare both classes,
        so the manifest states what is actually on disk.
      </description>
      <spec>
        In ADVERSARY_DESCRIPTIONS (tools/simulated_bids/manifest.py, lines ~6-35), replace:

            "A14": "Orphan SBRef (no matching BOLD run)"

        with:

            "A14": ("Orphaned rest run-01 files: the BOLD NIfTI is removed, leaving both "
                    "its SBRef pair and its own BOLD sidecar with no image"),
      </spec>
      <dependencies>none</dependencies>
      <risk>low - Single dict value; text only, no behavior.</risk>
      <rollback>Restore manifest.py from the pre-build backup.</rollback>
      <acceptance>The generated README.md's adversary table renders the A14 row with the new text.</acceptance>
    </change>

    <change id="C8" priority="P2" source_item="P2 (F4): A9 manifest description must declare dangling IntendedFor">
      <file path="tools/simulated_bids/manifest.py" action="modify" />
      <description>
        A9's dwi branch wipes the entire dwi directory, which leaves both acq-dwi fieldmaps
        carrying IntendedFor pointers to files that no longer exist. Its manifest description
        declares only the missing modality. The user's locked decision is to keep the behavior
        and declare the dangling pointers.

        Note the description is keyed by adversary ID only, while A9 has two branches selected by
        the matrix `target` string (sub-002 takes missing_T2w, sub-010 takes the dwi branch). The
        replacement text must therefore cover both branches and scope the dangling-IntendedFor
        consequence to the dwi branch specifically, or it will misdescribe sub-002.
      </description>
      <spec>
        In ADVERSARY_DESCRIPTIONS (tools/simulated_bids/manifest.py, lines ~6-35), replace:

            "A9": "Missing optional modality (T2w or DWI absent)"

        with:

            "A9": ("Missing optional modality. The T2w variant removes the anatomical only; "
                   "the DWI variant removes the whole dwi directory, which additionally leaves "
                   "both acq-dwi fieldmaps with IntendedFor pointers to absent files"),

        Review but do NOT change "A19": "Mixed data types across runs (int16 vs float32)". Under
        the C2 inversion the polarity flips (run-01 float32, run-02 int16), but the description
        names both dtypes without asserting which run holds which, so it remains accurate. The
        per-run assignment is declared in the matrix `details` dict, which C2 inverts.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - Single dict value; text only, no behavior.</risk>
      <rollback>Restore manifest.py from the pre-build backup.</rollback>
      <acceptance>The generated README.md's adversary table renders the A9 row with the new text, covering both branches.</acceptance>
    </change>

  </changes>

  <execution_order>
    C1, C5, C2, C4, C6, C3, C7, C8

    Rationale. C1 first: it establishes the _save_nifti signature and the import that C5 and C2
    depend on. C5, C2, C4, C6 next: each rewrites a distinct adversary function body, and doing
    them before the broad guard sweep means C3 edits their final text once rather than racing
    them. C3 second-to-last among code changes: it touches roughly 25 functions and would
    otherwise conflict textually with every preceding change. C7 and C8 last: they are isolated
    to manifest.py and depend on nothing.

    Note the intermediate state after C3 but before C4 is expected to FAIL generation, because
    A25's declared run-01 target is genuinely absent. The listed order places C4 before C3
    precisely so no such broken intermediate is ever committed.

    Dispatch partitioning: C1 spans modalities.py and adversaries.py; C2/C4/C5/C6/C3 are all
    adversaries.py; C7/C8 are manifest.py. Because six of eight changes touch the same file,
    they MUST be dispatched sequentially, not in parallel. C7 and C8 may be dispatched together
    as a single manifest.py group, concurrently with the adversaries.py chain.
  </execution_order>

  <rollback_strategy>
    This project is NOT a git repository (verified: `git rev-parse --show-toplevel` returns
    "fatal: not a git repository"). No git-based rollback is available, so rollback is
    file-backup based and the backup MUST be taken before the first edit or it does not exist.

    Before C1, copy the three target files to a timestamped backup directory:

        mkdir -p sandbox/backups/pre_implement_20260717_082844
        cp tools/simulated_bids/modalities.py \
           tools/simulated_bids/adversaries.py \
           tools/simulated_bids/manifest.py \
           sandbox/backups/pre_implement_20260717_082844/

    To roll back any change, copy the corresponding file back from that directory. Restoring is
    an overwrite of an existing file and therefore requires explicit per-invocation user
    approval under the destructive-operations policy; the build must surface the request rather
    than restore unilaterally.

    Granularity: the backup is per-file, not per-change. Because six of the eight changes touch
    adversaries.py, restoring that file reverts all six. Per-change rollback is not available
    without git. If finer granularity is needed, the build should be dispatched in the listed
    order and halted at the first failure, so at most one change is in flight at a time.
  </rollback_strategy>

  <post_build>
    Not part of this plan; recorded so the sequencing is explicit and nothing is silently dropped.

    1. sandbox/verify_dataset.py carries three known checker bugs diagnosed during the run-local
       session and deliberately left unfixed: the A5 check targets task-rest but A5 targets
       task-emotionalnback; the A7 check filters out any filename containing "task-", which
       excludes the task-otherstudy file A7 creates; the A15 raw_keys regex assumes 2-space JSON
       indent but the actual indent is 4. These must be fixed before the post-build re-run, and
       the verifier must additionally read dtype via dataobj.slope rather than
       header["scl_slope"] (finding F-A). The re-run must require 28/28, not 27/28.
    2. Re-run the smoke loop and the verifier.
    3. /test for the generator package. This plan runs no tests; /implement is not the testing skill.
    4. /brainstorm for cohort design: the clean dataset, and subject/session re-sizing for both
       datasets under a disk budget.
  </post_build>
</implement_plan>
