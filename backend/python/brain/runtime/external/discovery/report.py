"""Human-review dossier projection."""

from brain.runtime.external.discovery.models import CandidateReviewDossier, DiscoveryCandidate


def build_review_dossier(candidate: DiscoveryCandidate) -> CandidateReviewDossier:
    return CandidateReviewDossier(candidate=candidate)
