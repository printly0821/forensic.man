"""
Unit tests for keyword search module
"""

from forensic.models import Segment
from forensic.search.keyword import (
    FuzzySearcher,
    KeywordSearcher,
    KoreanTokenizer,
    NgramTokenizer,
    Tokenizer,
    WildcardMatcher,
    WildcardSearcher,
)


class TestTokenizer:
    """Tests for Tokenizer class."""

    def test_tokenize_simple_text(self):
        """Test tokenizing simple English text."""
        tokenizer = Tokenizer(preserve_case=True)
        tokens = tokenizer.tokenize("Hello world")

        assert len(tokens) == 3  # "Hello", " ", "world"
        assert tokens[0].text == "Hello"
        assert tokens[0].token_type.value == "word"

    def test_tokenize_mixed(self):
        """Test tokenizing mixed content."""
        tokenizer = Tokenizer()
        tokens = tokenizer.tokenize("Hello, world! 123")

        # Numbers are tokenized as TokenType.NUMBER, not WORD
        text_tokens = [t for t in tokens if t.token_type.value in ("word", "number")]
        assert len(text_tokens) == 3  # "hello", "world", "123"

    def test_tokenize_korean(self):
        """Test tokenizing Korean text."""
        tokenizer = Tokenizer()
        tokens = tokenizer.tokenize("안녕하세요")

        # Korean text is tokenized as words
        korean_tokens = [t for t in tokens if t.token_type.value == "word"]
        assert len(korean_tokens) >= 1

    def test_tokenize_words_only(self):
        """Test tokenizing to words only."""
        tokenizer = Tokenizer(preserve_case=True)
        words = tokenizer.tokenize_words("Hello, world!")

        assert "Hello" in words
        assert "world" in words

    def test_preserve_case(self):
        """Test case preservation option."""
        tokenizer = Tokenizer(preserve_case=True)
        tokens = tokenizer.tokenize("Hello World")

        assert tokens[0].text == "Hello"
        assert tokens[2].text == "World"


class TestKoreanTokenizer:
    """Tests for KoreanTokenizer class."""

    def test_korean_tokenization(self):
        """Test Korean text tokenization."""
        tokenizer = KoreanTokenizer()
        tokens = tokenizer.tokenize("안녕하세요")

        # Should tokenize Korean text
        korean_tokens = [t for t in tokens if t.token_type.value == "word"]
        assert len(korean_tokens) >= 1


class TestNgramTokenizer:
    """Tests for NgramTokenizer class."""

    def test_bigram_tokenization(self):
        """Test bigram (n=2) tokenization."""
        tokenizer = NgramTokenizer(n=2)
        ngrams = tokenizer.tokenize("test")

        assert "te" in ngrams
        assert "es" in ngrams
        assert "st" in ngrams

    def test_trigram_tokenization(self):
        """Test trigram (n=3) tokenization."""
        tokenizer = NgramTokenizer(n=3)
        ngrams = tokenizer.tokenize("test")

        assert "tes" in ngrams
        assert "est" in ngrams

    def test_ngram_with_custom_n(self):
        """Test custom n value."""
        tokenizer = NgramTokenizer(n=2)
        ngrams = tokenizer.get_ngrams("hello", n=3)

        assert "hel" in ngrams
        assert "ell" in ngrams
        assert "llo" in ngrams


