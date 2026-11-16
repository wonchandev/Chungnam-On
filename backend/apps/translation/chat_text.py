"""채팅 번역 입력에서 널리 쓰이는 약어를 풀고 이모티콘을 보존한다."""

import regex


ABBREVIATIONS = {
    "ko": {
        "ㅇㅋ": "알겠어요", "ㅇㅇ": "네", "ㄴㄴ": "아니요", "ㄱㄱ": "시작해요", "ㄳ": "감사합니다",
        "ㅈㅅ": "죄송합니다", "ㅊㅋ": "축하합니다", "칼퇴": "정시에 퇴근", "노쇼": "연락 없이 나타나지 않음",
    },
    "en": {
        "asap": "as soon as possible", "thx": "thank you", "idk": "I don't know", "brb": "be right back",
        "np": "no problem", "lol": "ha ha",
    },
}
TOKEN_PATTERN = regex.compile(r"https?://\S+|[\w.+-]+@[\w.-]+\.[\w-]+|[@#]\w+|(?P<word>\w+)", regex.IGNORECASE)
LAUGHTER = regex.compile(r"(?:ㅋ{2,}|ㅎ{2,})\Z")
EMOTICONS = (":)", ":-)", ":(", ":-(", ";)", ";-)", ":D", "^^", "^_^")
CLUSTER_PATTERN = regex.compile(r"(?<!\w)(?:" + "|".join(map(regex.escape, EMOTICONS)) + r")(?!\w)|\X")
EMOJI_PATTERN = regex.compile(r"[\p{Extended_Pictographic}\p{Regional_Indicator}\u20e3]")


def expand_abbreviations(text: str, source: str) -> str:
    rules = ABBREVIATIONS.get(source)
    if rules is None:
        return text

    def replace(match):
        word = match["word"]
        if not word:
            return match[0]
        if source == "ko" and LAUGHTER.fullmatch(word):
            return "하하"
        return rules.get(word.lower(), word)

    return TOKEN_PATTERN.sub(replace, text)


def mark_emoticons(text: str) -> tuple[str, dict[str, str]]:
    prefix = "CHUNGNAMTERM"
    while prefix in text:
        prefix += "X"
    replacements = {}

    def replace(match):
        cluster = match[0]
        if cluster not in EMOTICONS and not EMOJI_PATTERN.search(cluster):
            return cluster
        marker = f"{prefix}{len(replacements)}X"
        replacements[marker] = cluster
        return marker

    return CLUSTER_PATTERN.sub(replace, text), replacements
