"""
무결성 검증 모듈
"""
import hashlib
from datetime import datetime

from forensic.evidence.models.evidence import Evidence
from forensic.models.transcript import Segment, Transcript


class IntegrityChecker:
    HASH_ALGORITHM = "sha256"

    def compute_hash(self, evidence: Evidence) -> str:
        hash_fields = [
            evidence.id,
            evidence.transcript_id,
            ",".join(sorted(evidence.segment_ids)),
            evidence.category.value,
            evidence.description,
            evidence.content_sample,
            evidence.speaker or "",
            evidence.target or "",
        ]
        if evidence.timestamp:
            hash_fields.append(evidence.timestamp.isoformat())
        hash_string = "|".join(hash_fields)
        hash_obj = hashlib.sha256(hash_string.encode("utf-8"))
        return hash_obj.hexdigest()

    def compute_segment_hash(self, segment: Segment) -> str:
        hash_string = (
            f"{segment.id}|{segment.speaker}|{segment.start_time}|"
            f"{segment.end_time}|{segment.content}"
        )
        return hashlib.sha256(hash_string.encode("utf-8")).hexdigest()

    def compute_transcript_hash(self, transcript: Transcript) -> str:
        hash_string = (
            f"{transcript.id}|"
            f"{transcript.file_path}|"
            f"{transcript.date.isoformat() if transcript.date else ''}|"
            f"{len(transcript.segments)}"
        )
        return hashlib.sha256(hash_string.encode("utf-8")).hexdigest()

    def verify_integrity(self, evidence: Evidence, expected_hash: str = "") -> bool:
        if not expected_hash:
            expected_hash = evidence.integrity_hash
        if not expected_hash:
            return False
        computed_hash = self.compute_hash(evidence)
        return computed_hash == expected_hash

    def verify_timestamp(self, evidence: Evidence, original_segment: Segment) -> bool:
        if not evidence.timestamp:
            return True
        segment_time = datetime.fromtimestamp(original_segment.start_time)
        evidence_time = evidence.timestamp
        time_diff = abs((evidence_time - segment_time).total_seconds())
        return time_diff <= 1.0

    def verify_source_reference(self, evidence: Evidence, transcript: Transcript) -> bool:
        if evidence.transcript_id != transcript.id:
            return False
        transcript_segment_ids = {s.id for s in transcript.segments}
        return all(seg_id in transcript_segment_ids for seg_id in evidence.segment_ids)

    def compute_full_integrity_hash(self, evidence_list: list[Evidence]) -> str:
        sorted_evidence = sorted(evidence_list, key=lambda e: e.id)
        hash_values = [self.compute_hash(e) for e in sorted_evidence]
        combined = "|".join(hash_values)
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()


__all__ = ["IntegrityChecker"]
