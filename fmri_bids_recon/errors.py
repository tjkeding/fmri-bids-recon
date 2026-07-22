"""Exception hierarchy for fmri-bids-recon.

BidsReconError
    GuardError  (BLOCKING)
        VersionFloorError
        AnatSuffixError
        PhaseEncodingError
        FieldmapCoverageError
        LabelCollisionError
        EmptyLabelError
        LabelDriftError
        TaskRenameError
        PhysioAssociationError
        ConversionError
        PhysioParseError
        NavigatorDropError
    ConfigError
    ToolUnavailableError
    ReviewFlag  (non-blocking, collected only)
SpecFinding  (dataclass, not an exception)
"""

from dataclasses import dataclass


class BidsReconError(Exception):
    """Base exception for all fmri-bids-recon errors.

    Parameters
    ----------
    message : str
        Human-readable error description.
    context : dict, optional
        Structured key/value payload for logging and downstream handling.
    """

    def __init__(self, message: str = "", context: dict | None = None) -> None:
        super().__init__(message)
        self.context: dict = context if context is not None else {}


class GuardError(BidsReconError):
    """Base for all BLOCKING assertion failures.

    Raising a GuardError halts pipeline execution for the affected subject/run.
    All subclasses accept a context dict as their primary argument.
    """


class VersionFloorError(GuardError):
    """dcm2niix version is below the verified minimum floor."""


class AnatSuffixError(GuardError):
    """Physics-derived verdict disagrees with the anatomical name token."""


class PhaseEncodingError(GuardError):
    """Phase-encoding pair members are not opposite, or the dir- label
    disagrees with the _PA/_AP name token."""


class FieldmapCoverageError(GuardError):
    """Orphan fieldmap pair, or a run precedes all available pairs."""


class LabelCollisionError(GuardError):
    """Two distinct series descriptions resolve to the same BIDS label."""


class EmptyLabelError(GuardError):
    """A series description strips to an empty BIDS label."""


class LabelDriftError(GuardError):
    """A known series description re-derives to a different label than
    previously recorded."""


class TaskRenameError(GuardError):
    """Old task label is absent and a new label is present with a matching
    acquisition signature, indicating an undeclared task rename."""


class PhysioAssociationError(GuardError):
    """Physio file geometry does not match its candidate BOLD run's."""


class ConversionError(GuardError):
    """dcm2niix returned a non-zero exit status."""


class PhysioParseError(GuardError):
    """A PMU physio log carried no usable sampling rate."""


class NavigatorDropError(GuardError):
    """An EPI-physics multi-volume series would be dropped as a navigator."""


class ConfigError(BidsReconError):
    """Malformed configuration or no participants resolved after expansion."""


class ToolUnavailableError(BidsReconError):
    """An external tool crashed, is absent, or returned an unparseable result.

    The dataset is UNCHECKED. This is NOT a pass.
    """


class ReviewFlag(BidsReconError):
    """NON-blocking advisory flag.

    ReviewFlags are collected and reported but never raised as exceptions
    during normal pipeline execution.
    """


@dataclass
class SpecFinding:
    """Post-hoc BIDS spec-check result from the validator.

    NOT an exception. Carries the validator's verdict about a tree that
    is already written to disk.
    """

    severity: str
    code: str
    location: str
    message: str = ""
