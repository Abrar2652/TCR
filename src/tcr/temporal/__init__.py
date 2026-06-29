"""Allen-style temporal layer: a second verification axis over compound spans."""
from tcr.temporal.allen import Allen, relate, converse, TO_REACHABLE
from tcr.temporal.spans import Span, compound_spans, all_derivation_spans
from tcr.temporal.timeline import (
    TimelineSpec, TimelineReport, TimelineViolation,
    extract_timeline, check_timeline,
)

__all__ = [
    "Allen", "relate", "converse", "TO_REACHABLE",
    "Span", "compound_spans", "all_derivation_spans",
    "TimelineSpec", "TimelineReport", "TimelineViolation",
    "extract_timeline", "check_timeline",
]
