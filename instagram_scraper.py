# -*- coding: utf-8 -*-
"""
Instagram 爬蟲 - 未登入公開版
功能：關鍵字/Hashtag 搜尋、公開貼文內容、互動數據
輸出：CSV / JSON

注意：未登入版本只能抓公開內容，部分數據可能受限
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
from pathlib import Path
from typing import List, Dict, Optional

from output_utils import _safe_filename, _safe_print

logger = logging.getLogger(__name__)

# === User-Agent 輪換池（從 dcard_scraper 引入）===
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
]

# === 反爬蟲配置 ===
RETRY_MAX = 4
RETRY_BASE_DELAY = 2.0

# === 常數 ===
# Instagram 搜尋 URL（探索頁面 + 關鍵字）
SEARCH_BASE = "https://www.instagram.com/explore/search/keyword/"
# 備用：Hashtag 搜尋
HASHTAG_BASE = "https://www.instagram.com/explore/tags/"
MAX_SCROLL_ROUNDS = 30  # 最大滾動次數
POSTS_PER_SCROLL = 12   # 每輪預期載入的貼文數

# === 輸出欄位 ===
CSV_HEADERS = [
    "關鍵字", "貼文網址", "作者帳號", "貼文內容", "Hashtags",
    "發布時間", "按讚數", "留言數", "擷取時間"
]


def get_random_user_agent() -> str:
    return random.choice(USER_AGENTS)


def get_retry_delay(attempt: int, base_delay: float = RETRY_BASE_DELAY) -> float:
    """指數退避延遲"""
    delay = base_delay * (2 ** attempt)
    return delay + random.uniform(0, 1)


def parse_instagram_date(date_text: str) -> Optional[datetime]:
    """解析 Instagram 日期格式"""
    if not date_text:
        return None
    
    now = datetime.now()
    date_lower = date_text.lower().strip()
    
    # 支援格式：2小時前、2 小時前、2h ago、2 hours ago
    hour_match = re.search(r'(\d+)\s*(小時|hour|hr|s)', date_lower)
    if hour_match:
        hours = int(hour_match.group(1))
        return now - timedelta(hours=hours)
    
    # 天：2天前、2d ago
    day_match = re.search(r'(\d+)\s*(天|day|d)', date_lower)
    if day_match:
        days = int(day_match.group(1))
        return now - timedelta(days=days)
    
    # 週：1週前、1w ago
    week_match = re.search(r'(\d+)\s*(週|week|w)', date_lower)
    if week_match:
        weeks = int(week_match.group(1))
        return now - timedelta(weeks=weeks)
    
    # 月：1月前
    month_match = re.search(r'(\d+)\s*(月|month|mo)', date_lower)
    if month_match:
        months = int(month_match.group(1))
        return now - timedelta(days=months * 30)
    
    # 年：1年前
    year_match = re.search(r'(\d+)\s*(年|year|yr)', date_lower)
    if year_match:
        years = int(year_match.group(1))
        return now - timedelta(days=years * 365)
    
    return None


def extract_hashtags(text: str) -> List[str]:
    """提取文字中的 Hashtags"""
    if not text:
        return []
    hashtags = re.findall(r'#(\w+)', text)
    return hashtags


def scrape_instagram_search(
    page,
    keyword: str,
    all_results: List[Dict],
    time_range_days: int = 30,
    max_scroll: int = MAX_SCROLL_ROUNDS
) -> int:
    """執行 Instagram 搜尋並抓取貼文"""
    
    # URL 編碼
    encoded_keyword = urllib.parse.quote(keyword)
    search_url = f"{SEARCH_BASE}{encoded_keyword}/"
    
    _safe_print(f"\n[*] 搜尋關鍵字：{keyword}")
    _safe_print(f"    URL：{search_url}")
    
    total_added = 0
    
    try:
        # 前往搜尋頁面
        page.goto(search_url, wait_until="networkidle", timeout=30000)
        time.sleep(random.uniform(3.0, 5.0))
        
        # 檢查是否被阻擋
        if "blocked" in page.url.lower() or "challenge" in page.url.lower():
            _safe_print(f"    [!] Instagram 要求驗證，可能被臨時封鎖")
            return 0
        
        # 等待貼文載入
        try:
            page.wait_for_selector('article a[href*="/p/"]', timeout=15000)
        except Exception:
            _safe_print(f"    [!] 無法載入搜尋結果，可能被限制")
            return 0
        
        # 滾動載入更多貼文
        prev_count = 0
        no_new_count = 0
        
        for scroll_round in range(max_scroll):
            # 模擬人類滾動
            scroll_distance = random.randint(400, 800)
            page.evaluate(f"window.scrollBy(0, {scroll_distance})")
            time.sleep(random.uniform(2.0, 3.5))
            
            # 取得目前貼文數量
            posts = page.query_selector_all('article a[href*="/p/"]')
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
        
        # 抓取所有貼文連結
        post_links = page.query_selector_all('article a[href*="/p/"]')
        _safe_print(f"    找到 {len(post_links)} 個貼文連結")
        
        # 去重
        seen_urls = set()
        cutoff_date = datetime.now() - timedelta(days=time_range_days)
        
        for link_el in post_links:
            try:
                href = link_el.get_attribute("href")
                if not href or "/p/" not in href:
                    continue
                
                # 完整 URL
                if not href.startswith("http"):
                    href = "https://www.instagram.com" + href
                
                # 提取貼文 ID 去重
                post_id = re.search(r'/p/([^/]+)', href)
                if not post_id:
                    continue
                post_id = post_id.group(1)
                
                if post_id in seen_urls:
                    continue
                seen_urls.add(post_id)
                
                # 點擊進入貼文頁面
                link_el.click()
                time.sleep(random.uniform(1.5, 2.5))
                
                # 等待貼文內容載入
                try:
                    page.wait_for_selector('article', timeout=10000)
                except:
                    page.keyboard.press("Escape")
                    continue
                
                # 提取資料
                post_data = extract_post_data(page, keyword)
                
                # 時間過濾
                if post_data.get("date_obj"):
                    if post_data["date_obj"] < cutoff_date:
                        page.keyboard.press("Escape")
                        time.sleep(0.5)
                        continue
                
                all_results.append(post_data)
                total_added += 1
                
                if total_added % 10 == 0:
                    _safe_print(f"    已擷取 {total_added} 篇...")
                
                # 返回搜尋結果頁
                page.keyboard.press("Escape")
                time.sleep(random.uniform(1.0, 2.0))
                
            except Exception as e:
                try:
                    page.keyboard.press("Escape")
                except:
                    pass
                continue
        
        _safe_print(f"    完成！共擷取 {total_added} 篇符合條件的貼文")
        
    except Exception as e:
        logger.exception(f"搜尋 {keyword} 發生錯誤")
        _safe_print(f"    [!] 錯誤：{str(e)[:50]}")
    
    return total_added


def extract_post_data(page, keyword: str) -> Dict:
    """從 Instagram 貼文頁面提取資料"""
    data = {
        "keyword": keyword,
        "url": "",
        "author": "",
        "content": "",
        "hashtags": "",
        "date_text": "",
        "date_obj": None,
        "likes": 0,
        "comments": 0,
        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    
    try:
        # 取得 URL
        url = page.url
        data["url"] = url
        
        # 取得作者帳號
        author_el = page.query_selector('header a[href*="/"]')
        if author_el:
            author_link = author_el.get_attribute("href") or ""
            author_match = re.search(r'/([^/]+)/$', author_link)
            if author_match:
                data["author"] = author_match.group(1)
        
        # 取得內文
        article = page.query_selector('article')
        if article:
            # 取得所有文字內容
            text_content = []
            
            # 標題（如果有）
            title_el = article.query_selector('h1')
            if title_el:
                text_content.append(title_el.inner_text())
            
            # 主要內文
            main_div = article.query_selector('div[role="menu"]') or article.query_selector('ul')
            if main_div:
                # 找到文章主要內容區塊（通常在上方）
                paragraphs = main_div.query_selector_all('div > span, p')
                for p in paragraphs:
                    txt = p.inner_text().strip()
                    if txt and len(txt) > 2:
                        text_content.append(txt)
            
            full_text = "\n".join(text_content)
            data["content"] = full_text[:2000]  # 限制長度
            
            # 提取 Hashtags
            hashtags = extract_hashtags(full_text)
            data["hashtags"] = ",".join(hashtags)
        
        # 取得時間
        time_el = page.query_selector('time')
        if time_el:
            datetime_attr = time_el.get_attribute("datetime")
            if datetime_attr:
                try:
                    data["date_obj"] = datetime.fromisoformat(datetime_attr.replace("Z", "+00:00"))
                    data["date_text"] = data["date_obj"].strftime("%Y-%m-%d %H:%M")
                except:
                    pass
        
        # 取得按讚數
        like_spans = page.query_selector_all('section span html-entity')
        for span in like_spans:
            txt = span.inner_text().replace(",", "").replace(".", "")
            if txt.isdigit():
                data["likes"] = int(txt)
                break
        
        # 備用方法：找 "按讚" 相關文字
        if data["likes"] == 0:
            article_text = page.inner_text("article")
            like_match = re.search(r'([\d,.]+)\s*(個)?讚', article_text)
            if like_match:
                likes_str = like_match.group(1).replace(",", "")
                data["likes"] = int(likes_str)
        
        # 取得留言數
        comment_links = page.query_selector_all('ul a[href*="/p/"]')
        # 留言數通常在第二個連結
        if len(comment_links) > 1:
            comment_text = comment_links[1].inner_text()
            comment_match = re.search(r'([\d,.]+)', comment_text)
            if comment_match:
                data["comments"] = int(comment_match.group(1).replace(",", ""))
        
    except Exception as e:
        logger.exception("提取貼文資料失敗")
    
    return data


def run_instagram_scrape(
    keywords: List[str],
    time_range_days: int = 30,
    output_dir: str = None,
    keyword_label: str = None,
    headless: bool = True,
    max_scroll: int = MAX_SCROLL_ROUNDS
):
    """
    執行 Instagram 搜尋並產出報表
    
    參數：
    - keywords: 關鍵字列表
    - time_range_days: 只抓取這天數內的貼文
    - output_dir: 輸出目錄
    - keyword_label: 檔名用代表關鍵字
    - headless: 是否無頭模式
    - max_scroll: 最大滾動次數
    
    回傳：(all_results, output_dir)
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _safe_print("⚠️ 請安裝 Playwright：pip install playwright && playwright install chromium")
        return [], output_dir or "."
    
    if not keywords:
        keywords = ["instagram"]
    
    try:
        from output_utils import get_report_output_dir
        out = output_dir or get_report_output_dir("reports")
    except ImportError:
        out = output_dir or "reports"
    os.makedirs(out, exist_ok=True)
    
    label = keyword_label or keywords[0]
    all_results = []
    
    try:
        with sync_playwright() as p:
            # 啟動瀏覽器（反偵測）
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
            
            # 注入反偵測腳本
            page = context.new_page()
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            # 執行搜尋
            for kw in keywords:
                kw = (kw or "").strip()
                if not kw:
                    continue
                
                scrape_instagram_search(
                    page, kw, all_results, 
                    time_range_days=time_range_days,
                    max_scroll=max_scroll
                )
                
                # 關鍵字間隔
                if len(keywords) > 1:
                    time.sleep(random.uniform(3.0, 5.0))
            
            browser.close()
    
    except Exception as e:
        _safe_print(f"\n❌ Instagram 爬蟲執行失敗：{e}")
        import traceback
        traceback.print_exc()
    
    # 儲存結果
    if all_results:
        save_results(all_results, label, out)
    
    _safe_print(f"\n[*] Instagram 爬蟲完成：共 {len(all_results)} 篇")
    return all_results, out


