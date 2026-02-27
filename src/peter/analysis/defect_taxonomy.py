from __future__ import annotations

from enum import Enum


class CanonicalDefect(str, Enum):
    CRACKING = "CRACKING"
    PEELING_FLAKING = "PEELING_FLAKING"
    BLISTERING = "BLISTERING"
    EFFLORESCENCE = "EFFLORESCENCE"
    DAMPNESS_MOULD_ALGAE = "DAMPNESS_MOULD_ALGAE"
    DELAMINATION = "DELAMINATION"
    RUST_STAINING = "RUST_STAINING"
    POOR_COVERAGE_EXPOSED_SUBSTRATE = "POOR_COVERAGE_EXPOSED_SUBSTRATE"

    # Non-blocking visual observations
    UNEVEN_SHEEN = "UNEVEN_SHEEN"
    TEXTURE_INCONSISTENCY = "TEXTURE_INCONSISTENCY"


MUST_NOT_MISS_VISUAL_TIER1: set[CanonicalDefect] = {
    CanonicalDefect.CRACKING,
    CanonicalDefect.PEELING_FLAKING,
    CanonicalDefect.BLISTERING,
    CanonicalDefect.EFFLORESCENCE,
    CanonicalDefect.DAMPNESS_MOULD_ALGAE,
    CanonicalDefect.DELAMINATION,
}

# More visually ambiguous: require higher confidence or higher severity to block.
MUST_NOT_MISS_VISUAL_TIER2: set[CanonicalDefect] = {
    CanonicalDefect.RUST_STAINING,
    CanonicalDefect.POOR_COVERAGE_EXPOSED_SUBSTRATE,
}
