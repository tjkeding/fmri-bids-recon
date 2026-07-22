<implement_plan>
  <meta project="fmri-bids-recon" mode="implement" submodule="plan" timestamp="2026-07-22T17:30:00Z" />
  <input_reports>
    <report path="(user direct instruction)" mode="user" key_items="3" />
  </input_reports>
  <changes>
    <change id="C1" priority="P1" source_item="user item 3: dicom_pattern redesign">
      <file path="fmri_bids_recon/config.py" action="modify" />
      <file path="config/study.example.yaml" action="modify" />
      <file path="README.md" action="modify" />
      <file path="INPUT_SPECIFICATION.md" action="modify" />
      <description>Rename dicom_pattern to dicom_template and change format placeholders from {sub}/{ses} to {subject}/{session}. Add load-time validation that both placeholders are present in the template string.</description>
      <spec>
In fmri_bids_recon/config.py:

1. StudyConfig dataclass (line 123): rename field `dicom_pattern: str` to `dicom_template: str`. Update the docstring (lines 97-98) from:
   "dicom_pattern : str\n    Per-subject/session path pattern under ``dicom_root``.  Supports\n    ``{sub}`` and ``{ses}`` format placeholders."
   to:
   "dicom_template : str\n    Per-subject/session path template under ``dicom_root``.  Supports\n    ``{subject}`` and ``{session}`` format placeholders."

2. load_config() (line 211): change `dicom_pattern = str(raw["dicom_pattern"])` to `dicom_template = str(raw["dicom_template"])`.

3. Add validation immediately after the dicom_template assignment (after the new line 211):
   ```python
   if "{subject}" not in dicom_template:
       raise ValueError(
           "dicom_template must contain a '{subject}' placeholder."
       )
   if "{session}" not in dicom_template:
       raise ValueError(
           "dicom_template must contain a '{session}' placeholder."
       )
   ```

4. Participant expansion (line 257): change `dicom_pattern.format(sub=sub, ses=ses)` to `dicom_template.format(subject=sub, session=ses)`.

5. ConfigError context (line 284): change `"dicom_pattern": dicom_pattern` to `"dicom_template": dicom_template`.

6. StudyConfig constructor call (line 318): change `dicom_pattern=dicom_pattern` to `dicom_template=dicom_template`.

In config/study.example.yaml:

Replace the dicom_pattern block (lines 35-39) with:
```yaml
# REQUIRED. Per-subject/session path template relative to dicom_root.
# {subject} is replaced by each ID from the subjects list.
# {session} is replaced by each label from the sessions list.
# Any other text is treated as a literal directory name.
#
# Examples:
#   '{subject}/{session}'                -> dicom_root/001/01
#   '{subject}/ses-{session}/DICOMS'     -> dicom_root/001/ses-01/DICOMS
#   'wave{session}/{subject}/raw'        -> dicom_root/wave01/001/raw
dicom_template: '{subject}/{session}'
```

In README.md line 79: change `dicom_pattern: '{sub}/{ses}'                    # Path pattern under dicom_root` to `dicom_template: '{subject}/{session}'           # Path template under dicom_root`.

In INPUT_SPECIFICATION.md line 18: change the dicom_pattern row to:
`| `dicom_template` | string | Must contain `{subject}` and `{session}` format placeholders. | Per-subject/session path template relative to `dicom_root`. Evaluated as `dicom_root / dicom_template.format(subject=&lt;id&gt;, session=&lt;label&gt;)`. |`

In INPUT_SPECIFICATION.md line 69: change "according to `dicom_pattern`. For the default pattern `{sub}/{ses}`" to "according to `dicom_template`. For the default template `{subject}/{session}`".
      </spec>
      <dependencies>none</dependencies>
      <risk>low - field rename and placeholder rename; no behavioral change to expansion logic; all references enumerated via grep</risk>
      <rollback>Revert the field name and placeholder names to their original values in all four files.</rollback>
    </change>

    <change id="C2" priority="P1" source_item="user item 1: subjects from file">
      <file path="fmri_bids_recon/config.py" action="modify" />
      <file path="config/study.example.yaml" action="modify" />
      <file path="README.md" action="modify" />
      <file path="INPUT_SPECIFICATION.md" action="modify" />
      <description>Allow subjects to be specified as either an inline YAML list (current behavior) or as an absolute path to a single-column text file of subject IDs. Detection is type-based: if the YAML value is a string, it is treated as a file path; if a list, it is treated as inline IDs.</description>
      <spec>
