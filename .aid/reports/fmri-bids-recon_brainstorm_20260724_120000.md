<brainstorm_report>
  <meta project="bids-recon" mode="brainstorm" timestamp="2026-07-24T12:00:00-04:00" />
  <context_files>
    <file path="fmri_bids_recon/deface.py" relevance="Defacing module; contains the CalledProcessError gap and FileNotFoundError handler to remove" />
    <file path="fmri_bids_recon/__main__.py" relevance="Pipeline entry point; deface call site (line 304), pre-flight check insertion point (lines 126-130), exception handlers (lines 333-347)" />
    <file path="fmri_bids_recon/config.py" relevance="StudyConfig dataclass (deface field addition), load_config (YAML parsing), physio toggle pattern to mirror" />
    <file path="fmri_bids_recon/errors.py" relevance="ToolUnavailableError class used for pre-flight failure" />
    <file path="tests/test_deface.py" relevance="Existing test asserting CalledProcessError propagation (line 223-230) plus FileNotFoundError handling (line 213-220); both need re-expression" />
    <file path="tests/test_config.py" relevance="Existing config tests; physio toggle tests (lines 197-213) as pattern for new deface toggle tests" />
    <file path="config/study.example.yaml" relevance="Example config; needs deface field addition" />
    <file path="README.md" relevance="User-facing docs; FSL missing from Prerequisites and Dependencies table" />
    <file path="INPUT_SPECIFICATION.md" relevance="Internal spec; FSL enforcement column needs update from 'Soft' to conditional" />
  </context_files>
  <topics>
    <topic id="T1" title="Deface stage error handling redesign">
      <summary>The pipeline crashes with exit code 2 ("Unexpected error") when pydeface fails due to missing FSL, after completing hours of convert+assemble work. The current CalledProcessError propagation was deliberate (test_deface.py:223-230) but conflates systemic environment failures with per-file processing failures and contradicts the INPUT_SPECIFICATION's documented "soft" enforcement. The fix introduces a pre-flight check and maintains hard enforcement for users who opt in.</summary>
      <research>No external research required. The design space is bounded by the existing error hierarchy, the pydeface/FSL dependency chain (confirmed via the runtime traceback: pydeface/utils.py:94 raises OSError when flirt is absent), and the INPUT_SPECIFICATION's documented enforcement model.</research>
      <approaches>
        <approach id="A1" label="Catch and skip (soft degradation)" feasibility="high" risk="low">
          <description>Catch CalledProcessError in deface.py, log warning, return output_paths. Pipeline continues to validation.</description>
          <pros>Matches INPUT_SPECIFICATION's documented "soft" contract. Simple implementation.</pros>
          <cons>User must read logs to know defacing was skipped. If user intended defacing, silent degradation masks a configuration problem. No distinction between "user didn't want deface" and "user wanted deface but it failed."</cons>
        </approach>
        <approach id="A2" label="Catch and raise ToolUnavailableError" feasibility="high" risk="low">
          <description>Catch CalledProcessError, raise ToolUnavailableError. Pipeline halts with exit code 4.</description>
          <pros>Correct exit code (4, not 2). Clear error message.</pros>
          <cons>Still halts after hours of processing. Does not solve the timing problem.</cons>
        </approach>
        <approach id="A3" label="Pre-flight check with config toggle" feasibility="high" risk="low">
          <description>When config.deface is true, verify pydeface and flirt are on PATH at startup (alongside assert_dcm2niix_version). Raise ToolUnavailableError if either is absent. When config.deface is false, skip the deface stage entirely. CalledProcessError propagates at runtime (hard enforcement). Remove the existing FileNotFoundError handler in deface.py since pre-flight validation makes it redundant, and under hard enforcement any runtime FileNotFoundError should propagate.</description>
          <pros>Fails within seconds of invocation, not after hours of processing. User intent is explicit via config toggle. Hard enforcement matches user's expectation when they opt in. Return-value invariant preserved (no false positives in the defaced-paths list).</pros>
          <cons>Couples pre-flight check to knowledge of pydeface's internals (checking for flirt). If pydeface changes its FSL dependency, the check could become stale. Mitigated by: flirt has been pydeface's sole FSL dependency for its entire history.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A3">User selected A3 with hard enforcement. Pre-flight check at startup verifies pydeface and flirt on PATH when config.deface=true; raises ToolUnavailableError (exit code 4) if either is absent. CalledProcessError propagates at runtime (per-file failures halt the pipeline). FileNotFoundError handler in deface.py:95-101 removed (redundant after pre-flight; under hard enforcement, runtime FileNotFoundError should propagate). When config.deface=false, the deface stage is skipped entirely with no pre-flight check.</decision>
    </topic>
    <topic id="T2" title="Config toggle for the deface stage">
      <summary>The pipeline has no mechanism to disable the deface stage. The physio stage has a boolean toggle (config.physio, default false); the deface stage should mirror this pattern. The default value determines whether existing deployments break on upgrade.</summary>
      <research>No external research required. The physio toggle pattern in config.py (line 126, 252) and __main__.py (lines 191-206) provides the implementation template.</research>
      <approaches>
        <approach id="A1" label="Default true (backward compat)" feasibility="high" risk="med">
          <description>deface: true by default. Existing configs without the field get current behavior (minus the crash, plus the pre-flight check).</description>
          <pros>No silent behavior change for existing users.</pros>
          <cons>Breaks fresh installations where FSL is absent (pre-flight check halts at startup). Contradicts the deface docstring's "opt-in" characterization. FSL is not pip/conda installable, so the default creates an external dependency on every installation.</cons>
        </approach>
        <approach id="A2" label="Default false (explicit opt-in)" feasibility="high" risk="low">
          <description>deface: false by default. Users who want defacing add one line to their config. No INFO log when field is absent (user accepts default by omission, consistent with physio).</description>
          <pros>Consistent with physio toggle. Consistent with deface docstring ("opt-in, NOT part of the analysis path"). No external dependency on fresh installations. No pre-flight check unless user opts in.</pros>
          <cons>Users who previously relied on defacing (even if it was crashing) stop getting defaced outputs. Mitigated by: the deface field in study.example.yaml and README documentation make the toggle discoverable.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A2">Default false. No INFO log on absent field. Consistent with physio toggle behavior and the deface stage's self-described "opt-in" contract.</decision>
    </topic>
    <topic id="T3" title="FSL runtime dependency documentation">
      <summary>FSL is documented in INPUT_SPECIFICATION.md (3 locations) but absent from README.md (Prerequisites, Dependencies table) and environment.yml. With the pre-flight check halting on missing FSL when deface:true, users need clear documentation in the user-facing README. FSL remains unpinned (any version) because flirt's CLI has been stable for 15+ years, pydeface owns the FSL interface, and no empirical incompatibility has been observed.</summary>
      <research>No external research required. FSL's flirt tool has maintained a stable CLI since its initial release (~2001). pydeface 2.1.0's FSL dependency is confirmed by the runtime traceback (pydeface/utils.py:94).</research>
      <approaches>
        <approach id="A1" label="Document across four sites" feasibility="high" risk="low">
          <description>Add FSL to README Prerequisites (conditional on deface:true), annotate pydeface row in README Dependencies table with "(requires FSL flirt)", add deface:false field to study.example.yaml with FSL requirement comment, update INPUT_SPECIFICATION enforcement column from "Soft" to conditional.</description>
          <pros>Comprehensive coverage. User encounters the FSL requirement before hitting the pre-flight failure.</pros>
          <cons>None identified.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Document FSL across all four sites. FSL unpinned (any version); no version floor enforced. Version pinning deferred until an empirical incompatibility is observed.</decision>
    </topic>
  </topics>
  <action_items>
    <item priority="P0" target_mode="implement" description="Add deface:bool field to StudyConfig (default false), parse from YAML in load_config(), gate deface stage in __main__.py on config.deface" />
    <item priority="P0" target_mode="implement" description="Add pre-flight check for pydeface and flirt at startup in __main__.py (alongside assert_dcm2niix_version), gated on config.deface=true; raise ToolUnavailableError if either is absent" />
    <item priority="P0" target_mode="implement" description="Remove FileNotFoundError handler in deface.py:95-101 (redundant after pre-flight; under hard enforcement, runtime FileNotFoundError should propagate)" />
    <item priority="P1" target_mode="implement" description="Add deface:false field with FSL requirement comment to study.example.yaml" />
    <item priority="P1" target_mode="implement" description="Add FSL to README.md Prerequisites (conditional) and annotate pydeface row in Dependencies table" />
    <item priority="P1" target_mode="implement" description="Update INPUT_SPECIFICATION.md FSL enforcement column from 'Soft (deface stage skipped if unavailable)' to 'Hard when deface: true (pre-flight check halts pipeline); stage skipped when deface: false'" />
    <item priority="P1" target_mode="test" description="Re-express test_deface.py: update CalledProcessError propagation test (line 223-230) and FileNotFoundError test (line 213-220) to match new contract; add tests for pre-flight check and config toggle" />
  </action_items>
  <next_steps>Proceed to /implement to build the changes across config.py, deface.py, __main__.py, study.example.yaml, README.md, and INPUT_SPECIFICATION.md. Follow with /test to re-express existing deface tests and add coverage for the new pre-flight check and config toggle.</next_steps>
</brainstorm_report>
