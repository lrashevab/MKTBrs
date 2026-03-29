# -*- coding: utf-8 -*-
"""
Facebook 爬蟲 - 未登入公開版
功能：關鍵字搜尋、公開粉專貼文、社團貼文
輸出：CSV / JSON

⚠️ 限制說明：
- 未登入版本能抓取的內容非常有限
- 部分粉專貼文可能被隱藏
- 按讚數、留言數可能顯示受限
- 社團內容幾乎無法抓取（需要登入）
- 建議使用備用帳號登入以獲得更多結果
"""

import csv
import json
import logging
import os
import random
import re
import time
import urllib.parse
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from output_utils import _safe_filename, _safe_print

logger = logging.getLogger(__name__)

# === User-Agent 輪換池 ===
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
]

# === 反爬蟲配置 ===
RETRY_MAX = 3
RETRY_BASE_DELAY = 2.0
REQUEST_TIMEOUT = 30000

# === 常數 ===
SEARCH_BASE = "https://www.facebook.com/search/posts/"
MAX_SCROLL_ROUNDS = 25

# === 輸出欄位 ===
CSV_HEADERS = [
    "關鍵字", "類型", "貼文網址", "作者/粉專", "貼文內容", "Hashtags",
    "發布時間", "按讚數", "留言數", "分享數", "擷取時間"
]


def get_random_user_agent() -> str:
    return random.choice(USER_AGENTS)


def get_retry_delay(attempt: int, base_delay: float = RETRY_BASE_DELAY) -> float:
    """指數退避延遲"""
    delay = base_delay * (2 ** attempt)
    return delay + random.uniform(0, 1)


def parse_facebook_date(date_text: str) -> Optional[datetime]:
    """解析 Facebook 日期格式"""
    if not date_text:
        return None
    
    now = datetime.now()
    date_lower = date_text.lower().strip()
    
    # 小時前
    hour_match = re.search(r'(\d+)\s*小時', date_lower)
    if hour_match:
        hours = int(hour_match.group(1))
        return now - timedelta(hours=hours)
    
    # 天前
    day_match = re.search(r'(\d+)\s*天', date_lower)
    if day_match:
        days = int(day_match.group(1))
        return now - timedelta(days=days)
    
    # 週前
    week_match = re.search(r'(\d+)\s*週', date_lower)
    if week_match:
        weeks = int(week_match.group(1))
        return now - timedelta(weeks=weeks)
    
    # 月前
    month_match = re.search(r'(\d+)\s*個月', date_lower)
    if month_match:
        months = int(month_match.group(1))
        return now - timedelta(days=months * 30)
    
    # 年前
    year_match = re.search(r'(\d+)\s*年', date_lower)
    if year_match:
        years = int(year_match.group(1))
        return now - timedelta(days=years * 365)
    
    # 標準日期格式
    date_formats = ["%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%Y年%m月%d日"]
    for fmt in date_formats:
        try:
            return datetime.strptime(date_text[:10], fmt)
        except:
            continue
    
    return None


def extract_hashtags(text: str) -> List[str]:
    """提取 Hashtags"""
    if not text:
        return []
    hashtags = re.findall(r'#(\w+)', text)
    return hashtags


