<implement_report>
  <meta project="bids-recon" mode="implement" submodule="build" timestamp="2026-07-21T20:28:00Z" />
  <spec_ref>bids-recon_implement_plan_20260721_200500.md</spec_ref>

  <changes_applied>

    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="bids_recon/stage4_assemble.py" lines_changed="~48" />
      </files_modified>
      <notes>
        Removed the deny-list frozenset and the scrub() function entirely.
        All 7 former scrub() call sites now pass the raw sidecar dict
        directly, except the two BOLD/SBRef sites, which use a dict copy
        because a subsequent TaskName mutation follows. Module docstring
        updated. Verified via grep: zero remaining references to the
        removed deny-list or function in this file.
      </notes>
    </change>

    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="bids_recon/report.py" lines_changed="~53" />
      </files_modified>
      <notes>
        Removed the scrub-audit section, its imports, and all docstring
        references to it. The conversion report is now a seven-section
        document ending at the PatientID cross-check. Verified via grep:
        zero remaining references to the removed deny-list, the audit, or
        the associated exception import in this file.
      </notes>
    </change>

    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="bids_recon/stage4_assemble.py" lines_changed="1" />
      </files_modified>
      <notes>
        The sessions.tsv acq_time field now goes through the same
        ISO-8601 normalization helper already used for every scans.tsv
        row, instead of writing the raw DICOM timestamp string verbatim.
        Verified via grep.
      </notes>
    </change>

    <change id="C4" status="done" user_decision="n/a">
      <files_modified>
        <file path="bids_recon/stage4_assemble.py" lines_changed="1" />
      </files_modified>
      <notes>
        The age-in-decimal-years calculation now divides by the Gregorian
        mean year length instead of the Julian approximation. Verified via
        grep.
      </notes>
    </change>

    <change id="C5" status="done" user_decision="n/a">
      <files_modified>
        <file path="bids_recon/json_intermediate.py" lines_changed="170 (new file)" />
        <file path="bids_recon/__main__.py" lines_changed="~10" />
      </files_modified>
      <notes>
        Replaced the pickle-based intermediate serialization between the
        convert and assemble phases with a JSON-based equivalent. The new
        module recursively encodes and decodes every type that appears in
        the intermediate structure: the frozen series dataclass and its
        nested Path/datetime/tuple fields, the fieldmap-pairing and
        registry-delta dataclasses, the physio-log dataclasses, the
        advisory-flag exception type, the string enum used for series
        roles, and dictionaries keyed by integer series number (JSON
        requires string keys, so these are tagged and restored on load).
        Verified: no remaining references to the removed serialization
        library anywhere in the entry point; both files parse cleanly and
        import without error; a manual verification also caught and fixed
        one stale comment left over from the prior implementation.
      </notes>
    </change>

    <change id="C6" status="done" user_decision="proceed">
      <files_modified>
        <file path="tools/simulated_bids/config.py" lines_changed="~55" />
        <file path="tools/simulated_bids/modalities.py" lines_changed="~10" />
        <file path="tools/simulated_bids/scaffold.py" lines_changed="~5" />
        <file path="tools/simulated_bids/__main__.py" lines_changed="~45" />
      </files_modified>
      <notes>
        Added a function that computes the fourteen simulated patient-level
        fields (identifiers, demographic values, timestamps) for one
        acquisition series, matching what the conversion tool produces from
        real scanner DICOMs. Threaded these values through every modality
        generator and into the underlying sidecar-merging helper. Updated
        the per-session scan listing to carry real simulated acquisition
        timestamps instead of a placeholder.

        Deviation caught during verification, corrected before proceeding:
        the initial birth-date formula truncated the fractional part of
        each subject's declared age, so a subject declared at 9.8 years
        old would receive a birth date exactly 9 years before the study
        date. This meant the pipeline's own preferred age-computation path
        (deriving age from birth date and acquisition time) would recover
        an age up to 0.8 years off from what was declared, and would
        disagree with the age string field by up to a full year. It also
        meant the regenerated fixtures could not exercise the
        fractional-day precision the Gregorian-year-length fix above is
        meant to validate, since every computed age would land near a
        whole-year boundary regardless of which year-length constant was
        used. The formula was corrected to derive the birth date from the
        full fractional age (subject to the day-level precision inherent
        in a date-only DICOM field). Verified numerically after the fix:
        recovered decimal age matches the declared age to within about
        one-thousandth of a year across both fractional-age and
        whole-integer-age subjects, down from an error of up to 0.8 years
        beforehand. This was surfaced to the user before proceeding and
        approved.
      </notes>
    </change>

    <change id="C7" status="skipped" user_decision="modify">
      <files_modified />
      <notes>
        Scope corrected by the user during the build: executing pipeline
        or generator runs against real data belongs to run-local, not to
        this implement build. The two stale dataset directories were
        deleted at the user's explicit direction (the clean-profile
        directory was already known incomplete from an earlier crashed
        run, and the adversarial-profile directory predated the
        patient-field and age-precision fixes above). Regenerating both
        datasets with the updated generator, and validating the output
        sidecars, is deferred to run-local.
      </notes>
    </change>

  </changes_applied>

  <summary>
    <total_changes>7</total_changes>
    <completed>6</completed>
    <skipped>1</skipped>
    <blocked>0</blocked>
  </summary>

  <next_steps>
    Run /run-local to regenerate both simulated datasets (adversarial and
    clean profiles) with the updated generator and validate the output:
    confirm all fourteen patient-level fields are present in generated
    sidecars, confirm the clean-profile run completes all four subjects
    across three sessions without the crash seen previously, and confirm
    the corrected age-precision formula produces sensible decimal ages
    when the pipeline itself processes the regenerated fixtures.

    Recommended after that: run /test to design test coverage for the
    changes in this build. In particular: round-trip tests for the new
    JSON intermediate serialization (encode then decode should reproduce
    the original structure exactly, including nested dataclasses,
    integer-keyed dictionaries, and the frozen series type); and updates
    to the two existing test files that currently assert the removed
    scrub behavior, which will now fail on collection or execution.
  </next_steps>

</implement_report>