def save_results(results: List[Dict], keyword: str, output_dir: str):
    """儲存 CSV 和 JSON"""
    safe_kw = _safe_filename(keyword)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    
    csv_path = os.path.join(output_dir, f"instagram_{safe_kw}_{ts}.csv")
    json_path = os.path.join(output_dir, f"instagram_{safe_kw}_{ts}.json")
    
    # CSV
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "關鍵字": r.get("keyword", ""),
                "貼文網址": r.get("url", ""),
                "作者帳號": r.get("author", ""),
                "貼文內容": r.get("content", ""),
                "Hashtags": r.get("hashtags", ""),
                "發布時間": r.get("date_text", ""),
                "按讚數": r.get("likes", 0),
                "留言數": r.get("comments", 0),
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
    print("  Instagram 爬蟲（未登入公開版）")
    print("=" * 50)
    
    kw = input("\n請輸入搜尋關鍵字：").strip() or "美食"
    days = int(input("搜尋幾天內的貼文（預設 30）：").strip() or "30")
    
    show_browser = input("\n是否顯示瀏覽器視窗？(y/n，預設 n)：").strip().lower() != "n"
    
    print("\n" + "=" * 50)
    print("開始執行...")
    print("=" * 50)
    
    run_instagram_scrape(
        keywords=[kw],
        time_range_days=days,
        headless=not show_browser
    )


if __name__ == "__main__":
    main()
