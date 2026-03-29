# -*- coding: utf-8 -*-
"""
PTT 全站競品輿情搜尋器：依關鍵字搜尋「所有看板」的貼文，支援翻頁、時間區間篩選
輸出：CSV + 四維度輿情 JSON（使用 sentiment_config）
可指定 output_dir（流程整合時與 Dcard 共用同一 campaign 資料夾）
"""

# --- 引入需要的工具（套件）---
import csv
import json
import logging
import os
import re
import time
import urllib.parse
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from output_utils import _safe_filename

logger = logging.getLogger(__name__)

try:
    from sentiment_config import get_negative_words, analyze_sentiment_categories
except ImportError:
    def get_negative_words(industry=None):
        return ["雷", "爛", "騙", "貴", "沒效", "後悔", "盤子", "割韭菜", "退費", "話術", "假", "套路"]
    def analyze_sentiment_categories(text, industry=None):
        return []

# --- 設定常數 ---
# 看板列表來源：批踢踢熱門看板首頁 https://www.ptt.cc/bbs/index.html
PTT_BASE = "https://www.ptt.cc"
BOARD_INDEX_URL = "https://www.ptt.cc/bbs/index.html"
SEARCH_URL_TEMPLATE = "https://www.ptt.cc/bbs/{board}/search?q={keyword}"
PTT_HOME = "https://www.ptt.cc/"

COOKIES = {"over18": "1"}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.ptt.cc/bbs/index.html",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

FALLBACK_BOARDS = [
    "Gossiping", "Stock", "C_Chat", "Tech_Job", "MobileComm", "NBA", "Baseball",
    "LoL", "WomenTalk", "Boy-Girl", "movie", "japan_travel", "travel", "Lifeismoney",
]

# 時間區間選項（年數）
TIME_RANGE_OPTIONS = {
    "1": ("一年內", 1),
    "2": ("三年內", 3),
    "3": ("五年內", 5),
    "4": ("十年內", 10),
}

# 連線重試與節流（可從 config 覆寫）
def _get_ptt_config():
    try:
        from config import Config
        return {
            "retries": getattr(Config, "RETRY_TIMES", 5),
            "retry_delay": 3,
            "delay_boards": getattr(Config, "PTT_DELAY_BETWEEN_BOARDS", 2.0),
            "delay_pages": getattr(Config, "PTT_DELAY_BETWEEN_PAGES", 1.0),
            "delay_article": getattr(Config, "PTT_DELAY_ARTICLE", 0.8),
            "timeout": getattr(Config, "REQUEST_TIMEOUT", 20),
        }
    except ImportError:
        return {"retries": 5, "retry_delay": 3, "delay_boards": 2.0, "delay_pages": 1.0, "delay_article": 0.8, "timeout": 20}

REQUEST_RETRIES = 5
REQUEST_RETRY_DELAY = 3
DELAY_BETWEEN_BOARDS = 2.0
DELAY_BETWEEN_PAGES = 1.0


