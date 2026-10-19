"""Private, content-first HTML generated from current SQLite revisions only."""
from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

from .catalog import Catalog, resolve_data_dir
from .contracts import ContractError

LABELS = {"effects": "用途與效果", "acquisition": "取得方式", "conditions": "使用限制", "cooking": "烹煮效果"}
STAT_LABELS = {"weight": "負重", "hunger": "飢餓", "bonus_stamina": "額外耐力", "poison": "中毒"}


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def short_note(text: str, topic: str) -> str:
    text = re.sub(r"（[^（）]*暫譯[^（）]*）", "", text)
    if topic == "cooking":
        text = re.sub(r"^烹(?:煮|飪)[：:]\s*", "", text)
    if topic == "acquisition":
        text = re.sub(r"^來源[：:]\s*", "", text)
    return text


def render_review(store: Catalog, output: str) -> dict[str, Any]:
    path = Path(output).expanduser().resolve()
    resolve_data_dir(path.parent)  # Private output must stay outside checkouts.
    if path.suffix.lower() != ".html":
        raise ContractError("review output must be a private .html file")
    rows = [store.entry(r[0]) for r in store.db.execute("SELECT entry_id FROM entries ORDER BY entry_id")]
    items = [r for r in rows if "organization" in r["entry"]]
    badges = [r for r in rows if "badge_details" in r["entry"]]
    selected = items + badges
    anchors = {r["entry"]["entry_id"]: "card-" + str(i) for i, r in enumerate(selected)}
    by_id = {r["entry"]["entry_id"]: r for r in selected}
    graph: dict[str, dict[str, set[str]]] = {eid: {} for eid in by_id}
    for row in selected:
        entry = row["entry"]
        for link in entry.get("links", []):
            target = link["target_entry_id"]
            if target in graph:
                graph[entry["entry_id"]].setdefault(target, set()).add(link["kind"])
                graph[target].setdefault(entry["entry_id"], set()).add(link["kind"])
    cards = []
    missing_counts = {k: 0 for k in LABELS}
    for record in selected:
        entry = record["entry"]
        eid = entry["entry_id"]
        english = record["display_names"].get("en", {}).get("text", entry["name_en"])
        chinese = record["display_names"].get("zh-TW", {}).get("text", entry["name_zh"])
        kind = "item" if "organization" in entry else "badge"
        fields = []
        missing = []
        if kind == "item":
            organized = entry["organization"]
            for topic, label in LABELS.items():
                notes = [short_note(organized["notes_zh"][i], topic) for i in organized["topics"][topic]]
                if notes:
                    fields.append('<section><h3>' + label + '</h3><ul>' + ''.join('<li>' + esc(n) + '</li>' for n in notes) + '</ul></section>')
                else:
                    missing.append(label)
                    missing_counts[topic] += 1
            methods = [organized["notes_zh"][i] for i in organized["topics"]["badge_hints"]
                       if not re.match(r"^(Can be used for|Part of|Required for) ", entry["item_details"]["notes_en"][i])]
            if methods:
                fields.append('<section><h3>徽章用法</h3><ul>' + ''.join('<li>' + esc(n) + '</li>' for n in methods) + '</ul></section>')
        else:
            fields.append('<section><h3>解鎖條件（官方文字）</h3><p>' + esc(entry["badge_details"]["condition_zh"]) + '</p></section>')
        if graph[eid]:
            related = []
            for target, kinds in sorted(graph[eid].items()):
                other = by_id[target]["entry"]
                label = other["name_zh"]
                basis = "官方條件提及" if "condition_mentions_item" in kinds else "Items 備註提示"
                related.append('<li><a href="#' + anchors[target] + '" class="related">' + esc(label) + '</a><small>' + basis + '</small></li>')
            fields.append('<section><h3>' + ('相關徽章' if kind == 'item' else '相關道具') + '</h3><ul class="related-list">' + ''.join(related) + '</ul></section>')
        if missing:
            fields.append('<p class="missing">待補資料：' + '、'.join(missing) + '</p>')
        if kind == "item" and "detail_page" in entry:
            detail = entry["detail_page"]
            suffix = "" if detail["status"] == "verified" else "（未核對）"
            fields.append('<p><a href="' + esc(detail["url"]) + '" target="_blank" rel="noreferrer">道具詳細頁' + suffix + ' ↗</a></p>')
        evidence = []
        if kind == "item":
            statistics = []
            for stat, value in entry["item_details"]["statistics"].items():
                state = value["state"]
                text = str(value["value"]) if state == "value" else "來源標示 n/a（含義未確認）" if state == "source_na" else "來源未提供／待補查"
                statistics.append('<li>' + STAT_LABELS[stat] + '：' + esc(text) + '</li>')
            evidence.append('<h4>原表數值</h4><ul>' + ''.join(statistics) + '</ul>')
            detail = entry["item_details"]
            for key, label in (("biomes_en", "出現區域"), ("locations_en", "原表地點")):
                if detail[key]:
                    evidence.append('<p>' + label + '：' + esc('、'.join(detail[key])) + '</p>')
            if detail["notes_en"]:
                evidence.append('<h4>英文備註</h4><ul>' + ''.join('<li>' + esc(n) + '</li>' for n in detail["notes_en"]) + '</ul>')
            original_notes = [old for old, new in zip(detail["notes_zh"], entry["organization"]["notes_zh"]) if old != new]
            if original_notes:
                evidence.append('<h4>原始整理註記</h4><ul>' + ''.join('<li>' + esc(n) + '</li>' for n in original_notes) + '</ul>')
        else:
            evidence.append('<p>' + esc(entry["badge_details"]["condition_en"]) + '</p>')
        evidence.append('<h4>實際資料來源</h4>')
        seen = set()
        for source in record["sources"]:
            sid = source["source_id"]
            if sid in seen:
                continue
            seen.add(sid)
            cfg = source["source"]
            if cfg.get("acquisition", {}).get("kind") == "installed_game_text":
                label = '已保存官方遊戲文字（' + cfg["language"] + '；' + cfg["declared_version"] + '）'
                evidence.append('<p>' + esc(label) + '</p>')
            else:
                url = cfg.get("original_url", cfg["url"])
                # Only source attribution links, never a guessed individual page.
                if url.startswith("https://"):
                    evidence.append('<p><a href="' + esc(url) + '" target="_blank" rel="noreferrer">' + esc(cfg["title"]) + ' ↗</a></p>')
        if kind == "item":
            evidence.append('<p>用途內容與中文整理待審；原始備註及數值保留於 DB。' + ('個別詳細頁連結尚待核對。' if 'detail_page' not in entry else '詳細頁連結不是本卡資料引用來源。') + '</p>')
        status = '官方中英名稱' if record["display_names"].get("zh-TW", {}).get("status") == 'game_ui_verified' else '中文暫譯'
        search = ' '.join([english, chinese, *entry["aliases"], entry["summary_zh"], *entry.get("organization", {}).get("notes_zh", [])])
        state = {"pending_review": "待審核", "approved": "已核准", "published": "已發布", "rejected": "已拒絕"}[record["status"]]
        cards.append('<article id="' + anchors[eid] + '" data-kind="' + kind + '" data-search="' + esc(search) + '"><header><span class="tag">' + ('道具' if kind == 'item' else '遊戲徽章') + '</span><h2>' + esc(chinese) + '</h2><p class="english">' + esc(english) + '</p><small>' + status + ' · ' + state + '</small></header>' + ''.join(fields) + '<details><summary>原文與來源</summary>' + ''.join(evidence) + '</details></article>')
    content = '''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>PEAK 道具與徽章驗收</title><style>
:root{color-scheme:light;--ink:#202c34;--muted:#62717a;--line:#dce3e7;--accent:#1d6858}*{box-sizing:border-box}body{margin:0;background:#f3f6f7;color:var(--ink);font:16px/1.65 system-ui,"Microsoft JhengHei",sans-serif}main{max-width:1180px;margin:auto;padding:28px 22px 64px}h1{margin:0;font-size:30px}h2{font-size:22px;margin:6px 0 0}h3{font-size:15px;margin:0 0 5px;color:var(--accent)}h4{font-size:14px;margin-bottom:5px}p{margin:6px 0}a{color:#1d6858;text-underline-offset:3px}small,.english,.missing{color:var(--muted)}small{font-size:12px}.intro{margin:9px 0 18px;color:var(--muted)}nav{position:sticky;top:0;z-index:2;display:flex;gap:12px;align-items:center;flex-wrap:wrap;background:#f3f6f7f5;padding:12px 0;border-bottom:1px solid var(--line)}input,select{font:inherit;padding:10px;border:1px solid #b8c8ce;border-radius:7px;background:white}input{flex:1;min-width:210px}#cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:18px;margin-top:20px;align-items:start}article{background:white;border:1px solid var(--line);border-radius:12px;padding:22px;scroll-margin-top:100px}article:target{outline:3px solid #9bc9b6}article header{border-bottom:1px solid var(--line);padding-bottom:14px;margin-bottom:16px}.tag{font-size:11px;letter-spacing:1px;color:var(--accent)}.english{font-size:13px;overflow-wrap:anywhere}section{margin:0 0 16px}ul{margin:0;padding-left:21px}li{margin:4px 0}.related-list{list-style:none;padding:0}.related-list li{display:flex;gap:9px;align-items:baseline;flex-wrap:wrap}.missing{font-size:13px;margin:16px 0}details{border-top:1px solid var(--line);padding-top:12px;color:var(--muted);font-size:13px}summary{cursor:pointer;color:var(--accent)}details[open] summary{margin-bottom:12px}.summary{font-size:13px;margin-top:26px}[hidden]{display:none!important}
</style><main>'''
    states = '全部待審核' if all(r['status'] == 'pending_review' for r in selected) else '審核狀態見各卡'
    content += '<h1>PEAK 道具與徽章</h1><p>' + str(len(items)) + ' 件道具 · ' + str(len(badges)) + ' 個遊戲徽章 · ' + states + '</p><p class="intro">道具用途依已保存的 Items 備註整理；官方名稱與徽章條件採本機已保存的遊戲文字。遊戲徽章與 Steam 成就的對應尚未核對。</p><nav><input id="query" aria-label="搜尋名稱、別名或內容" placeholder="搜尋名稱、別名或內容"><select id="kind" aria-label="顯示類型"><option value="">全部</option><option value="item">道具</option><option value="badge">徽章</option></select><span id="count"></span></nav><div id="cards">' + ''.join(cards) + '</div>'
    content += '<details class="summary"><summary>資料範圍與待補進度</summary><p>道具數值原樣保留；n/a 的含義未確認，未改成 0 或不適用。用途整理與暫譯由 agent 編輯，未經使用者批准；本頁不會發布資料。</p><p>缺少獨立備註的道具：' + str(sum(not r["entry"]["item_details"]["notes_en"] for r in items)) + ' 件。各欄待補：' + '、'.join(LABELS[k] + ' ' + str(n) + ' 件' for k, n in missing_counts.items()) + '。</p><p>徽章條件保留官方顯示文字；模糊條件未補寫成實際解鎖邏輯。Items 的「可用於」僅為提示。內容版本與來源可在每張卡的來源明細查看。</p></details></main>'
    content += r'''<script>const q=document.querySelector('#query'),kind=document.querySelector('#kind'),cards=[...document.querySelectorAll('article')];const norm=s=>s.normalize('NFKC').toLocaleLowerCase().replace(/\s+/g,'');function filter(){let n=0;for(const c of cards){c.hidden=!!((kind.value&&c.dataset.kind!==kind.value)||!norm(c.dataset.search).includes(norm(q.value)));if(!c.hidden)n++}document.querySelector('#count').textContent=n+' 筆'}q.addEventListener('input',filter);kind.addEventListener('change',filter);document.querySelectorAll('a.related').forEach(a=>a.addEventListener('click',()=>{q.value='';kind.value='';filter()}));filter();</script></html>'''
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"output": str(path), "items": len(items), "game_badges": len(badges), "missing_topics": missing_counts,
            "scope": "review_preview", "generated_from": "current SQLite revisions", "network_requests": 0}
