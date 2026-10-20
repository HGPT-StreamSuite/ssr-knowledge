"""Server-rendered UI. Every navigation queries SQLite; no embedded corpus."""
from __future__ import annotations

from html import escape
from typing import Any
from urllib.parse import urlencode, urlsplit

from .review_page import STAT_LABELS

KINDS = {"all": "全部", "item": "道具", "badge": "遊戲徽章", "other": "其他"}
STYLE = """
:root{color-scheme:light;--ink:#21313a;--muted:#64727b;--line:#d9e2e6;--green:#226653}*{box-sizing:border-box}body{margin:0;background:#f3f6f7;color:var(--ink);font:16px/1.65 system-ui,'Microsoft JhengHei',sans-serif}main{max-width:1120px;margin:auto;padding:28px 20px 64px}h1{margin:0;font-size:29px}h2{margin:0;font-size:22px}h3{font-size:16px;color:var(--green);margin:0 0 6px}h4{font-size:14px;margin-bottom:5px}p{margin:7px 0}a{color:var(--green);text-underline-offset:3px}button,.button{display:inline-block;border:1px solid #9dbab0;border-radius:7px;padding:8px 14px;background:#fff;color:var(--green);font:inherit;cursor:pointer;text-decoration:none}button.primary{background:var(--green);color:white}input,select{font:inherit;border:1px solid #b5c6cd;background:white;border-radius:7px;padding:9px;max-width:100%}form{display:flex;align-items:end;flex-wrap:wrap;gap:10px;margin:20px 0}label{display:flex;flex-direction:column;font-size:13px;gap:4px}.search{flex:1;min-width:200px}.meta{margin:16px 0;padding:14px 17px;background:#e8eff1;border-radius:8px;font-size:13px;color:#435761}.path{overflow-wrap:anywhere;font-family:ui-monospace,Consolas,monospace}.muted,small{color:var(--muted)}small{font-size:12px}.counts{margin:10px 0}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:16px}.card,.detail{background:white;border:1px solid var(--line);border-radius:11px;padding:21px}.card h2{font-size:20px}.english{font-size:13px;color:var(--muted);overflow-wrap:anywhere}.teaser{margin:12px 0;font-size:15px}.tag{display:inline-block;font-size:12px;background:#edf5f0;color:#356650;border-radius:4px;padding:2px 7px;margin:4px 5px 4px 0}.status{font-size:13px;margin:4px 0}.detail{margin:18px 0 24px;max-width:880px}.detail section{margin:20px 0}.detail ul{padding-left:22px;margin:5px 0}.detail li{margin:5px 0}.detail header{border-bottom:1px solid var(--line);padding-bottom:15px;margin-bottom:15px}details{border-top:1px solid var(--line);margin-top:20px;padding-top:12px;font-size:14px;color:var(--muted)}summary{cursor:pointer;color:var(--green)}details[open] summary{margin-bottom:14px}.missing{font-size:13px;color:var(--muted);margin:15px 0}.related{list-style:none;padding:0!important}.related li{margin:8px 0}.related small{margin-left:10px}.source{padding:9px 0;border-bottom:1px solid #eef1f2}.pages{display:flex;align-items:center;justify-content:center;gap:16px;margin:24px 0}.error{border:2px solid #b74139;background:#fff2ef;padding:22px;border-radius:10px}.error h2{color:#922f29}.warning{color:#8b5615;background:#fff4df;padding:10px;border-radius:5px}.result-note{font-size:13px;margin-bottom:12px}
"""


def esc(value: Any) -> str:
    return escape(str(value), quote=True)


def link(options: dict[str, Any], **changes: Any) -> str:
    values = {"q": options.get("q", ""), "kind": options.get("kind", "all"), "page": options.get("page", 1), "page_size": options.get("page_size", 20)}
    if options.get("entry_id"):
        values["entry"] = options["entry_id"]
    values.update(changes)
    return "/?" + urlencode({k: v for k, v in values.items() if v is not None and v != ""})


