"""
JSON 내보내기 모듈
"""
import json
from pathlib import Path

from forensic.evidence.models.evidence import Evidence
from forensic.evidence.models.export import ExportConfig


class JSONExporter:
    def __init__(self, config: ExportConfig = None) -> None:
        self.config = config or ExportConfig()

    def export_json(
        self,
        evidence_list: list[Evidence],
        output_path: Path,
        include_context: bool = True,
        include_metadata: bool = True,
        include_hash: bool = True,
    ) -> Path:
        output_path = Path(output_path).with_suffix(".json")
        filtered = self._filter_by_config(evidence_list)

        data = {
            "export_config": {
                "format": "JSON",
                "include_context": include_context,
                "include_metadata": include_metadata,
                "include_hash": include_hash,
                "min_importance": self.config.min_importance,
                "exported_at": None,  # Will be set
            },
            "total_count": len(evidence_list),
            "exported_count": len(filtered),
            "evidence": [
                self._evidence_to_dict(e, include_context, include_metadata, include_hash)
                for e in filtered
            ],
        }

        with open(output_path, "w", encoding=self.config.output_encoding) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return output_path

    def _filter_by_config(self, evidence_list: list[Evidence]) -> list[Evidence]:
        return [e for e in evidence_list if self.config.should_include_evidence(e)]

    def _evidence_to_dict(
        self,
        evidence: Evidence,
        include_context: bool,
        include_metadata: bool,
        include_hash: bool,
    ) -> dict:
        data = {
            "id": evidence.id,
            "transcript_id": evidence.transcript_id,
            "segment_ids": evidence.segment_ids,
            "category": evidence.category.value,
            "description": evidence.description,
            "importance": evidence.importance,
            "speaker": evidence.speaker,
            "target": evidence.target,
            "timestamp": evidence.timestamp.isoformat() if evidence.timestamp else None,
            "content_sample": evidence.content_sample,
            "occurrence_count": evidence.occurrence_count,
            "confidence": evidence.confidence,
            "source_pattern_type": evidence.source_pattern_type,
            "source_pattern_id": evidence.source_pattern_id,
            "created_at": evidence.created_at.isoformat(),
            "validation_status": evidence.validation_status,
            "export_status": evidence.export_status,
            "related_evidence_ids": evidence.related_evidence_ids,
        }

        if include_context:
            data["context_before"] = evidence.context_before
            data["context_after"] = evidence.context_after

        if include_hash:
            data["integrity_hash"] = evidence.integrity_hash

        if include_metadata:
            data["metadata"] = evidence.metadata

        return data


__all__ = ["JSONExporter"]