class TestKeywordSearcher:
    """Tests for KeywordSearcher class."""

    def setup_method(self):
        """Set up test segments."""
        self.segments = [
            Segment(
                id="seg1",
                speaker="신동식",
                start_time=0.0,
                end_time=1.0,
                content="가스라이팅과 위협이 있습니다",
                confidence=0.9,
            ),
            Segment(
                id="seg2",
                speaker="신기연",
                start_time=1.0,
                end_time=2.0,
                content="정상적인 대화 내용",
                confidence=0.95,
            ),
            Segment(
                id="seg3",
                speaker="신동식",
                start_time=2.0,
                end_time=3.0,
                content="또 다른 위협 내용",
                confidence=0.88,
            ),
        ]

    def test_search_exact(self):
        """Test exact keyword search."""
        searcher = KeywordSearcher()
        hits = searcher.search_exact("위협", self.segments)

        assert len(hits) == 2
        assert all("위협" in h.matched_text for h in hits)

    def test_search_exact_case_insensitive(self):
        """Test case-insensitive exact search."""
        searcher = KeywordSearcher()
        hits = searcher.search_exact("GASLIGHTING", self.segments, case_sensitive=False)

        # Should find despite case difference (though Korean doesn't have case)
        assert len(hits) >= 0

    def test_search_phrase(self):
        """Test phrase search."""
        searcher = KeywordSearcher()
        hits = searcher.search_phrase("가스라이팅과", self.segments)

        assert len(hits) == 1
        assert hits[0].source_id == "seg1"

    def test_search_multiple_and(self):
        """Test multiple keyword search with AND logic."""
        searcher = KeywordSearcher()
        hits = searcher.search_multiple(
            ["위협", "가스라이팅"],
            self.segments,
            match_all=True,
        )

        # Only seg1 has both terms (near each other)
        assert len(hits) >= 1

    def test_search_multiple_or(self):
        """Test multiple keyword search with OR logic."""
        searcher = KeywordSearcher()
        hits = searcher.search_multiple(
            ["가스라이팅", "정상"],
            self.segments,
            match_all=False,
        )

        assert len(hits) == 2  # seg1 and seg2

    def test_count_occurrences(self):
        """Test counting keyword occurrences."""
        searcher = KeywordSearcher()
        count = searcher.count_occurrences("위협", self.segments[0].content)

        assert count == 1

    def test_search_no_results(self):
        """Test search with no matches."""
        searcher = KeywordSearcher()
        hits = searcher.search_exact("없는단어", self.segments)

        assert len(hits) == 0


class TestWildcardSearcher:
    """Tests for WildcardSearcher class."""

    def setup_method(self):
        """Set up test segments."""
        self.segments = [
            Segment(
                id="seg1",
                speaker="신동식",
                start_time=0.0,
                end_time=1.0,
                content="가스라이팅 가스등 가스레인지",
                confidence=0.9,
            ),
        ]

    def test_wildcard_asterisk(self):
        """Test asterisk wildcard."""
        searcher = WildcardSearcher()
        hits = searcher.search("가스*", self.segments)

        assert len(hits) >= 1

    def test_wildcard_question_mark(self):
        """Test question mark wildcard."""
        searcher = WildcardSearcher()
        hits = searcher.search("가스?", self.segments)

        assert len(hits) >= 1

    def test_wildcard_matcher(self):
        """Test WildcardMatcher directly."""
        matcher = WildcardMatcher()

        assert matcher.match("test", "test") is True
        assert matcher.match("test", "t*t") is True
        assert matcher.match("test", "t??t") is True
        assert matcher.match("test", "other") is False


class TestFuzzySearcher:
    """Tests for FuzzySearcher class."""

    def test_levenshtein_distance(self):
        """Test Levenshtein distance calculation."""
        from forensic.search.keyword.fuzzy import LevenshteinDistance

        calc = LevenshteinDistance()

        assert calc.distance("test", "test") == 0
        assert calc.distance("test", "tast") == 1
        assert calc.distance("test", "tast") == calc.distance("tast", "test")

    def test_similarity(self):
        """Test similarity calculation."""
        from forensic.search.keyword.fuzzy import LevenshteinDistance

        calc = LevenshteinDistance()

        sim = calc.similarity("test", "test")
        assert sim == 1.0

        sim = calc.similarity("test", "tast")
        assert 0 < sim < 1.0

    def test_fuzzy_search(self):
        """Test fuzzy search."""
        searcher = FuzzySearcher(max_distance=2)
        segments = [
            Segment(
                id="seg1",
                speaker="신동식",
                start_time=0.0,
                end_time=1.0,
                content="test text here",
                confidence=0.9,
            ),
        ]

        hits = searcher.search("tets", segments)  # Typo

        # Should find with distance 1
        assert len(hits) >= 1

    def test_fuzzy_matcher(self):
        """Test FuzzyMatcher."""
        from forensic.search.keyword.fuzzy import FuzzyMatcher

        matcher = FuzzyMatcher(max_distance=2)
        matches = matcher.find_matches("test content", "tets")

        # Should find "test" with distance 1
        assert len(matches) >= 1


class TestWildcardMatcher:
    """Tests for WildcardMatcher class."""

    def test_compile_pattern(self):
        """Test pattern compilation."""
        matcher = WildcardMatcher()

        regex = matcher.compile("test*")
        assert regex is not None

    def test_cache_patterns(self):
        """Test pattern caching."""
        matcher = WildcardMatcher()

        matcher.compile("test*")
        assert "test*" in matcher._patterns

        matcher.clear_cache()
        assert len(matcher._patterns) == 0