def safe_url(value: Any) -> bool:
    if not isinstance(value, str) or any(ord(c) < 32 for c in value):
        return False
    parsed = urlsplit(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.hostname) and not parsed.username and not parsed.password


def shell(content: str) -> str:
    return '<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PEAK 本機 DB 驗收</title><style>' + STYLE + '</style><main>' + content + '</main></html>'


def source_html(source: dict[str, Any]) -> str:
    title = esc(source["title"])
    if safe_url(source["url"]):
        title = '<a href="' + esc(source["url"]) + '" target="_blank" rel="noreferrer">' + title + ' ↗</a>'
    kind = source["acquisition_kind"]
    label = "使用者提供附件" if kind == "user_provided_text" else "已保存的本機官方文字" if kind == "installed_game_text" else "已保存的來源引用"
    parts = [label]
    if source.get("version"):
        parts.append(esc(source["version"]))
    if source.get("source_updated_at"):
        parts.append('來源標示日期 ' + esc(source["source_updated_at"]))
    parts.append('保存時間 ' + esc(source["saved_at"]))
    return '<div class="source"><p>' + title + '</p><small>' + ' · '.join(parts) + '</small></div>'


def detail_html(entry: dict[str, Any], options: dict[str, Any]) -> str:
    content = '<a class="button" href="' + esc(link(options, entry=None)) + '">返回結果</a><article class="detail"><header><h2>' + esc(entry["name_zh"]) + '</h2><p class="english">' + esc(entry["name_en"]) + '</p><small>' + esc(entry["name_label"]) + '</small></header>'
    content += '<p class="status">' + esc(entry["review_label"]) + '</p><p class="status">' + esc(entry["source_label"]) + '</p>'
    if entry["stale"]:
        content += '<p class="warning">引用來源已有更新；此處顯示條目保存的版本。</p>'
    detail = entry["detail_page"]
    if detail:
        content += '<p class="status">' + esc(detail["label"])
        if safe_url(detail["url"]):
            content += ' · <a href="' + esc(detail["url"]) + '" target="_blank" rel="noreferrer">開啟單品頁 ↗</a>'
        content += '</p>'
    for section in entry["sections"]:
        if section["notes"]:
            content += '<section><h3>' + esc(section["label"]) + '</h3><ul>' + ''.join('<li>' + esc(n) + '</li>' for n in section["notes"]) + '</ul></section>'
    if entry["relations"]:
        content += '<section><h3>相關條目</h3><ul class="related">'
        for related in entry["relations"]:
            url = '/?' + urlencode({"entry": related["entry_id"]})
            content += '<li><a href="' + esc(url) + '">' + esc(related["name_zh"]) + '</a><small>' + esc('、'.join(related["evidence"])) + '</small></li>'
        content += '</ul></section>'
    if entry["missing_topics"]:
        content += '<p class="missing">待補資料：' + esc('、'.join(entry["missing_topics"])) + '</p>'
    content += '<details><summary>原文、數值與實際來源</summary>'
    if entry["aliases"]:
        content += '<p>別名：' + esc('、'.join(dict.fromkeys(entry["aliases"]))) + '</p>'
    if entry["statistics"]:
        content += '<h4>原表數值</h4><ul>'
        for field, value in entry["statistics"].items():
            text = str(value["value"]) if value["state"] == "value" else "n/a（來源標示，含義未確認）" if value["state"] == "source_na" else "來源未提供／待補查"
            content += '<li>' + esc(STAT_LABELS[field]) + '：' + esc(text) + '</li>'
        content += '</ul>'
    for field, label in (("biomes_en", "原表區域"), ("locations_en", "原表地點")):
        if entry[field]:
            content += '<p>' + label + '：' + esc('、'.join(entry[field])) + '</p>'
    original = entry["notes_en"] or ([entry["condition_en"]] if entry["condition_en"] else [])
    if original:
        content += '<h4>英文原文</h4><ul>' + ''.join('<li>' + esc(n) + '</li>' for n in original) + '</ul>'
    if entry["steam_equivalence"] == "unverified":
        content += '<p>此為遊戲徽章；與 Steam 成就的對應尚未核對。</p>'
    content += '<h4>實際來源紀錄</h4>' + ''.join(source_html(s) for s in entry["sources"])
    content += '<p>條目保存時間：' + esc(entry["saved_at"]) + '</p></details></article>'
    return content


