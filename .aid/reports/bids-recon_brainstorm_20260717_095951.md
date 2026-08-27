<brainstorm_report>
  <meta project="bids-recon" mode="brainstorm" timestamp="2026-07-17T09:59:51-04:00" />

  <context_files>
    <file path="tools/simulated_bids/config.py" relevance="Scale-driving constants: shapes, volume counts, DEMOGRAPHICS (10 rows), SESSIONS, N_SUBJECTS" />
    <file path="tools/simulated_bids/adversaries.py" relevance="ADVERSARY_MATRIX distribution and all 28 apply_A{n} implementations" />
    <file path="tools/simulated_bids/__main__.py" relevance="Generation flow; subject enumeration; hardcoded run-count loops and IntendedFor construction" />
    <file path="tools/simulated_bids/scaffold.py" relevance="participants.tsv / sessions.tsv writers, sourced from DEMOGRAPHICS" />
    <file path="tools/simulated_bids/manifest.py" relevance="ADVERSARY_DESCRIPTIONS and README generation; hardcodes subject counts" />
    <file path="bids-recon_implement_build_20260717_085620.md" relevance="Immediately prior build: int16 baseline, guard sweep, A25 repoint, A15 relocation machinery" />
  </context_files>

  <topics>

    <topic id="T1" title="Dataset purpose split: fixture vs workload">
      <summary>
        The existing dataset is 9/10 subjects adversarial, 24/30 subject-sessions touched, and exactly
        ONE fully clean subject. For testing analysis pipelines it therefore serves at N=1, which is
        not a degraded capability but an absent one. The dataset is a mutant corpus, not a workload:
        one defect per unit, deterministically labeled, every defect class represented once. That is
        the correct design for measuring fault detection and the wrong design for measuring behavior
        on typical data.
      </summary>
      <research>
        Framing anchored in three literatures rather than analogy. Fault-seeding / mutation testing
        (DeMillo, Lipton and Sayward 1978; surveyed in Jia and Harman, IEEE TSE 37(5), 2011) supplies
        the corpus concept and the one-fault-per-unit convention that exists to prevent fault coupling.
        Spectrum bias (Ransohoff and Feinstein, NEJM 299:926, 1978) supplies the reason performance
        measured on a case-enriched sample does not transfer to a different case-mix. Outcome-dependent
        (case-control) sampling supplies the formal statement: relative quantities are recoverable from
        enriched samples, absolute ones are not.
      </research>
      <approaches>
        <approach id="A1" label="Two datasets" feasibility="high" risk="low">
          <description>Keep the adversarial fixture as the mutant corpus; add a separate clean cohort as the realistic workload. The generator already builds every subject clean in phase 1 and only then applies adversaries in phase 3, so a clean cohort is the existing code path with phase 3 skipped.</description>
          <pros>Each dataset serves the purpose it is designed for; no redesign of the fixture; near-zero incremental generator complexity.</pros>
          <cons>Two datasets to store, generate, and keep in sync.</cons>
        </approach>
        <approach id="A2" label="Dilute the fixture" feasibility="low" risk="high">
          <description>Increase N and lower defect prevalence toward a realistic rate.</description>
          <cons>Still not a realistic case-mix; multiplies disk cost; destroys the one-defect-per-unit property that makes the fixture useful.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        User directive: split into two datasets. The adversarial dataset stays as designed; a clean
        version is added. Sizing for both reopened under a disk budget, which drives T3 through T7.
      </decision>
    </topic>

    <topic id="T2" title="Terminating vs propagating defects (the governing lens)">
      <summary>
        User-supplied reframing that governs matrix composition. A TERMINATING defect is one whose only
        correct resolution is "exclude this unit"; once detected and logged, the unit leaves the pipeline
        and the test surface is a single bit. A PROPAGATING defect does not trigger exclusion, passes
        silently into analysis, and corrupts the result. Only the second class gives a post-reconstruction
        pipeline anything to be tested against, and it is where the scientific risk lives because nothing
        warns you.
      </summary>
      <research>
        Classification performed against all 28 implemented adversaries. Result: 4 unambiguously
        terminating (missing session, empty session, missing modality, missing BOLD run), 5
        pipeline-dependent (protocol typo, mixed PatientIDs, stale foreign series, missing TaskName,
        extra localizer), 19 unambiguously propagating. The matrix is therefore already ~68%
        propagation-dominant, which contradicted the initial concern that it was exclusion-heavy.
        Caveat recorded: the surviving-PHI adversary is a compliance defect, not an analytic one; it
        reaches downstream but corrupts nothing.
      </research>
      <approaches>
        <approach id="A1" label="Keep all 28, add missing silent killers" feasibility="high" risk="low">
          <description>Retain the 4 terminating adversaries (they cost near-zero and two of them remove data) and add the absent propagating classes.</description>
          <pros>Strengthens the class that matters without discarding verified, working adversaries.</pros>
        </approach>
        <approach id="A2" label="Prune the terminating four" feasibility="med" risk="med">
          <cons>Discards genuinely realistic scenarios and invalidates prior run-local verification against those subjects.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        Keep all 28; add three missing silent killers. Coverage gap identified within the propagating
        class, not in the terminating/propagating ratio.
      </decision>
    </topic>

    <topic id="T3" title="Run counts per session">
      <summary>
        BOLD volumes are 82.5% of a session's bytes (rest 50.0%, enback 32.2%); DWI is 14.7%; anatomicals
        are 2.1%. Neither subject count nor session count is the dominant lever. Measured per-session cost
        at the new int16 baseline: 1.77 GB at 3 rest + 2 enback.
      </summary>
      <decision status="decided" chosen="2 rest + 2 enback">
        User directive: drop to 2 rest runs and 2 enback runs. Retains robustness testing against
        multiple-run BOLD sequences while removing one rest run per session. Per-session cost falls to
        1.47 GB (rest 904.6 -> 602.9 MB).
      </decision>
    </topic>

    <topic id="T4" title="Volume counts: full-scale vs reduced">
      <summary>
        Whether the fixture needs realistic run lengths turns entirely on whether it is ever pushed
        through a downstream analysis pipeline. 26 of 28 defects are scale-free; the two scale-coupled
        ones are already proven rescalable by the existing smoke driver.
      </summary>
      <research>
        The decisive argument is fault attribution, not realism. A 40-volume run is 32 seconds of data;
        pushed through preprocessing or a first-level GLM it breaks for reasons unrelated to the seeded
        defect (confound regression, aCompCor, and prewhitening all want timepoints). Every downstream
        failure would then be confounded with "the run was too short," destroying attribution. This is the
        same coupling logic that makes stacking many adversaries on one subject a problem, reintroduced
        by the back door. Note the residual distinction: a short fixture still shows THAT a defect reaches
        downstream, but not HOW WRONG the results get, and not with a clean attribution.
      </research>
      <approaches>
        <approach id="A1" label="Both full-scale" feasibility="high" risk="low">
          <description>Fixture and clean cohort both at 383 rest / 370 enback volumes.</description>
          <pros>Every downstream failure attributable to its seeded defect; single config; fixture usable end-to-end.</pros>
          <cons>Costs ~38 GB more than a shrunk fixture.</cons>
        </approach>
        <approach id="A2" label="Shrink the fixture" feasibility="high" risk="med">
          <cons>The 19 propagating adversaries could only ever be observed at the curation boundary, never in a real analytic result; downstream failures confounded with run length.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        User: the adversarial dataset is used within /test to design tests, troubleshoot solutions, and
        verify fixes; the clean dataset is used within /run-local and /test for typical end-to-end runs.
        "Both will be used at almost every analytic stage." Both therefore reach downstream and both stay
        full-scale. The orchestrator's initial recommendation (shrink the fixture) was reversed on the
        attribution argument before the decision was taken.
      </decision>
    </topic>

    <topic id="T5" title="Clean cohort sizing">
      <summary>
        Sizing driven by the user's clarification that group-level analyses are the LEAST likely use;
        almost all testing with both datasets is at the WITHIN-SUBJECT level. That invalidated two
        earlier lines of argument (a demographic-cell floor of N=6, and an N>=20 floor to keep mixed-model
        convergence failures attributable), both of which answered a group-level question that is not
        being asked.
      </summary>
      <research>
        Under within-subject testing the unit of test is the run or subject-session. Each subject already
        carries 12 BOLD runs, 3 DWI, 3 T1w/T2w pairs and 9 fieldmaps across 3 sessions. Additional subjects
        buy only independent noise realizations and enough units to exercise subject-level parallel
        dispatch rather than falling back to serial.
      </research>
      <decision status="decided" chosen="4 subjects x 3 sessions">
        4 subjects x 3 sessions = 12 units = 17.6 GB. 48 BOLD runs of within-subject surface across four
        independent noise realizations. N=2 was rejected: it cannot separate "works for subjects" from
        "works for this subject" and barely exercises a queue.
      </decision>
    </topic>

    <topic id="T6" title="Identity, seeds, and independence">
      <summary>
        The clean cohort was described as "independent." Generated with the fixture's seed it would be
        byte-identical to the fixture's pre-adversary state, which is not independent in any sense.
      </summary>
      <decision status="decided" chosen="distinct IDs, distinct pinned seeds">
        Clean cohort takes subject IDs sub-101 through sub-104 (distinct ID space, so a clean subject can
        never be confused with a fixture subject in logs, derivatives, or a merged analysis). Fixture keeps
        seed 42; clean cohort uses seed 1729. Both seeds recorded in each dataset's README. Bit
        reproducibility matters because /test consumes these as a regression oracle.
      </decision>
    </topic>

    <topic id="T7" title="Fixture matrix redesign">
      <summary>
        Three constraints forced a full redesign: the three new adversaries need placement; no pure-clean
        subject may remain in the fixture (sub-001 currently carries zero); and the worst offenders
        (7 and 6 adversaries) must come down while the mild-to-severe gradation is preserved.
      </summary>
      <research>
        Fault-coupling rationale: mutation testing seeds one fault per program copy precisely so a failure
        can be attributed to a specific defect. The current stacking (up to 7 per subject) violates that and
        is the mechanism that produced the A25 defect (an earlier adversary deleted the file a later one
        needed) and the A15 erasure hazard (a JSON round-trip collapses a duplicate key).
      </research>
      <decision status="decided" chosen="13 subjects, gradation 1,1,1,1,2,2,3,3,3,4,4,5,5">
        35 instances across 31 types; 4 reuses (A3, A5, A7, A27), all on the two severe subjects where a
        repeat instance is most defensible. Max per subject falls from 7 to 5; no subject carries zero.
        The four single-defect subjects deliberately carry the four highest-impact silent killers in
        complete isolation, where attribution is perfect.

        FULL LOCKED MATRIX:
          sub-001  1  A20 SliceTiming in ms                                          [silent killer, isolated]
          sub-002  1  A26 FFS orientation flip                                       [silent killer, isolated]
          sub-003  1  A29 PED polarity flip                              *NEW*       [silent killer, isolated]
          sub-004  1  A30 bvec sign/frame error                          *NEW*       [silent killer, isolated]
          sub-005  2  A31 voxel-size drift *NEW*, A16 pixdim4-vs-JSON TR             [A31 spans sessions]
          sub-006  2  A24 TR drift, A17 qform/sform disagree                         [A24 spans sessions]
          sub-007  3  A4 scan restart, A8 wrong multiband, A21 missing TaskName
          sub-008  3  A10 missing EES, A22 IntendedFor URI, A23 fmap TRT mismatch    [distortion-correction cluster]
          sub-009  3  A12 bval/bvec mismatch, A18 scl_slope NaN, A13 fmap geometry   [A12/A18 hit different dwi files]
          sub-010  4  A3 protocol typo, A5 protocol rename, A7 stale series, A27 extra localizer  [A5 spans sessions]
          sub-011  4  A11 PHI field, A19 mixed dtype, A28 decimal comma, A15 duplicate key (MUST BE LAST)
          sub-012  5  A1 missing session, A9 missing T2w, A14 orphan SBRef, A25 duplicate run, A6 mixed PatientIDs
          sub-013  5  A2 empty session, A27 extra localizer, A7 stale series, A3 protocol typo, A5 protocol rename

        Noted consequences: A15 relocates from sub-009 to sub-011 and MUST remain last in that subject's
        list, because A11 round-trips JSON on the same session and would collapse the duplicate key; the
        comment and placement built in the prior implement session hardcode sub-009 and must move with it.
        The post-condition assert added in that session is what catches this if it is done wrong. The two
        severe subjects each lose a session to a session-level defect, so each carries four adversaries
        across two surviving sessions rather than five across three.
      </decision>
    </topic>

    <topic id="T8" title="Three new silent-killer adversaries">
      <summary>
        Coverage gap within the propagating class. Three classic silent killers absent from the matrix:
        phase-encoding polarity, diffusion gradient orientation, and longitudinal geometry drift. The
        existing bval/bvec adversary only produces a length mismatch, which errors loudly.
      </summary>
      <decision status="decided" chosen="all three as specified">
        A29: flip PhaseEncodingDirection j -> j- on rest run-01 BOLD sidecar; fieldmaps left correct.
             Distortion correction applies the warp backwards, roughly doubling geometric distortion
             instead of removing it. No error, no warning.
        A30: negate the x-component (first row) of all .bvec entries. Dimensionally valid so nothing
             complains; tractography comes out mirrored left-right.
        A31: regenerate ses-03 rest BOLD at genuine 2.5 mm voxels (shape ~86x86x58) with matching affine
             and SliceThickness. A true protocol drift, not a metadata lie. Single-session analysis looks
             fine; longitudinal registration and averaging silently misalign.
        Each requires an implementation plus a manifest description. None exist today.
      </decision>
    </topic>

    <topic id="T9" title="Generation mechanism and demographics">
      <summary>
        The two datasets differ along four axes at once: subject roster (13 vs 4), ID space (001-013 vs
        101-104), seed (42 vs 1729), and whether adversaries run. Threading four independent switches
        through the CLI is how they drift out of sync.
      </summary>
      <research>
        Verified against the codebase, not assumed. main() enumerates DEMOGRAPHICS directly (N_SUBJECTS is
        vestigial, used only in a print statement). scaffold.write_participants_tsv iterates ALL of
        DEMOGRAPHICS unconditionally, so once that table holds 17 rows both datasets would list every
        subject from the other: a BIDS validity error and a cross-dataset leak. Run counts are hardcoded
        as range(1, 4) / range(1, 3) at four sites including IntendedFor construction. manifest.py
        hardcodes three strings the redesign falsifies.
      </research>
      <decision status="decided" chosen="PROFILES in config, selected by --profile">
        PROFILES = {
          "adversarial": {"subject_ids": [f"sub-{i:03d}" for i in range(1, 14)], "seed": 42,   "apply_adversaries": True},
          "clean":       {"subject_ids": [f"sub-{i:03d}" for i in range(101, 105)], "seed": 1729, "apply_adversaries": False},
        }
        Invocation: python -m tools.simulated_bids OUT --profile clean
        The profile roster is the single source of truth and MUST filter the scaffold writers, not only the
        generation loop.

        Seven new fabricated demographic rows (uniform baseline ages 9-12, +2.0 yr per session, alternating
        sex, rotating handedness), all values invented, none derived from any real participant:
          sub-011  fixture  F  R   9.5   [high tier]
          sub-012  fixture  M  L  11.1   [severe tier]
          sub-013  fixture  F  A  10.7   [severe tier]
          sub-101  clean    F  R   9.4
          sub-102  clean    M  L  10.3
          sub-103  clean    F  A  11.2
          sub-104  clean    M  R  12.1
      </decision>
    </topic>

    <topic id="T10" title="Disk budget and the real constraint">
      <summary>
        Dataset size was never the binding constraint. Preprocessing scratch is.
      </summary>
      <research>
        Research agent R1 (lit_state: consensus). fMRIPrep's own benchmarks page reports 2.30 GB output /
        ~54.8 GB scratch and 5.10 GB output / ~121 GB scratch for two representative datasets under v23.1.4
        (fmriprep.org/en/latest/benchmarks.html). The --level minimal mode introduced in v23.2.0 reduces
        derivatives to ~543-602 MB and scratch to ~1.9-2.9 GB, roughly 10-20x smaller output and >40x
        smaller scratch. ABCD's own fMRIPrep community collection runs --level minimal specifically to
        preserve storage on >10,000 participants (docs.abcdstudy.org). Community reports: ~3.5-5.8 GB per
        subject output, working directories exceeding 200 GB (github.com/NickESouter/fMRIPrepCleanup).
        Honest limitation recorded by the agent: input sizes are not published alongside those benchmarks,
        so no authoritative derivative-to-input RATIO is recoverable; the absolute per-subject figures are
        the usable result.
      </research>
      <decision status="decided" chosen="~75 GB of datasets; scratch flagged as the operational constraint">
        Measured per-session cost 1.47 GB at 2 rest + 2 enback, int16 (gz ratio 0.81, measured not assumed).
        Fixture 13 x 3 = 39 units = 57.3 GB. Clean 4 x 3 = 12 units = 17.6 GB. Total ~75 GB against 420 GB
        free (plus ~7 GB returning from sandbox cleanup).

        Operational consequence, recorded but NOT a dataset-design decision: ~345 GB of remaining headroom
        absorbs one subject at default fMRIPrep settings (121 GB peak scratch) but CANNOT absorb four
        concurrently (~484 GB). Since exercising subject-level parallelism motivated N=4, default-mode
        preprocessing and 4-way parallelism do not coexist on this disk. --level minimal dissolves the
        tension. This is a pipeline-invocation choice for the user, not a change to either dataset.
      </decision>
    </topic>

    <topic id="T11" title="Dataset location">
      <summary>Both datasets must live outside the project for broader local use.</summary>
      <decision status="decided" chosen="~/simulated-bids/{adversarial,clean}/">
        Parent at ~/simulated-bids/ with adversarial/ and clean/ subdirectories. PREREQUISITE, not a
        decision taken here: writing there requires a filesystem grant the user issues. The orchestrator
        will surface the exact grants.sh invocation (path, operations, tools, session-bound vs persistent)
        for explicit approval at generation time. No self-granting under any circumstance.
      </decision>
    </topic>

  </topics>

  <action_items>
    <item priority="P0" target_mode="implement" description="config.py: add PROFILES (adversarial: sub-001..013, seed 42, adversaries on; clean: sub-101..104, seed 1729, adversaries off); add BOLD_REST_RUNS=2 and BOLD_ENBACK_RUNS=2 constants; append the seven fabricated demographic rows; retire or repurpose the vestigial N_SUBJECTS" />
    <item priority="P0" target_mode="implement" description="__main__.py: add --profile; drive subject enumeration from the profile roster rather than the full DEMOGRAPHICS table; replace the four hardcoded run-count sites (range(1,4)/range(1,3) at the generation loops and both IntendedFor constructions) with the run-count constants; make the profile seed authoritative over the --seed default" />
    <item priority="P0" target_mode="implement" description="scaffold.py: filter write_participants_tsv (and any other DEMOGRAPHICS-driven writer) by the active profile roster. Without this, each dataset's participants.tsv lists the other dataset's subjects: a BIDS validity error and a cross-dataset leak" />
    <item priority="P0" target_mode="implement" description="adversaries.py: implement apply_A29 (PhaseEncodingDirection j -> j- on rest run-01 BOLD sidecar), apply_A30 (negate bvec first row), apply_A31 (regenerate ses-03 rest BOLD at genuine 2.5mm voxels with matching affine and SliceThickness), each guarded by the requirement helpers established in the prior build" />
    <item priority="P0" target_mode="implement" description="adversaries.py: rewrite ADVERSARY_MATRIX to the locked 13-subject table in T7. A15 relocates from sub-009 to sub-011 and MUST remain last in that list; the sub-009-specific comment added in the prior build must move with it" />
    <item priority="P1" target_mode="implement" description="manifest.py: add A29/A30/A31 descriptions; correct the three hardcoded strings falsified by the redesign ('10 subjects (sub-001 through sub-010)', 'sub-001: clean baseline (no adversaries)', and the literal clean row in the adversary table); record the profile seed in the generated README" />
    <item priority="P1" target_mode="test" description="sandbox/verify_dataset.py: fix the three known checker bugs (A5 targets task-emotionalnback not task-rest; the A7 check filters out the task-otherstudy file its adversary creates; the A15 regex assumes 2-space JSON indent where the actual is 4); read dtype via dataobj.slope not header['scl_slope']; extend coverage from 28 to 31 adversaries and to the 13-subject roster" />
    <item priority="P1" target_mode="run-local" description="Request the filesystem grant for ~/simulated-bids/ (exact grants.sh invocation surfaced for explicit user approval), then generate both profiles and run the corrected verifier at 31/31" />
  </action_items>

  <next_steps>
    /implement plan against this report. The action items are dependency-ordered: the config profile and
    run-count constants underpin everything; the scaffold filter must land with them or the first clean
    generation produces an invalid participants.tsv; the three new adversaries and the matrix rewrite are
    independent of each other but both depend on the roster existing. Testing and generation follow, in
    that order, and the filesystem grant gates generation.
  </next_steps>
</brainstorm_report>
