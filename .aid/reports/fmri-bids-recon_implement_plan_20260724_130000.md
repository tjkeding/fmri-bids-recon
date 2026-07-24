<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-07-24T13:00:00-04:00" />
  <input_reports>
    <report path="bids-recon_brainstorm_20260724_120000.md" mode="brainstorm" key_items="7" />
  </input_reports>
  <changes>
    <change id="C1" priority="P0" source_item="brainstorm AI #1 (config toggle)">
      <file path="fmri_bids_recon/config.py" action="modify" />
      <description>Add deface:bool field to StudyConfig (default False) and parse it from YAML in load_config(), mirroring the existing physio toggle.</description>
      <spec>
        1. In the StudyConfig docstring (after the physio entry, currently at line 103-104), add:

            deface : bool
                Whether to run the defacing stage.  Defaults to False.  Requires
                ``pydeface`` and FSL ``flirt`` on PATH; the pipeline verifies both
                at startup when this flag is True.

        2. In the StudyConfig dataclass fields (after `physio: bool = False` at line 126), add:

            deface: bool = False

        3. In load_config(), after `physio = bool(raw.get("physio", False))` (line 252), add:

            deface = bool(raw.get("deface", False))

        4. In the StudyConfig constructor call (line 352-362), after `physio=physio,` add:

            deface=deface,
      </spec>
      <dependencies>none</dependencies>
      <risk>low - mirrors an existing pattern (physio); default False preserves backward compatibility</risk>
      <rollback>Revert the 4 insertion sites in config.py</rollback>
    </change>

    <change id="C2" priority="P0" source_item="brainstorm AI #2 (pre-flight check), AI #3 (remove FileNotFoundError handler)">
      <file path="fmri_bids_recon/deface.py" action="modify" />
      <description>Add assert_deface_tools() pre-flight function and remove the FileNotFoundError handler. Under the new hard-enforcement contract, both FileNotFoundError and CalledProcessError propagate naturally when deface is enabled.</description>
      <spec>
        1. Add import of ToolUnavailableError. After the existing `from .config import StudyConfig` (line 15), add:

            from .errors import ToolUnavailableError

        2. Add the pre-flight function after the logger definition (line 17) and before the deface() function (line 20):

            def assert_deface_tools() -> None:
                """Pre-flight: verify pydeface and FSL flirt are on PATH.

                Called at pipeline startup when config.deface is True. Raises
                ToolUnavailableError if either binary is absent, halting the
                pipeline before any DICOM processing begins.
                """
                missing = [t for t in ("pydeface", "flirt") if shutil.which(t) is None]
                if missing:
                    raise ToolUnavailableError(
                        f"deface is enabled but required tool(s) not on PATH: "
                        f"{', '.join(missing)}. Install the required tools or "
                        f"set deface: false in the config."
                    )

        3. Remove the FileNotFoundError except block (lines 95-101). The entire try/except wrapping the subprocess.run calls (lines 79-101) should be unwrapped: remove the `try:` at line 79 and the `except FileNotFoundError: ... continue` at lines 95-101, de-indenting the subprocess.run calls by one level to sit directly in the for-loop body. Both CalledProcessError and FileNotFoundError will propagate naturally (hard enforcement).

           Before:
               try:
                   if tool == "pydeface":
                       subprocess.run(...)
                   elif tool == "afni_refacer":
                       subprocess.run(...)
               except FileNotFoundError:
                   logger.warning(...)
                   continue

           After:
               if tool == "pydeface":
                   subprocess.run(...)
               elif tool == "afni_refacer":
                   subprocess.run(...)
      </spec>
      <dependencies>none</dependencies>
      <risk>low - assert_deface_tools is a new function; FileNotFoundError handler removal is safe because pre-flight check ensures the tools exist before deface() is called</risk>
      <rollback>Remove assert_deface_tools function, re-add the try/except FileNotFoundError handler, remove the ToolUnavailableError import</rollback>
    </change>

    <change id="C3" priority="P0" source_item="brainstorm AI #2 (pre-flight in __main__), AI #1 (deface gate)">
      <file path="fmri_bids_recon/__main__.py" action="modify" />
      <description>Add deface pre-flight check at startup (alongside dcm2niix version check) gated on config.deface, and gate the Phase 5 deface call on config.deface.</description>
      <spec>
        1. Update the deface import (line 35). Change:

            from .deface import deface

           To:

            from .deface import assert_deface_tools, deface

        2. After the dcm2niix version check block (lines 126-130), add a deface pre-flight block:

            # --- Deface pre-flight ---
            if config.deface:
                try:
                    assert_deface_tools()
                except ToolUnavailableError as exc:
                    logger.error('Deface pre-flight failed: %s', exc)
                    sys.exit(4)

        3. Gate the Phase 5 deface call (line 303-304). Change:

            # === PHASE 5: DEFACE (hardcoded pydeface) ===
            deface(config)

           To:

            # === PHASE 5: DEFACE ===
            if config.deface:
                deface(config)
      </spec>
      <dependencies>C1 (config.deface field), C2 (assert_deface_tools function)</dependencies>
      <risk>low - pre-flight check mirrors dcm2niix pattern; deface gate mirrors physio gate pattern</risk>
      <rollback>Revert import, remove pre-flight block, remove deface gate conditional</rollback>
    </change>

    <change id="C4" priority="P1" source_item="brainstorm AI #4 (example config)">
      <file path="config/study.example.yaml" action="modify" />
      <description>Add the deface field to the example config with a comment noting the FSL requirement, mirroring the physio entry.</description>
      <spec>
        After the physio entry (line 83), add:

            # OPTIONAL. Set to true to enable anatomical defacing via pydeface.
            # Requires FSL (specifically flirt) to be installed and on PATH.
            # Defaced copies are written to derivatives/defaced/; the analysis
            # anat/ directories are never modified. Defaults to false when omitted.
            deface: false
      </spec>
      <dependencies>none</dependencies>
      <risk>low - documentation only</risk>
      <rollback>Remove the added lines</rollback>
    </change>

    <change id="C5" priority="P1" source_item="brainstorm AI #5 (README FSL docs)">
      <file path="README.md" action="modify" />
      <description>Add FSL to Prerequisites section and annotate the pydeface row in the Dependencies table.</description>
      <spec>
        1. In the Prerequisites section (after line 33, before the blank line), add:

            - **FSL** (any version): required only if the `deface` stage is enabled (`deface: true` in the study config). Specifically, `flirt` must be on PATH. FSL must be installed separately; it is not included in the conda environment.

        2. In the Dependencies table (line 170), change:

            | pydeface | 2.1.0 | Anatomical defacing |

           To:

            | pydeface | 2.1.0 | Anatomical defacing (requires FSL `flirt` on PATH) |
      </spec>
      <dependencies>none</dependencies>
      <risk>low - documentation only</risk>
      <rollback>Revert the two edits</rollback>
    </change>

    <change id="C6" priority="P1" source_item="brainstorm AI #6 (INPUT_SPECIFICATION FSL update)">
      <file path="INPUT_SPECIFICATION.md" action="modify" />
      <description>Update the FSL enforcement column and Known Limitations to reflect the new conditional enforcement model.</description>
      <spec>
        1. Update the FSL row in the External Tool Requirements table (line 134). Change:

            | FSL `flirt` | any | Soft (deface stage skipped if unavailable). | Required only for the deface stage. Must be installed separately. |

           To:

            | FSL `flirt` | any | Hard when `deface: true` (pre-flight check halts pipeline); stage skipped when `deface: false` (default). | Required only when the deface stage is enabled. Must be installed separately. |

        2. Update the Known Limitations entry (line 203). Change:

            4. **Defacing requires FSL**: the `pydeface` package is a Python wrapper around FSL's `flirt`. Systems without FSL installed will skip the deface stage silently.

           To:

            4. **Defacing requires FSL**: the `pydeface` package is a Python wrapper around FSL's `flirt`. When `deface: true` is set in the study config, the pipeline verifies that both `pydeface` and `flirt` are on PATH at startup and halts immediately if either is absent.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - documentation only</risk>
      <rollback>Revert the two edits</rollback>
    </change>
  </changes>
  <execution_order>C1, C2, C3, C4, C5, C6</execution_order>
  <notes>
    The brainstorm report includes one test action item (P1, target_mode="test"): re-express test_deface.py CalledProcessError and FileNotFoundError tests, add tests for pre-flight check and config toggle. This is deferred to /test per implement constraints (no testing in implement). Specific tests affected:
    - test_deface.py:213-220 (test_an_absent_defacing_tool_does_not_claim_to_have_defaced_anything): currently asserts FileNotFoundError is caught and returns []. Needs re-expression: FileNotFoundError now propagates.
    - test_deface.py:223-230 (test_a_defacing_tool_that_fails_stops_rather_than_reporting_success): currently asserts CalledProcessError propagates. Behavior unchanged but test documentation may need update.
    - New tests needed: assert_deface_tools() raises ToolUnavailableError when pydeface/flirt absent; config.deface default is False; config.deface=true parses correctly; StudyConfig constructor accepts deface parameter.
  </notes>
</implement_plan>
