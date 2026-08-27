<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-07-21T13:35:56Z" />
  <input_reports>
    <report path="bids-recon_implement_build_20260721_082241.md" mode="implement:build" key_items="2" />
    <report path="bids-recon_implement_plan_20260717_101506.md" mode="implement:plan" key_items="2" />
  </input_reports>

  <resolved_decisions>
    The original plan's post_build note recommends "read dtype via dataobj.slope rather
    than header['scl_slope']" for the A18 scl_slope check. This recommendation is not
    adopted: nibabel's ArrayProxy normalizes NaN slope to 1.0 (the identity scalar), so
    switching from header["scl_slope"] to dataobj.slope would cause the A18 check to
    report False for a valid NaN slope, introducing a regression. The existing
    header["scl_slope"] approach correctly returns the raw NaN value. Kept as-is.
  </resolved_decisions>

  <changes>
    <change id="C1" priority="P1" source_item="build_report next_steps item 1; plan post_build item 1">
      <file path="sandbox/smoke_run.py" action="modify" />
      <description>
        Update the smoke-run driver for the profile-driven CLI. The generator now requires
        --profile; invoking main() without it raises an argparse error. The driver must also
        use the profile's declared seed rather than a hardcoded 42, so both profiles produce
        bit-identical output whether run via the smoke driver or the main CLI.
      </description>
      <spec>
        1. Update the module docstring (lines 1-21):
           - Change "10 subjects, 3 sessions, 28 adversaries" to
             "13 subjects (adversarial) or 4 subjects (clean), 3 sessions, 31 adversaries"
           - No other docstring changes needed; the rest remains accurate.

        2. Replace the __main__ block (lines 65-68) with argparse-based profile selection:

             if __name__ == "__main__":
                 import argparse
                 p = argparse.ArgumentParser(
                     description="Reduced-scale smoke test for the simulated-BIDS generator.")
                 p.add_argument("output_dir", nargs="?",
                                default=str(REPO / "sandbox" / "smoke_out"),
                                help="Root directory for the generated dataset.")
                 p.add_argument("--profile", choices=["adversarial", "clean"],
                                default="adversarial",
                                help="Dataset profile (default: adversarial).")
                 args = p.parse_args()
                 seed = cfg.get_profile(args.profile)["seed"]
                 sys.argv = ["tools.simulated_bids", args.output_dir,
                              "--profile", args.profile, "--seed", str(seed)]
                 gen.main()

           Key points:
           - output_dir is optional positional (nargs="?"), defaulting to sandbox/smoke_out.
           - --profile defaults to "adversarial" (exercises all code paths including adversaries).
           - Seed is derived from the profile via cfg.get_profile(), not hardcoded.
           - sys.argv is reconstructed with --profile and --seed before calling gen.main().

        3. Lines 30-63 (config patching, import assertions, truncated_volumes rescaling):
           NO CHANGES. The config patching of BOLD_REST_VOLUMES, BOLD_ENBACK_VOLUMES, and
           DWI_PARAMS remains correct. The import-order assertions remain correct. The
           truncated_volumes rescaling loop iterates ADVERSARY_MATRIX (now 13 subjects)
           and rescales any entry with a truncated_volumes detail; this is harmless for the
           clean profile (adversaries are not applied) and correct for the adversarial profile.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - sandbox driver, no codebase changes, only argparse addition + seed derivation</risk>
      <rollback>restore from backup</rollback>
    </change>

    <change id="C2" priority="P0" source_item="build_report next_steps item 2; plan post_build item 2">
      <file path="sandbox/verify_dataset.py" action="modify" />
      <description>
        Fix three known checker bugs (A5 task target, A7 filter logic, A15 indent regex),
        update all 28 existing checks to match the new 13-subject adversary matrix, and add
        verification checks for the three new adversary types (A29, A30, A31) to reach full
        31/31 type coverage across all 13 subjects.
      </description>
      <spec>
        Part A: Bug fixes (3)

        BUG 1 — A5 check (lines 70-75): targets task-rest; A5 modifies task-emotionalnback.
        Fix: change both sidecar paths from task-rest to task-emotionalnback. Update subject
        to sub-010 (ses-01 vs ses-02). The check verifies ProtocolName differs across sessions:

            a = F("sub-010", "ses-01") / "sub-010_ses-01_task-emotionalnback_run-01_bold.json"
            b = F("sub-010", "ses-02") / "sub-010_ses-02_task-emotionalnback_run-01_bold.json"
            sa = js(a).get("ProtocolName") if a.exists() else None
            sb = js(b).get("ProtocolName") if b.exists() else None
            check("A5", sa is not None and sb is not None and sa != sb,
                  f"ses-01 ProtocolName={sa!r} vs ses-02={sb!r}")

        BUG 2 — A7 check (lines 86-90): filter `"task-" not in p.name` excludes the
        task-otherstudy file that A7 creates. Fix: search for the specific file by name:

            f = ROOT / "sub-010" / "ses-03" / "func"
            stale = f / "sub-010_ses-03_task-otherstudy_run-01_bold.nii.gz"
            check("A7", stale.exists(), f"sub-010/ses-03 task-otherstudy exists={stale.exists()}")

        BUG 3 — A15 check (lines 33-37): raw_keys regex `\s{2}` assumes 2-space JSON indent;
        actual indent is 4 (_save_json uses json.dump with indent=4). Fix: change `\s{2}` to
        `\s{4}` in the raw_keys function:

            return re.findall(r'^\s{4}"([^"]+)"\s*:', txt, re.M)

        Part B: Complete subject/session re-mapping (all 31 checks)

        The following table maps every check to its correct subject/session/target in the
        new 13-subject adversary matrix. Checks marked SAME need no location change; all
        others need their subject and/or session references updated. The exact code for each
        check follows the same structure as the existing file; only the subject/session/path
        literals change unless otherwise noted.

        A1:  sub-012/ses-02 absent (was sub-006/ses-02)
        A2:  sub-013/ses-03 empty (was sub-009/ses-03)
        A3:  sub-010/ses-01 rest SeriesDescription contains typo "ABCD_fMRI_rset"
             (was sub-005/ses-01 rest + sub-010/ses-03 enback; now both instances target rest;
             check one representative: sub-010/ses-01, verify SD != "ABCD_fMRI_rest")
        A4:  sub-007/ses-01, run-01 truncated, extra run is run-03 (was run-04; extra_run
             changed from 4 to 3 because BOLD_REST_RUNS dropped from 3 to 2)
        A5:  sub-010/ses-01+02 task-emotionalnback (BUG FIX; was sub-008 task-rest)
        A6:  sub-012/ses-01 (was sub-009/ses-01); details ids are SIM_PT_012A/B
        A7:  sub-010/ses-03 task-otherstudy (BUG FIX; was sub-010/ses-01 broken filter)
        A8:  sub-007/ses-02 — SAME
        A9:  sub-012/ses-01, T2w only (was sub-002/ses-02 T2w + sub-010/ses-03 dwi;
             DWI variant no longer assigned; remove the DWI portion of the check)
        A10: sub-008/ses-01 (was sub-003/ses-01)
        A11: sub-011/ses-01 (was sub-008/ses-02)
        A12: sub-009/ses-01 (was sub-009/ses-02; session changed)
        A13: sub-009/ses-03 (was sub-006/ses-01)
        A14: sub-012/ses-03 (was sub-008/ses-03)
        A15: sub-011/ses-03 (BUG FIX regex; was sub-009/ses-01)
        A16: sub-005/ses-02 — SAME
        A17: sub-006/ses-01 only (was sub-007/ses-03 + sub-010/ses-01 with break;
             now single subject; remove the loop-with-break pattern, check sub-006/ses-01
             anat T1w for qform != sform)
        A18: sub-009/ses-02 (was sub-008/ses-01); keep header["scl_slope"] (resolved decision)
        A19: sub-011/ses-02 (was sub-009/ses-02)
        A20: sub-001/ses-01 (was sub-006/ses-03)
        A21: sub-007/ses-03 (was sub-005/ses-03)
        A22: sub-008/ses-02 (was sub-007/ses-01)
        A23: sub-008/ses-03 (was sub-009/ses-01); fmap TRT=0.06 vs bold TRT=0.045391
        A24: sub-006, sessions ses-02+03 (was sub-004; TR values: ses-02=0.801, ses-03=0.802)
        A25: sub-012/ses-03, dst_run=3 from src_run=2 (was sub-008/ses-03 run-04 from run-01)
        A26: sub-002/ses-01 (was sub-010/ses-02)
        A27: sub-010/ses-02 or sub-013/ses-01 (was sub-003/ses-03); check for localizer files
        A28: sub-011 (was sub-004); check participants.tsv comma decimal

        Part C: New checks (3)

        A29 (sub-003/ses-01): Phase-encoding direction flipped on rest run-01.
            p = F("sub-003", "ses-01") / "sub-003_ses-01_task-rest_run-01_bold.json"
            pe = js(p).get("PhaseEncodingDirection") if p.exists() else None
            check("A29", pe == "j-",
                  f"rest run-01 PhaseEncodingDirection={pe!r} (expected 'j-', clean='j')")

        A30 (sub-004/ses-01): Diffusion gradient x-component negated in bvec.
            dd = ROOT / "sub-004" / "ses-01" / "dwi"
            bc = next(iter(dd.glob("*.bvec")), None)
            if bc:
                rows = bc.read_text().strip().split("\n")
                x_vals = [float(v) for v in rows[0].split()]
                n_neg = sum(1 for v in x_vals if v < 0)
                n_pos = sum(1 for v in x_vals if v > 0)
                check("A30", n_neg > n_pos,
                      f"bvec x-row: {n_neg} negative vs {n_pos} positive "
                      f"(negated axis should flip majority)")
            else:
                check("A30", False, "bvec file not found")

        A31 (sub-005/ses-03): Voxel-size drift on rest protocol.
            f03 = F("sub-005", "ses-03") / "sub-005_ses-03_task-rest_run-01_bold.nii.gz"
            f01 = F("sub-005", "ses-01") / "sub-005_ses-01_task-rest_run-01_bold.nii.gz"
            z03 = nib.load(str(f03)).header.get_zooms()[:3] if f03.exists() else None
            z01 = nib.load(str(f01)).header.get_zooms()[:3] if f01.exists() else None
            check("A31", z03 is not None and z01 is not None and z03 != z01,
                  f"ses-03 voxel={z03} vs ses-01 voxel={z01} "
                  f"(expect 2.5mm vs 2.4mm)")

        Part D: Docstring and summary updates

        1. Update module docstring to remove stale references (no specific counts to update;
           the docstring doesn't mention subject/adversary counts).
        2. At the bottom, the summary line currently says "materialized: {n}/{n}" where n
           is the result count. This is dynamic and needs no change. The results list
           will naturally grow from 28 to 31 entries.
      </spec>
      <dependencies>none</dependencies>
      <risk>medium - extensive rewrite of check references; each check's subject/session
        must exactly match the adversary matrix. A single mapping error produces a false
        FAIL. Mitigated by the deterministic mapping table above and by the fact that
        running the verifier against a generated dataset provides end-to-end validation.</risk>
      <rollback>restore from backup</rollback>
    </change>
  </changes>

  <execution_order>
    C1, C2 (parallel — disjoint files: smoke_run.py vs verify_dataset.py)

    Both changes are independent and touch non-overlapping files. They can be dispatched
    concurrently. Neither has a dependency on the other.
  </execution_order>

  <rollback_strategy>
    This project is NOT a git repository. Rollback is file-backup based.

    Before the first edit, copy both target files to a timestamped backup directory:

        mkdir -p sandbox/backups/pre_implement_20260721_093556
        cp sandbox/smoke_run.py \
           sandbox/verify_dataset.py \
           sandbox/backups/pre_implement_20260721_093556/

    Record SHA-256 of each original in the build report so a restore is verifiable.
    Restoring requires explicit per-invocation user approval.
  </rollback_strategy>

  <post_build>
    No items deferred. This plan addresses ALL remaining deferred items from the prior build
    that are code changes. The two remaining items from the original plan's post_build are
    downstream skill invocations, not code changes:

    1. /test for the generator package — invoked separately after this build.
    2. /run-local to request the ~/simulated-bids/ filesystem grant and generate both
       profiles — invoked after /test, requiring explicit user approval for the grant.

    These are consistent with the user's stated sequencing: "ONE more round of implementation
    and testing, and then will proceed to 'run-local'."
  </post_build>
</implement_plan>
