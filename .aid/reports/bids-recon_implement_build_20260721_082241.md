<implement_report>
  <meta project="bids-recon" mode="implement" submodule="build" timestamp="2026-07-21T12:22:41Z" />
  <spec_ref>bids-recon_implement_plan_20260717_101506.md</spec_ref>
  <pre_build>
    <backup path="sandbox/backups/pre_implement_20260721_101506/">
      <file path="config.py" sha256="6fb7bdd96c4b4a8ee7e5ec3fc52a57a60ce0da9270dce97308c815d2202b7ed6" />
      <file path="scaffold.py" sha256="032a8ce39829296a6f929843a6be97a09b840373c63c21b0053689f022ab97c0" />
      <file path="__main__.py" sha256="baf5a63ac7d17c7f5d090c478daf30adfb346feb8ce4d60d94f68ed1d215e6a4" />
      <file path="adversaries.py" sha256="2b0e550c6de5a40475c7e6afacdd7cc99442c7ae9f7d57140b34905c042b6c3a" />
      <file path="manifest.py" sha256="a16c2f0194e774bd296738e8916bd4bc39853f547c23ffdb8a25eba79dede294" />
    </backup>
  </pre_build>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/config.py" lines_changed="~25" />
      </files_modified>
      <notes>Added the two-profile configuration dictionary (an adversarial profile with 13 subjects and seed 42; a clean profile with 4 subjects and seed 1729), a lookup helper that raises on an unknown profile name, shared run-count constants for the rest and emotional n-back tasks, and the drift-geometry constants used by the new voxel-size-drift adversary. Removed the now-obsolete single-roster subject-count constant. Independently verified by reading the full landed file; confirmed the profile dictionary and constants exactly match what downstream changes require.</notes>
    </change>
    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/scaffold.py" lines_changed="~20" />
      </files_modified>
      <notes>The dataset-description writer now takes the profile name and profile dictionary, embedding the profile and its seed into the dataset description's provenance field so the two datasets are distinguishable from their metadata alone. The participants-table writer now filters the full demographics table down to a caller-supplied subject roster, since that table spans both profiles and an unfiltered write would leak the other profile's subjects into the current dataset. Independently verified by reading the full landed file; call signatures match exactly what the profile-driven CLI change and the manifest change expect.</notes>
    </change>
    <change id="C4" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/adversaries.py" lines_changed="~70" />
      </files_modified>
      <notes>Added three new silent-killer adversaries, each a propagating defect that triggers no exclusion and corrupts analysis silently: a phase-encoding-direction flip confined to the rest task's first run only (its fieldmap pair still declares the true polarity, so distortion correction applies the warp backwards rather than failing); a diffusion-gradient sign flip performed via exact text substitution rather than a numeric round-trip, to avoid silently rewriting the untouched rows' formatting; and a voxel-size drift that regenerates the rest task's images together with its own fieldmap pair only, deliberately leaving the other task's protocol and fieldmap pair untouched (an initial wider draft was corrected after verifying on disk that the two functional fieldmap pairs are task-specific, not shared). All three independently verified by reading the full landed file: function bodies match the specification verbatim and are placed in their designated sections. Deviation: the dispatched agent also appended references to the three new adversaries onto three existing subjects' entries in the adversary-assignment matrix, which was outside this change's declared scope (matrix authorship belonged exclusively to the following change). This was assessed as harmless rather than a scope violation requiring a halt, because the following change replaces that matrix in its entirety rather than merging into it; independently confirmed post-hoc that no trace of the premature edit survived into the final matrix.</notes>
    </change>
    <change id="C5" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/adversaries.py" lines_changed="~110" />
      </files_modified>
      <notes>Replaced the adversary-assignment matrix in full with the locked 13-subject roster: per-subject instance counts of 1, 1, 1, 1, 2, 2, 3, 3, 3, 4, 4, 5, 5 (35 instances total, spanning all 31 adversary types), with the duplicate-sidecar-key adversary placed last within its subject's list as required, since any later JSON round-trip on the same file would erase its effect. Added a shared helper that appends a newly created BOLD run to its covering fieldmap pair's IntendedFor list, resolved by the declared B0-field association rather than by run index (index is an artifact of generation order, not a stable identifier), and wired it into both the run-duplication adversary and the scan-restart adversary so a run either of them creates can no longer end up with an undeclared, one-sided fieldmap association. Independently verified by reading the full landed file against all locked acceptance criteria: subject count and per-subject counts, full type coverage, instance total, last-position ordering, and the presence and correct call-site usage of the new symmetry helper. Confirmed the duplicate-key adversary and its survival check were left untouched, as required.</notes>
    </change>
    <change id="C6" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/manifest.py" lines_changed="~90" />
      </files_modified>
      <notes>Added descriptions for the three new adversary types. Changed the manifest writer to accept the profile name and profile dictionary, and restructured the generated README into three parts: shared sections (dataset name, modality inventory, generation invocation, all keyed off the profile), a reproducibility section recording the profile name and seed (emitted for both profiles, since downstream regression testing needs to recover the generating seed from the dataset itself), and an adversary section emitted only when the profile applies adversaries, replaced by a short no-defects statement naming the adversarial counterpart when it does not. Every count, roster reference, and severity label in the adversary section is now derived from the adversary matrix and the profile's subject roster rather than hardcoded, removing the stale single-subject "clean baseline" line and its literal table row. Independently verified by reading the full landed file: confirmed the literal string naming a clean baseline subject cannot appear in either generated variant, the adversarial variant's derived counts resolve to the full 13-subject, 31-type roster, and the clean variant's statement correctly names its adversarial counterpart.</notes>
    </change>
    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/__main__.py" lines_changed="~40" />
      </files_modified>
      <notes>Added a required profile selection argument (adversarial or clean) and an optional seed override to the command-line interface. Replaced all four hardcoded functional run-count sites with the shared constants, including the two IntendedFor list comprehensions, so a future change to the run counts cannot silently desynchronize the fieldmap associations from the actual generated runs. Generation now iterates the selected profile's declared subject roster rather than the full demographics table, so a roster that names a subject absent from demographics raises immediately instead of silently producing a short dataset. The scaffold-writing, adversary-application, and manifest-writing phases all now receive the resolved profile; adversary application is additionally intersected against the active roster so a matrix entry for a subject the current profile does not generate is skipped rather than raising against a directory that was never created. Independently verified by reading the full landed file against all locked acceptance criteria, and cross-checked against the already-verified call signatures in the scaffold and manifest changes; no deviations from specification.</notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>6</total_changes>
    <completed>6</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <next_steps>
    Recommended: run /test to validate all changes.

    Four items were recorded in the plan's post-build notes as explicitly out of this build's
    file scope and are not addressed here:
    1. The sandbox smoke-run driver invokes the CLI directly and will need an explicit profile
       argument added before it can run again.
    2. The sandbox dataset verifier carries three pre-existing checker bugs unrelated to this
       build and currently covers only 28 of 31 adversary types across 10 of 13 subjects; it
       needs updating to full 31-of-31 coverage.
    3. No test suite has yet been run against the generator package.
    4. Generating either profile end to end will require /run-local to request the filesystem
       grant for the external output directory, which is never self-granted and must be
       surfaced for explicit user approval.
  </next_steps>
</implement_report>
