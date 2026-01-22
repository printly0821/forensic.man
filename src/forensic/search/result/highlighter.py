"""
Search result highlighter

Provides highlighting of matched terms in search results.
"""

import re

from forensic.search.models import Match, SearchHit
from forensic.search.models.result import ContextPreview


class Highlighter:
    """
    Highlighter for search results.

    Adds highlighting markup to matched text in search results.
    """

    def __init__(
        self,
        tag: str = "mark",
        attrs: dict | None = None,
    ) -> None:
        """
        Initialize the highlighter.

        Args:
            tag: HTML tag name for highlighting (default: "mark")
            attrs: Additional attributes for the highlight tag
        """
        self._tag = tag
        self._attrs = attrs or {}

    def highlight(
        self,
        text: str,
        matches: list[Match],
        tag: str | None = None,
    ) -> str:
        """
        Highlight matched portions of text.

        Args:
            text: Text to highlight
            matches: List of matches to highlight
            tag: Override default tag for this highlight

        Returns:
            Text with highlighting markup
        """
        if not matches:
            return text

        highlight_tag = tag or self._tag
        attrs_str = self._build_attrs_str()

        # Sort matches by position (reverse order for insertion)
        sorted_matches = sorted(
            matches,
            key=lambda m: m.position.start,
            reverse=True,
        )

        result = text

        for match in sorted_matches:
            start = match.position.start
            end = match.position.end

            if start < 0 or end > len(result):
                continue

            before = result[:start]
            matched = result[start:end]
            after = result[end:]

            highlighted = f"<{highlight_tag}{attrs_str}>{matched}</{highlight_tag}>"
            result = before + highlighted + after

        return result

    def highlight_keywords(
        self,
        text: str,
        keywords: list[str],
        case_sensitive: bool = False,
    ) -> str:
        """
        Highlight keywords in text.

        Args:
            text: Text to highlight
            keywords: List of keywords to highlight
            case_sensitive: Whether to match case

        Returns:
            Text with highlighted keywords
        """
        if not keywords:
            return text

        result = text
        attrs_str = self._build_attrs_str()

        # Sort keywords by length (longest first) to handle overlapping
        sorted_keywords = sorted(keywords, key=len, reverse=True)

        for keyword in sorted_keywords:
            if not keyword:
                continue

            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = re.compile(re.escape(keyword), flags)

            def replace_fn(m: re.Match) -> str:
                return f"<{self._tag}{attrs_str}>{m.group()}</{self._tag}>"

            result = pattern.sub(replace_fn, result)

        return result

    def highlight_regex(
        self,
        text: str,
        pattern: str,
    ) -> str:
        """
        Highlight regex matches in text.

        Args:
            text: Text to highlight
            pattern: Regular expression pattern

        Returns:
            Text with highlighted matches
        """
        try:
            regex = re.compile(pattern)
        except re.error:
            return text

        attrs_str = self._build_attrs_str()

        def replace_fn(m: re.Match) -> str:
            return f"<{self._tag}{attrs_str}>{m.group()}</{self._tag}>"

        return regex.sub(replace_fn, text)

    def remove_highlighting(self, text: str) -> str:
        """
        Remove highlighting markup from text.

        Args:
            text: Text with highlighting

        Returns:
            Plain text without highlighting markup
        """
        # Remove highlight tags
        pattern = re.compile(rf"<{self._tag}[^>]*>(.*?)</{self._tag}>")
        return pattern.sub(r"\1", text)

    def get_plain_text(self, text: str) -> str:
        """
        Get plain text version of highlighted text.

        Args:
            text: Text with potential highlighting

        Returns:
            Plain text
        """
        return self.remove_highlighting(text)

    def create_context_preview(
        self,
        text: str,
        match_start: int,
        match_end: int,
        before_chars: int = 100,
        after_chars: int = 100,
    ) -> ContextPreview:
        """
        Create a context preview around a match.

        Args:
            text: Full text
            match_start: Start position of match
            match_end: End position of match
            before_chars: Characters of context before match
            after_chars: Characters of context after match

        Returns:
            ContextPreview with before, matched, and after text
        """
        before_start = max(0, match_start - before_chars)
        before_text = text[before_start:match_start]

        matched_text = text[match_start:match_end]

        after_end = min(len(text), match_end + after_chars)
        after_text = text[match_end:after_end]

        # Add ellipsis if truncated
        if before_start > 0:
            before_text = "..." + before_text

        if after_end < len(text):
            after_text = after_text + "..."

        return ContextPreview(
            before_text=before_text,
            matched_text=matched_text,
            after_text=after_text,
            highlighted=f"{before_text}[{matched_text}]{after_text}",
        )

    def highlight_hit(
        self,
        hit: SearchHit,
        tag: str | None = None,
    ) -> SearchHit:
        """
        Add highlighting to a search hit.

        Args:
            hit: Search hit to highlight
            tag: Override default tag

        Returns:
            New SearchHit with highlighted text
        """
        highlighted_text = self.highlight(
            hit.matched_text,
            hit.matches,
            tag,
        )

        # Create new hit with highlighting
        hit_dict = hit.model_dump()
        hit_dict["highlighted_text"] = highlighted_text

        return SearchHit(**hit_dict)

    def _build_attrs_str(self) -> str:
        """Build attribute string for highlight tag."""
        if not self._attrs:
            return ""

        attrs = [f'{k}="{v}"' for k, v in self._attrs.items()]
        return " " + " ".join(attrs) if attrs else ""


class AnsiHighlighter(Highlighter):
    """
    ANSI escape code based highlighter for terminal output.

    Uses ANSI color codes instead of HTML tags.
    """

    # ANSI color codes
    COLORS = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "bold": "\033[1m",
        "underline": "\033[4m",
        "reset": "\033[0m",
    }

    def __init__(
        self,
        color: str = "yellow",
        bold: bool = True,
    ) -> None:
        """
        Initialize the ANSI highlighter.

        Args:
            color: Color name for highlighting
            bold: Whether to use bold text
        """
        super().__init__()
        self._color = color
        self._bold = bold

    def highlight(
        self,
        text: str,
        matches: list[Match],
        _tag: str | None = None,
    ) -> str:
        """
        Highlight matches using ANSI codes.

        Args:
            text: Text to highlight
            matches: List of matches
            _tag: Ignored (for compatibility with base class)

        Returns:
            Text with ANSI highlighting
        """
        if not matches:
            return text

        # Build ANSI codes
        start_code = self.COLORS.get(self._color, "")
        if self._bold:
            start_code = self.COLORS["bold"] + start_code
        end_code = self.COLORS["reset"]

        # Sort matches by position (reverse order)
        sorted_matches = sorted(
            matches,
            key=lambda m: m.position.start,
            reverse=True,
        )

        result = text

        for match in sorted_matches:
            start = match.position.start
            end = match.position.end

            if start < 0 or end > len(result):
                continue

            before = result[:start]
            matched = result[start:end]
            after = result[end:]

            highlighted = f"{start_code}{matched}{end_code}"
            result = before + highlighted + after

        return result


__all__ = [
    "Highlighter",
    "AnsiHighlighter",
]
