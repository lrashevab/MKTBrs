# -*- coding: utf-8 -*-
"""
Google 新聞／媒體爬蟲：以關鍵字搜尋 Google News RSS，產出 CSV／JSON。
供流程整合：關鍵字、搜尋期間（天數）、輸出目錄。
"""

import csv
import json
import logging
import os
import re
import time
import urllib.parse
from datetime import datetime, timedelta

try:
    import feedparser
except ImportError:
    feedparser = None

try:
    import requests
    from bs4 import BeautifulSoup
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

from output_utils import _safe_filename

logger = logging.getLogger(__name__)

RSS_BASE = "https://news.google.com/rss/search"
DEFAULT_HL = "zh-TW"
DEFAULT_CEID = "TW:zh-Hant"


# 新聞內文主要區塊 selector（優先順序）
_CONTENT_SELECTORS = [
    'article', '[role="main"]', 'main',
    '.article-content', '.article-body', '.post-content',
    '.entry-content', '.content-body', '#article-body',
    '#main-content', '.story-body', '.news-content',
]

_FETCH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _fetch_article_content(url: str, timeout: int = 10, max_chars: int = 1500) -> str:
    """
    嘗試抓取新聞文章完整內文（最多 max_chars 字）。
    失敗時靜默回傳空字串，不影響整體流程。
    """
    if not _HAS_REQUESTS or not url:
        return ''
    try:
        resp = requests.get(url, headers=_FETCH_HEADERS,
                            timeout=timeout, allow_redirects=True)
        if resp.status_code != 200:
            return ''
        # 優先嘗試 UTF-8（台灣新聞站大多為 UTF-8），失敗才用 chardet
        try:
            text_decoded = resp.content.decode('utf-8')
        except UnicodeDecodeError:
            enc = resp.apparent_encoding or 'utf-8'
            text_decoded = resp.content.decode(enc, errors='replace')
        soup = BeautifulSoup(text_decoded, 'html.parser')
        # 移除雜訊標籤
        for tag in soup(['script', 'style', 'nav', 'header',
                         'footer', 'aside', 'form', 'figure']):
            tag.decompose()
        # 嘗試主要內文 selector
        content = ''
        for sel in _CONTENT_SELECTORS:
            el = soup.select_one(sel)
            if el:
                content = el.get_text(separator='\n').strip()
                break
        if not content:
            content = soup.get_text(separator='\n').strip()
        # 清理：保留長度 > 15 的行，去掉純空白
        lines = [ln.strip() for ln in content.split('\n')
                 if len(ln.strip()) > 15]
        return '\n'.join(lines)[:max_chars]
    except Exception:
        return ''


def _parse_entry_date(entry):
    """從 RSS entry 取得日期，回傳 datetime 或 None"""
    if getattr(entry, "published_parsed", None):
        try:
            from time import mktime
            return datetime.fromtimestamp(mktime(entry.published_parsed))
        except Exception:
            pass
    if getattr(entry, "updated_parsed", None):
        try:
            from time import mktime
            return datetime.fromtimestamp(mktime(entry.updated_parsed))
        except Exception:
            pass
    return None


def fetch_google_news_rss(keyword, num=100, hl=DEFAULT_HL, ceid=DEFAULT_CEID):
    """抓取 Google News RSS，回傳 list of entries（每筆含 title, link, published, summary）。"""
    if not feedparser:
        print("⚠️ 請安裝 feedparser：pip install feedparser")
        return []
    q = urllib.parse.quote(keyword)
    url = f"{RSS_BASE}?q={q}&hl={hl}&ceid={ceid}&num={num}"
    try:
        d = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"})
    except Exception as e:
        print(f"⚠️ Google News RSS 請求失敗：{e}")
        return []
    return getattr(d, "entries", [])


