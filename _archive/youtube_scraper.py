# -*- coding: utf-8 -*-
"""
YouTube 爬蟲 - 使用 YouTube Data API v3
功能：關鍵字搜尋影片、頻道影片列表、留言擷取
輸出：CSV / JSON

⚠️ 配額說明：
- YouTube Data API 免費配額：每日 10,000 units
- 搜尋 API 每次呼叫使用 100 units
- 影片詳細資料每次呼叫使用 1 unit
- 建議：控制搜尋次數，避免額度用盡
"""

import csv
import json
import logging
import os
import random
import re
import time
from datetime import datetime
from typing import List, Dict, Optional

from output_utils import _safe_filename, _safe_print

logger = logging.getLogger(__name__)

# === 輸出欄位 ===
CSV_HEADERS = [
    "關鍵字", "影片網址", "影片標題", "頻道名稱", "頻道ID",
    "發布時間", "觀看數", "按讚數", "留言數",
    "影片描述", "標籤", "縮圖網址", "擷取時間"
]

# === API 配置 ===
MAX_RESULTS_PER_SEARCH = 50  # 每次搜尋最多回傳結果
MAX_COMMENTS_PER_VIDEO = 20  # 每部影片最多擷取留言數


def get_youtube_api_key() -> str:
    """從環境變數取得 YouTube API Key"""
    # 先嘗試從 config 讀取
    try:
        from config import Config
        api_key = getattr(Config, 'YOUTUBE_API_KEY', '') or os.getenv('YOUTUBE_API_KEY', '')
        if api_key:
            return api_key
    except ImportError:
        pass
    
    # 從環境變數直接讀取
    return os.getenv('YOUTUBE_API_KEY', '')


def search_videos_by_keyword(
    api_key: str,
    keyword: str,
    max_results: int = MAX_RESULTS_PER_SEARCH,
    published_after: str = None
) -> List[Dict]:
    """
    使用 YouTube Data API 搜尋影片
    
    參數：
    - api_key: YouTube Data API Key
    - keyword: 搜尋關鍵字
    - max_results: 最大結果數
    - published_after: 發布時間下限 (ISO 8601 format)
    
    回傳：影片 ID 列表
    """
    import urllib.request
    import urllib.parse
    
    video_ids = []
    
    url = f"https://www.googleapis.com/youtube/v3/search"
    params = {
        'part': 'snippet',
        'q': keyword,
        'type': 'video',
        'maxResults': min(max_results, 50),
        'key': api_key,
        'order': 'relevance',  # 相關性排序
        'videoCaption': 'any',  # 任何字幕
    }
    
    if published_after:
        params['publishedAfter'] = published_after
    
    query_string = urllib.parse.urlencode(params)
    full_url = f"{url}?{query_string}"
    
    try:
        request = urllib.request.Request(full_url)
        request.add_header('User-Agent', 'Mozilla/5.0')
        
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        if 'items' in data:
            for item in data['items']:
                if 'videoId' in item.get('id', {}):
                    video_ids.append({
                        'video_id': item['id']['videoId'],
                        'snippet': item.get('snippet', {})
                    })
        
        _safe_print(f"    搜尋「{keyword}」找到 {len(video_ids)} 部影片")
        
    except Exception as e:
        _safe_print(f"    [!] API 搜尋失敗：{str(e)[:50]}")
        
        # 如果是配額不足，提供提示
        if 'quota' in str(e).lower():
            _safe_print(f"    [!] 可能是配額不足，請稍後再試或更換 API Key")
    
    return video_ids


def get_video_details(api_key: str, video_ids: List[str]) -> List[Dict]:
    """取得影片詳細資料"""
    import urllib.request
    import urllib.parse
    
    videos = []
    
    # YouTube API 每次最多 50 個 ID
    batch_size = 50
    
    for i in range(0, len(video_ids), batch_size):
        batch = video_ids[i:i + batch_size]
        ids_string = ','.join(batch)
        
        url = f"https://www.googleapis.com/youtube/v3/videos"
        params = {
            'part': 'snippet,statistics,contentDetails',
            'id': ids_string,
            'key': api_key,
        }
        
        query_string = urllib.parse.urlencode(params)
        full_url = f"{url}?{query_string}"
        
        try:
            request = urllib.request.Request(full_url)
            request.add_header('User-Agent', 'Mozilla/5.0')
            
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            if 'items' in data:
                for item in data['items']:
                    video_data = {
                        'video_id': item['id'],
                        'title': item.get('snippet', {}).get('title', ''),
                        'description': item.get('snippet', {}).get('description', ''),
                        'channel_title': item.get('snippet', {}).get('channelTitle', ''),
                        'channel_id': item.get('snippet', {}).get('channelId', ''),
                        'published_at': item.get('snippet', {}).get('publishedAt', ''),
                        'thumbnail': item.get('snippet', {}).get('thumbnails', {}).get('high', {}).get('url', ''),
                        'tags': item.get('snippet', {}).get('tags', []),
                        'view_count': item.get('statistics', {}).get('viewCount', '0'),
                        'like_count': item.get('statistics', {}).get('likeCount', '0'),
                        'comment_count': item.get('statistics', {}).get('commentCount', '0'),
                    }
                    videos.append(video_data)
            
            # API 請求間隔
            if i + batch_size < len(video_ids):
                time.sleep(0.1)
            
        except Exception as e:
            _safe_print(f"    [!] 取得影片詳細資料失敗：{str(e)[:50]}")
    
    return videos