In fmri_bids_recon/config.py, load_config(), replace lines 212-213:
```python
subjects = [str(s) for s in raw["subjects"]]
```
with:
```python
raw_subjects = raw["subjects"]
if isinstance(raw_subjects, str):
    subjects_path = Path(raw_subjects)
    if not subjects_path.is_absolute():
        raise ValueError(
            f"subjects file path must be absolute, got: '{raw_subjects}'"
        )
    if not subjects_path.exists():
        raise FileNotFoundError(
            f"subjects file not found: '{subjects_path}'"
        )
    subjects = []
    with subjects_path.open("r") as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            subjects.append(stripped)
    if not subjects:
        raise ValueError(
            f"subjects file contains no valid entries: '{subjects_path}'"
        )
elif isinstance(raw_subjects, list):
    subjects = [str(s) for s in raw_subjects]
else:
    raise ValueError(
        f"subjects must be a YAML list of IDs or an absolute path to a "
        f"text file, got type: {type(raw_subjects).__name__}"
    )
```

The existing downstream validation (BIDS alphanumeric check, duplicate check) applies unchanged to subjects loaded from either source.

Update the load_config() docstring (around line 194) to add: "If ``subjects`` is a string, it is treated as an absolute path to a single-column text file of subject IDs. Blank lines and lines starting with ``#`` are skipped."

In config/study.example.yaml, update the subjects comment block (lines 45-48) to:
```yaml
# REQUIRED. Subject IDs to process, specified as either:
#   (a) An inline YAML list:  subjects: ['001', '002']
#   (b) An absolute path to a single-column text file:
#       subjects: '/absolute/path/to/subject_ids.txt'
#       (blank lines and # comment lines are skipped)
#
# Each entry must be alphanumeric (^[a-zA-Z0-9]+$).  Do NOT include the
# "sub-" prefix.  Duplicate entries are rejected.
```

In README.md, update the subjects block (lines 81-83) to show both forms:
```yaml
subjects:                                        # Inline list...
  - '001'
  - '002'
# subjects: '/absolute/path/to/subject_ids.txt' # ...or text file
```

In INPUT_SPECIFICATION.md line 19, update the subjects row to:
`| `subjects` | list of strings, or string (absolute path) | Each entry must match `^[a-zA-Z0-9]+$`. No `sub-` prefix. No duplicates. If a string, must be an absolute path to an existing file. | Subject IDs to process. If a string, treated as an absolute path to a single-column text file (blank lines and `#` comment lines are skipped). |`

In INPUT_SPECIFICATION.md, add a new validation rule after rule 3 (line 45):
"3a. **Subjects file path**: if `subjects` is a string, it must be an absolute path to an existing file containing at least one valid entry."
      </spec>
      <dependencies>none (independent of C1)</dependencies>
      <risk>low - additive feature; existing list-based behavior is unchanged; type detection via isinstance is unambiguous since YAML scalars parse as str and sequences parse as list</risk>
      <rollback>Revert load_config() to the single-line `subjects = [str(s) for s in raw["subjects"]]`. Revert documentation.</rollback>
    </change>

    <change id="C3" priority="P2" source_item="user item 2: sessions bracket notation comment">
      <file path="config/study.example.yaml" action="modify" />
      <description>Update the sessions comment block to show inline bracket notation (YAML flow sequence) as an alternative to the multi-line block sequence, since most users will be more comfortable with that form.</description>
      <spec>
In config/study.example.yaml, replace the sessions comment block (lines 52-59) with:
```yaml
# REQUIRED. List of session labels to process.  May be specified as a
# multi-line list (below) or inline: sessions: ['01', '02']
#
# Each entry must be a zero-padded integer with at least 2 digits
# (^[0-9]{2,}$).  Do NOT include the "ses-" prefix.  Duplicate entries
# are rejected.
#
# The pipeline resolves DICOM paths for every (subject, session) combination
# (cross product of subjects x sessions).  Pairs whose resolved path does not
# exist on disk are skipped with an INFO-level log message; no error is raised
# unless ALL pairs are missing.
```
      </spec>
      <dependencies>none</dependencies>
      <risk>low - comment-only change, no code modification</risk>
      <rollback>Restore original comment text.</rollback>
    </change>
  </changes>
  <execution_order>C1, C2, C3 (independent; may execute in parallel)</execution_order>
</implement_plan>
