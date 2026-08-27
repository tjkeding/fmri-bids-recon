<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-08-19T17:58:30Z" />
  <input_reports>
    <report path="bids-recon_test_20260819_173418.md" mode="test" key_items="1" />
  </input_reports>
  <changes>
    <change id="C1" priority="P1" source_item="action_items/item[@priority='P1']">
      <file path="fmri_bids_recon/config.py" action="modify" />
      <description>Wrap the FileNotFoundError raised by _load_raw() when the config YAML file does not exist as a ConfigError. This ensures load_and_validate() propagates a typed exception that __main__.py's existing except ConfigError handler catches, producing exit code 2 (config/input validation error) instead of falling through to the bare Exception catch-all at exit code 1.</description>
      <spec>
In load_and_validate() (line 384), wrap the _load_raw(path) call in a try/except:

    try:
        raw = _load_raw(path)
    except FileNotFoundError:
        raise ConfigError(
            f"Config file not found: '{path}'"
        ) from None

The _validate_raw() and _resolve_config() calls remain unwrapped. The FileNotFoundError for a missing subjects file (raised explicitly in _validate_raw at line 217) is NOT affected by this change.

Update the docstring's Raises section to reflect the new behavior:
- FileNotFoundError: narrow to "If a referenced subjects file does not exist." (removing "the config file or")
- ConfigError: expand to "If the config file does not exist, or if no DICOM paths resolve after expansion."

No changes to __main__.py. No changes to any test files. The existing test_a_config_error_exits_two (asserting exit code 2 for a missing config file) becomes the regression test for this fix.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - single-site catch in a public API function; _validate_raw's explicit FileNotFoundError for missing subjects file is structurally unreachable from this catch (it executes after _load_raw returns successfully); existing test_a_missing_subjects_file_is_refused exercises the subjects file path independently and is unaffected</risk>
      <rollback>Revert the try/except block and docstring in load_and_validate() to the prior state (bare _load_raw(path) call).</rollback>
    </change>
  </changes>
  <execution_order>C1</execution_order>
</implement_plan>
