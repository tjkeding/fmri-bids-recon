<brainstorm_report>
  <meta project="fmri-bids-recon" mode="brainstorm" timestamp="2026-08-27T19:09:41Z" />
  <context_files>
    <file path="fmri_bids_recon/stage2_classify.py" relevance="Classification engine; Rule 5 misclassifies calibration sequences as FMAP_FUNC; target for post-classification PE axis validation pass" />
    <file path="fmri_bids_recon/stage3_map.py" relevance="Fieldmap pairing logic; PhaseEncodingError raised when non-opposite PE directions paired" />
    <file path="fmri_bids_recon/sidecar.py" relevance="pe_axis property (line 98-106) provides polarity-stripped PE axis for cross-series comparison" />
    <file path="fmri_bids_recon/warnings.py" relevance="graded_warning and severity constants used for DROP_CALIBRATION audit trail" />
    <file path="fmri_bids_recon/errors.py" relevance="PhaseEncodingError definition; the error this guard prevents" />
  </context_files>
  <topics>
    <topic id="T1" title="Calibration sequence exclusion guard design">
      <summary>
        Siemens vNav setter calibration sequences (single-volume spin-echo EPI, PE direction 'i'/LR, sagittal orientation) are misclassified as FMAP_FUNC by Rule 5 in stage2_classify.py, then fail the opposite-PE pairing check in stage3_map.py, raising PhaseEncodingError. No vendor-agnostic DICOM token or existing BIDS tool approach exists for calibration exclusion. The approved design uses a two-layer guard: (1) a physics-based PE axis validation pass that checks modality-scoped PE axis compatibility between fieldmap candidates and their target modality, and (2) a secondary vendor-dispatched description keyword guard for defense-in-depth.
      </summary>
      <research>
        R1 (cross-vendor calibration DICOM signals, lit_state=speculative): No standardized DICOM ImageType token marks calibration sequences across Siemens, GE, and Philips. Siemens vNav setters share ProtocolName with diagnostic scans (ReproIn Issue #40); distinguished only by SequenceName and instance count. GE calibration metadata resides in private DICOM tags not surfaced by dcm2niix. Siemens vNav ImageComments (per-TR motion estimates) are not fully preserved in dcm2niix BIDS sidecars (dcm2niix Issue #481).

        R2 (BIDS tools calibration exclusion patterns, lit_state=consensus): No BIDS conversion tool (heudiconv, BIDScoin, dcm2bids) has a vendor-agnostic semantic rule for calibration exclusion. BIDScoin has a structured 'exclude' datatype but requires user-authored ProtocolName/SeriesDescription patterns. heudiconv/ReproIn excludes scouts via hardcoded SeriesDescription substring matching. ReproIn's ImageType-based fieldmap classification broke on Siemens XA30 firmware (reproin Issue #73), demonstrating firmware-version instability of ImageType heuristics.

        R3 (cross-vendor calibration physical parameters, lit_state=speculative): GE ASSET calibration scans are recognized as non-standard series in draft BIDS language (acq-ASSET entity). BIDS SBRef (single-band reference) scans intentionally share geometry and PE direction with their paired diagnostic run. Vendor pulse-sequence manuals are not openly web-indexed; empirical validation against real DICOM samples is required per vendor. WebSearch budget exhausted before dispatch; findings limited to WebFetch of known URLs.

        PV-1/PV-2/PV-3 (proposal verification, 3/3 returned concerns at high confidence): All three agents validated the PE axis guard architecture as sound and consistent with codebase patterns (NORM/ND twin-resolution pass, sidecar.pe_axis docstring invariant). Four refinements incorporated: (1) modality-scoped PE axis matching (FMAP_FUNC vs BOLD only, FMAP_DWI vs DWI only), (2) empty target set bypass to avoid false demotion in partial/aborted protocols, (3) compound keyword matching to narrow false-positive surface, (4) explicit DROP_CALIBRATION routing specification.
      </research>
      <approaches>
        <approach id="A1" label="Description keywords only" feasibility="high" risk="high">
          <description>Vendor-dispatched SeriesDescription substring matching (e.g., Siemens: "setter", "prescan"; GE: TBD; Philips: TBD). Mirrors existing SCOUT_KEYWORDS pattern.</description>
          <pros>Simple implementation; directly addresses the known Siemens vNav case.</pros>
          <cons>Vendor-specific, fragile across firmware versions. User explicitly rejected the Siemens-only variant of this approach. Cannot be extended to unknown vendors without empirical samples. False-positive risk on legitimate protocols containing keyword substrings.</cons>
        </approach>
        <approach id="A2" label="ImageType/DICOM token guards" feasibility="medium" risk="high">
          <description>Guard FMAP_FUNC/FMAP_DWI classification on specific ImageType tokens (e.g., requiring FMRI or ND tokens).</description>
          <pros>Uses structured DICOM fields rather than free-text description.</pros>
          <cons>Firmware-unstable: ReproIn Issue #73 documents ImageType vocabulary change across Siemens XA30. Not standardized across vendors. DICOM PS3.3 defines no calibration-specific Value 3 term for ImageType.</cons>
        </approach>
        <approach id="A3" label="Physics-based PE axis validation" feasibility="high" risk="low">
          <description>Post-classification pass requiring each FMAP_FUNC/FMAP_DWI candidate's PE axis to match at least one series of its target modality (BOLD for FMAP_FUNC, DWI for FMAP_DWI). Non-matching series demoted to DROP_CALIBRATION with graded_warning.</description>
          <pros>Vendor-agnostic. Rooted in the physical necessity that a fieldmap must share PE axis with its correction target (Jezzard and Balaban, MRM 1995). Consistent with codebase's own documented invariant (sidecar.py pe_axis docstring). Mirrors existing NORM/ND post-classification pattern.</pros>
          <cons>Cannot catch calibration sequences that happen to share PE axis with targets (unknown frequency across vendors). Requires non-empty target set to function (addressed by empty-target bypass). Cross-vendor coverage cannot be validated from literature alone.</cons>
          <statistical_considerations>The guard encodes a necessary condition for fieldmap utility, not a sufficient one. False negatives (calibration sequences sharing PE axis with targets) are possible but do not produce PhaseEncodingError; they would instead produce a fieldmap with mismatched geometry, caught by stage3's existing geometry check.</statistical_considerations>
        </approach>
        <approach id="A4" label="Hybrid: PE axis + description keywords" feasibility="high" risk="low">
          <description>Primary: PE axis validation pass (A3). Secondary: vendor-dispatched compound keyword guard (keyword AND single-volume AND description stem differs from any target series) for defense-in-depth against edge cases where calibration sequences share PE axis with targets.</description>
          <pros>Two independent layers. PE axis provides vendor-agnostic physics-based coverage. Keywords catch vendor-specific edge cases that bypass the PE axis check. Compound match requirement narrows false-positive surface relative to simple keyword matching.</pros>
          <cons>Keyword layer requires maintenance as new vendor patterns are discovered. Compound match adds implementation complexity relative to A3 alone.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A4">
        Hybrid approach (A4) approved. PE axis validation as the primary vendor-agnostic guard, with compound description keyword matching as secondary defense-in-depth.

        Implementation specification:
        1. Add DROP_CALIBRATION to the Role enum (after DROP_ANAT_ND_T2W).
        2. Add a post-classification "calibration sequence exclusion" pass after the NORM/ND twin resolution pass (line 407+), following the same architectural pattern.
        3. PE axis check is modality-scoped: FMAP_FUNC checked against PE axes of BOLD series only; FMAP_DWI checked against PE axes of DWI series only.
        4. Empty target bypass: if zero series of the corresponding target modality exist in the session, skip the PE axis check for that fieldmap type (do not demote).
        5. Non-matching series demoted to DROP_CALIBRATION with graded_warning at medium severity.
        6. Secondary keyword guard: compound match requiring keyword ("setter", "prescan") AND single-volume (n_volumes == 1) AND description stem differs from any target modality series description stem.
        7. DROP_CALIBRATION routing: silent discard in stage4_assemble.py (consistent with DROP_NAVIGATOR, DROP_SCOUT, DROP_DERIVED), with graded_warning providing audit traceability.
        8. Cross-vendor coverage limitation acknowledged: full validation requires empirical testing against GE and Philips calibration DICOM samples. The PE axis guard is demonstrably correct for the Siemens vNav setter case and is a necessary condition for fieldmap utility across all vendors.
      </decision>
    </topic>
  </topics>
  <action_items>
    <item priority="P0" target_mode="implement" description="Add DROP_CALIBRATION role to Role enum in stage2_classify.py" />
    <item priority="P0" target_mode="implement" description="Add post-classification PE axis validation pass to classify() in stage2_classify.py: modality-scoped PE axis check for FMAP_FUNC (vs BOLD) and FMAP_DWI (vs DWI), with empty-target bypass and graded_warning at medium severity on demotion" />
    <item priority="P1" target_mode="implement" description="Add secondary compound keyword guard in classify(): vendor-dispatched keywords (Siemens: 'setter', 'prescan') with compound match requirement (keyword AND single-volume AND description stem mismatch vs target modality)" />
    <item priority="P1" target_mode="implement" description="Verify DROP_CALIBRATION is silently discarded by stage4_assemble.py (confirm existing DROP_* fallthrough behavior covers new role)" />
    <item priority="P1" target_mode="test" description="Test PE axis guard with vNav setter scenario (PE axis 'i' with BOLD PE axis 'j'), empty-target bypass, matching PE axis pass-through, and compound keyword guard" />
  </action_items>
  <next_steps>Recommended: /implement to build the calibration exclusion guard per the specification above, followed by /test to validate against the vNav setter scenario and edge cases.</next_steps>
</brainstorm_report>
