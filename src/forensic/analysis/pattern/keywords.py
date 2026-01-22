"""
Keyword dictionaries for pattern detection.

Contains Korean language patterns for detecting gaslighting,
emotional manipulation, and threat patterns in forensic transcripts.
"""


class KeywordDictionary:
    """
    Centralized keyword dictionary for pattern detection.

    Contains Korean keywords for various manipulation patterns
    commonly found in forensic transcript analysis.
    """

    # Gaslighting pattern keywords
    GASLIGHTING = {
        "DENIAL": [
            "그런 적 없어",
            "내가 언제",
            "무슨 소리야",
            "말도 안 돼",
            "있은 적도 없는데",
            "상상하는 거야",
        ],
        "TRIVIALIZING": [
            "별거 아니야",
            "예민해",
            "오버하네",
            "그게 뭐가 문제야",
            "과민 반응이야",
            "심각하지 않아",
            "생각해 봐야지",
        ],
        "COUNTERING": [
            "네가 잘못 기억해",
            "그렇게 말한 적 없어",
            "착각하는 거야",
            "기억력이 왜 그래",
            "헛소리하지 마",
            "기억이 잘못됐어",
        ],
        "BLOCKING": [
            "그 얘기는 그만",
            "지금 그게 중요해?",
            "딴 소리 하네",
            "괜히 그래",
            "얘기 안 해도 돼",
            "필요 없는 얘기야",
        ],
        "DIVERTING": [
            "그보다",
            "아무튼",
            "어쨌든",
            "그런 건 나중에",
            "딴 얘기 하자",
            "주제 바꾸자",
        ],
        "FORGETTING": [
            "몰라도 돼",
            "기억 안 나",
            "까먹었어",
            "아 그래",
            "상관없어",
            "중요하지 않아",
        ],
        "WITHHOLDING": [
            "나중에 알려줄게",
            "지금은 말할 때가 아냐",
            "넌 몰라도 돼",
            "너랑은 상관없어",
            "알 필요 없어",
        ],
    }

    # Emotional manipulation keywords
    EMOTIONAL_MANIPULATION = {
        "GUILT_TRIPPING": [
            "네가 이렇게 해서",
            "다 네 때문이야",
            "나한테 왜 이래",
            "내가 얼마나 힘든지",
            "너 때문에",
            "너만 좀 잘해줘",
            "너라서 다행이야",
            "내가 다 해줬는데",
        ],
        "SHAMING": [
            "창피하지도 않아",
            "부끄러운 줄 알아",
            "사람이 어떻게",
            "제정신이야",
            "망신이야",
            "창피하냐",
            "수치심을 느껴라",
        ],
        "FEAR_INDUCING": [
            "두고 봐",
            "가만 안 둬",
            "후회하게 될 거야",
            "몰라볼 거야",
            "신중해야 해",
            "큰일 난다",
        ],
        "LOVE_BOMBING": [
            "사랑해",
            "너밖에 없어",
            "가장 소중해",
            "없이는 못살아",
            "모든 걸 다 줄게",
            "넌 내 전부야",
        ],
        "SILENT_TREATMENT": [
            # This is detected through absence patterns, not keywords
            # But certain phrases indicate intent to ignore
            "대답 안 해줄게",
            "신경 쓰지 마",
            "무시할 거야",
        ],
        "VICTIMHOOD": [
            "나만 손해야",
            "나는 잘못한 게 없어",
            "나한테만 화내",
            "난 피해자야",
            "나만 힘들어",
            "왜 나만",
            "불공정해",
        ],
    }

    # Threat pattern keywords
    THREAT = {
        "EXPLICIT_THREAT": [
            "죽여버릴",
            "가만 안 둬",
            "없애버릴",
            "죽어",
            "쳐죽일",
            "끝내주겠다",
        ],
        "IMPLICIT_THREAT": [
            "신중해야 할 거야",
            "후회하게 될 거야",
            "생각해 봐",
            "큰일 날 거야",
            "조심해야 해",
        ],
        "FINANCIAL_THREAT": [
            "돈 안 줄 거야",
            "상속에서 빼버릴",
            "한 푼도 못 받아",
            "경제적 제재",
            "돈 끊을 거야",
            "유산 못 받아",
        ],
        "SOCIAL_THREAT": [
            "아는 사람한테 다 말할",
            "다 알게 될 거야",
            "망하게 해줄게",
            "명성을 잃게 될 거야",
            "사회적으로 죽을 거야",
        ],
        "LEGAL_THREAT": [
            "고소할 거야",
            "법적으로 문제될 거야",
            "법원에 가",
            "소송할 거야",
            "처벌받게 될 거야",
        ],
    }

    @classmethod
    def get_gaslighting_keywords(cls, pattern_type: str) -> list[str]:
        """Get keywords for a specific gaslighting pattern type."""
        return cls.GASLIGHTING.get(pattern_type, [])

    @classmethod
    def get_manipulation_keywords(cls, manipulation_type: str) -> list[str]:
        """Get keywords for a specific emotional manipulation type."""
        return cls.EMOTIONAL_MANIPULATION.get(manipulation_type, [])

    @classmethod
    def get_threat_keywords(cls, threat_type: str) -> list[str]:
        """Get keywords for a specific threat type."""
        return cls.THREAT.get(threat_type, [])

    @classmethod
    def all_gaslighting_keywords(cls) -> dict[str, list[str]]:
        """Get all gaslighting keywords as a dictionary."""
        return cls.GASLIGHTING.copy()

    @classmethod
    def all_manipulation_keywords(cls) -> dict[str, list[str]]:
        """Get all emotional manipulation keywords as a dictionary."""
        return cls.EMOTIONAL_MANIPULATION.copy()

    @classmethod
    def all_threat_keywords(cls) -> dict[str, list[str]]:
        """Get all threat keywords as a dictionary."""
        return cls.THREAT.copy()
