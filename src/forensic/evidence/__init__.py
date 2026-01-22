"""
forensic.evidence 패키지

증거 추출, 맥락 보존, 검증, 내보내기 기능을 제공합니다.
"""

from forensic.evidence.context import (
    ContextPreserver,
    FlowExtractor,
    SegmentLinker,
)
from forensic.evidence.exporter import (
    ChainExporter,
    JSONExporter,
    LegalExporter,
)
from forensic.evidence.extractor import (
    EvidenceExtractor,
    PatternMatch,
    assign_importance,
    categorize,
    generate_chain_id,
    generate_evidence_id,
    get_categorizer,
    get_id_generator,
    get_importance_assigner,
)
from forensic.evidence.models.chain import ChainBuilder, EvidenceChain
from forensic.evidence.models.evidence import (
    Evidence,
    EvidenceCategory,
    create_evidence,
)
from forensic.evidence.models.export import (
    ChainOfCustody,
    ExportConfig,
    LegalDocument,
)
from forensic.evidence.models.validation import (
    MergeProposal,
    ValidationReport,
    ValidationResult,
)
from forensic.evidence.validator import (
    DuplicateDetector,
    EvidenceValidator,
    IntegrityChecker,
    ReportGenerator,
)

__all__ = [
    "EvidenceCategory",
    "Evidence",
    "create_evidence",
    "ValidationResult",
    "ValidationReport",
    "MergeProposal",
    "EvidenceChain",
    "ChainBuilder",
    "ExportConfig",
    "LegalDocument",
    "ChainOfCustody",
    "EvidenceExtractor",
    "PatternMatch",
    "get_id_generator",
    "generate_evidence_id",
    "generate_chain_id",
    "get_importance_assigner",
    "assign_importance",
    "get_categorizer",
    "categorize",
    "ContextPreserver",
    "FlowExtractor",
    "SegmentLinker",
    "EvidenceValidator",
    "IntegrityChecker",
    "DuplicateDetector",
    "ReportGenerator",
    "JSONExporter",
    "LegalExporter",
    "ChainExporter",
]

__version__ = "1.0.0"