def get_video_comments(
    api_key: str,
    video_id: str,
    max_results: int = MAX_COMMENTS_PER_VIDEO
) -> List[Dict]:
    """取得影片留言"""
    import urllib.request
    import urllib.parse
    
    comments = []
    
    url = f"https://www.googleapis.com/youtube/v3/commentThreads"
    params = {
        'part': 'snippet',
        'videoId': video_id,
        'maxResults': min(max_results, 100),
        'order': 'relevance',  # 按相關性排序
        'key': api_key,
    }
    
    query_string = urllib.parse.urlencode(params)
    full_url = f"{url}?{query_string}"
    
    try:
        request = urllib.request.Request(full_url)
        request.add_header('User-Agent', 'Mozilla/5.0')
        
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        if 'items' in data:
            for item in data['items']:
                comment = item.get('snippet', {}).get('topLevelComment', {}).get('snippet', {})
                comments.append({
                    'author': comment.get('authorDisplayName', ''),
                    'text': comment.get('textDisplay', ''),
                    'like_count': comment.get('likeCount', 0),
                    'published_at': comment.get('publishedAt', ''),
                })
    
    except Exception as e:
        # 留言可能關閉，靜默略過
        pass
    
    return comments


def get_channel_videos(api_key: str, channel_id: str, max_results: int = 50) -> List[Dict]:
    """取得頻道的影片列表"""
    import urllib.request
    import urllib.parse
    
    # 先取得頻道的「上傳」播放清單 ID
    channel_url = f"https://www.googleapis.com/youtube/v3/channels"
    params = {
        'part': 'contentDetails',
        'id': channel_id,
        'key': api_key,
    }
    
    uploads_id = None
    
    try:
        query_string = urllib.parse.urlencode(params)
        full_url = f"{channel_url}?{query_string}"
        
        request = urllib.request.Request(full_url)
        request.add_header('User-Agent', 'Mozilla/5.0')
        
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        if 'items' in data and data['items']:
            uploads_id = data['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    
    except Exception as e:
        _safe_print(f"    [!] 取得頻道資料失敗：{str(e)[:50]}")
        return []
    
    if not uploads_id:
        return []
    
    # 取得上傳影片清單
    playlist_url = f"https://www.googleapis.com/youtube/v3/playlistItems"
    params = {
        'part': 'snippet',
        'playlistId': uploads_id,
        'maxResults': min(max_results, 50),
        'key': api_key,
    }
    
    videos = []
    
    try:
        query_string = urllib.parse.urlencode(params)
        full_url = f"{playlist_url}?{query_string}"
        
        request = urllib.request.Request(full_url)
        request.add_header('User-Agent', 'Mozilla/5.0')
        
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        if 'items' in data:
            for item in data['items']:
                snippet = item.get('snippet', {})
                videos.append({
                    'video_id': snippet.get('resourceId', {}).get('videoId', ''),
                    'title': snippet.get('title', ''),
                    'description': snippet.get('description', ''),
                    'channel_title': snippet.get('channelTitle', ''),
                    'channel_id': snippet.get('channelId', ''),
                    'published_at': snippet.get('publishedAt', ''),
                    'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
                })
    
    except Exception as e:
        _safe_print(f"    [!] 取得播放清單失敗：{str(e)[:50]}")
    
    return videos


def parse_youtube_date(date_str: str) -> Optional[datetime]:
    """解析 YouTube 日期格式"""
    if not date_str:
        return None
    
    try:
        # ISO 8601 格式：2024-01-15T12:00:00Z
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except:
        return None


def run_youtube_scrape(
    keywords: List[str] = None,
    channel_ids: List[str] = None,
    channel_usernames: List[str] = None,
    time_range_days: int = 30,
    output_dir: str = None,
    keyword_label: str = None,
    include_comments: bool = False,
    max_videos_per_keyword: int = 30
):
    """
    執行 YouTube 搜尋並產出報表
    
    參數：
    - keywords: 關鍵字列表
    - channel_ids: 頻道 ID 列表
    - channel_usernames: 頻道名稱列表（會自動轉換為 ID）
    - time_range_days: 搜尋天數
    - output_dir: 輸出目錄
    - keyword_label: 檔名用關鍵字
    - include_comments: 是否擷取留言
    - max_videos_per_keyword: 每個關鍵字最多影片數
    
    回傳：(results, output_dir)
    """
    api_key = get_youtube_api_key()
    
    if not api_key:
        _safe_print("\n⚠️ 請先設定 YouTube API Key")
        _safe_print("   在 system.env 或 .env 中加入：YOUTUBE_API_KEY=你的API金鑰")
        _safe_print("   申請網址：https://console.cloud.google.com/")
        return [], output_dir or "."
    
    keywords = keywords or []
    channel_ids = channel_ids or []
    channel_usernames = channel_usernames or []
    
    if not keywords and not channel_ids and not channel_usernames:
        keywords = ["測試"]
    
    try:
        from output_utils import get_report_output_dir
        out = output_dir or get_report_output_dir("reports")
    except ImportError:
        out = output_dir or "reports"
    os.makedirs(out, exist_ok=True)
    
    label = keyword_label or (keywords[0] if keywords else "youtube")
    all_results = []
    all_comments = []
    
    # 計算發布時間下限
    from datetime import timedelta
    published_after = None
    if time_range_days < 9999:
        published_dt = datetime.now() - timedelta(days=time_range_days)
        published_after = published_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    _safe_print("\n" + "=" * 50)
    _safe_print("  YouTube 爬蟲（API v3）")
    _safe_print("=" * 50)
    _safe_print(f"\n⚠️  配額提醒：免費額度 10,000 units/天")
    _safe_print(f"    搜尋每次使用 ~100 units")
    _safe_print(f"    取得影片詳細資料每次使用 ~1 unit\n")
    
    # 處理頻道名稱（轉換為 ID）
    processed_channel_ids = list(channel_ids)
    
    # 關鍵字搜尋
    for kw in keywords:
        kw = (kw or "").strip()
        if not kw:
            continue
        
        _safe_print(f"\n[*] 搜尋關鍵字：{kw}")
        
        # 搜尋影片
        search_results = search_videos_by_keyword(
            api_key, kw,
            max_results=max_videos_per_keyword,
            published_after=published_after
        )
        
        if not search_results:
            continue
        
        # 取得影片 ID 列表
        video_ids = [r['video_id'] for r in search_results]
        
        # 取得詳細資料
        _safe_print(f"    取得詳細資料中...")
        video_details = get_video_details(api_key, video_ids)
        
        # 取得留言（可選）
        if include_comments:
            _safe_print(f"    擷取留言中...")
        
        for video in video_details:
            # 時間過濾
            if time_range_days < 9999:
                video_date = parse_youtube_date(video.get('published_at', ''))
                if video_date:
                    cutoff = datetime.now() - timedelta(days=time_range_days)
                    if video_date < cutoff:
                        continue
            
            result = {
                "keyword": kw,
                "video_url": f"https://www.youtube.com/watch?v={video['video_id']}",
                "title": video['title'],
                "channel_title": video['channel_title'],
                "channel_id": video['channel_id'],
                "published_at": video['published_at'],
                "view_count": video['view_count'],
                "like_count": video['like_count'],
                "comment_count": video['comment_count'],
                "description": video['description'][:2000],
                "tags": ",".join(video.get('tags', [])),
                "thumbnail": video['thumbnail'],
                "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
            
            all_results.append(result)
            
            # 留言
            if include_comments:
                comments = get_video_comments(api_key, video['video_id'])
                for comment in comments:
                    comment_result = {
                        "video_id": video['video_id'],
                        "video_title": video['title'],
                        "author": comment['author'],
                        "text": comment['text'][:1000],
                        "like_count": comment['like_count'],
                        "published_at": comment['published_at'],
                        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    }
                    all_comments.append(comment_result)
            
            _safe_print(f"    ✓ {video['title'][:40]}...")
        
        # 避免太快用完配額
        time.sleep(0.5)
    
    # 處理頻道
    all_channel_ids = processed_channel_ids
    
    # 轉換頻道名稱為 ID
    for username in channel_usernames:
        username = (username or "").strip()
        if not username:
            continue
        
        _safe_print(f"\n[*] 處理頻道：{username}")
        
        # 搜尋頻道
        search_results = search_videos_by_keyword(
            api_key, username,
            max_results=1,
            published_after=None
        )
        
        if search_results:
            # 從搜尋結果取得頻道 ID
            snippet = search_results[0].get('snippet', {})
            found_channel_id = snippet.get('channelId', '')
            if found_channel_id and found_channel_id not in all_channel_ids:
                all_channel_ids.append(found_channel_id)
    
    # 取得頻道影片
    for channel_id in all_channel_ids:
        channel_id = (channel_id or "").strip()
        if not channel_id:
            continue
        
        _safe_print(f"\n[*] 取得頻道 {channel_id} 的影片")
        
        channel_videos = get_channel_videos(api_key, channel_id, max_results=20)
        
        for video in channel_videos:
            result = {
                "keyword": f"channel:{channel_id}",
                "video_url": f"https://www.youtube.com/watch?v={video['video_id']}",
                "title": video['title'],
                "channel_title": video['channel_title'],
                "channel_id": video['channel_id'],
                "published_at": video['published_at'],
                "view_count": "0",  # 播放清單 API 不含統計
                "like_count": "0",
                "comment_count": "0",
                "description": video['description'][:2000],
                "tags": "",
                "thumbnail": video['thumbnail'],
                "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
            all_results.append(result)
    
    # 儲存結果
    if all_results:
        save_results(all_results, all_comments, label, out)
    
    _safe_print(f"\n[*] YouTube 爬蟲完成：共 {len(all_results)} 部影片")
    if all_comments:
        _safe_print(f"    留言數：{len(all_comments)} 則")
    
    return all_results, out


def save_results(results: List[Dict], comments: List[Dict], keyword: str, output_dir: str):
    """儲存 CSV 和 JSON"""
    safe_kw = _safe_filename(keyword)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    
    csv_path = os.path.join(output_dir, f"youtube_{safe_kw}_{ts}.csv")
    json_path = os.path.join(output_dir, f"youtube_{safe_kw}_{ts}.json")
    
    # CSV
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "關鍵字": r.get("keyword", ""),
                "影片網址": r.get("video_url", ""),
                "影片標題": r.get("title", ""),
                "頻道名稱": r.get("channel_title", ""),
                "頻道ID": r.get("channel_id", ""),
                "發布時間": r.get("published_at", ""),
                "觀看數": r.get("view_count", "0"),
                "按讚數": r.get("like_count", "0"),
                "留言數": r.get("comment_count", "0"),
                "影片描述": r.get("description", ""),
                "標籤": r.get("tags", ""),
                "縮圖網址": r.get("thumbnail", ""),
                "擷取時間": r.get("scraped_at", ""),
            })
    
    # JSON（含留言）
    output_data = {
        "keyword": keyword,
        "total_videos": len(results),
        "total_comments": len(comments),
        "videos": results,
    }
    
    if comments:
        output_data["comments"] = comments
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
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
    print("  YouTube 爬蟲（API v3）")
    print("=" * 50)
    
    # 檢查 API Key
    api_key = get_youtube_api_key()
    if not api_key:
        print("\n⚠️  請先設定 YouTube API Key")
        print("   在 system.env 中加入：YOUTUBE_API_KEY=你的API金鑰")
        return
    
    print(f"\n✓ 已偵測到 YouTube API Key")
    
    choice = input("\n請選擇搜尋類型：")
    print("  1. 關鍵字搜尋")
    print("  2. 頻道 ID")
    choice = input("請輸入選項 (1-2)：").strip() or "1"
    
    if choice == "1":
        kw = input("\n請輸入搜尋關鍵字：").strip() or "美食"
        keywords = [kw]
        channel_ids = []
    else:
        ch = input("\n請輸入頻道 ID：").strip()
        keywords = []
        channel_ids = [ch]
    
    days = int(input("搜尋幾天內的影片（預設 30，輸入 9999 代表不限）：").strip() or "30")
    
    include_comments = input("是否擷取留言？(y/n，預設 n)：").strip().lower() == "y"
    
    print("\n" + "=" * 50)
    print("開始執行...")
    print("=" * 50)
    
    run_youtube_scrape(
        keywords=keywords,
        channel_ids=channel_ids,
        time_range_days=days,
        include_comments=include_comments
    )


if __name__ == "__main__":
    main()
