"""关键词列表 + 打分函数。增/删关键词直接改这两个列表即可。"""

PAIN_KEYWORDS_ZH = [
    "难用", "好烦", "求推荐", "太麻烦", "效率低",
    "有没有", "替代品", "手动", "每次都要", "痛点",
    "吐槽", "坑", "踩雷",
]

PAIN_KEYWORDS_EN = [
    "frustrated", "annoying", "wish there was", "is there a tool",
    "alternative to", "better way to", "why is", "hate",
    "painful", "manually", "tedious", "anyone know",
    "struggling with", "pain point",
]

ALL_KEYWORDS = PAIN_KEYWORDS_ZH + PAIN_KEYWORDS_EN


def score_item(title: str, content: str | None) -> tuple[int, list[str]]:
    """扫描标题+正文。标题命中 +2,仅正文命中 +1,同关键词只计一次。
    返回 (pain_score, 命中的关键词列表)。
    """
    title_l = (title or "").lower()
    content_l = (content or "").lower()
    score = 0
    matched: list[str] = []
    for kw in ALL_KEYWORDS:
        kw_l = kw.lower()
        if kw_l in title_l:
            score += 2
            matched.append(kw)
        elif kw_l in content_l:
            score += 1
            matched.append(kw)
    return score, matched
