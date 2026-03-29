# -*- coding: utf-8 -*-
"""
Threads 爬蟲：V7.1（完整修復版）
核心改進：
1. 包含文章內容與留言
2. 優化日期解析（支援多種格式）
3. 改進內容擷取（完整文章內容）
4. 區分主文章 vs 留言
"""

import json
import os
import re
import time
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

from output_utils import _safe_filename

DEFAULT_PROFILE_DIR = Path(__file__).resolve().parent / "threads_browser_profile"


def parse_threads_date(date_text):
    """
    解析 Threads 的日期文字，轉換成 datetime
    
    支援格式：
    - "2 小時前" / "2h" / "2 hours ago"
    - "3 天前" / "3d" / "3 days ago"
    - "1 週前" / "1w" / "1 week ago"
    - "2 月 25 日" / "Feb 25"
    - "2026-02-25" (ISO 格式)
    - "2026-02-25T15:30:00" (完整 ISO 格式)
    """
    if not date_text:
        return None
    
    date_text = date_text.strip()
    now = datetime.now()
    
    try:
        # 🆕 格式 0：ISO 格式（最可靠）
        # 例如：2026-02-25T15:30:00.000Z
        if "T" in date_text or re.match(r'\d{4}-\d{2}-\d{2}', date_text):
            try:
                # 移除時區資訊
                date_text_clean = date_text.replace("Z", "").split(".")[0]
                return datetime.fromisoformat(date_text_clean)
            except:
                pass
        
        date_text_lower = date_text.lower()
        
        # 格式 1：「X 小時前」或「Xh」或「X hours ago」
        if any(keyword in date_text_lower for keyword in ["小時", "hour", "hr"]) or date_text_lower.endswith("h"):
            match = re.search(r'(\d+)', date_text)
            if match:
                hours = int(match.group(1))
                return now - timedelta(hours=hours)
        
        # 格式 2：「X 天前」或「Xd」或「X days ago」
        if any(keyword in date_text_lower for keyword in ["天", "day"]) or date_text_lower.endswith("d"):
            match = re.search(r'(\d+)', date_text)
            if match:
                days = int(match.group(1))
                return now - timedelta(days=days)
        
        # 格式 3：「X 週前」或「Xw」或「X weeks ago」
        if any(keyword in date_text_lower for keyword in ["週", "week", "wk"]) or date_text_lower.endswith("w"):
            match = re.search(r'(\d+)', date_text)
            if match:
                weeks = int(match.group(1))
                return now - timedelta(weeks=weeks)
        
        # 格式 4：「X 月前」或「X months ago」
        if any(keyword in date_text_lower for keyword in ["月前", "month"]):
            match = re.search(r'(\d+)', date_text)
            if match:
                months = int(match.group(1))
                return now - timedelta(days=months * 30)
        
        # 格式 5：「2 月 25 日」（今年）
        if "月" in date_text and "日" in date_text:
            match = re.search(r'(\d+)\s*月\s*(\d+)', date_text)
            if match:
                month = int(match.group(1))
                day = int(match.group(2))
                year = now.year
                # 如果日期在未來，代表是去年
                date = datetime(year, month, day)
                if date > now:
                    date = datetime(year - 1, month, day)
                return date
        
        # 格式 6：「Feb 25」（英文）
        month_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
        }
        for month_name, month_num in month_map.items():
            if month_name in date_text_lower:
                match = re.search(r'(\d+)', date_text)
                if match:
                    day = int(match.group(1))
                    year = now.year
                    date = datetime(year, month_num, day)
                    if date > now:
                        date = datetime(year - 1, month_num, day)
                    return date
        
        # 格式 7：「2026 年 2 月 25 日」
        match = re.search(r'(\d{4})\s*年\s*(\d+)\s*月\s*(\d+)', date_text)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            return datetime(year, month, day)
        
    except Exception as e:
        pass
    
    return None