def scrape_facebook_search(
    page,
    keyword: str,
    all_results: List[Dict],
    time_range_days: int = 30,
    max_scroll: int = MAX_SCROLL_ROUNDS
) -> int:
    """執行 Facebook 搜尋並抓取貼文"""
    
    encoded_keyword = urllib.parse.quote(keyword)
    search_url = f"{SEARCH_BASE}?q={encoded_keyword}"
    
    _safe_print(f"\n[*] 搜尋關鍵字：{keyword}")
    _safe_print(f"    URL：{search_url}")
    
    total_added = 0
    
    try:
        # 前往搜尋頁面
        page.goto(search_url, wait_until="networkidle", timeout=REQUEST_TIMEOUT)
        time.sleep(random.uniform(4.0, 6.0))
        
        # 檢查是否被阻擋
        if "checkpoint" in page.url.lower() or "login" in page.url.lower():
            _safe_print(f"    [!] Facebook 要求登入或驗證")
            return 0
        
        # 檢查是否有驗證挑戰
        challenge = page.query_selector('[data-testid="checkpoint"]')
        if challenge:
            _safe_print(f"    [!] Facebook 驗證頁面")
            return 0
        
        # 等待內容載入
        try:
            page.wait_for_selector('div[role="article"], article', timeout=15000)
        except Exception:
            # 嘗試備用選擇器
            try:
                page.wait_for_selector('div[aria-describedby]', timeout=10000)
            except:
                _safe_print(f"    [!] 無法載入搜尋結果")
                return 0
        
        # 滾動載入更多貼文
        prev_count = 0
        no_new_count = 0
        
        for scroll_round in range(max_scroll):
            # 模擬人類滾動
            scroll_distance = random.randint(300, 700)
            page.evaluate(f"window.scrollBy(0, {scroll_distance})")
            time.sleep(random.uniform(2.0, 3.0))
            
            # 取得目前貼文數量
            posts = page.query_selector_all('div[role="article"], article, a[href*="/groups/"], a[href*="/pages/"]')
            current_count = len(posts)
            
            if current_count == prev_count:
                no_new_count += 1
                if no_new_count >= 3:
                    _safe_print(f"    [*] 已到底部，共載入 {current_count} 篇")
                    break
            else:
                no_new_count = 0
                if scroll_round % 5 == 0:
                    _safe_print(f"    載入中... 目前 {current_count} 篇")
            
            prev_count = current_count
        
        # 抓取貼文連結
        post_links = []
        
        # 方法 1：找貼文連結
        link_elements = page.query_selector_all('a[href*="/groups/"], a[href*="/pages/"], a[href*="/story.php"]')
        for link in link_elements:
            href = link.get_attribute("href")
            if href and ('/groups/' in href or '/pages/' in href or '/story.php' in href):
                if not href.startswith("http"):
                    href = "https://www.facebook.com" + href
                post_links.append({"url": href, "type": "post"})
        
        # 去重
        seen_urls = set()
        for link in post_links:
            url = link["url"]
            post_id = re.search(r'(?:groups|pages|story)\.php\?story_fbid=(\w+)', url) or re.search(r'/(\w+)/$', url)
            if post_id:
                pid = post_id.group(1) if post_id.group(1) else url
                if pid not in seen_urls:
                    seen_urls.add(pid)
                    
                    # 進入貼文頁面抓取詳細資料
                    post_data = fetch_post_detail(page, url, keyword, link["type"])
                    if post_data:
                        # 時間過濾
                        cutoff_date = datetime.now() - timedelta(days=time_range_days)
                        if post_data.get("date_obj") and post_data["date_obj"] < cutoff_date:
                            continue
                        
                        all_results.append(post_data)
                        total_added += 1
                        
                        if total_added % 10 == 0:
                            _safe_print(f"    已擷取 {total_added} 篇...")
                    
                    # 隨機延遲
                    time.sleep(random.uniform(2.0, 4.0))
        
        _safe_print(f"    完成！共擷取 {total_added} 篇符合條件的貼文")
        
    except Exception as e:
        logger.exception(f"搜尋 {keyword} 發生錯誤")
        _safe_print(f"    [!] 錯誤：{str(e)[:80]}")
    
    return total_added


