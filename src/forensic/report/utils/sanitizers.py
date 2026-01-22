import re


class PIISanitizer:
    PHONE_PATTERNS = [r"\d{3}-\d{4}-\d{4}", r"\d{2,3}-\d{3,4}-\d{4}"]
    ID_NUMBER_PATTERNS = [r"\d{6}-\d{7}", r"\d{13}"]

    def __init__(self, mask_phone: bool = True, mask_id_number: bool = True, mask_char: str = "*") -> None:
        self._mask_phone = mask_phone
        self._mask_id_number = mask_id_number
        self._mask_char = mask_char

    def sanitize(self, text: str) -> str:
        result = text
        if self._mask_phone:
            for pattern in self.PHONE_PATTERNS:
                result = re.sub(pattern, self._mask_match_phone, result)
        if self._mask_id_number:
            for pattern in self.ID_NUMBER_PATTERNS:
                result = re.sub(pattern, self._mask_match_id, result)
        return result

    def _mask_match_phone(self, m: re.Match) -> str:
        parts = m.group().split("-")
        if len(parts) == 3:
            return f"{parts[0]}-{self._mask_char * len(parts[1])}-{self._mask_char * len(parts[2])}"
        return self._mask_char * len(m.group())

    def _mask_match_id(self, m: re.Match) -> str:
        text = m.group()
        if "-" in text:
            parts = text.split("-")
            return f"{parts[0]}-{self._mask_char * 7}"
        if len(text) == 13:
            return f"{text[:6]}-{self._mask_char * 7}"
        return self._mask_char * len(text)

    def detect_pii(self, text: str) -> dict:
        detected = {}
        phones = []
        for pattern in self.PHONE_PATTERNS:
            phones.extend(re.findall(pattern, text))
        if phones:
            detected["phone_numbers"] = phones
        return detected

class ContentSanitizer:
    @staticmethod
    def normalize_whitespace(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def truncate(text: str, max_length: int, suffix: str = "...") -> str:
        if len(text) <= max_length:
            return text
        return text[: max_length - len(suffix)] + suffix

    @staticmethod
    def escape_html(text: str) -> str:
        return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace('"', "&quot;").replace("'", "&#39;"))

def sanitize_text(text: str, mask_pii: bool = True, normalize: bool = True) -> str:
    result = text
    if mask_pii:
        sanitizer = PIISanitizer()
        result = sanitizer.sanitize(result)
    if normalize:
        result = ContentSanitizer.normalize_whitespace(result)
    return result