def find_date_in_element(element):
    """
    在元素中尋找日期
    返回：(date_text, date_obj)
    """
    try:
        # 🆕 方法 1：找到 time 標籤（最可靠）
        time_el = element.query_selector("time")
        
        if time_el:
            # 嘗試取得 datetime 屬性（ISO 格式，最準確）
            datetime_attr = time_el.get_attribute("datetime")
            if datetime_attr:
                date_obj = parse_threads_date(datetime_attr)
                if date_obj:
                    return (datetime_attr, date_obj)
            
            # 如果沒有 datetime 屬性，取得文字內容
            date_text = time_el.inner_text().strip()
            if date_text:
                date_obj = parse_threads_date(date_text)
                if date_obj:
                    return (date_text, date_obj)
        
        # 🆕 方法 2：在元素文字中尋找日期
        text = (element.inner_text() or "").strip()
        
        # 用正則表達式尋找日期
        patterns = [
            # ISO 格式
            (r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', None),
            (r'\d{4}-\d{2}-\d{2}', None),
            # 相對時間
            (r'(\d+)\s*(小時|天|週|月|hour|day|week|month)', None),
            (r'(\d+)\s*h', None),
            (r'(\d+)\s*d', None),
            (r'(\d+)\s*w', None),
            # 絕對日期
            (r'(\d+)\s*月\s*(\d+)\s*日', None),
            (r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d+', re.IGNORECASE),
        ]
        
        for pattern, flags in patterns:
            if flags:
                match = re.search(pattern, text, flags)
            else:
                match = re.search(pattern, text)
            
            if match:
                date_text = match.group(0)
                date_obj = parse_threads_date(date_text)
                if date_obj:
                    return (date_text, date_obj)
        
        return (None, None)
    
    except Exception:
        return (None, None)


def get_full_article_text(element):
    """
    取得完整的文章內容
    """
    try:
        text = (element.inner_text() or "").strip()
        
        if not text:
            return ""
        
        # 🆕 過濾掉不需要的行
        lines = text.split("\n")
        content_lines = []
        
        skip_keywords = [
            "threads.com",
            "讚", "留言", "分享", "追蹤", "已追蹤",
            "Like", "Comment", "Share", "Follow", "Following",
            "Verified", "驗證",
        ]
        
        for line in lines:
            line = line.strip()
            
            # 跳過空行
            if not line:
                continue
            
            # 跳過太短的行（可能是按鈕）
            if len(line) < 2:
                continue
            
            # 跳過包含特定關鍵字的行
            if any(keyword in line for keyword in skip_keywords):
                continue
            
            # 跳過純數字（可能是按讚數）
            if line.isdigit():
                continue
            
            content_lines.append(line)
        
        return "\n".join(content_lines)
    
    except Exception:
        return ""


def check_login_status(page):
    """檢查是否已登入 Threads"""
    try:
        if "login" in page.url.lower() or "accounts" in page.url.lower():
            return False
        login_button = page.query_selector('a[href*="login"]')
        if login_button:
            button_text = login_button.inner_text().lower()
            if "登入" in button_text or "login" in button_text:
                return False
        avatar = page.query_selector('img[alt*="profile"]') or page.query_selector('[aria-label*="個人檔案"]')
        if avatar:
            return True
        return True
    except Exception:
        return False


def get_articles_with_dates(page, domain):
    """
    取得所有文章及其日期（包含留言）
    
    🆕 V7.3 改進：
    - 使用「文章 ID」去重（而不是完整連結）
    - 改進容器選擇邏輯
    - 放寬文字長度限制
    - 增加除錯資訊
    """
    articles = []
    
    try:
        # 找到所有包含 /post/ 的連結
        post_links = page.query_selector_all('a[href*="/post/"]')
        
        print(f"    🔍 找到 {len(post_links)} 個文章連結")
        
        seen_post_ids = set()  # 🆕 使用文章 ID 去重
        processed_count = 0
        skipped_duplicate = 0
        skipped_short = 0
        skipped_error = 0
        
        for idx, link_el in enumerate(post_links):
            try:
                href = link_el.get_attribute("href")
                if not href or "/post/" not in href:
                    continue
                
                processed_count += 1
                
                # 取得完整連結
                if href.startswith("/"):
                    full_link = f"https://www.{domain}{href}"
                else:
                    full_link = href
                
                # 🆕 提取文章 ID（用於去重）
                # 例如：/post/ABC123?xmt=... → ABC123
                post_id_match = re.search(r'/post/([^/?]+)', href)
                if not post_id_match:
                    continue
                
                post_id = post_id_match.group(1)
                
                # 🆕 使用文章 ID 去重（而不是完整連結）
                if post_id in seen_post_ids:
                    skipped_duplicate += 1
                    continue
                seen_post_ids.add(post_id)
                
                # 🆕 改進的容器選擇邏輯
                # 策略：往上找，直到找到「包含完整文章內容」的容器
                container = link_el
                found_good_container = False
                
                for level in range(12):  # 往上找 12 層
                    try:
                        parent = container.evaluate_handle("el => el.parentElement").as_element()
                        if not parent:
                            break
                        
                        # 取得文字內容
                        text = (parent.inner_text() or "").strip()
                        text_length = len(text)
                        
                        # 檢查是否為「好的容器」
                        # 條件：
                        # 1. 長度 > 20（至少要有一些內容）
                        # 2. 長度 < 5000（不能太長，避免包含多篇文章）
                        # 3. 包含日期資訊（代表這是一個完整的文章容器）
                        if 20 < text_length < 5000:
                            # 檢查是否包含日期關鍵字
                            has_date = any(keyword in text for keyword in [
                                "小時", "天", "週", "月",
                                "hour", "day", "week", "month",
                                "h", "d", "w"
                            ])
                            
                            if has_date:
                                container = parent
                                found_good_container = True
                                break
                        
                        container = parent
                    
                    except:
                        break
                
                # 如果沒找到好的容器，使用當前容器
                if not found_good_container:
                    # 往上找 5 層作為備用
                    for _ in range(5):
                        try:
                            parent = container.evaluate_handle("el => el.parentElement").as_element()
                            if parent:
                                container = parent
                        except:
                            break
                
                container_text = (container.inner_text() or "").strip()
                
                # 🆕 改進的留言偵測邏輯
                is_reply = False
                
                # 方法 1：檢查關鍵字
                reply_keywords = [
                    "正在回覆", "回覆", "Replying to", "Reply to",
                    "回應", "In reply to", "回复"
                ]
                
                for keyword in reply_keywords:
                    if keyword in container_text:
                        is_reply = True
                        break
                
                # 方法 2：檢查連結參數
                if not is_reply:
                    if "?xmt=" in full_link or "&xmt=" in full_link:
                        # 有 xmt 參數，但不一定是留言
                        # 需要進一步檢查
                        pass
                
                # 方法 3：檢查是否在開頭就有 @username
                if not is_reply:
                    lines = container_text.split("\n")
                    for line in lines[:5]:  # 檢查前 5 行
                        line = line.strip()
                        if line.startswith("@") and len(line) > 1:
                            is_reply = True
                            break
                
                # 取得作者名稱
                author = ""
                try:
                    author_match = re.search(r'/@([^/]+)/', full_link)
                    if author_match:
                        author = author_match.group(1)
                except:
                    pass
                
                # 取得日期
                date_text, date_obj = find_date_in_element(container)
                
                # 取得完整文章內容
                full_text = get_full_article_text(container)
                
                # 🆕 放寬文字長度限制（允許短留言）
                if len(full_text) < 5:  # 從 10 改成 5
                    skipped_short += 1
                    continue
                
                articles.append({
                    "link": full_link,
                    "date_text": date_text,
                    "date_obj": date_obj,
                    "text": full_text,
                    "is_reply": is_reply,
                    "author": author,
                })
                
                # 每 100 個顯示進度
                if (idx + 1) % 100 == 0:
                    print(f"      已處理 {idx + 1} 個連結，找到 {len(articles)} 篇文章")
            
            except Exception as e:
                skipped_error += 1
                continue
        
        # 🆕 顯示詳細統計
        print(f"\n    📊 處理統計：")
        print(f"       總連結數：{len(post_links)}")
        print(f"       已處理：{processed_count}")
        print(f"       跳過（重複）：{skipped_duplicate}")
        print(f"       跳過（太短）：{skipped_short}")
        print(f"       跳過（錯誤）：{skipped_error}")
        print(f"       ✅ 找到文章：{len(articles)} 篇\n")
        
        # 顯示留言統計
        main_articles = [a for a in articles if not a["is_reply"]]
        reply_articles = [a for a in articles if a["is_reply"]]
        print(f"    📊 文章類型：")
        print(f"       主文章：{len(main_articles)} 篇")
        print(f"       留言/回覆：{len(reply_articles)} 篇")
    
    except Exception as e:
        print(f"    ⚠️ 取得文章失敗：{e}")
    
    return articles




def run_threads_scrape(
    keyword,
    time_range_days=30,
    output_dir=None,
    headless=False,
    user_data_dir=None,
    max_scroll=500,
    force_login=True,
    use_threads_com=True,
    include_replies=True,  # 🆕 是否包含留言（預設 True）
):
    """
    執行 Threads 關鍵字搜尋並產出報表。
    
    🆕 V7.1 核心改進：
    - 優化日期解析（支援 ISO 格式、time 標籤）
    - 改進內容擷取（完整文章內容）
    - 區分主文章 vs 留言
    - 包含文章內容與留言
    
    參數：
    - keyword: 搜尋關鍵字
    - time_range_days: 搜尋幾天內的文章（預設 30）
    - include_replies: 是否包含留言（預設 True）
    - max_scroll: 最大滾動次數（預設 500）
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("⚠️ 請安裝 Playwright：pip install playwright && playwright install chromium")
        return [], output_dir or "."

    keyword = (keyword or "").strip()
    if not keyword:
        print("❌ 關鍵字不可為空")
        return [], output_dir or "."

    try:
        from output_utils import get_campaign_output_dir
        out = output_dir or get_campaign_output_dir()
    except ImportError:
        out = output_dir or "."
    os.makedirs(out, exist_ok=True)

    encoded_q = urllib.parse.quote(keyword)
    domain = "threads.com" if use_threads_com else "threads.net"
    
    # 使用「最新」模式（確保按時間排序）
    search_url = f"https://www.{domain}/search?q={encoded_q}&f=latest"
    
    print(f"  🔍 Threads 搜尋模式：最新貼文（按時間排序）")
    print(f"  📅 日期範圍：最近 {time_range_days} 天")
    print(f"  💬 包含留言：{'是' if include_replies else '否'}")
    print(f"  🌐 使用域名：{domain}")
    print(f"  📜 最大滾動次數：{max_scroll}")
    
    rows = []
    profile_dir = Path(user_data_dir) if user_data_dir else DEFAULT_PROFILE_DIR
    
    # 計算截止日期
    cutoff_date = datetime.now() - timedelta(days=time_range_days)
    print(f"  ⏰ 截止日期：{cutoff_date.strftime('%Y-%m-%d %H:%M')}")

    try:
        with sync_playwright() as p:
            profile_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"  📁 使用瀏覽器設定檔：{profile_dir}")
            
            context = p.chromium.launch_persistent_context(
                str(profile_dir),
                headless=headless,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                locale="zh-TW",
                channel="chromium",
            )
            page = context.pages[0] if context.pages else context.new_page()

            print(f"  🌐 正在開啟 Threads 搜尋頁面...")
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            
            print(f"  ⏳ 等待頁面完全載入...")
            time.sleep(10)

            # 檢查登入狀態
            is_logged_in = check_login_status(page)
            
            if not is_logged_in and force_login:
                print("\n" + "="*60)
                print("⚠️  偵測到未登入 Threads")
                print("="*60)
                print("\n請在「剛開啟的瀏覽器視窗」內完成登入")
                print("="*60)
                
                input("\n✅ 登入完成後請按 Enter 繼續...")
                
                page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(10)
                
                is_logged_in = check_login_status(page)
                
                if not is_logged_in:
                    print("\n❌ 仍未偵測到登入狀態")
                    context.close()
                    return [], out
                else:
                    print("✅ 登入成功！")
            else:
                print("✅ 已登入 Threads")

            # 核心邏輯：按日期範圍滾動
            print(f"\n" + "="*60)
            print(f"📜 開始按日期範圍載入文章")
            print(f"="*60)
            print(f"  🎯 目標：找到所有 {time_range_days} 天內的文章")
            print(f"  ⏱️  策略：滾動到「超過 {time_range_days} 天」為止")
            print(f"="*60 + "\n")
            
            last_count = 0
            no_new_count = 0
            
            for scroll_num in range(max_scroll):
                # 滾動
                page.evaluate("window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })")
                
                # 停留 8 秒，等待載入
                time.sleep(8)
                
                # 取得所有文章及其日期
                all_articles = get_articles_with_dates(page, domain)
                
                # 分類：在範圍內 vs 超出範圍
                in_range = []
                out_of_range = []
                no_date = []
                
                for article in all_articles:
                    if article["date_obj"]:
                        if article["date_obj"] >= cutoff_date:
                            in_range.append(article)
                        else:
                            out_of_range.append(article)
                    else:
                        no_date.append(article)
                
                # 更新計數
                current_in_range = len(in_range)
                current_out_of_range = len(out_of_range)
                
                # 顯示進度
                print(f"    第 {scroll_num + 1:3d} 次滾動：", end="")
                print(f"範圍內 {current_in_range:3d} 篇，", end="")
                print(f"超出範圍 {current_out_of_range:3d} 篇，", end="")
                print(f"無日期 {len(no_date):3d} 篇")
                
                # 停止條件：連續找到 10 篇超出範圍的文章
                if current_out_of_range >= 10:
                    print(f"\n  ✅ 已找到 {current_out_of_range} 篇超出範圍的文章")
                    print(f"  📊 判斷：已滾動到 {time_range_days} 天之前，停止滾動")
                    break
                
                # 檢查是否有新文章
                if current_in_range > last_count:
                    last_count = current_in_range
                    no_new_count = 0
                else:
                    no_new_count += 1
                    
                    # 如果連續 10 次沒有新文章，停止
                    if no_new_count >= 10:
                        print(f"\n  ⚠️ 連續 {no_new_count} 次沒有新文章，停止滾動")
                        break
                
                # 每 20 次滾動顯示進度
                if (scroll_num + 1) % 20 == 0:
                    print(f"\n  📊 進度報告：")
                    print(f"     已滾動：{scroll_num + 1} 次")
                    print(f"     範圍內文章：{current_in_range} 篇")
                    print(f"     超出範圍文章：{current_out_of_range} 篇")
                    print()
                
                # 如果連續 3 次沒有新文章，嘗試往上滾再往下滾
                if no_new_count == 3:
                    print(f"    → 嘗試往上滾再往下滾（觸發載入機制）...")
                    page.evaluate("window.scrollBy({ top: -500, behavior: 'smooth' })")
                    time.sleep(2)
                    page.evaluate("window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })")
                    time.sleep(8)
            
            # 最終取得所有文章
            print(f"\n  🔍 最終取得所有文章...")
            all_articles = get_articles_with_dates(page, domain)
            
            # 過濾：只保留範圍內的文章
            articles_in_range = [a for a in all_articles if a["date_obj"] and a["date_obj"] >= cutoff_date]
            articles_out_of_range = [a for a in all_articles if a["date_obj"] and a["date_obj"] < cutoff_date]
            articles_no_date = [a for a in all_articles if not a["date_obj"]]
            
            print(f"\n  📊 文章分類：")
            print(f"     範圍內（{time_range_days} 天內）：{len(articles_in_range)} 篇 ✅")
            print(f"     超出範圍：{len(articles_out_of_range)} 篇")
            print(f"     無法判斷日期：{len(articles_no_date)} 篇")
            
            # 決策：包含「無法判斷日期」的文章
            if articles_no_date:
                print(f"\n  ℹ️  發現 {len(articles_no_date)} 篇無法判斷日期的文章")
                print(f"     這些文章可能在範圍內，已包含在結果中")
                articles_to_scrape = articles_in_range + articles_no_date
            else:
                articles_to_scrape = articles_in_range
            
            # 🆕 過濾留言（如果需要）
            if not include_replies:
                articles_to_scrape = [a for a in articles_to_scrape if not a["is_reply"]]
                print(f"\n  🚫 已排除留言，剩餘 {len(articles_to_scrape)} 篇主文章")
            else:
                main_articles = [a for a in articles_to_scrape if not a["is_reply"]]
                reply_articles = [a for a in articles_to_scrape if a["is_reply"]]
                print(f"\n  📊 文章類型：")
                print(f"     主文章：{len(main_articles)} 篇")
                print(f"     留言/回覆：{len(reply_articles)} 篇")
            
            print(f"\n  📊 最終決定：爬取 {len(articles_to_scrape)} 篇文章")

            # 建立輸出資料
            print(f"\n" + "="*60)
            print(f"🔍 開始整理文章資料")
            print(f"="*60)
            
            for idx, article in enumerate(articles_to_scrape):
                try:
                    rows.append({
                        "keyword": keyword,
                        "text": article["text"][:2000],  # 限制長度
                        "link": article["link"],
                        "author": article["author"],
                        "is_reply": "是" if article["is_reply"] else "否",
                        "date_text": article["date_text"] or "未知",
                        "date": article["date_obj"].strftime("%Y-%m-%d %H:%M") if article["date_obj"] else "未知",
                        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    })
                    
                    if (idx + 1) % 50 == 0:
                        print(f"  已整理 {idx + 1}/{len(articles_to_scrape)} 篇文章")
                
                except Exception as e:
                    continue
            
            print(f"  ✅ 整理完成，共 {len(rows)} 篇文章")

            context.close()
    
    except Exception as e:
        print(f"\n❌ Threads 爬蟲執行失敗：{e}")
        import traceback
        traceback.print_exc()

    # 去重
    unique_rows = []
    seen_links = set()
    for row in rows:
        link = row.get("link", "")
        if link and link not in seen_links:
            seen_links.add(link)
            unique_rows.append(row)
    
    rows = unique_rows
    
    # 按日期排序（最新的在前面）
    rows.sort(key=lambda x: x.get("date", ""), reverse=True)

    _save_threads_output(rows, keyword, out, time_range_days, include_replies)
    
    if rows:
        print(f"\n" + "="*60)
        print(f"✅ Threads 爬蟲完成")
        print(f"="*60)
        print(f"  找到文章數：{len(rows)} 篇（{time_range_days} 天內）")
        print(f"  輸出目錄：{out}")
        
        # 檢查是否有 @cosmos_alley 的文章
        cosmos_posts = [r for r in rows if "cosmos_alley" in r.get("author", "").lower() or "cosmos_alley" in r.get("link", "").lower()]
        if cosmos_posts:
            print(f"\n🎉 找到 @cosmos_alley 的文章：{len(cosmos_posts)} 篇")
            for post in cosmos_posts:
                print(f"\n   作者：@{post.get('author', '未知')}")
                print(f"   類型：{'留言' if post.get('is_reply') == '是' else '主文章'}")
                print(f"   日期：{post.get('date_text', '未知')}")
                print(f"   內容：{post['text'][:100]}...")
                print(f"   連結：{post['link']}")
        else:
            print(f"\n⚠️ 未找到 @cosmos_alley 的文章")
        
        # 統計資訊
        print(f"\n📊 統計資訊：")
        print(f"   總文章數：{len(rows)} 篇")
        print(f"   日期範圍：{time_range_days} 天內")
        print(f"   有日期的文章：{len([r for r in rows if r.get('date') != '未知'])} 篇")
        print(f"   主文章：{len([r for r in rows if r.get('is_reply') == '否'])} 篇")
        print(f"   留言/回覆：{len([r for r in rows if r.get('is_reply') == '是'])} 篇")
        
        # 顯示日期分布
        dates_with_date = [r for r in rows if r.get("date") != "未知"]
        if dates_with_date:
            oldest = min(dates_with_date, key=lambda x: x["date"])
            newest = max(dates_with_date, key=lambda x: x["date"])
            print(f"   最新文章：{newest.get('date')}")
            print(f"   最舊文章：{oldest.get('date')}")
    else:
        print(f"\n⚠️ Threads 爬蟲完成：0 篇文章")
    
    return rows, out


def _save_threads_output(rows, keyword, out, time_range_days, include_replies):
    """寫入 CSV 與 JSON"""
    import csv as csv_module
    safe_kw = _safe_filename(keyword)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    
    reply_suffix = "_with_replies" if include_replies else "_no_replies"
    csv_path = os.path.join(out, f"threads_{safe_kw}_{time_range_days}days{reply_suffix}_{ts}.csv")
    json_path = os.path.join(out, f"threads_{safe_kw}_{time_range_days}days{reply_suffix}_{ts}.json")
    
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv_module.DictWriter(f, fieldnames=["keyword", "text", "link", "author", "is_reply", "date_text", "date", "scraped_at"])
        w.writeheader()
        w.writerows(rows)
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "keyword": keyword,
            "time_range_days": time_range_days,
            "include_replies": include_replies,
            "total": len(rows),
            "rows": rows
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n📁 輸出檔案：")
    print(f"   CSV：{csv_path}")
    print(f"   JSON：{json_path}")
    
    return csv_path, json_path


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    
    print("="*60)
    print("🔍 Threads 爬蟲（V7.1 完整修復版）")
    print("="*60)
    print("\n🆕 核心改進：")
    print("  ✅ 優化日期解析（支援 ISO 格式、time 標籤）")
    print("  ✅ 改進內容擷取（完整文章內容）")
    print("  ✅ 區分主文章 vs 留言")
    print("  ✅ 包含文章內容與留言")
    print("="*60)
    
    kw = input("\n請輸入 Threads 搜尋關鍵字：").strip() or "功夫"
    days = int(input("搜尋幾天內的文章（預設 30）：").strip() or "30")
    
    include_replies_input = input("是否包含留言？(y/n，預設 y)：").strip().lower()
    include_replies = include_replies_input != "n"
    
    show_browser = input("\n是否顯示瀏覽器視窗？(y/n，預設 y)：").strip().lower() != "n"
    
    print("\n" + "="*60)
    print("開始執行...")
    print("="*60)
    
    run_threads_scrape(
        kw,
        time_range_days=days,
        include_replies=include_replies,
        headless=not show_browser,
        max_scroll=1000,
        force_login=True,
        use_threads_com=True,
    )
