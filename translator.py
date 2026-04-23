"""Google 非官方翻译接口 + 自动翻译英文源条目。"""
import httpx

import db

TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
ENGLISH_SOURCES = ["hackernews", "reddit", "github"]


def _translate(text: str, sl: str = "en", tl: str = "zh-CN") -> str:
    if not text.strip():
        return text
    r = httpx.get(
        TRANSLATE_URL,
        params={"client": "gtx", "sl": sl, "tl": tl, "dt": "t", "q": text},
        timeout=10,
    )
    r.raise_for_status()
    return "".join(p[0] for p in r.json()[0] if p[0])


def translate_new_items() -> None:
    """翻译英文源中未翻译的条目,逐条调 Google 翻译。"""
    items = db.get_untranslated(ENGLISH_SOURCES)
    if not items:
        print("[translate] no new items")
        return
    ok = 0
    for it in items:
        try:
            title_zh = _translate(it["title"])
            content_zh = _translate((it["content"] or "")[:300]) if it["content"] else ""
            db.update_translated(it["id"], title_zh, content_zh)
            ok += 1
        except Exception as e:
            print(f"[translate] item {it['id']} failed: {e}")
    print(f"[translate] translated {ok}/{len(items)}")