def fetch_post_detail(page, url: str, keyword: str, post_type: str = "post") -> Optional[Dict]:
    """進入貼文頁面抓取詳細資料"""
    
    data = {
        "keyword": keyword,
        "type": post_type,
        "url": url,
        "author": "",
        "content": "",
        "hashtags": "",
        "date_text": "",
        "date_obj": None,
        "likes": 0,
        "comments": 0,
        "shares": 0,
        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    
    try:
        # 開新分頁抓取
        new_page = page.context.new_page()
        new_page.goto(url, wait_until="networkidle", timeout=20000)
        time.sleep(random.uniform(2.0, 3.0))
        
        # 檢查是否需要登入
        if "login" in new_page.url.lower():
            new_page.close()
            return None
        
        # 取得作者
        author_el = new_page.query_selector('h1 a, h2 a, [role="heading"] a, a[href*="/pages/"]')
        if author_el:
            author_text = author_el.inner_text().strip()
            if author_text:
                data["author"] = author_text
        
        # 備用：從 URL 提取粉專名稱
        if not data["author"]:
            page_match = re.search(r'/pages/[^/]+/(\d+)', url)
            if page_match:
                data["author"] = f"Page ID: {page_match.group(1)}"
        
        # 取得內文
        content_div = new_page.query_selector('div[data-testid="post_message"]')
        if not content_div:
            content_div = new_page.query_selector('div[role="article"]')
        if not content_div:
            content_div = new_page.query_selector('span[class*="text"]')
        
        if content_div:
            full_text = content_div.inner_text().strip()[:3000]
            data["content"] = full_text
            
            # 提取 Hashtags
            hashtags = extract_hashtags(full_text)
            data["hashtags"] = ",".join(hashtags)
        
        # 取得時間
        time_el = new_page.query_selector('a[href*="/events/"], abbr, span[data-testid="sentence"]')
        if time_el:
            date_text = time_el.inner_text().strip()
            data["date_text"] = date_text
            data["date_obj"] = parse_facebook_date(date_text)
        
        # 取得互動數據
        # 按讚
        like_patterns = [
            'span[data-testid*="like"]',
            'a[href*="/like"]',
            'span[class*="like"]'
        ]
        for pattern in like_patterns:
            el = new_page.query_selector(pattern)
            if el:
                like_text = el.inner_text()
                like_match = re.search(r'([\d,.]+)', like_text)
                if like_match:
                    data["likes"] = int(like_match.group(1).replace(",", ""))
                    break
        
        # 留言
        comment_patterns = [
            'a[href*="/comment"]',
            'span[data-testid*="comment"]'
        ]
        for pattern in comment_patterns:
            el = new_page.query_selector(pattern)
            if el:
                comment_text = el.inner_text()
                comment_match = re.search(r'([\d,.]+)', comment_text)
                if comment_match:
                    data["comments"] = int(comment_match.group(1).replace(",", ""))
                    break
        
        # 分享
        share_el = new_page.query_selector('a[href*="/share"]')
        if share_el:
            share_text = share_el.inner_text()
            share_match = re.search(r'([\d,.]+)', share_text)
            if share_match:
                data["shares"] = int(share_match.group(1).replace(",", ""))
        
        new_page.close()
        
    except Exception as e:
        logger.exception(f"抓取貼文詳情失敗：{url}")
    
    return data


def scrape_page_posts(
    page,
    page_url: str,
    keyword: str,
    all_results: List[Dict],
    time_range_days: int = 30,
    max_scroll: int = MAX_SCROLL_ROUNDS
) -> int:
    """抓取特定粉專的貼文"""
    
    _safe_print(f"\n[*] 抓取粉專：{page_url}")
    
    total_added = 0
    
    try:
        page.goto(page_url, wait_until="networkidle", timeout=REQUEST_TIMEOUT)
        time.sleep(random.uniform(3.0, 5.0))
        
        # 檢查登入
        if "login" in page.url.lower():
            _safe_print(f"    [!] 需要登入才能查看")
            return 0
        
        # 滾動載入
        for scroll_round in range(max_scroll):
            page.evaluate(f"window.scrollBy(0, {random.randint(300, 600)})")
            time.sleep(random.uniform(2.0, 3.0))
            
            if scroll_round % 5 == 0:
                _safe_print(f"    滾動中... 第 {scroll_round + 1} 輪")
        
        # 抓取貼文連結
        post_links = page.query_selector_all('a[href*="/story.php"]')
        
        for link_el in post_links[:30]:  # 最多抓 30 篇
            try:
                href = link_el.get_attribute("href")
                if href and "/story.php" in href:
                    if not href.startswith("http"):
                        href = "https://www.facebook.com" + href
                    
                    post_data = fetch_post_detail(page, href, keyword, "page_post")
                    if post_data:
                        cutoff_date = datetime.now() - timedelta(days=time_range_days)
                        if post_data.get("date_obj") and post_data["date_obj"] < cutoff_date:
                            continue
                        
                        all_results.append(post_data)
                        total_added += 1
                        
                        time.sleep(random.uniform(1.5, 3.0))
            except:
                continue
        
    except Exception as e:
        logger.exception(f"抓取粉專失敗：{page_url}")
    
    return total_added


def run_facebook_scrape(
    keywords: List[str] = None,
    page_urls: List[str] = None,
    time_range_days: int = 30,
    output_dir: str = None,
    keyword_label: str = None,
    headless: bool = True,
    max_scroll: int = MAX_SCROLL_ROUNDS
):
    """
    執行 Facebook 搜尋並產出報表
    
    參數：
    - keywords: 關鍵字列表
    - page_urls: 特定粉專網址列表
    - time_range_days: 天數
    - output_dir: 輸出目錄
    - keyword_label: 檔名用關鍵字
    - headless: 是否無頭
    - max_scroll: 最大滾動次數
    
    回傳：(results, output_dir)
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _safe_print("⚠️ 請安裝 Playwright：pip install playwright && playwright install chromium")
        return [], output_dir or "."
    
    keywords = keywords or []
    page_urls = page_urls or []
    
    if not keywords and not page_urls:
        keywords = ["測試"]
    
    try:
        from output_utils import get_report_output_dir
        out = output_dir or get_report_output_dir("reports")
    except ImportError:
        out = output_dir or "reports"
    os.makedirs(out, exist_ok=True)
    
    label = keyword_label or (keywords[0] if keywords else "facebook")
    all_results = []
    
    try:
        with sync_playwright() as p:
            random_ua = get_random_user_agent()
            browser = p.chromium.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )
            
            context = browser.new_context(
                user_agent=random_ua,
                viewport={"width": random.choice([1366, 1440]), "height": random.choice([768, 900])},
                locale="zh-TW",
                timezone_id="Asia/Taipei",
            )
            
            page = context.new_page()
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            # 關鍵字搜尋
            for kw in keywords:
                kw = (kw or "").strip()
                if not kw:
                    continue
                
                scrape_facebook_search(
                    page, kw, all_results,
                    time_range_days=time_range_days,
                    max_scroll=max_scroll
                )
                
                if len(keywords) > 1:
                    time.sleep(random.uniform(3.0, 6.0))
            
            # 特定粉專抓取
            for page_url in page_urls:
                page_url = (page_url or "").strip()
                if not page_url:
                    continue
                
                if not page_url.startswith("http"):
                    page_url = f"https://www.facebook.com/{page_url}"
                
                scrape_page_posts(
                    page, page_url, label,
                    time_range_days=time_range_days,
                    max_scroll=max_scroll
                )
            
            browser.close()
    
    except Exception as e:
        _safe_print(f"\n❌ Facebook 爬蟲執行失敗：{e}")
        import traceback
        traceback.print_exc()
    
    # 儲存結果
    if all_results:
        save_results(all_results, label, out)
    
    _safe_print(f"\n[*] Facebook 爬蟲完成：共 {len(all_results)} 篇")
    return all_results, out


def save_results(results: List[Dict], keyword: str, output_dir: str):
    """儲存 CSV 和 JSON"""
    safe_kw = _safe_filename(keyword)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    
    csv_path = os.path.join(output_dir, f"facebook_{safe_kw}_{ts}.csv")
    json_path = os.path.join(output_dir, f"facebook_{safe_kw}_{ts}.json")
    
    # CSV
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "關鍵字": r.get("keyword", ""),
                "類型": r.get("type", ""),
                "貼文網址": r.get("url", ""),
                "作者/粉專": r.get("author", ""),
                "貼文內容": r.get("content", ""),
                "Hashtags": r.get("hashtags", ""),
                "發布時間": r.get("date_text", ""),
                "按讚數": r.get("likes", 0),
                "留言數": r.get("comments", 0),
                "分享數": r.get("shares", 0),
                "擷取時間": r.get("scraped_at", ""),
            })
    
    # JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "keyword": keyword,
            "total_posts": len(results),
            "posts": results
        }, f, ensure_ascii=False, indent=2)
    
    _safe_print(f"\n📁 輸出檔案：")
    _safe_print(f"   CSV：{csv_path}")
    _safe_print(f"   JSON：{json_path}")


def main():
    """主程式"""
    import sys
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except:
            pass
    
    print("=" * 50)
    print("  Facebook 爬蟲（未登入公開版）")
    print("=" * 50)
    print("\n⚠️  注意：未登入版本能抓取的內容有限")
    
    choice = input("\n請選擇搜尋類型：")
    print("  1. 關鍵字搜尋")
    print("  2. 粉專網址")
    choice = input("請輸入選項 (1-2)：").strip() or "1"
    
    if choice == "1":
        kw = input("\n請輸入搜尋關鍵字：").strip() or "美食"
        keywords = [kw]
        page_urls = []
    else:
        kw = input("\n請輸入粉專網址或名稱：").strip()
        keywords = []
        page_urls = [kw]
    
    days = int(input("搜尋幾天內的貼文（預設 30）：").strip() or "30")
    show_browser = input("\n是否顯示瀏覽器視窗？(y/n，預設 n)：").strip().lower() != "n"
    
    print("\n" + "=" * 50)
    print("開始執行...")
    print("=" * 50)
    
    run_facebook_scrape(
        keywords=keywords,
        page_urls=page_urls,
        time_range_days=days,
        headless=not show_browser
    )


if __name__ == "__main__":
    main()
