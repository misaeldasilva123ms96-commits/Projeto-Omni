"""Non-executable external API discovery control plane."""

from brain.runtime.external.discovery.client import DiscoveryClient
from brain.runtime.external.discovery.models import CandidateReviewDossier, DiscoveryCandidate
from brain.runtime.external.discovery.report import build_review_dossier
from brain.runtime.external.discovery.search import search_candidates
from brain.runtime.external.discovery.sources import build_discovery_source_registry

__all__ = [
    "CandidateReviewDossier",
    "DiscoveryCandidate",
    "DiscoveryClient",
    "build_discovery_source_registry",
    "build_review_dossier",
    "search_candidates",
]
