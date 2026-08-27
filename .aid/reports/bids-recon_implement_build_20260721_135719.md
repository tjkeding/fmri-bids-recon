<implement_report>
  <meta project="bids-recon" mode="implement" submodule="build" timestamp="2026-07-21T13:57:19Z" />
  <spec_ref>bids-recon_implement_plan_20260721_093556.md</spec_ref>
  <pre_build>
    <backup path="sandbox/backups/pre_implement_20260721_093556/">
      <file path="smoke_run.py" sha256="7b01dc89fcda2aaffc07a17db4e9bb27d820e6d14d180c38d0bb6659f2398093" />
      <file path="verify_dataset.py" sha256="6ae960526190b7883023aeb8b73ab4de5c70dbb26358c7735c18a2e42e02242e" />
    </backup>
  </pre_build>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="sandbox/smoke_run.py" lines_changed="~18" />
      </files_modified>
      <notes>Updated the module docstring to reflect the new subject and adversary counts, and replaced the hardcoded, seed-42, no-profile invocation with an argparse-based driver that requires no arguments by default (profile defaults to adversarial) but accepts an explicit profile choice and an optional output directory. The seed is now derived from the selected profile's declared seed rather than hardcoded, so the smoke driver and the main CLI are guaranteed to produce identical output for a given profile. The config-patching, import-order assertions, and truncated-volumes rescaling logic were left untouched, as specified. Independently verified by reading the full landed file: the docstring, argparse block, and unchanged sections all match the specification exactly.</notes>
    </change>
    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="sandbox/verify_dataset.py" lines_changed="~230" />
      </files_modified>
      <notes>Fixed all three known checker bugs: the raw-key duplicate-casing detector now matches the actual four-space JSON indentation instead of an assumed two-space indentation; the protocol-rename check now targets the emotional n-back sidecars that the corresponding adversary actually modifies, rather than the resting-state sidecars it previously (and incorrectly) targeted; and the stale-series check now looks for the specific file the corresponding adversary creates, rather than relying on a filename-exclusion filter that inadvertently excluded that same file. All twenty-eight pre-existing checks were remapped to the correct subject, session, and file targets in the current thirteen-subject adversary assignment matrix, and three new checks were added for the three adversary types introduced in the prior build (a phase-encoding-direction flip, a diffusion-gradient sign flip, and a voxel-size drift), bringing total coverage to all thirty-one adversary types. Independently verified by reading the full landed file and cross-checking every one of the thirty-one checks against the actual adversary assignment matrix in the codebase (not just the plan's mapping table): every subject, session, and target field matches exactly, all three bug fixes are present and correctly implemented, and the scl_slope check correctly retains the header-based read rather than switching to the dataobj-based read (the previously resolved decision to avoid a NaN-normalization regression). No deviations from specification.</notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>2</total_changes>
    <completed>2</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <next_steps>
    Recommended: run /test to validate all changes.

    No items deferred. This build completes all code changes identified across the two most
    recent implementation rounds. The two remaining downstream items are skill invocations,
    not code changes, consistent with the user's stated sequencing:

    1. /test for the generator package.
    2. /run-local to request the ~/simulated-bids/ filesystem grant and generate both
       profiles, following /test.
  </next_steps>
</implement_report>
