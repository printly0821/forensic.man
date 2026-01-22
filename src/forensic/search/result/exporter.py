"""
Search result exporter

Provides export functionality for search results in various formats.
"""

import json
from csv import DictWriter
from datetime import datetime
from pathlib import Path
from typing import Any

from forensic.search.models import SearchHit


class ResultExporter:
    """
    Exporter for search results.

    Exports search results to various file formats including
    JSON, CSV, and Markdown.
    """

    def __init__(self) -> None:
        """Initialize the result exporter."""

    def export_json(
        self,
        hits: list[SearchHit],
        output_path: Path | str,
        indent: int = 2,
    ) -> Path:
        """
        Export search results to JSON format.

        Args:
            hits: List of search hits to export
            output_path: Path to output file
            indent: JSON indentation level

        Returns:
            Path to the exported file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = [self._hit_to_dict(hit) for hit in hits]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)

        return output_path

    def export_csv(
        self,
        hits: list[SearchHit],
        output_path: Path | str,
    ) -> Path:
        """
        Export search results to CSV format.

        Args:
            hits: List of search hits to export
            output_path: Path to output file

        Returns:
            Path to the exported file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not hits:
            # Create empty CSV with headers
            with open(output_path, "w", encoding="utf-8", newline="") as f:
                writer = DictWriter(
                    f,
                    fieldnames=[
                        "id",
                        "source_type",
                        "source_id",
                        "score",
                        "matched_text",
                        "speaker",
                        "timestamp",
                    ],
                )
                writer.writeheader()
            return output_path

        # Convert hits to dictionaries
        data = [self._hit_to_dict(hit) for hit in hits]

        # Flatten dictionaries for CSV
        fieldnames = self._get_csv_fieldnames(data)

        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for row in data:
                # Flatten nested structures
                flat_row = self._flatten_dict(row)
                writer.writerow(flat_row)

        return output_path

    def export_markdown(
        self,
        hits: list[SearchHit],
        output_path: Path | str,
        title: str = "Search Results",
    ) -> Path:
        """
        Export search results to Markdown format.

        Args:
            hits: List of search hits to export
            output_path: Path to output file
            title: Title for the document

        Returns:
            Path to the exported file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            f"# {title}\n",
            f"*Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            f"*Total results: {len(hits)}*\n",
            "---\n",
        ]

        for i, hit in enumerate(hits, 1):
            lines.append(f"## Result {i}\n")
            lines.append(f"**Score:** {hit.score:.2f}\n")
            lines.append(f"**Source:** {hit.source_type} ({hit.source_id})\n")

            if hit.speaker:
                lines.append(f"**Speaker:** {hit.speaker}\n")

            if hit.timestamp:
                lines.append(f"**Timestamp:** {hit.timestamp}\n")

            lines.append("\n**Matched Text:**\n")
            lines.append(f"> {hit.matched_text}\n")

            if hit.context_before or hit.context_after:
                lines.append("\n**Context:**\n")
                if hit.context_before:
                    lines.append(f"...{hit.context_before}")
                lines.append(f"**{hit.matched_text}**")
                if hit.context_after:
                    lines.append(f"{hit.context_after}...")
                lines.append("")

            lines.append("---\n")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return output_path

    def export_html(
        self,
        hits: list[SearchHit],
        output_path: Path | str,
        title: str = "Search Results",
    ) -> Path:
        """
        Export search results to HTML format.

        Args:
            hits: List of search hits to export
            output_path: Path to output file
            title: Title for the document

        Returns:
            Path to the exported file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        html_parts = [
            "<!DOCTYPE html>",
            '<html lang="en">',
            "<head>",
            f"<title>{title}</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }",
            ".hit { border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 5px; }",
            ".score { color: #666; font-size: 0.9em; }",
            ".matched { background-color: #fff3cd; padding: 2px 4px; }",
            ".context { color: #555; font-style: italic; }",
            ".metadata { margin-top: 10px; font-size: 0.9em; color: #666; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>{title}</h1>",
            f"<p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Results: {len(hits)}</p>",
        ]

        for hit in hits:
            html_parts.append('<div class="hit">')
            html_parts.append(f"<h3>Result: {hit.source_id}</h3>")
            html_parts.append(
                f'<p class="score">Score: {hit.score:.2f} | Type: {hit.source_type}</p>'
            )

            if hit.speaker:
                html_parts.append(f"<p><strong>Speaker:</strong> {hit.speaker}</p>")

            html_parts.append(f'<p><span class="matched">{hit.matched_text}</span></p>')

            if hit.context_before or hit.context_after:
                html_parts.append('<p class="context">')
                if hit.context_before:
                    html_parts.append(f"...{hit.context_before}")
                html_parts.append(f"<strong>{hit.matched_text}</strong>")
                if hit.context_after:
                    html_parts.append(f"{hit.context_after}...")
                html_parts.append("</p>")

            html_parts.append("</div>")

        html_parts.extend(
            [
                "</body>",
                "</html>",
            ]
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(html_parts))

        return output_path

    def export(
        self,
        hits: list[SearchHit],
        output_path: Path | str,
        format: str = "json",
        **kwargs,
    ) -> Path:
        """
        Export search results to the specified format.

        Args:
            hits: List of search hits to export
            output_path: Path to output file
            format: Export format (json, csv, markdown, html)
            **kwargs: Additional arguments for specific exporters

        Returns:
            Path to the exported file
        """
        format = format.lower()

        if format == "json":
            return self.export_json(hits, output_path, **kwargs)
        elif format == "csv":
            return self.export_csv(hits, output_path, **kwargs)
        elif format in ("markdown", "md"):
            return self.export_markdown(hits, output_path, **kwargs)
        elif format == "html":
            return self.export_html(hits, output_path, **kwargs)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _hit_to_dict(self, hit: SearchHit) -> dict[str, Any]:
        """Convert a SearchHit to a dictionary for export."""
        return {
            "id": hit.id,
            "source_type": hit.source_type,
            "source_id": hit.source_id,
            "score": hit.score,
            "matched_text": hit.matched_text,
            "highlighted_text": hit.highlighted_text,
            "context_before": hit.context_before,
            "context_after": hit.context_after,
            "speaker": hit.speaker,
            "timestamp": hit.timestamp.isoformat() if hit.timestamp else None,
            "file_path": str(hit.file_path) if hit.file_path else None,
            "position": {
                "start": hit.position.start,
                "end": hit.position.end,
            },
            "metadata": hit.metadata,
        }

    def _get_csv_fieldnames(self, data: list[dict]) -> list[str]:
        """Get fieldnames for CSV export."""
        fieldnames = set()

        for row in data:
            flat = self._flatten_dict(row)
            fieldnames.update(flat.keys())

        return sorted(fieldnames)

    def _flatten_dict(
        self,
        d: dict[str, Any],
        parent_key: str = "",
        sep: str = ".",
    ) -> dict[str, Any]:
        """Flatten nested dictionaries."""
        items: list[tuple[str, Any]] = []

        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k

            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))

        return dict(items)


__all__ = [
    "ResultExporter",
]