def run_google_news_scrape(keywords, time_range_days=180, output_dir=None, keyword_label=None):
    """
    執行 Google 新聞搜尋並產出報表。
    keywords: 關鍵字列表
    time_range_days: 只保留此天數內的報導
    output_dir: 輸出目錄（None 則用 output_utils 建立）
    keyword_label: 檔名用代表關鍵字
    回傳 (rows, output_dir)
    """
    if not keywords:
        keywords = ["新聞"]
    try:
        from output_utils import get_campaign_output_dir
        out = output_dir or get_campaign_output_dir()
    except ImportError:
        out = output_dir or "."
    os.makedirs(out, exist_ok=True)

    cutoff = datetime.now() - timedelta(days=time_range_days)
    all_rows = []
    seen_links = set()

    for kw in keywords:
        kw = (kw or "").strip()
        if not kw:
            continue
        entries = fetch_google_news_rss(kw)
        for e in entries:
            pub_dt = _parse_entry_date(e)
            if pub_dt and pub_dt < cutoff:
                continue
            link = getattr(e, "link", "") or ""
            if link and link in seen_links:
                continue
            seen_links.add(link)
            title = getattr(e, "title", "") or ""
            summary = getattr(e, "summary", "") or ""
            # 清理 HTML 標籤
            if summary:
                summary = re.sub(r"<[^>]+>", "", summary).strip()
            source = getattr(e, "source", None)
            source_name = getattr(source, "title", "") if source else ""
            pub_str = pub_dt.strftime("%Y-%m-%d %H:%M") if pub_dt else ""
            all_rows.append({
                "keyword": kw,
                "title": title,
                "link": link,
                "summary": summary[:500],
                "source": source_name,
                "published": pub_str,
                "content": "",   # 稍後補抓
            })

    # ── 補抓完整內文（前 N 篇，按發布時間排序）─────────────────
    try:
        from config import Config
        fetch_limit = getattr(Config, "GOOGLE_NEWS_FETCH_LIMIT", 50)
        fetch_delay = getattr(Config, "GOOGLE_NEWS_FETCH_DELAY", 0.4)
        request_timeout = getattr(Config, "REQUEST_TIMEOUT", 30)
    except ImportError:
        fetch_limit, fetch_delay, request_timeout = 50, 0.4, 30
    fetch_count = min(fetch_limit, len(all_rows))
    if fetch_count > 0 and _HAS_REQUESTS:
        logger.info("補抓前 %s 篇完整內文（共 %s 篇）", fetch_count, len(all_rows))
        for i, row in enumerate(all_rows):
            if i >= fetch_count:
                break
            content = _fetch_article_content(row["link"], timeout=request_timeout)
            row["content"] = content
            if (i + 1) % 10 == 0:
                logger.info("已完成 %s/%s 篇", i + 1, fetch_count)
            time.sleep(fetch_delay)

    label = keyword_label or (keywords[0] if keywords else "news")
    safe_label = _safe_filename(label)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    csv_path = os.path.join(out, f"google_news_{safe_label}_{ts}.csv")
    json_path = os.path.join(out, f"google_news_{safe_label}_{ts}.json")

    FIELDS = ["keyword", "title", "link", "summary", "content", "source", "published"]
    if all_rows:
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore')
            w.writeheader()
            w.writerows(all_rows)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"keyword_label": label, "time_range_days": time_range_days,
                       "rows": all_rows}, f, ensure_ascii=False, indent=2)
        fetched = sum(1 for r in all_rows if r.get("content"))
        print(f"  Google 新聞：{len(all_rows)} 篇，其中 {fetched} 篇有完整內文 → {csv_path}")
    else:
        print("  Google 新聞：0 筆（可能被限流或無符合結果）")

    return all_rows, out


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    kw = input("請輸入搜尋關鍵字：").strip() or "台灣"
    days = int(input("搜尋幾天內（預設 30）：").strip() or "30")
    run_google_news_scrape([kw], time_range_days=days, keyword_label=kw)