def _get_with_retry(session, url, timeout=20):
    """發送 GET 並在連線被重置時重試（指數退避）"""
    last_err = None
    for attempt in range(REQUEST_RETRIES):
        try:
            resp = session.get(url, timeout=timeout)
            # 429 Too Many Requests：等更久再重試
            if resp.status_code == 429:
                wait = REQUEST_RETRY_DELAY * (3 ** attempt)
                print(f"    PTT 請求過於頻繁(429)，等待 {wait} 秒...")
                time.sleep(wait)
                continue
            # 503 Service Unavailable：短暫等待重試
            if resp.status_code == 503:
                wait = REQUEST_RETRY_DELAY * (2 ** attempt)
                print(f"    PTT 暫時無法連線(503)，{wait} 秒後重試...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except (requests.ConnectionError, requests.Timeout, ConnectionResetError, OSError) as e:
            last_err = e
            if attempt < REQUEST_RETRIES - 1:
                wait = REQUEST_RETRY_DELAY * (2 ** attempt)
                print(f"    連線中斷，{wait} 秒後重試 ({attempt + 1}/{REQUEST_RETRIES})...")
                time.sleep(wait)
                # 重建 session 的 cookies，避免 over18 cookie 失效
                session.cookies.set("over18", "1", domain=".ptt.cc")
    raise last_err if last_err else requests.ConnectionError("Max retries exceeded")



def parse_date_from_link(link):
    """從 PTT 文章連結提取發佈日期（連結格式含 Unix timestamp，如 M.1762956277.A.XXX）"""
    match = re.search(r"M\.(\d+)\.", link)
    if match:
        try:
            ts = int(match.group(1))
            return datetime.fromtimestamp(ts)
        except (ValueError, OSError):
            pass
    return None


def _parse_push_count(push_str):
    """將推文數字串轉為整數，用於排序（爆=100, XX=-10, 其餘轉整數）"""
    s = str(push_str).strip()
    if s == "爆":
        return 100
    if s.startswith("X"):
        return -10
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


def fetch_ptt_article_content(session, url, top_n=20, timeout=15):
    """進入 PTT 文章頁面，抓取內文與前 top_n 則推文（推+噓+箭頭）"""
    if not url or not url.startswith("http"):
        return "", ""
    try:
        resp = _get_with_retry(session, url, timeout=timeout)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        # --- 抓內文 ---
        main_content = soup.find("div", id="main-content")
        content = ""
        if main_content:
            # 複製節點，移除 meta 資訊、推文，剩下正文
            import copy
            content_copy = copy.copy(main_content)
            for tag in content_copy.select(
                "div.article-metaline, div.article-metaline-right, div.push, div.richcontent"
            ):
                tag.decompose()
            content = content_copy.get_text(separator="\n").strip()
            # 去除頁尾固定文字
            content = re.sub(r"--\n?※.*", "", content, flags=re.DOTALL).strip()

        # --- 抓推文 ---
        pushes = []
        for push in soup.select("div.push")[:top_n]:
            tag_el = push.select_one("span.push-tag")
            user_el = push.select_one("span.push-userid")
            text_el = push.select_one("span.push-content")
            if text_el:
                tag_str = tag_el.get_text(strip=True) if tag_el else ""
                user_str = user_el.get_text(strip=True) if user_el else ""
                text_str = text_el.get_text(strip=True).lstrip(": ")
                pushes.append(f"{tag_str} {user_str}: {text_str}")

        return content, " | ".join(pushes)

    except Exception as e:
        print(f"    [!] 文章內文抓取失敗：{url[:60]}... ({e})")
        return "", ""


def get_all_boards(session):
    """從 PTT 熱門看板首頁 (https://www.ptt.cc/bbs/index.html) 取得看板名稱列表"""
    try:
        response = _get_with_retry(session, BOARD_INDEX_URL, timeout=15)
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")
        boards = set()
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            match = re.match(r"/bbs/([^/?]+)", href)
            if match:
                board = match.group(1)
                if board not in ("index", "search", "cls") and len(board) > 1:
                    boards.add(board)
        return sorted(boards)
    except Exception as e:
        print(f"取得看板列表失敗：{e}")
        return []


def search_board(session, board, encoded_keyword, cutoff_date, delay_pages=None):
    """
    搜尋單一看板，自動翻頁直到沒有下一頁或文章超過時間區間
    cutoff_date: 只保留此日期之後的文章；delay_pages: 翻頁間隔秒數
    """
    if delay_pages is None:
        delay_pages = DELAY_BETWEEN_PAGES
    url = SEARCH_URL_TEMPLATE.format(board=board, keyword=encoded_keyword)
    rows = []
    page = 1

    while True:
        try:
            response = _get_with_retry(session, url, timeout=15)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")
            post_blocks = soup.find_all("div", class_="r-ent")

            for block in post_blocks:
                title_div = block.find("div", class_="title")

                if title_div and title_div.find("a"):
                    a_tag = title_div.find("a")
                    title = a_tag.get_text(strip=True)
                    link = a_tag.get("href", "")
                    if link and not link.startswith("http"):
                        link = PTT_BASE + link
                else:
                    title = title_div.get_text(strip=True) if title_div else "（無法取得標題）"
                    link = ""

                author_div = block.find("div", class_="author")
                author = author_div.get_text(strip=True) if author_div else "（未知）"

                nrec_div = block.find("div", class_="nrec")
                push_count = nrec_div.get_text(strip=True) if nrec_div else "0"
                if not push_count:
                    push_count = "0"

                # 從連結提取發佈日期
                pub_date = parse_date_from_link(link)
                date_str = pub_date.strftime("%Y-%m-%d") if pub_date else ""

                # 時間篩選：若無日期或早於 cutoff，跳過
                if pub_date and cutoff_date and pub_date < cutoff_date:
                    continue

                rows.append([title, author, push_count, link, board, date_str])

            # 尋找「下頁」連結
            next_url = None
            for a in soup.find_all("a", href=True):
                if "下頁" in a.get_text():
                    href = a.get("href", "")
                    if href and href != "#":
                        next_url = PTT_BASE + href if not href.startswith("http") else href
                        break

            if not next_url or next_url == url:
                break

            url = next_url
            page += 1
            time.sleep(delay_pages)

        except (requests.RequestException, ConnectionResetError, OSError) as e:
            print(f"    [{board}] 頁面 {page} 連線失敗（{e}），略過此頁繼續")
            break  # 該板中斷，繼續下一個看板（不影響整體流程）

    return rows


def run_ptt_scrape(keyword, time_years=1, output_dir=None):
    """
    執行 PTT 競品輿情搜尋。若 output_dir 為 None 則建立 reports_YYYYMMDD_HHMM。
    回傳 (all_rows, output_dir)。
    """
    if not keyword or not keyword.strip():
        return [], output_dir or "."
    keyword = keyword.strip()
    try:
        from output_utils import get_report_output_dir
        out = output_dir or get_report_output_dir("reports")
    except ImportError:
        out = output_dir or "."
    os.makedirs(out, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    cutoff_date = datetime.now() - timedelta(days=time_years * 365)
    encoded_keyword = urllib.parse.quote(keyword)
    output_file = os.path.join(out, f"ptt_competitor_{_safe_filename(keyword, default='keyword')}_{ts}.csv")

    cfg = _get_ptt_config()
    logger.info("正在搜尋 PTT「%s」...", keyword)
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        session.cookies.set("over18", "1", domain=".ptt.cc")
        _get_with_retry(session, PTT_HOME, timeout=cfg["timeout"])
        time.sleep(1.5)
        try:
            boards = get_all_boards(session)
        except (requests.RequestException, ConnectionResetError, OSError) as e:
            logger.warning("取得看板列表失敗（%s），改用預設看板", e)
            boards = []
        if not boards:
            boards = FALLBACK_BOARDS
        all_rows = []
        seen_links = set()
        for i, board in enumerate(boards, 1):
            try:
                rows = search_board(session, board, encoded_keyword, cutoff_date, delay_pages=cfg["delay_pages"])
                for row in rows:
                    link = row[3]
                    if link and link not in seen_links:
                        seen_links.add(link)
                        all_rows.append(row)
                if rows:
                    logger.info("  [%s/%s] %s：找到 %s 篇", i, len(boards), board, len(rows))
            except (requests.RequestException, ConnectionResetError, OSError) as e:
                logger.exception("  [%s/%s] %s：略過", i, len(boards), board)
            time.sleep(cfg["delay_boards"])

        # --- 依推文數排序，前 N 篇完整抓取內文 + 推文 ---
        try:
            from config import Config
            content_limit = Config.PTT_CONTENT_FETCH_LIMIT
        except Exception:
            content_limit = 50

        all_rows.sort(key=lambda r: _parse_push_count(r[2]), reverse=True)

        print(f"\n[*] 共 {len(all_rows)} 篇，開始抓取前 {min(content_limit, len(all_rows))} 篇完整內文...")
        for i, row in enumerate(all_rows):
            if i < content_limit and row[3]:
                art_content, art_pushes = fetch_ptt_article_content(session, row[3], top_n=20, timeout=cfg["timeout"])
                row.append(art_content)
                row.append(art_pushes)
                if (i + 1) % 10 == 0:
                    logger.info("    已完成 %s / %s 篇...", i + 1, min(content_limit, len(all_rows)))
                time.sleep(cfg["delay_article"])
            else:
                row.append("")
                row.append("")

        with open(output_file, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["標題", "作者", "推文數", "文章連結", "看板", "發佈日期", "內文", "熱門推文(20則)"])
            writer.writerows(all_rows)

        full_text = " ".join(str(row[0]) + " " + str(row[6]) for row in all_rows)
        neg_words = get_negative_words()
        neg_count = sum(1 for row in all_rows if any(nw in (str(row[0]) + str(row[6])) for nw in neg_words))
        anger_index = (neg_count / len(all_rows)) * 100 if all_rows else 0
        sentiment_result = analyze_sentiment_categories(full_text)
        sentiment_file = os.path.join(out, f"ptt_sentiment_{_safe_filename(keyword, default='keyword')}_{ts}.json")
        with open(sentiment_file, "w", encoding="utf-8") as sf:
            json.dump({
                "keyword": keyword,
                "article_count": len(all_rows),
                "anger_index": round(anger_index, 1),
                "sentiment_categories": sentiment_result,
                "source": "ptt",
            }, sf, ensure_ascii=False, indent=2)
        print(f"[*] PTT 報告已儲存至：{out}")
        print(f"    CSV：{output_file}")
        print(f"    輿情 JSON：{sentiment_file}")
        return all_rows, out
    except Exception as e:
        print(f"PTT 搜尋錯誤：{e}")
        return [], out


def fetch_competitor_posts():
    """主程式（互動式）"""
    keyword = input("請輸入你想搜尋的競品關鍵字：").strip()
    if not keyword:
        print("未輸入關鍵字，程式結束。")
        return
    print("\n請選擇時間區間：")
    for k, (name, _) in TIME_RANGE_OPTIONS.items():
        print(f"  {k}. {name}")
    choice = input("請輸入選項 (1-4，直接 Enter 預設一年內)：").strip() or "1"
    years = TIME_RANGE_OPTIONS.get(choice, ("一年內", 1))[1]
    print(f"\n只搜尋 {years} 年內的文章\n")
    rows, out = run_ptt_scrape(keyword, time_years=years, output_dir=None)
    if rows:
        print("-" * 60)
        for i, row in enumerate(rows[:20], 1):
            print(f"【{i}】[{row[4]}] {row[0]} （{row[5]}）")
            print(f"  作者：{row[1]}｜推文：{row[2]}")
        if len(rows) > 20:
            print(f"  ... 其餘 {len(rows) - 20} 篇請見 CSV")


if __name__ == "__main__":
    fetch_competitor_posts()
