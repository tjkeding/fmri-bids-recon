<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-07-17T10:15:06-04:00" />

  <input_reports>
    <report path="bids-recon_brainstorm_20260717_095951.md" mode="brainstorm" key_items="7" />
  </input_reports>

  <scope_note>
    The seven action items in the input report are the mandate. Three additional decisions were
    surfaced to the user during planning, because reading the files the report referenced revealed
    gaps its action items did not cover, and all three were explicitly resolved before this spec
    was written:
      - the clean profile's README (write_manifest emits an adversary matrix sourced from
        ADVERSARY_MATRIX, which under the clean profile would describe 13 subjects and 31 defects
        inside a dataset containing neither) -> profile-aware manifest;
      - dataset_description.json identity (hardcoded Name would make both datasets byte-identical
        there) -> per-profile Name plus seed/profile in GeneratedBy;
      - A31's scope (drifting only rest BOLD would incidentally create a fieldmap/BOLD geometry
        mismatch, which is A13's declared defect on a different subject, giving sub-005 an
        undeclared second defect) -> drift the whole ses-03 functional protocol.
    No item is carried in from any other source. The report's run-local action item (filesystem
    grant and generation) is not an implement item and is not addressed here.
  </scope_note>

  <verified_findings>
    Established by reading the codebase during planning, not assumed. Each drives a change below.

    V1. main() enumerates DEMOGRAPHICS directly (`for demo in DEMOGRAPHICS`, line 97). N_SUBJECTS is
        vestigial: its only use is the print at line 96. Roster selection must therefore filter
        DEMOGRAPHICS, and changing N_SUBJECTS alone would do nothing.

    V2. scaffold.write_participants_tsv(out_dir) iterates ALL of DEMOGRAPHICS unconditionally
        (line 24). With 17 rows in the table, each dataset's participants.tsv would list the other
        dataset's subjects: BIDS-invalid and a cross-dataset leak.

    V3. Run counts are hardcoded at four sites in __main__.generate_clean_session: line 36
        `range(1, 4)` (rest generation), line 40 `range(1, 3)` (enback generation), line 53
        `range(1, 3)` (enback IntendedFor), line 63 `range(1, 4)` (rest IntendedFor). Dropping to
        2 rest runs without fixing line 63 leaves the fieldmap pointing at a run-03 that no longer
        exists.

    V4. manifest.py hardcodes three strings the redesign falsifies: line 51
        "- 10 subjects (sub-001 through sub-010), 3 sessions each"; line 52 "- sub-001: clean
        baseline (no adversaries)"; line 71 the literal `| sub-001 | Clean | (none) |` table row.

    V5. Adversary targeting semantics, confirmed by reading the implementations, which govern the
        collision analysis in C5: apply_A3 selects rest when "rest" is in `target`, else enback.
        apply_A5 targets enback ONLY. apply_A20 selects enback when "enback" is in `target`, else
        `task-*_run-*_bold.json` (both tasks). apply_A17 selects anat T1w when "t1w" is in
        `target`, else func rest run-01.

    V6. apply_A25 hardcodes dst run-04 and src run-02; apply_A4's matrix entry declares
        extra_run=4. Under 2 rest runs both indices leave a gap at run-03 and must be
        parameterised.

    V7. _generate_bvecs produces a (3, n) float64 array written as 3 whitespace-separated rows.
        Row 0 is the x-component, which is A30's target.

    V8. generate_bold emits BOTH a BOLD and an SBRef NIfTI, so any adversary that regenerates
        functional data must cover both.
  </verified_findings>

  <changes>

    <change id="C1" priority="P0" source_item="config.py: PROFILES, run-count constants, demographic rows, N_SUBJECTS">
      <file path="tools/simulated_bids/config.py" action="modify" />
      <description>
        Establish the profile as the single source of truth for the four axes on which the two
        datasets differ (subject roster, ID space, seed, adversary switch), lift the run counts out
        of hardcoded loop bounds into named constants because run count is now the primary sizing
        lever, add the seven fabricated demographic rows, and add the geometry constants A31 needs.
      </description>
      <spec>
        Append seven rows to DEMOGRAPHICS, preserving the existing dict shape exactly. All values
        are fabricated; none derive from any real participant.

            {"participant_id": "sub-011", "sex": "F", "handedness": "R", "age_ses01": 9.5},
            {"participant_id": "sub-012", "sex": "M", "handedness": "L", "age_ses01": 11.1},
            {"participant_id": "sub-013", "sex": "F", "handedness": "A", "age_ses01": 10.7},
            {"participant_id": "sub-101", "sex": "F", "handedness": "R", "age_ses01": 9.4},
            {"participant_id": "sub-102", "sex": "M", "handedness": "L", "age_ses01": 10.3},
            {"participant_id": "sub-103", "sex": "F", "handedness": "A", "age_ses01": 11.2},
            {"participant_id": "sub-104", "sex": "M", "handedness": "R", "age_ses01": 12.1},

        Replace the N_SUBJECTS line with run-count constants and the profile table:

            # Runs per session per task. These are the dominant disk lever: BOLD volumes are
            # ~82% of a session's bytes. Both IntendedFor construction and the generation
            # loops derive from these, so the two cannot drift apart.
            BOLD_REST_RUNS = 2
            BOLD_ENBACK_RUNS = 2

            # Dataset profiles. The two datasets differ on four coupled axes (roster, ID space,
            # seed, adversary switch); declaring them together is what keeps them in sync.
            PROFILES = {
                "adversarial": {
                    "subject_ids": [f"sub-{i:03d}" for i in range(1, 14)],
                    "seed": 42,
                    "apply_adversaries": True,
                    "dataset_name": "Simulated BIDS Dataset (Adversarial Fixture)",
                },
                "clean": {
                    "subject_ids": [f"sub-{i:03d}" for i in range(101, 105)],
                    "seed": 1729,
                    "apply_adversaries": False,
                    "dataset_name": "Simulated BIDS Dataset (Clean Workload)",
                },
            }

            # A31 (voxel-size drift): ses-03 functional protocol geometry. 2.5 mm over the same
            # FOV as the 2.4 mm baseline: 90 * 2.4 / 2.5 = 86.4 -> 86; 60 * 2.4 / 2.5 = 57.6 -> 58.
            DRIFT_VOXEL_SIZE = (2.5, 2.5, 2.5)
            DRIFT_SHAPE_SPATIAL = (86, 86, 58)

        Delete N_SUBJECTS entirely. It is vestigial (finding V1): its only consumer is a print
        statement, which C3 rewrites to use the profile roster length. Leaving it would create a
        second, silently-wrong source of truth for the subject count.

        Add a helper below age_at_session:

            def get_profile(name: str) -> dict:
                """Return the named profile, or raise with the valid choices."""
                if name not in PROFILES:
                    raise KeyError(
                        f"unknown profile {name!r}; choose from {sorted(PROFILES)}")
                return PROFILES[name]

        Leave SESSIONS, BOLD_REST_VOLUMES (383), BOLD_ENBACK_VOLUMES (370), and every *_PARAMS
        dict unchanged. Both datasets are full-scale by decision; volume counts do not change.
      </spec>
      <dependencies>none</dependencies>
      <risk>
        low - Additive except for the N_SUBJECTS deletion, which fails loudly at import
        (ImportError in __main__) rather than silently, and C3 removes that import in the same
        batch.
      </risk>
      <rollback>Restore config.py from the pre-build backup.</rollback>
      <acceptance>
        PROFILES["adversarial"]["subject_ids"] has 13 entries sub-001..sub-013;
        PROFILES["clean"]["subject_ids"] has 4 entries sub-101..sub-104; DEMOGRAPHICS has 17 rows;
        BOLD_REST_RUNS == BOLD_ENBACK_RUNS == 2; N_SUBJECTS is absent; get_profile raises KeyError
        on an unknown name.
      </acceptance>
    </change>

    <change id="C2" priority="P0" source_item="scaffold.py: filter participants.tsv by roster; per-profile dataset_description">
      <file path="tools/simulated_bids/scaffold.py" action="modify" />
      <description>
        Close the cross-dataset leak identified in finding V2, and give each dataset a distinct
        identity so no tool or log can confuse them. Without the roster filter the first clean
        generation produces a participants.tsv listing 13 subjects that do not exist in it.
      </description>
      <spec>
        Change the signature of write_participants_tsv to take the active roster and filter on it:

            def write_participants_tsv(out_dir: Path, roster: list[str]) -> None:
                """Write participants.tsv for the subjects in `roster` only.

                Filtering is not cosmetic: DEMOGRAPHICS holds every subject across both
                dataset profiles, so an unfiltered write lists the other dataset's subjects,
                which is both BIDS-invalid and a cross-dataset leak.
                """
                lines = ["participant_id\tage\tsex\thandedness"]
                for d in DEMOGRAPHICS:
                    if d["participant_id"] not in roster:
                        continue
                    lines.append(
                        f"{d['participant_id']}\t{d['age_ses01']}\t{d['sex']}\t{d['handedness']}"
                    )
                (out_dir / "participants.tsv").write_text("\n".join(lines) + "\n")

        The participants.json metadata block below it is unchanged.

        Change the signature of write_dataset_description to take the profile:

            def write_dataset_description(out_dir: Path, profile_name: str,
                                          profile: dict) -> None:
                """Write dataset_description.json identifying this specific dataset.

                Name and GeneratedBy carry the profile and seed so the two datasets are
                distinguishable from their metadata alone, not only from their path.
                """
                desc = {
                    "Name": profile["dataset_name"],
                    "BIDSVersion": "1.9.0",
                    "DatasetType": "raw",
                    "License": "CC0",
                    "GeneratedBy": [{
                        "Name": "simulated_bids",
                        "Version": "1.0.0",
                        "Description": f"profile={profile_name}; seed={profile['seed']}",
                    }],
                }
                with open(out_dir / "dataset_description.json", "w") as f:
                    json.dump(desc, f, indent=4)

        write_sessions_tsv and write_scans_tsv are unchanged: both are already per-subject and
        take the subject as an argument, so neither can leak across profiles.
      </spec>
      <dependencies>C1 (profile dict shape, including the dataset_name key)</dependencies>
      <risk>
        low - Two signature changes, both with exactly one call site (in __main__), updated by C3
        in the same batch. A missed call site raises TypeError at import-time-adjacent execution,
        not silently.
      </risk>
      <rollback>Restore scaffold.py from the pre-build backup.</rollback>
      <acceptance>
        Under the clean profile, participants.tsv contains exactly 4 data rows, all sub-1xx, and
        no sub-0xx row. Under the adversarial profile it contains exactly 13 rows, all sub-0xx.
        Each dataset_description.json carries its own Name and records profile and seed.
      </acceptance>
    </change>

    <change id="C3" priority="P0" source_item="__main__.py: --profile, roster-driven generation, run-count constants, seed">
      <file path="tools/simulated_bids/__main__.py" action="modify" />
      <description>
        Make the profile drive generation end to end, and eliminate the four hardcoded run-count
        sites (finding V3). Line 63 is the load-bearing one: dropping to 2 rest runs without
        fixing it leaves every fieldmap in both datasets with an IntendedFor pointing at a
        rest run-03 that no longer exists.
      </description>
      <spec>
        Imports: replace

            from .config import DEMOGRAPHICS, SESSIONS, N_SUBJECTS

        with

            from .config import DEMOGRAPHICS, SESSIONS, get_profile
            from .config import BOLD_REST_RUNS, BOLD_ENBACK_RUNS

        (the existing BOLD_REST_VOLUMES / BOLD_ENBACK_VOLUMES import line is unchanged).

        In generate_clean_session, replace the four hardcoded run counts. Line 35 comment becomes
        "# Functional: BOLD_REST_RUNS rest runs + BOLD_ENBACK_RUNS enback runs".

            for run in range(1, BOLD_REST_RUNS + 1):       # was range(1, 4)
            for run in range(1, BOLD_ENBACK_RUNS + 1):     # was range(1, 3)

            enback_intended = [
                f"{ses}/func/{sub}_{ses}_task-emotionalnback_run-{r:02d}_bold.nii.gz"
                for r in range(1, BOLD_ENBACK_RUNS + 1)    # was range(1, 3)
            ]
            rest_intended = [
                f"{ses}/func/{sub}_{ses}_task-rest_run-{r:02d}_bold.nii.gz"
                for r in range(1, BOLD_REST_RUNS + 1)      # was range(1, 4)
            ]

        Update the two IntendedFor comments to "-> enback runs 1..BOLD_ENBACK_RUNS" and
        "-> rest runs 1..BOLD_REST_RUNS" so they cannot go stale against the constants.

        In main(), add the profile argument and make its seed authoritative:

            parser.add_argument("--profile", choices=["adversarial", "clean"],
                                required=True,
                                help="Dataset profile: subject roster, seed, and whether "
                                     "adversaries are applied.")
            parser.add_argument("--seed", type=int, default=None,
                                help="Override the profile's seed. Omit to use it.")

        After parsing:

            profile = get_profile(args.profile)
            roster = profile["subject_ids"]
            seed = args.seed if args.seed is not None else profile["seed"]
            rng = np.random.default_rng(seed)

        Phase 1: drive the loop from the roster, not the full table.

            print(f"Profile '{args.profile}': {len(roster)} subjects x "
                  f"{len(SESSIONS)} sessions (seed {seed})...")
            demo_by_id = {d["participant_id"]: d for d in DEMOGRAPHICS}
            for sub in roster:
                demo = demo_by_id[sub]
                sub_rng = np.random.default_rng(rng.integers(0, 2**31))
                for ses in SESSIONS:
                    ... unchanged body ...

        Iterate `roster` rather than `demo_by_id` so subject order is the profile's declared
        order, and so a roster naming a subject absent from DEMOGRAPHICS raises KeyError loudly
        instead of silently generating a short dataset.

        Phase 2:

            write_dataset_description(out, args.profile, profile)
            write_participants_tsv(out, roster)

        Phase 3: gate on the profile and intersect with the roster.

            if profile["apply_adversaries"]:
                print("\nApplying adversarial mutations...")
                for sub in sorted(set(ADVERSARY_MATRIX) & set(roster)):
                    applied = apply_adversaries(out, sub)
                    if applied:
                        print(f"  {sub}: {', '.join(applied)}")

        The intersection is a guard, not decoration: it means a matrix entry for a subject the
        active profile does not generate is skipped rather than raising inside an adversary on a
        directory that was never created.

        Phase 4:

            write_manifest(out, args.profile, profile)
      </spec>
      <dependencies>C1 (get_profile, run-count constants), C2 (both scaffold signatures), C6 (write_manifest signature)</dependencies>
      <risk>
        medium - The most cross-cutting change. --profile is deliberately `required=True`, which
        is a breaking CLI change: the existing invocation `python -m tools.simulated_bids OUT
        --seed 42` will now fail with a clear argparse error rather than silently generating the
        adversarial dataset. That is intended; an implicit default is how the wrong dataset gets
        generated into the wrong directory. Note sandbox/smoke_run.py invokes main() via
        sys.argv and will need `--profile adversarial` added; it is a sandbox driver, out of
        scope for this spec, and is recorded in post_build.
      </risk>
      <rollback>Restore __main__.py from the pre-build backup.</rollback>
      <acceptance>
        `--profile clean` generates exactly sub-101..sub-104 with seed 1729 and applies zero
        adversaries. `--profile adversarial` generates sub-001..sub-013 with seed 42 and applies
        the matrix. Every fieldmap's IntendedFor enumerates rest runs 01-02 and enback runs 01-02
        only. Omitting --profile exits with an argparse error.
      </acceptance>
    </change>

    <change id="C4" priority="P0" source_item="adversaries.py: implement A29, A30, A31">
      <file path="tools/simulated_bids/adversaries.py" action="modify" />
      <description>
        Add the three missing silent killers. Each is a propagating defect: it does not trigger
        exclusion, passes silently into analysis, and corrupts the result. All three are guarded
        by the requirement helpers so a missing declared target raises rather than no-ops.
      </description>
      <spec>
        Add to the config import line: DRIFT_VOXEL_SIZE, DRIFT_SHAPE_SPATIAL, BOLD_ENBACK_VOLUMES,
        BOLD_REST_RUNS, BOLD_ENBACK_RUNS. Add to the modalities import: generate_bold is NOT
        imported (see the A31 note below); _make_affine and _save_nifti are already imported.

        Place all three in the appropriate existing banner sections.

        apply_A29 (sidecar mutations section):

            def apply_A29(out_dir: Path, sub: str, spec: dict) -> None:
                """Flip PhaseEncodingDirection on rest run-01 BOLD; fieldmaps stay correct.

                The fieldmap pair still declares the true polarity, so distortion
                correction applies the warp backwards rather than failing. Nothing
                errors; the output is simply more distorted than the input.
                """
                wrong = spec["details"]["wrong"]
                for ses in spec["sessions"]:
                    func_dir = out_dir / sub / ses / "func"
                    p = _require(
                        func_dir / f"{sub}_{ses}_task-rest_run-01_bold.json", "A29")
                    sc = _load_json(p)
                    sc["PhaseEncodingDirection"] = wrong
                    _save_json(p, sc)

        apply_A30 (gradient table mutations section, beside apply_A12):

            def apply_A30(out_dir: Path, sub: str, spec: dict) -> None:
                """Negate one bvec row, mirroring diffusion gradients on that axis.

                The file stays dimensionally valid and every vector stays unit-norm, so
                no validator complains. Tractography is mirrored.
                """
                axis = spec["details"]["axis"]
                for ses in spec["sessions"]:
                    dwi_dir = out_dir / sub / ses / "dwi"
                    for p in _require_glob(dwi_dir, "*.bvec", "A30"):
                        rows = p.read_text().strip().split("\n")
                        vals = [float(v) for v in rows[axis].split()]
                        rows[axis] = " ".join(f"{-v:.6f}" for v in vals)
                        p.write_text("\n".join(rows) + "\n")

        Format note (finding V7): the bvec file is 3 whitespace-separated rows of %.6f. Negating
        in text preserves the existing formatting exactly; round-tripping through numpy would
        rewrite all three rows and change the file's formatting beyond the declared defect.
        Negating -0.000000 yields 0.000000 for b=0 volumes, which is numerically identical.

        apply_A31 (NIfTI header / geometry mutations section):

        SCOPE CORRECTION, recorded because the reasoning behind the wider draft was wrong.
        An earlier draft drifted BOTH tasks, justified by the claim that the acq-func fieldmaps
        are IntendedFor both tasks, so drifting them while leaving enback at 2.4 mm would merely
        relocate the mismatch onto enback. That premise is FALSE. Verified on disk: the two
        acq-func pairs are TASK-SPECIFIC. acq-func run-01 (pepolarfunc01) is IntendedFor enback
        runs only; acq-func run-02 (pepolarfunc02) is IntendedFor rest runs only. Every BOLD run
        is covered by exactly one pair, declared from both directions (the fieldmap names the run
        in IntendedFor; the run names the fieldmap in B0FieldSource). Because rest owns a
        dedicated fieldmap pair, drifting rest plus that pair leaves enback and pepolarfunc01
        internally consistent at 2.4 mm and untouched. The narrow scope is therefore both correct
        and strictly more attributable, and is what is specified here.

            def apply_A31(out_dir: Path, sub: str, spec: dict) -> None:
                """Regenerate the rest protocol at a drifted voxel size.

                A genuine protocol drift, not a mislabelled header: the data really are
                acquired at a different resolution. Rest and its own fieldmap pair move
                together, so the session stays internally consistent and the ONLY defect
                is cross-session geometry drift. Drifting the BOLD without its fieldmap
                would leave the two mismatched, which is A13's declared defect on another
                subject and would give this subject an undeclared second defect. enback
                and its own fieldmap pair are deliberately untouched: they are a separate
                association and nothing about them changes.
                """
                voxel = tuple(spec["details"]["voxel_size"])
                shape = tuple(spec["details"]["shape_spatial"])
                affine = _make_affine(voxel)
                for ses in spec["sessions"]:
                    rng = np.random.default_rng(8801)
                    func_dir = out_dir / sub / ses / "func"
                    fmap_dir = out_dir / sub / ses / "fmap"

                    # Rest BOLD + SBRef at the drifted geometry.
                    for p in _require_glob(
                            func_dir, f"{sub}_{ses}_task-rest_run-*_bold.nii.gz", "A31"):
                        data = structured_noise_4d(shape, BOLD_REST_VOLUMES, rng)
                        _save_nifti(data, affine, BOLD_PARAMS["RepetitionTime"], p)
                    for p in _require_glob(
                            func_dir, f"{sub}_{ses}_task-rest_run-*_sbref.nii.gz", "A31"):
                        data = structured_noise_4d(shape, 1, rng)[..., 0]
                        _save_nifti(data, affine, BOLD_PARAMS["RepetitionTime"], p)

                    # Rest's OWN fieldmap pair only, resolved by association rather than
                    # by hardcoded run index: the pair whose B0FieldIdentifier matches what
                    # the rest runs declare as their B0FieldSource.
                    rest_json = _require_glob(
                        func_dir, f"{sub}_{ses}_task-rest_run-01_bold.json", "A31")[0]
                    b0_ids = set(_load_json(rest_json).get("B0FieldSource", []))
                    drifted_fmaps = []
                    for p in sorted(fmap_dir.glob(f"{sub}_{ses}_acq-func_*_epi.json")):
                        if not set(_load_json(p).get("B0FieldIdentifier", [])) & b0_ids:
                            continue
                        drifted_fmaps.append(p)
                        nii = p.with_suffix("").with_suffix(".nii.gz")
                        data = structured_noise_4d(
                            shape, FMAP_EPI_PARAMS["n_volumes"], rng)
                        _save_nifti(data, affine,
                                    FMAP_EPI_PARAMS["RepetitionTime"], nii)
                    if not drifted_fmaps:
                        raise RuntimeError(
                            f"A31: declared target missing: no acq-func fieldmap under "
                            f"{fmap_dir} declares B0FieldIdentifier in {sorted(b0_ids)}")

                    # SliceThickness on the drifted sidecars only.
                    for p in sorted(
                            func_dir.glob(f"{sub}_{ses}_task-rest_run-*.json")) + drifted_fmaps:
                        sc = _load_json(p)
                        sc["SliceThickness"] = voxel[2]
                        _save_json(p, sc)

        Resolving rest's fieldmap by B0FieldIdentifier rather than by the run-02 filename is
        deliberate. The run index of rest's fieldmap is an artefact of generation order; hardcoding
        it would silently drift the WRONG pair (enback's) if that order ever changed. The
        association is the invariant, the filename is not.

        A31 rewrites the images in place rather than calling generate_bold, because generate_bold
        also rewrites sidecars from scratch (SliceTiming, B0FieldSource, TaskName) and would
        discard any sidecar mutation an earlier adversary applied. In-place regeneration confines
        A31 to the declared geometry defect. Importing generate_bold here would also create an
        avoidable second adversaries -> modalities coupling beyond the two helpers already shared.

        The acq-dwi fieldmap is deliberately NOT drifted: it belongs to the diffusion protocol
        (IntendedFor the dwi run), not the functional one, and drifting it would exceed the
        declared defect.
      </spec>
      <dependencies>C1 (DRIFT_* constants; run-count constants)</dependencies>
      <risk>
        medium - A31 is the only adversary that regenerates image data at a new shape, and it is
        the largest single write in the matrix (both tasks plus fieldmaps for one session).
        A29 and A30 are small and localized. A30's text-level negation is chosen specifically to
        avoid reformatting the file beyond the declared defect.
      </risk>
      <rollback>Restore adversaries.py from the pre-build backup.</rollback>
      <acceptance>
        A29: sub-003 ses-01 rest run-01 BOLD sidecar has PhaseEncodingDirection "j-" while its
        acq-func fieldmap sidecars retain "j"/"j-" unchanged.
        A30: sub-004 ses-01 .bvec row 0 is the exact negation of the pre-adversary row 0; rows 1
        and 2 are byte-identical to before; column count is unchanged and matches the .bval count.
        A31: on sub-005 ses-03, the rest BOLD + SBRef NIfTIs AND the acq-func fieldmap pair whose
        B0FieldIdentifier the rest runs cite (pepolarfunc02) have shape (86, 86, 58) at 2.5 mm
        pixdim; the enback BOLD/SBRef, the enback fieldmap pair (pepolarfunc01), the dwi, and the
        acq-dwi fieldmap all remain (90, 90, 60) / (140, 140, 81) at their baseline voxel sizes;
        ses-01 and ses-02 are untouched.
      </acceptance>
    </change>

    <change id="C5" priority="P0" source_item="adversaries.py: rewrite ADVERSARY_MATRIX to the locked 13-subject table">
      <file path="tools/simulated_bids/adversaries.py" action="modify" />
      <description>
        Replace ADVERSARY_MATRIX with the locked 13-subject roster: no pure-clean subject, max 5
        adversaries per subject (down from 7), gradation 1,1,1,1,2,2,3,3,3,4,4,5,5, 35 instances
        across 31 types. The brainstorm locked subject-to-adversary but not session-to-adversary,
        so session assignments and per-subject details are derived here under the collision rules
        below and are presented for review as part of this plan.
      </description>
      <spec>
        Session-assignment rules applied, in order of precedence:
          1. Session-level defects (A1 missing, A2 empty) take one session; every other adversary
             on that subject targets a surviving session.
          2. No two adversaries on the same subject may write the same file on the same session.
             Per finding V5, A3-rest and A5 (enback-only) do not collide even when co-sessioned.
          3. A15 is placed on a session no other JSON-writing adversary touches, AND kept last in
             its subject's list. Either alone would suffice; both are used because A15's defect is
             erasable by any later JSON round-trip and the cost of redundancy here is zero.
          4. Where an adversary keeps its previous subject, its previous session and details are
             preserved verbatim.

        Replace the entire ADVERSARY_MATRIX literal with:

            ADVERSARY_MATRIX = {
                # --- Mild (1 adversary): the four highest-impact silent killers, each in
                # complete isolation. One defect per subject means any downstream failure
                # here has exactly one possible explanation.
                "sub-001": [
                    {"id": "A20", "sessions": ["ses-01"], "target": "slicetiming_milliseconds"},
                ],
                "sub-002": [
                    {"id": "A26", "sessions": ["ses-01"], "target": "ffs_orientation"},
                ],
                "sub-003": [
                    {"id": "A29", "sessions": ["ses-01"], "target": "pe_direction_flip_rest",
                     "details": {"wrong": "j-", "correct": "j"}},
                ],
                "sub-004": [
                    {"id": "A30", "sessions": ["ses-01"], "target": "bvec_x_sign_flip",
                     "details": {"axis": 0}},
                ],
                # --- Low (2 adversaries)
                "sub-005": [
                    {"id": "A31", "sessions": ["ses-03"], "target": "voxel_size_drift_func",
                     "details": {"voxel_size": [2.5, 2.5, 2.5],
                                 "shape_spatial": [86, 86, 58]}},
                    {"id": "A16", "sessions": ["ses-02"], "target": "t1w_pixdim4_mismatch",
                     "details": {"pixdim4": 0.0, "json_tr": 2.5}},
                ],
                "sub-006": [
                    {"id": "A24", "sessions": ["ses-02", "ses-03"], "target": "tr_drift_rest_bold",
                     "details": {"ses-02": 0.801, "ses-03": 0.802}},
                    {"id": "A17", "sessions": ["ses-01"], "target": "t1w_qform_sform_disagree",
                     "details": {"z_offset_mm": 0.5}},
                ],
                # --- Moderate (3 adversaries)
                "sub-007": [
                    {"id": "A4", "sessions": ["ses-01"], "target": "scan_restart_rest",
                     "details": {"truncated_volumes": 140, "extra_run": 3}},
                    {"id": "A8", "sessions": ["ses-02"], "target": "wrong_mb_enback",
                     "details": {"wrong_mb": 4}},
                    {"id": "A21", "sessions": ["ses-03"],
                     "target": "enback_run01_missing_taskname"},
                ],
                "sub-008": [
                    {"id": "A10", "sessions": ["ses-01"],
                     "target": "bold_rest_run01_missing_ees"},
                    {"id": "A22", "sessions": ["ses-02"], "target": "intendedfor_path_format",
                     "details": {"format": "bids_uri"}},
                    {"id": "A23", "sessions": ["ses-03"], "target": "fmap_trt_mismatch",
                     "details": {"fmap_trt": 0.06, "bold_trt": 0.045391}},
                ],
                "sub-009": [
                    {"id": "A12", "sessions": ["ses-01"], "target": "bval_bvec_mismatch",
                     "details": {"bval_count": 102, "bvec_count": 103}},
                    {"id": "A18", "sessions": ["ses-02"], "target": "dwi_scl_slope_nan"},
                    {"id": "A13", "sessions": ["ses-03"], "target": "fmap_geometry_mismatch",
                     "details": {"fmap_voxel": 2.5}},
                ],
                # --- High (4 adversaries)
                "sub-010": [
                    {"id": "A3", "sessions": ["ses-01"], "target": "protocol_typo_rest",
                     "details": {"wrong": "ABCD_fMRI_rset", "correct": "ABCD_fMRI_rest"}},
                    {"id": "A5", "sessions": ["ses-01", "ses-02"], "target": "protocol_rename",
                     "details": {"ses-01_desc": "ABCD_fMRI_faces",
                                 "ses-02_desc": "ABCD_fMRI_emotion"}},
                    {"id": "A27", "sessions": ["ses-02"], "target": "extra_localizer_series"},
                    {"id": "A7", "sessions": ["ses-03"], "target": "stale_extra_series",
                     "details": {"desc": "OtherStudy_motor_bold"}},
                ],
                # A15 MUST be applied last for this subject: it injects a duplicate JSON key
                # via raw text substitution, and any later adversary that json.load/json.dump's
                # the same sidecar collapses it. It is additionally placed on ses-03, which no
                # other adversary here touches.
                "sub-011": [
                    {"id": "A11", "sessions": ["ses-01"], "target": "surviving_phi_field",
                     "details": {"field": "PatientSex", "value": "F"}},
                    {"id": "A19", "sessions": ["ses-02"], "target": "mixed_dtype_across_runs",
                     "details": {"run01_dtype": "float32", "run02_dtype": "int16"}},
                    {"id": "A28", "sessions": ["ses-01", "ses-02", "ses-03"],
                     "target": "locale_decimal_participants_tsv"},
                    {"id": "A15", "sessions": ["ses-03"],
                     "target": "duplicate_sidecar_key_casing"},
                ],
                # --- Severe (5 adversaries)
                "sub-012": [
                    {"id": "A1", "sessions": ["ses-02"], "target": "missing_session"},
                    {"id": "A9", "sessions": ["ses-01"], "target": "missing_T2w"},
                    {"id": "A6", "sessions": ["ses-01"], "target": "mixed_patient_ids",
                     "details": {"id_a": "SIM_PT_012A", "id_b": "SIM_PT_012B"}},
                    {"id": "A14", "sessions": ["ses-03"], "target": "orphan_sbref"},
                    {"id": "A25", "sessions": ["ses-03"], "target": "duplicate_rest_run",
                     "details": {"src_run": 2, "dst_run": 3}},
                ],
                "sub-013": [
                    {"id": "A2", "sessions": ["ses-03"], "target": "empty_session"},
                    {"id": "A27", "sessions": ["ses-01"], "target": "extra_localizer_series"},
                    {"id": "A3", "sessions": ["ses-01"], "target": "protocol_typo_rest",
                     "details": {"wrong": "ABCD_fMRI_rest_", "correct": "ABCD_fMRI_rest"}},
                    {"id": "A5", "sessions": ["ses-01", "ses-02"], "target": "protocol_rename",
                     "details": {"ses-01_desc": "ABCD_fMRI_faces",
                                 "ses-02_desc": "ABCD_fMRI_emotion"}},
                    {"id": "A7", "sessions": ["ses-02"], "target": "stale_extra_series",
                     "details": {"desc": "OtherStudy_dti_bold"}},
                ],
            }

        Two call-site changes follow from the run-count reduction (finding V6), plus a
        fieldmap-symmetry change that applies to both run-creating adversaries.

        FIELDMAP SYMMETRY (user-approved during planning; applies to A4 and A25). Both A4's
        re-acquired run and A25's duplicate run copy the run-01 (or run-02) BOLD sidecar, which
        carries a B0FieldSource naming the covering fieldmap pair. But nothing adds the new run
        to that fieldmap's IntendedFor, so the association is declared from one side only: the
        new run points at the fieldmap, the fieldmap does not point back. Verified on disk against
        the current generator output (sub-007 ses-01 rest_run-04 declares B0FieldSource
        pepolarfunc02, which does not name it in IntendedFor). This is an undeclared second defect
        on subjects whose adversary declares only a restart / duplicate. The fix restores symmetry
        so each adversary materializes exactly its declared defect.

        Add a shared helper to the "Shared helpers" section, below _require_rglob:

            def _add_to_fieldmap_intendedfor(func_dir: Path, fmap_dir: Path, sub: str,
                                             ses: str, new_bold_nii: str, aid: str) -> None:
                """Append a newly-created BOLD run to its covering fieldmap's IntendedFor.

                A run created by an adversary declares B0FieldSource pointing at a fieldmap
                pair, but the pair's IntendedFor is written once at generation and does not
                know about the new run. Left alone, that one-sided association is an
                undeclared defect. This resolves the pair by B0FieldIdentifier (the
                invariant), not by run index (an artefact of generation order), and adds the
                run's subject-relative path to every member of that pair.
                """
                stem = new_bold_nii[:-len(".nii.gz")] if new_bold_nii.endswith(".nii.gz") \
                    else new_bold_nii
                src_sidecar = func_dir / f"{stem}.json"
                b0_ids = set(_load_json(src_sidecar).get("B0FieldSource", []))
                if not b0_ids:
                    return
                rel = f"{ses}/func/{new_bold_nii}"
                for p in sorted(fmap_dir.glob(f"{sub}_{ses}_acq-func_*_epi.json")):
                    sc = _load_json(p)
                    if not set(sc.get("B0FieldIdentifier", [])) & b0_ids:
                        continue
                    intended = sc.get("IntendedFor", [])
                    if rel not in intended:
                        intended.append(rel)
                        sc["IntendedFor"] = intended
                        _save_json(p, sc)

        The subject-relative path form `{ses}/func/{filename}` matches the IntendedFor convention
        the generator already writes (verified: existing entries read
        "ses-01/func/sub-001_ses-01_task-rest_run-01_bold.nii.gz"). SBRef is intentionally not
        added, consistent with the pipeline's own convention that fieldmap IntendedFor lists BOLD
        runs, not their SBRefs (established while reviewing bids_recon/__main__.py, where the
        target filter admits only Role.BOLD and Role.DWI).

        apply_A25: parameterise the run indices instead of hardcoding run-02 -> run-04 (with two
        rest runs, a run-04 duplicate leaves a gap at run-03 no acquisition explains), AND call
        the symmetry helper for the created run.

            src_run = spec["details"]["src_run"]
            dst_run = spec["details"]["dst_run"]
            ...
                    src_stem = f"{sub}_{ses}_task-rest_run-{src_run:02d}{suffix}"
                    dst_stem = f"{sub}_{ses}_task-rest_run-{dst_run:02d}{suffix}"
            # after the copy loop, once the dst _bold.json exists on disk:
            _add_to_fieldmap_intendedfor(
                func_dir, out_dir / sub / ses / "fmap", sub, ses,
                f"{sub}_{ses}_task-rest_run-{dst_run:02d}_bold.nii.gz", "A25")

        The docstring's rationale is preserved and updated to name src_run rather than run-02, and
        to note that the duplicate is registered with its covering fieldmap.

        apply_A4: extra_run now reads 3 from the matrix (no index change needed), AND the extra
        run is registered with its covering fieldmap. After the existing block that writes the
        extra run's NIfTI and its sidecar:

            _add_to_fieldmap_intendedfor(
                func_dir, out_dir / sub / ses / "fmap", sub, ses,
                f"{extra_stem}.nii.gz", "A4")

        where extra_stem is the existing local variable
        f"{sub}_{ses}_task-rest_run-{extra_run:02d}_bold". A4's declared defect (a truncated run
        plus a complete re-acquisition) is unchanged; the helper only closes the association the
        re-acquisition would have had if it were a real scan.

        Do NOT change apply_A15's implementation or the _assert_A15_survived post-condition
        checker; both are keyed by adversary ID, not by subject, and the checker is what catches
        a mis-placement of A15 here.
      </spec>
      <dependencies>C4 (A29/A30/A31 must exist before the matrix names them; apply_adversaries resolves via globals() at call time, so this ordering is for coherence rather than import safety)</dependencies>
      <risk>
        high - The largest semantic change in the plan. Every adversary except those on sub-005
        and sub-006 changes subject, session, or both, so the entire run-local verification
        performed against the previous matrix is invalidated and must be redone. The collision
        analysis above is reasoned from the implementations (finding V5), not executed; the
        corrected verifier at 31/31 is what proves it. Risk is mitigated by the requirement
        guards from the prior build: a mis-assigned session raises by adversary ID rather than
        silently no-opping.
      </risk>
      <rollback>Restore adversaries.py from the pre-build backup.</rollback>
      <acceptance>
        ADVERSARY_MATRIX has exactly 13 subjects sub-001..sub-013; per-subject counts are
        1,1,1,1,2,2,3,3,3,4,4,5,5 in that order; the union of ids is exactly A1..A31 (31 types);
        total instances = 35; A15 is the last entry of sub-011; no subject has zero adversaries.
        Fieldmap symmetry: after A4 on sub-007 and A25 on sub-012, the created rest run appears in
        the IntendedFor of the acq-func fieldmap pair it cites via B0FieldSource, so no BOLD run
        declares a fieldmap that does not declare it back.
      </acceptance>
    </change>

    <change id="C6" priority="P1" source_item="manifest.py: profile-aware manifest, new descriptions, hardcoded strings, seed">
      <file path="tools/simulated_bids/manifest.py" action="modify" />
      <description>
        Make the README describe the dataset it is actually in. Run under the clean profile today,
        write_manifest emits an adversary matrix describing 13 subjects and 31 defects into a
        dataset that has neither. Also correct the three strings the redesign falsifies
        (finding V4) and record each profile's seed.
      </description>
      <spec>
        Add three entries to ADVERSARY_DESCRIPTIONS:

            "A29": ("Phase-encoding direction flipped on rest run-01 BOLD; the fieldmap pair "
                    "still declares the true polarity, so distortion correction applies the "
                    "warp backwards instead of failing"),
            "A30": ("Diffusion gradient x-component negated in the bvec file; dimensionally "
                    "valid and unit-norm, so nothing warns, but tractography is mirrored"),
            "A31": ("Voxel-size drift across sessions: the ses-03 functional protocol (both "
                    "tasks and their acq-func fieldmaps) is acquired at 2.5 mm while ses-01 "
                    "and ses-02 are at 2.4 mm. The session is internally consistent, so only "
                    "cross-session comparison reveals it"),

        Change write_manifest's signature to take the profile:

            def write_manifest(out_dir: Path, profile_name: str, profile: dict) -> None:

        Structure the body into three parts:
          1. Shared sections (dataset name from profile["dataset_name"], modality inventory,
             session structure, generation instructions). The generation instruction line must
             show the actual invocation including the profile:
             `python -m tools.simulated_bids <out_dir> --profile {profile_name}`
          2. A "Reproducibility" section, emitted for BOTH profiles, recording
             `profile={profile_name}` and `seed={profile['seed']}`. This is required, not
             cosmetic: /test consumes both datasets as a regression oracle, so the seed that
             produced them must be discoverable from the dataset itself.
          3. The adversary sections (summary bullets, matrix table, per-subject detail), emitted
             ONLY when profile["apply_adversaries"] is true. When false, emit instead a short
             statement that this dataset carries no seeded defects and names its counterpart
             profile as the adversarial fixture.

        Within the adversary branch, derive every count and roster from data rather than
        hardcoding (finding V4). Replace line 51's "- 10 subjects (sub-001 through sub-010), 3
        sessions each" with a computed line over profile["subject_ids"] and SESSIONS. Delete
        line 52 ("- sub-001: clean baseline (no adversaries)") outright: it is now false, since
        no subject is clean. Delete the literal `| sub-001 | Clean | (none) |` row at line 71 for
        the same reason; the table is built by iterating ADVERSARY_MATRIX and every subject now
        appears there on its own.

        Replace the "sub-002 through sub-010: adversarial examples with graded severity" line
        with a computed severity summary derived from the per-subject instance counts, so it
        cannot go stale against a future matrix edit.
      </spec>
      <dependencies>C1 (PROFILES), C5 (final matrix)</dependencies>
      <risk>
        low - Documentation output only; no generated image or sidecar depends on it. The
        signature change has exactly one call site, updated by C3.
      </risk>
      <rollback>Restore manifest.py from the pre-build backup.</rollback>
      <acceptance>
        The clean dataset's README contains no adversary table, no per-subject defect list, and no
        reference to sub-0xx; it states it carries no seeded defects and records profile=clean and
        seed=1729. The adversarial README lists 13 subjects and 31 adversary types with no "clean
        baseline" line and no literal clean table row, and records profile=adversarial and
        seed=42. Neither README contains the string "sub-001 | Clean".
      </acceptance>
    </change>

  </changes>

  <execution_order>
    C1, C2, C4, C5, C6, C3

    Rationale. C1 first: PROFILES, the run-count constants, and the drift geometry underpin every
    other change. C2, C4, C5, C6 next: each edits a file C3 will call into, so landing them first
    means C3's signature updates match what already exists rather than racing them. C4 before C5
    because the matrix names the three new adversaries. C6 after C5 because the manifest derives
    its counts from the final matrix. C3 LAST, deliberately: it is the only change that rewrites
    the call sites for the new signatures in scaffold and manifest, so placing it last means
    every intermediate state has consistent callers, and the one moment the package is
    internally inconsistent (C1 deletes N_SUBJECTS while __main__ still imports it) is closed by
    the same change that ends the batch.

    Note the intermediate state between C1 and C3 will not import: __main__ imports N_SUBJECTS,
    which C1 deletes. This is unavoidable in any order that keeps config first, and it fails
    loudly at import rather than silently. Nothing runs between changes.

    Dispatch partitioning: C1 = config.py; C2 = scaffold.py; C4 + C5 = adversaries.py (MUST be
    sequential, same file); C6 = manifest.py; C3 = __main__.py. C1, C2, C6 touch disjoint files
    and could be dispatched concurrently, but C6 depends on C5's matrix content, so the safe
    concurrency is: C1 and C2 together, then C4 -> C5 -> C6, then C3.
  </execution_order>

  <rollback_strategy>
    This project is NOT a git repository (verified in the prior implement session:
    `git rev-parse --show-toplevel` returns "fatal: not a git repository"). Rollback is
    file-backup based and the backup MUST be taken before the first edit or it does not exist.

    Before C1, copy all five target files to a timestamped backup directory:

        mkdir -p sandbox/backups/pre_implement_20260717_101506
        cp tools/simulated_bids/config.py \
           tools/simulated_bids/scaffold.py \
           tools/simulated_bids/__main__.py \
           tools/simulated_bids/adversaries.py \
           tools/simulated_bids/manifest.py \
           sandbox/backups/pre_implement_20260717_101506/

    Record SHA-256 of each original in the build report so a restore is verifiable.

    To roll back, copy the file back. Restoring is an overwrite of an existing file and therefore
    requires explicit per-invocation user approval under the destructive-operations policy; the
    build must surface the request rather than restore unilaterally.

    Granularity: per-file, not per-change. C4 and C5 both touch adversaries.py, so restoring that
    file reverts both. Per-change rollback is unavailable without git; dispatch in the listed
    order and halt at the first failure so at most one change is in flight.

    Note the prior session's backup at sandbox/backups/pre_implement_20260717_082844/ predates
    the int16 baseline and the guard sweep. It is NOT a valid rollback target for this batch;
    restoring from it would silently revert the previous build. Use only the new directory.
  </rollback_strategy>

  <post_build>
    Not part of this plan; recorded so the sequencing is explicit and nothing is silently dropped.

    1. sandbox/smoke_run.py invokes main() through sys.argv and will break once --profile is
       required. It also rescales `truncated_volumes` and patches volume counts, both of which
       interact with the new constants. It is a sandbox driver, outside this spec's file scope,
       and needs updating before any smoke run.
    2. sandbox/verify_dataset.py carries three known checker bugs (the A5 check targets task-rest
       though A5 targets task-emotionalnback; the A7 check filters out the task-otherstudy file
       its adversary creates; the A15 regex assumes 2-space JSON indent where the actual is 4).
       It must also read dtype via dataobj.slope rather than header["scl_slope"], and extend from
       28 to 31 adversaries and from 10 to 13 subjects. The bar is 31/31.
    3. /test for the generator package. This plan runs no tests.
    4. /run-local to request the filesystem grant for ~/simulated-bids/ (surfaced for explicit
       user approval, never self-granted) and generate both profiles.
  </post_build>
</implement_plan>
