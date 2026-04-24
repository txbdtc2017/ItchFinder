"""Google 非官方翻译接口 + 自动翻译英文源条目。
translate_new_items 是 async generator,每处理一条 yield 一条进度字符串。
"""
from collections.abc import AsyncIterator

import httpx

import db

TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
ENGLISH_SOURCES = ["hackernews", "reddit", "github"]
BATCH_LIMIT = 200


async def _translate(client: httpx.AsyncClient, text: str) -> str:
    if not text.strip():
        return text
    r = await client.get(
        TRANSLATE_URL,
        params={"client": "gtx", "sl": "en", "tl": "zh-CN", "dt": "t", "q": text},
        timeout=10,
    )
    r.raise_for_status()
    return "".join(p[0] for p in r.json()[0] if p[0])


async def translate_new_items() -> AsyncIterator[str]:
    items = db.get_untranslated(ENGLISH_SOURCES, limit=BATCH_LIMIT)
    if not items:
        yield "翻译: 没有需要翻译的条目"
        return

    total = len(items)
    yield f"翻译: 开始处理 {total} 条英文内容"

    ok = 0
    fail = 0
    async with httpx.AsyncClient() as client:
        for i, it in enumerate(items, 1):
            try:
                title_zh = await _translate(client, it["title"])
                content_zh = ""
                if it["content"]:
                    content_zh = await _translate(client, it["content"][:300])
                db.update_translated(it["id"], title_zh, content_zh)
                ok += 1
                # 每 5 条推一次进度,最后一条必推
                if i % 5 == 0 or i == total:
                    yield f"翻译 ({i}/{total}) · {title_zh[:30]}"
            except Exception as e:
                fail += 1
                yield f"翻译失败 ({i}/{total}): {str(e)[:50]}"

    yield f"✓ 翻译完成: 成功 {ok} / 失败 {fail} / 共 {total}"
