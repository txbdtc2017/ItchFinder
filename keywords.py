"""关键词列表 + 打分函数。增/删关键词直接改这两个列表即可。
目标:软件/App/工具/自动化能解决的用户痛点(不包括 bug/崩溃这类临时缺陷)。
"""

PAIN_KEYWORDS_ZH = [
    # UX / 难用类
    "难用", "太麻烦", "流程繁琐", "效率低", "体验差",
    # 求推荐 / 替代品
    "求推荐", "有没有", "替代品", "推荐一个", "推荐几款",
    "好用的", "靠谱的", "哪款", "哪个好",
    # 想要 / 希望
    "希望有", "要是有", "想要一个", "想找", "在找",
    # 手动 / 重复
    "手动", "每次都要", "每天都要", "重复", "自动化",
    # 情绪 / 吐槽
    "好烦", "吐槽", "痛点", "不好用",
    # 功能缺失
    "为什么不能", "为什么没有", "不支持", "做不到",
]

PAIN_KEYWORDS_EN = [
    # UX / usability
    "hard to use", "confusing", "painful to use", "tedious",
    "cumbersome", "annoying", "frustrating",
    # Wishing for something
    "wish there was", "wish it could", "would love", "wish i had",
    "is there a tool", "is there an app", "anyone know a",
    "looking for a tool", "need a tool",
    # Alternatives
    "alternative to", "better than", "replace", "replacement for",
    "switching from",
    # Manual / automation
    "manually", "every time", "automate this", "repetitive",
    # Feature gap
    "why can't", "why doesn't", "why is there no", "missing feature",
    "no way to",
    # General complaint
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
