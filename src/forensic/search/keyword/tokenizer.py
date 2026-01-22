"""
Text tokenizer for search

Provides tokenization for Korean and English text with support
for different token types and morpheme analysis.
"""

import re

from forensic.search.models.query import Token, TokenType


class Tokenizer:
    """
    Text tokenizer for search operations.

    Splits text into tokens with type information.
    Supports Korean and English text.
    """

    # Korean character ranges
    KOREAN_RANGE = (0xAC00, 0xD7A3)  # Hangul syllables
    KOREAN_JAMO_RANGE = (0x1100, 0x11FF)  # Hangul Jamo

    def __init__(self, preserve_case: bool = False) -> None:
        """
        Initialize the tokenizer.

        Args:
            preserve_case: Whether to preserve original case (default: lowercase)
        """
        self._preserve_case = preserve_case

    def tokenize(self, text: str) -> list[Token]:
        """
        Tokenize text into tokens with type information.

        Args:
            text: Text to tokenize

        Returns:
            List of Token objects
        """
        if not text:
            return []

        tokens: list[Token] = []
        position = 0
        length = len(text)

        while position < length:
            char = text[position]

            if char.isspace():
                # Whitespace
                end = self._consume_while(text, position, str.isspace)
                tokens.append(
                    Token(
                        text=text[position:end],
                        start=position,
                        end=end,
                        token_type=TokenType.WHITESPACE,
                    )
                )
                position = end

            elif char.isdigit():
                # Number
                end = self._consume_while(text, position, str.isdigit)
                tokens.append(
                    Token(
                        text=text[position:end],
                        start=position,
                        end=end,
                        token_type=TokenType.NUMBER,
                    )
                )
                position = end

            elif char in ".,!?;:()[]{}\"'`~@#$%^&*|\\/<>+-=":
                # Punctuation
                tokens.append(
                    Token(
                        text=char,
                        start=position,
                        end=position + 1,
                        token_type=TokenType.PUNCTUATION,
                    )
                )
                position += 1

            elif self._is_korean(char):
                # Korean text
                end = self._consume_korean(text, position)
                token_text = text[position:end]
                tokens.append(
                    Token(
                        text=token_text if self._preserve_case else token_text.lower(),
                        start=position,
                        end=end,
                        token_type=TokenType.WORD,
                    )
                )
                position = end

            elif char.isalpha():
                # English/Latin text
                end = self._consume_while(text, position, str.isalpha)
                token_text = text[position:end]
                tokens.append(
                    Token(
                        text=token_text if self._preserve_case else token_text.lower(),
                        start=position,
                        end=end,
                        token_type=TokenType.WORD,
                    )
                )
                position = end

            else:
                # Special character
                tokens.append(
                    Token(
                        text=char,
                        start=position,
                        end=position + 1,
                        token_type=TokenType.SPECIAL,
                    )
                )
                position += 1

        return tokens

    def tokenize_words(self, text: str) -> list[str]:
        """
        Tokenize text into words only (no whitespace or punctuation).

        Args:
            text: Text to tokenize

        Returns:
            List of word strings
        """
        tokens = self.tokenize(text)
        return [t.text for t in tokens if t.token_type == TokenType.WORD]

    def tokenize_with_positions(
        self,
        text: str,
    ) -> list[tuple[str, int, int]]:
        """
        Tokenize text and return (word, start, end) tuples.

        Args:
            text: Text to tokenize

        Returns:
            List of (word, start, end) tuples
        """
        tokens = self.tokenize(text)
        return [(t.text, t.start, t.end) for t in tokens if t.token_type == TokenType.WORD]

    def _consume_while(
        self,
        text: str,
        position: int,
        predicate,
    ) -> int:
        """Consume characters while predicate is true."""
        end = position
        length = len(text)

        while end < length and predicate(text[end]):
            end += 1

        return end

    def _consume_korean(self, text: str, position: int) -> int:
        """Consume Korean characters."""
        end = position
        length = len(text)

        while end < length:
            char = text[end]
            if self._is_korean(char):
                end += 1
            elif char.isspace() or char in ".,!?;:":
                # Allow some separators within Korean phrases
                end += 1
            else:
                break

        return end

    def _is_korean(self, char: str) -> bool:
        """Check if a character is Korean."""
        code = ord(char)
        return (
            self.KOREAN_RANGE[0] <= code <= self.KOREAN_RANGE[1]
            or self.KOREAN_JAMO_RANGE[0] <= code <= self.KOREAN_JAMO_RANGE[1]
        )


