<implement_report>
  <meta project="bids-recon" mode="implement" submodule="build" timestamp="2026-07-30T18:07:20Z" />
  <spec_ref>bids-recon_implement_plan_20260730_133222.md</spec_ref>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/data/brainweb_crisp.nii.gz" lines_changed="n/a (binary, 7.1MB)" />
        <file path="tools/simulated_bids/data/download_brainweb.py" lines_changed="~95" />
      </files_modified>
      <notes>
        The BrainWeb CGI endpoint required a POST form submission rather than the GET-style query string originally specified; the download script was corrected to submit the required form fields. More significantly, the downloaded crisp discrete anatomical model contains 10 tissue classes (labels 0-9: background, csf, grey matter, white matter, fat, muscle/skin, skin, skull, glial matter, connective), not the 12 classes assumed during planning. There is no separate vessels, dura mater, or bone marrow class in this model; label 8 is glial matter, not vessels. This discrepancy was surfaced to the user before further changes were built, and the decision was to accept the real 10-class model as authoritative rather than sourcing the fuzzy per-tissue probability maps to approximate a 12-class model. All downstream tissue-class references were built against this corrected 10-class model.
      </notes>
    </change>

    <change id="C2" priority="P0" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/config.py" lines_changed="~120" />
      </files_modified>
      <notes>
        All synthesis constants were appended after the existing fieldmap acquisition parameters, adjusted to the corrected 10-class tissue model (five intensity and ADC tables, each keyed 0-9). The eight EN-back condition labels were corrected mid-build from an approximated naming scheme to the nomenclature the real ABCD emotional n-back protocol actually uses for its four stimulus categories (negative face, neutral face, positive face, place), after a naming mismatch was discovered between this file and the events module (see the events-module note below). Two constants beyond the original specification were added later in the build: a header-only rotation and translation range, deliberately smaller than and independent from the between-session and between-run pose ranges, to give every generated NIfTI file plausible, non-identical scanner metadata without disclosing the anatomical pose perturbation that the registration-testing stages need to discover through image content alone.
      </notes>
    </change>

    <change id="C3" priority="P0" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/events.py" lines_changed="~130 (net; includes a correction pass)" />
      </files_modified>
      <notes>
        The task timing module and the configuration extension were dispatched to two agents in parallel despite the timing module's declared dependency on the configuration constants. The resulting race meant the timing-module agent found the required constants absent at read time and defined its own local copies instead of importing them, including its own approximated condition-label list. This was corrected directly: the local constant definitions were removed and replaced with an import from the configuration module, and the condition-label mismatch this exposed was resolved as described in the configuration-extension note above. The task-timing algorithm itself (fixation distribution, alternating block ordering, boxcar neural timecourse construction) required no changes and was verified correct on first build.
      </notes>
    </change>

    <change id="C4" priority="P0" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/tissue.py" lines_changed="~330 (net; includes a correction pass)" />
      </files_modified>
      <notes>
        The per-tissue intensity lookup was implemented with a dynamically sized array derived from each intensity table's own keys, rather than a fixed count, so the module is not sensitive to the corrected tissue-class count. A significant correctness defect was found through direct numerical testing of the label-resampling function's returned NIfTI header: the header's translation component incorrectly incorporated part of the same rigid-body pose perturbation already baked into the resampled voxel content, an inconsistency provable with a synthetic point-source test (a resampled feature's true physical location and its header-reported location disagreed by exactly the perturbation's translation). Because the anatomical pose perturbation and a fully-disclosed header are mathematically mutually exclusive for the same transform (fully disclosing it algebraically cancels the very diversity the perturbation is meant to introduce into the voxel content), the fix introduces a second, independent, much smaller rigid-body perturbation used only for header construction, decoupled entirely from the anatomical pose. This was verified empirically: resampled voxel content is provably identical regardless of the header perturbation's value, while the returned header exactly and self-consistently reflects it. The convenience functions used by the adversary module were updated to generate this same header perturbation internally.
      </notes>
    </change>

    <change id="C5" priority="P0" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/bold_signal.py" lines_changed="~290 (net; includes two correction passes)" />
      </files_modified>
      <notes>
        Two significant defects were found through direct numerical testing rather than code inspection alone. First, the condition-specific activation-map generator's controlled spatial overlap between task conditions was implemented incorrectly in two compounding ways: the within-load shared voxel pool was sized using the full within-load overlap target added on top of the cross-load pool rather than the marginal difference between the two targets, and each condition's remaining voxels were drawn independently rather than from a single shared without-replacement pool, introducing uncontrolled additional overlap. Measured achieved overlap (82% within-load, 41% cross-load) substantially exceeded the intended targets (50% and 30%). While correcting the allocation logic, a further structural finding emerged: with eight total task conditions, the configured activation-extent range and the overlap targets are only jointly satisfiable by exact construction for roughly the bottom sixth of the configured extent range; for the remainder (the great majority of actual draws), achieving the extent range exactly and the overlap targets exactly are mathematically incompatible, a consequence of how many conditions must share a bounded pool of grey-matter voxels. This was resolved, with the user's direction, by preserving the activation-extent range exactly as configured and having the overlap targets act as guaranteed floors: hit exactly when the two ranges are jointly feasible, and exceeded in a fully deterministic, reproducible way (never falling short, never left to chance) otherwise. Both regimes were verified empirically. Second, and independently, the hemodynamic response function combined its two constituent gamma-shaped lobes before normalizing either of them, and because the two lobes' exponents differ substantially, their unnormalized peak magnitudes differ by roughly a factor of a million; the resulting function's values reached the billions rather than describing a proper unit-peak canonical hemodynamic response, which in turn caused the noise-generation step to receive a negative mean signal and raise a runtime error for any task-based functional run. This was corrected by normalizing each gamma lobe to its own unit peak before combining them and re-normalizing the combined result, which was verified to produce a standard canonical response shape (peak of 1.0 near the configured peak latency, a modest undershoot of the configured relative depth several seconds later). The user separately confirmed, after being informed that the corrected function's convolution with a sustained task block yields an observed plateau signal change several times larger than the configured neural-level activation magnitude (a genuine property of convolving a boxcar with a multi-second impulse response, not an error), that this is acceptable because the simulated datasets are not used for group-level effect-size-sensitive analyses.
      </notes>
    </change>

    <change id="C6" priority="P0" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/modalities.py" lines_changed="~150" />
      </files_modified>
      <notes>
        All five per-modality generator functions were updated to accept an already-resampled label array, an already-computed output affine, and the relevant bias and static-field arrays from the caller, and to use the passed-in affine for file output rather than constructing one internally. The internal affine-construction helper remains defined with an unchanged signature, since the adversary module continues to import it directly, but is no longer called by the generator functions themselves. The fieldmap-pair generator was implemented so that the two phase-encoding-direction files share the same underlying synthesized anatomy at each stacked-volume index, differing only in which direction the static-field-induced geometric distortion is applied, matching the physical reality that a paired fieldmap acquisition images the same anatomy twice with opposite readout polarity. Verified by direct execution of all five generator functions, including the event-file-writing path for the task-based functional runs, which surfaced the hemodynamic-response defect described above.
      </notes>
    </change>

    <change id="C7" priority="P0" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/__main__.py" lines_changed="~260 (substantially rewritten)" />
        <file path="tools/simulated_bids/manifest.py" lines_changed="1" />
      </files_modified>
      <notes>
        The session-orchestration function was rewritten well beyond the original plan's scope after a gap was found during the header-perturbation design work: the previously locked decision that between-run pose offsets should vary independently across runs had no implementation path in the original plan, which resampled each acquisition resolution once per session and reused it across every run of that type. The rebuilt orchestration now draws one session-level pose perturbation and one session-level header perturbation shared by every file in the session, resamples the two single-run structural modalities and one diffusion-weighted acquisition once each against the session-level pose, generates a session-level reference purely to produce the shared bias field, static field, and task activation maps, and then draws an independent between-run pose offset and performs an independent resampling for each of the four functional runs and each of the three fieldmap acquisitions. Verified end to end for a full single subject-session (twenty files, ~196 seconds), and separately confirmed that two runs resampled with independent offsets differ substantially in voxel content (29% of voxels) while sharing an identical output header, exactly matching the intended design.
      </notes>
    </change>

    <change id="C8" priority="P0" source_item="adversary transparency finding" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/adversaries.py" lines_changed="~15" />
      </files_modified>
      <notes>
        All seven data-fill call sites across the five affected adversary functions (the scan-restart, stale-series, extra-localizer, voxel-size-drift, and fieldmap-geometry-mismatch adversaries) were migrated from the retired noise generator to the new tissue-based convenience functions. Every random seed, every existing affine construction or reuse, and all surrounding file-path, sidecar, and control-flow logic were preserved exactly; only the data-fill call itself changed at each site. Verified by direct execution of all five affected functions against both freshly generated fixtures and, for two of them, a fully generated real subject session, confirming correct output shape, voxel geometry, and value ranges at every site with no deviation from the intended defect each adversary introduces.
      </notes>
    </change>

    <change id="C9" priority="P0" source_item="adversary transparency finding" status="done" user_decision="proceed">
      <files_modified>
        <file path="tools/simulated_bids/noise.py" lines_changed="&lt;DELETED&gt;" />
      </files_modified>
      <notes>
        Deleted after both the modality-generator migration and the adversary-function migration were complete and independently verified. A repository-wide search immediately before deletion confirmed zero remaining importers of the retired module. Deletion was carried out only after explicit, per-invocation user authorization, consistent with the destructive-operation policy governing this project.
      </notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>9</total_changes>
    <completed>9</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <next_steps>
    Recommended: run /test to design and update the test suite for the new tissue-synthesis modules (the prior noise-function tests are now obsolete) and to add signal-model validation coverage (tissue contrast ratios, noise distribution, activation-overlap behavior, header/content self-consistency).

    Also recommended before relying on this dataset for pipeline testing: a full regeneration of both the adversarial and clean profiles. Only single-session and per-adversary fixture-level generation were exercised during this build; the full seventeen-subject, three-session adversarial dataset was not regenerated end to end. Measured single-session generation time was approximately 196 seconds, consistent with the original estimate of several hours for the complete dataset.
  </next_steps>
</implement_report>