def render_page(model: dict[str, Any]) -> str:
    meta, options = model["metadata"], model["query"]
    counts = meta["counts"]
    content = '<h1>PEAK 本機 DB 驗收</h1><div class="meta"><strong>唯讀 · 每次查詢直接讀取 SQLite</strong><p class="path">' + esc(meta["database"]) + '</p><p>讀取時間：' + esc(meta["read_at"]) + '</p>'
    if meta["latest_revision_recorded_at"]:
        content += '<p>最近條目紀錄：' + esc(meta["latest_revision_recorded_at"]) + '</p>'
    content += '</div><p class="counts">' + str(counts["entries"]) + ' 條目 · 道具 ' + str(counts["items"]) + '（' + str(counts["organized_items"]) + ' 份詳細表） · 遊戲徽章 ' + str(counts["game_badges"]) + ' · 其他 ' + str(counts["other"]) + '</p>'
    if not counts["entries"]:
        content += '<p class="warning">這個 DB 沒有目前條目，請確認上方資料庫路徑。</p>'
    content += '<form method="get" action="/"><label class="search">中英文、別名或內容<input name="q" value="' + esc(options["q"]) + '" maxlength="200" placeholder="搜尋中文、English 或別名"></label><label>分類<select name="kind">'
    for value, label in KINDS.items():
        content += '<option value="' + value + '"' + (' selected' if options["kind"] == value else '') + '>' + label + '</option>'
    content += '</select></label><input type="hidden" name="page_size" value="' + str(options["page_size"]) + '"><button class="primary" type="submit">查詢</button><a class="button" href="' + esc(link(options)) + '">重新讀取 DB</a></form>'
    if model["detail"]:
        content += detail_html(model["detail"], options)
        return shell(content)
    content += '<p class="result-note">符合 ' + str(model["total_matches"]) + ' 筆 · 第 ' + str(options["page"]) + '／' + str(model["pages"]) + ' 頁</p>'
    if not model["entries"]:
        content += '<p>沒有符合條件的資料。</p>'
    else:
        content += '<div class="cards">'
        for entry in model["entries"]:
            url = link(options, entry=entry["entry_id"])
            content += '<article class="card"><h2><a href="' + esc(url) + '">' + esc(entry["name_zh"]) + '</a></h2><p class="english">' + esc(entry["name_en"]) + '</p><span class="tag">' + esc(KINDS[entry["kind"]]) + '</span><small>' + esc(entry["review_label"]) + '</small>'
            if entry["teaser"]:
                teaser = entry["teaser"]
                content += '<p class="teaser">' + esc(teaser[:180] + ('…' if len(teaser) > 180 else '')) + '</p>'
            content += '<p class="source-line"><small>' + esc(entry["source_label"]) + '</small></p></article>'
        content += '</div>'
    content += '<nav class="pages" aria-label="分頁">'
    if options["page"] > 1:
        content += '<a class="button" href="' + esc(link(options, page=options["page"] - 1, entry=None)) + '">上一頁</a>'
    if options["page"] < model["pages"]:
        content += '<a class="button" href="' + esc(link(options, page=options["page"] + 1, entry=None)) + '">下一頁</a>'
    content += '</nav>'
    return shell(content)


def render_error(value: dict[str, Any]) -> str:
    return shell('<h1>PEAK 本機 DB 驗收</h1><div class="error" role="alert"><h2>目前無法顯示資料</h2><p>' + esc(value["error"]) + '</p><p class="path">指定 DB：' + esc(value["database"]) + '</p><p>讀取時間：' + esc(value["read_at"]) + '</p><p>沒有載入替代、示範或前次查詢資料。</p><a class="button" href="/">重新讀取 DB</a></div>')