class KoreanTokenizer(Tokenizer):
    """
    Specialized tokenizer for Korean text.

    Provides better handling of Korean text patterns.
    """

    # Common Korean particles (josa)
    JOSA_PATTERN = re.compile(
        r"(이|가|을|를|의|에|에서|으로|로|과|와|도|만|까지|부터|보다|처럼|같이|한테|께|께서|이나|나|이랑|랑|이다|다)$"
    )

    def __init__(self, remove_josa: bool = False, preserve_case: bool = False) -> None:
        """
        Initialize the Korean tokenizer.

        Args:
            remove_josa: Whether to remove Korean particles from tokens
            preserve_case: Whether to preserve original case
        """
        super().__init__(preserve_case=preserve_case)
        self._remove_josa = remove_josa

    def tokenize(self, text: str) -> list[Token]:
        """
        Tokenize Korean text with special handling.

        Args:
            text: Text to tokenize

        Returns:
            List of Token objects
        """
        tokens = super().tokenize(text)

        if self._remove_josa:
            tokens = self._strip_josa(tokens)

        return tokens

    def _strip_josa(self, tokens: list[Token]) -> list[Token]:
        """Remove Korean particles from tokens."""
        result: list[Token] = []

        for token in tokens:
            if token.token_type == TokenType.WORD:
                # Check if token ends with josa
                match = self.JOSA_PATTERN.search(token.text)
                if match:
                    # Strip the josa
                    new_text = token.text[: match.start()]
                    if new_text:
                        result.append(
                            Token(
                                text=new_text,
                                start=token.start,
                                end=token.start + len(new_text),
                                token_type=TokenType.WORD,
                            )
                        )
                    # Add the josa as a separate token if non-empty
                    josa_text = match.group()
                    if josa_text:
                        result.append(
                            Token(
                                text=josa_text,
                                start=token.start + len(new_text),
                                end=token.end,
                                token_type=TokenType.WORD,
                            )
                        )
                else:
                    result.append(token)
            else:
                result.append(token)

        return result


class NgramTokenizer:
    """
    N-gram tokenizer for fuzzy matching and substring search.

    Creates character n-grams for text similarity matching.
    """

    def __init__(self, n: int = 2) -> None:
        """
        Initialize the n-gram tokenizer.

        Args:
            n: Size of n-grams (default: 2 for bigrams)
        """
        self._n = max(1, min(n, 5))  # Limit to 1-5

    def tokenize(self, text: str) -> list[str]:
        """
        Create n-grams from text.

        Args:
            text: Text to create n-grams from

        Returns:
            List of n-gram strings
        """
        if not text or len(text) < self._n:
            return []

        text = text.lower()
        ngrams: list[str] = []

        for i in range(len(text) - self._n + 1):
            ngram = text[i : i + self._n]
            ngrams.append(ngram)

        return ngrams

    def get_ngrams(self, text: str, n: int | None = None) -> list[str]:
        """
        Get n-grams with custom n value.

        Args:
            text: Text to process
            n: N-gram size (uses default if not specified)

        Returns:
            List of n-gram strings
        """
        if n is not None:
            old_n = self._n
            self._n = max(1, min(n, 5))
            result = self.tokenize(text)
            self._n = old_n
            return result

        return self.tokenize(text)


__all__ = [
    "Tokenizer",
    "KoreanTokenizer",
    "NgramTokenizer",
]
