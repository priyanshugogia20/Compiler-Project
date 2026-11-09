"""
repair/verifier.py
Verification loop: apply a patch, re-run the compiler, compare diagnostics.
"""
from __future__ import annotations

import logging
from typing import List, Tuple

from compiler.models import (
    AnalysisResult, Diagnostic, RepairCandidate, Severity, VerificationStatus
)
from compiler.orchestrator import Orchestrator
from repair.patcher import apply_candidate

log = logging.getLogger(__name__)


class VerificationResult:
    """Result of verifying a single RepairCandidate."""

    def __init__(
        self,
        candidate: RepairCandidate,
        patched_result: AnalysisResult,
        original_error_count: int,
    ) -> None:
        self.candidate = candidate
        self.patched_result = patched_result
        self.original_error_count = original_error_count

        after_errors = [d for d in patched_result.diagnostics if d.severity == Severity.ERROR]
        target_ids = set(candidate.target_diagnostic_ids)

        # Did the target diagnostic disappear?
        # Diagnostic IDs are positional (D0000, D0001, ...) and are reassigned
        # on every analysis run, so they cannot be compared across runs.
        # Instead compare how many errors of each targeted code remain.
        from collections import Counter

        before_errors = [
            d for d in candidate.diagnostics_before
            if d.severity == Severity.ERROR
        ]

        before_counts = Counter(d.code for d in before_errors)
        after_counts = Counter(d.code for d in after_errors)

        target_codes = Counter(
            d.code for d in before_errors
            if d.diagnostic_id in target_ids
        )

        target_resolved = bool(target_codes) and all(
            after_counts[code] <= before_counts[code] - count
            for code, count in target_codes.items()
        )
        after_counts = Counter(d.code for d in after_errors)

        increased_codes = {
            code: (before_counts[code], after_counts[code])
            for code in before_counts.keys() | after_counts.keys()
            if after_counts[code] > before_counts[code]
        }
        regression = bool(increased_codes) and (
            len(after_errors) > original_error_count
        )

        candidate.diagnostics_after = patched_result.diagnostics
        if not patched_result.tokens and not patched_result.ast:
            candidate.verification_status = VerificationStatus.VERIFICATION_FAILED
            candidate.verification_detail = "Re-analysis produced no output."
        elif regression:
            candidate.verification_status = VerificationStatus.REGRESSION
            candidate.verification_detail = (
                f"Error counts increased by diagnostic code: {increased_codes}. "
                f"Before: {original_error_count}, after: {len(after_errors)}."
            )
        elif target_resolved and len(after_errors) == 0:
            candidate.verification_status = VerificationStatus.VERIFIED
            candidate.verification_detail = (
                "Target error resolved. No errors remain."
            )
        elif target_resolved:
            candidate.verification_status = VerificationStatus.TARGET_RESOLVED
            candidate.verification_detail = (
                f"Target error resolved, but {len(after_errors)} error(s) remain."
            )
        else:
            candidate.verification_status = VerificationStatus.VERIFICATION_FAILED
            candidate.verification_detail = (
                "Target error persists after applying the patch."
            )


def verify_candidate(
    candidate: RepairCandidate,
    original_result: AnalysisResult,
) -> VerificationResult:
    """
    Apply *candidate* to original source, rerun analysis, compare.
    Updates candidate.verification_status in place.
    """
    source = original_result.source
    candidate.diagnostics_before = list(original_result.diagnostics)
    original_errors = [d for d in original_result.diagnostics if d.severity == Severity.ERROR]

    # Apply patch
    patched_source, err = apply_candidate(source, candidate)
    if err:
        candidate.verification_status = VerificationStatus.INVALID_PATCH
        candidate.verification_detail = f"Patch application failed: {err}"
        # Return a result without running VerificationResult's __init__
        # so it doesn't recalculate and overwrite our status
        class _EarlyReturn:
            pass
        vr = _EarlyReturn()
        vr.candidate = candidate  # type: ignore
        vr.patched_result = original_result  # type: ignore
        vr.original_error_count = len(original_errors)  # type: ignore
        return vr  # type: ignore

    # Rerun compiler
    try:
        orch = Orchestrator()
        patched_result = orch.analyze(patched_source)
    except Exception as exc:
        log.exception("Re-analysis crashed: %s", exc)
        candidate.verification_status = VerificationStatus.VERIFICATION_FAILED
        candidate.verification_detail = f"Re-analysis error: {exc}"
        return VerificationResult(candidate, original_result, len(original_errors))

    vr = VerificationResult(candidate, patched_result, len(original_errors))
    log.info(
        "Candidate %s verified: %s — %s",
        candidate.candidate_id,
        candidate.verification_status.value,
        candidate.verification_detail,
    )
    return vr
