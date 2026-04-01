import os
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")

youtube = build("youtube", "v3", developerKey=API_KEY)


def get_channel_id_by_name(channel_name):
    """用頻道名稱搜尋 Channel ID"""
    res = youtube.search().list(
        q=channel_name,
        part="snippet",
        type="channel",
        maxResults=1
    ).execute()

    items = res.get("items", [])
    if not items:
        print(f"❌ 找不到頻道：{channel_name}")
        return None

    channel_id = items[0]["snippet"]["channelId"]
    print(f"✅ {channel_name} → Channel ID：{channel_id}")
    return channel_id


def get_channel_stats(channel_id):
    """抓頻道基本數據：訂閱數"""
    res = youtube.channels().list(
        part="statistics,snippet",
        id=channel_id
    ).execute()

    items = res.get("items", [])
    if not items:
        return None

    stats = items[0]["statistics"]
    return {
        "subscribers": int(stats.get("subscriberCount", 0)),
        "total_videos": int(stats.get("videoCount", 0)),
    }


def get_recent_videos(channel_id, max_results=10):
    """抓最近 N 支影片的 ID"""
    res = youtube.search().list(
        channelId=channel_id,
        part="id",
        order="date",
        type="video",
        maxResults=max_results
    ).execute()

    return [item["id"]["videoId"] for item in res.get("items", [])]


def get_top_videos(channel_id, max_results=10):
    """抓最熱門 N 支影片的 ID"""
    res = youtube.search().list(
        channelId=channel_id,
        part="id",
        order="viewCount",
        type="video",
        maxResults=max_results
    ).execute()

    return [item["id"]["videoId"] for item in res.get("items", [])]


def get_video_stats(video_ids):
    """抓影片的觀看數和按讚數，回傳平均值"""
    if not video_ids:
        return {"avg_views": 0, "avg_likes": 0}

    res = youtube.videos().list(
        part="statistics",
        id=",".join(video_ids)
    ).execute()

    views, likes = [], []
    for item in res.get("items", []):
        stats = item["statistics"]
        views.append(int(stats.get("viewCount", 0)))
        likes.append(int(stats.get("likeCount", 0)))

    return {
        "avg_views": int(sum(views) / len(views)) if views else 0,
        "avg_likes": int(sum(likes) / len(likes)) if likes else 0,
    }


def fetch_youtube_data(channel_name):
    """主函式：輸入頻道名稱，回傳完整數據"""
    print(f"\n🔍 正在抓取：{channel_name}")

    channel_id = get_channel_id_by_name(channel_name)
    if not channel_id:
        return None

    stats = get_channel_stats(channel_id)
    if not stats:
        return None

    recent_ids = get_recent_videos(channel_id)
    recent_stats = get_video_stats(recent_ids)

    top_ids = get_top_videos(channel_id)
    top_stats = get_video_stats(top_ids)

    result = {
        "name": channel_name,
        "subscribers": stats["subscribers"],
        "recent_avg_views": recent_stats["avg_views"],
        "recent_avg_likes": recent_stats["avg_likes"],
        "recent_engagement_rate": round(recent_stats["avg_likes"] / recent_stats["avg_views"], 4) if recent_stats["avg_views"] else 0,
        "top_avg_views": top_stats["avg_views"],
        "top_avg_likes": top_stats["avg_likes"],
        "top_engagement_rate": round(top_stats["avg_likes"] / top_stats["avg_views"], 4) if top_stats["avg_views"] else 0,
    }

    print(f"   訂閱數：{result['subscribers']:,}")
    print(f"   近期均觀看：{result['recent_avg_views']:,}｜近期均讚：{result['recent_avg_likes']:,}｜近期互動率：{result['recent_engagement_rate']:.2%}")
    print(f"   熱門均觀看：{result['top_avg_views']:,}｜熱門均讚：{result['top_avg_likes']:,}｜熱門互動率：{result['top_engagement_rate']:.2%}")

    return result


# ── 測試用 ────────────────────────────────────────────────
if __name__ == "__main__":
    test_channels = ["東區德", "UC Training"]
    for name in test_channels:
        fetch_youtube_data(name)