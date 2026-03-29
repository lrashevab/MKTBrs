# -*- coding: utf-8 -*-
"""
P2 情緒分析強化模組
功能：
- 信心分數、三分類輸出（positive/negative/neutral）
- 六種細分情緒（anger/joy/sadness/surprise/fear/disgust）
- 中英文雙語支援
- 自訂外部詞典載入
- 行銷專用詞強化
"""

import json
import os
import re
from typing import Dict, List, Optional, Tuple

# ===========================================
# 基礎詞典（保留原有功能）
# ===========================================

# 通用負評詞（所有產業共用）
NEGATIVE_WORDS_BASE = [
    "雷", "爛", "騙", "貴", "沒效", "後悔", "盤子", "割韭菜", "退費", "假", "套路",
    "話術", "PUA", "直銷", "浪費錢", "不值得", "噱頭", "誇大", "廣告不實",
    "客服差", "態度差", "敷衍", "推銷", "強迫推銷", "罐頭", "背稿", "制式",
    "失望", "不推", "踩雷", "地雷", "噁心", "猥瑣", "噁", "反感", "討厭",
]

# 通用正面詞
POSITIVE_WORDS_BASE = [
    "推薦", "好用", "讚", "棒", "超棒", "很棒", "厲害", "強", "神", "完美",
    "滿意", "喜歡", "任用", "必買", "值得", "CP值高", "划算", "超值", "物超所值",
    "有效", "有用", "實用", "方便", "好用", "順手", "流暢", "自然",
    "開心", "舒服", "安心", "放心", "期待", "感謝", "謝謝", "讚讚",
    "品質好", "高品質", "用料好", "做工好", "質感", "精緻",
]

# 行銷專用詞（新增）
MARKETING_POSITIVE = [
    "爆款", "必買", "CP值", "划算", "推薦", "神器", "超值的",
    "搶爆", "熱賣", "口碑", "人氣", "夯", "大熱", "網紅",
    "激推", "真心推薦", "回購", "無限回購", "私心大推",
]

MARKETING_NEGATIVE = [
    "踩雷", "退貨", "詐騙", "爛", "根本", "浪費", "假貨",
    "雷區", "地雷", "勸退", "不推", "黑心", "坑錢",
    "踩坑", "被當盤子", "交智商稅", "不值得",
]

# 六種細分情緒詞典（中文）
EMOTION_KEYWORDS = {
    "anger": [
        "氣死", "氣憤", "生氣", "火大", "超氣", "怒", "不爽",
        "可惡", "扯", "離譜", "誇張", "黑心", "無良", "奸商",
        "騙錢", "坑人", "當盤子", "智商稅", "垃圾", "廢物",
    ],
    "joy": [
        "超開心", "太棒了", "完美", "愛了", "愛上", "幸福",
        "滿足", "興奮", "期待", "開心", "快樂", "爽", "讚",
        "推薦", "必買", "好用", "好用", "愛不釋手",
    ],
    "sadness": [
        "難過", "傷心", "失望", "心酸", "無奈", "鬱卒",
        "可惜", "遺憾", "崩潰", "哭", "淚", "灰心", "洩氣",
    ],
    "surprise": [
        "驚訝", "震驚", "嚇到", "超誇張", "不可思議", "竟然",
        "居然", "沒想到", "嚇死", "驚喜", "驚豔", "驚喜",
    ],
    "fear": [
        "怕", "擔心", "緊張", "焦慮", "不安", "恐懼",
        "不敢", "怕被", "擔心會", "會不會", "會怕",
    ],
    "disgust": [
        "噁心", "嘔吐", "反胃", "厭惡", "嫌棄", "不屑",
        "噁", "倒胃口", "不舒服", "不適", "過敏",
    ],
}

# 六種細分情緒詞典（英文）
EMOTION_KEYWORDS_EN = {
    "anger": [
        "angry", "furious", "mad", "hate", "terrible", "awful", "horrible",
        "scam", "fraud", "ripoff", "rip off", "cheat", "scam", "trash",
        "worst", "garbage", "junk", "waste", "money grab",
    ],
    "joy": [
        "happy", "love", "amazing", "awesome", "perfect", "great", "excellent",
        "recommend", "must buy", "best", "fantastic", "wonderful", "brilliant",
    ],
    "sadness": [
        "sad", "disappointed", "unfortunate", "regret", "upset", "heartbroken",
        "cry", "tears", "miss", "longing", "feel bad",
    ],
    "surprise": [
        "surprised", "shocked", "amazing", "incredible", "unbelievable",
        "wow", "unexpected", "can't believe", "astonished",
    ],
    "fear": [
        "afraid", "worried", "anxious", "nervous", "fear", "scared",
        "concerned", "panic", "terrified", "dread",
    ],
    "disgust": [
        "disgusting", "gross", "nasty", "awful", "terrible", "sick",
        "repulsive", "revolting", "vile", "dislike",
    ],
}

# 英文正負面詞典（行銷場景）
POSITIVE_WORDS_EN = [
    "recommend", "great", "excellent", "amazing", "awesome", "perfect",
    "best", "good", "love", "like", "fantastic", "wonderful", "brilliant",
    "outstanding", "superb", "quality", "worth", "value", "deal", "bargain",
    "happy", "satisfied", "pleased", "impressed", "useful", "effective",
    "must-buy", "must have", "highly recommend", "five stars", "10/10",
    "worth it", "good value", "good price", "affordable", "cheap",
]

NEGATIVE_WORDS_EN = [
    "bad", "terrible", "awful", "horrible", "worst", "hate", "dislike",
    "scam", "fraud", "ripoff", "cheat", "fake", "scam", "waste",
    "disappointed", "regret", "overpriced", "expensive", "not worth",
    "poor quality", "junk", "trash", "garbage", "useless", "worthless",
    "avoid", "not recommend", "stay away", "don't buy", "skip",
]

# 產業專屬詞典（保留）
INDUSTRY_WORDS = {
    "餐飲": ["油", "鹹", "甜", "膩", "份量少", "貴", "CP值", "衛生", "服務慢", "等很久", "雷", "地雷", "不推"],
    "電商": ["出貨慢", "退貨", "瑕疵", "假貨", "盜版", "客服", "包裝", "遲到", "缺貨", "取消訂單"],
    "課程": ["學費", "沒效", "退費", "話術", "PUA", "割韭菜", "盤子", "背稿", "罐頭", "套路"],
    "旅遊": ["踩雷", "雷", "貴", "行程", "導遊", "住宿", "衛生", "延誤", "取消"],
    "美妝保養": ["過敏", "沒效", "雷", "假貨", "盜版", "成分", "廣告不實"],
    "預設": [],
}

# 四維度情感（保留原有功能）
SENTIMENT_CATEGORIES = {
    "產品技術觀感": {
        "keywords": ["話術", "套路", "罐頭", "背稿", "假", "制式", "PUA", "開場白", "模板", "不自然"],
        "polarity": "負面 (覺得假/不真實)",
    },
    "情緒焦慮": {
        "keywords": ["尷尬", "自卑", "焦慮", "緊張", "沒自信", "心態", "勇氣", "被當怪人", "怕", "壓力"],
        "polarity": "中性/焦慮",
    },
    "商業消費爭議": {
        "keywords": ["割韭菜", "盤子", "貴", "學費", "退費", "騙", "浪費錢", "沒效", "直銷感", "雷", "爛"],
        "polarity": "極度負面",
    },
    "期待與正向需求": {
        "keywords": ["自然", "流暢", "幽默", "接話", "情緒價值", "有效", "有用", "專業", "推薦"],
        "polarity": "正面 (渴望)",
    },
}

# 停用詞
STOP_WORDS = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一個", "上", "也", "很", "到", "說", "要", "去", "你", "會", "著", "沒有", "看", "好", "自己", "這", "那", "什麼", "怎麼", "可以", "覺得", "大家", "問題", "分享"}


# ===========================================
# 工具函式
# ===========================================

def detect_language(text: str) -> str:
    """自動偵測語言：中文或英文"""
    if not text:
        return "unknown"
    
    # 計算中文字符數量
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    # 計算英文字符數量
    english_chars = len(re.findall(r'[a-zA-Z]', text))
    
    total = chinese_chars + english_chars
    if total == 0:
        return "unknown"
    
    if chinese_chars > english_chars * 0.5:
        return "zh"
    elif english_chars > chinese_chars * 0.5:
        return "en"
    else:
        return "mixed"


def load_custom_dict(path: str = None) -> Dict[str, List[str]]:
    """載入自訂外部詞典"""
    default_path = "custom_sentiment_dict.json"
    
    # 如果沒有指定路徑，嘗試預設路徑
    if path is None:
        path = default_path
    
    if not os.path.exists(path):
        return {"positive": [], "negative": []}
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return {
            "positive": data.get("positive", []),
            "negative": data.get("negative", []),
        }
    except Exception:
        return {"positive": [], "negative": []}


def get_negative_words(industry: str = None) -> List[str]:
    """取得負評詞列表"""
    words = list(NEGATIVE_WORDS_BASE) + list(MARKETING_NEGATIVE)
    
    if industry and industry.strip():
        key = industry.strip()
        if key in INDUSTRY_WORDS:
            for w in INDUSTRY_WORDS[key]:
                if w not in words:
                    words.append(w)
    return words


def get_positive_words(industry: str = None) -> List[str]:
    """取得正面詞列表"""
    words = list(POSITIVE_WORDS_BASE) + list(MARKETING_POSITIVE)
    return words


def get_all_sentiment_words(industry: str = None, custom_dict: Dict = None) -> Tuple[List[str], List[str]]:
    """取得完整的正負面詞典（合併內建 + 自訂）"""
    positive = list(POSITIVE_WORDS_BASE) + list(MARKETING_POSITIVE)
    negative = list(NEGATIVE_WORDS_BASE) + list(MARKETING_NEGATIVE)
    
    # 加入英文詞典
    positive += POSITIVE_WORDS_EN
    negative += NEGATIVE_WORDS_EN
    
    # 加入產業詞典
    if industry and industry.strip():
        key = industry.strip()
        if key in INDUSTRY_WORDS:
            negative += INDUSTRY_WORDS[key]
    
    # 加入自訂詞典
    if custom_dict:
        positive += custom_dict.get("positive", [])
        negative += custom_dict.get("negative", [])
    
    # 去重
    positive = list(set(positive))
    negative = list(set(negative))
    
    return positive, negative


def calculate_confidence(matched_count: int, total_words: int) -> float:
    """
    計算信心分數
    公式：(匹配詞數 / 總詞數) * 飽和係數
    飽和係數：當匹配詞數夠多時，分數趨近於 1
    """
    if total_words == 0:
        return 0.0
    
    # 基礎比率
    ratio = matched_count / total_words
    
    # 飽和係數：使用對數函數讓分數更平滑
    # 當 matched_count >= 5 時，接近 1
    saturation = 1 - (0.7 ** (matched_count + 1))
    
    confidence = ratio * saturation
    
    # 限制在 0-1 範圍
    return round(min(max(confidence, 0.0), 1.0), 2)


def calculate_sentiment_scores(text: str, positive_words: List[str], negative_words: List[str]) -> Dict[str, float]:
    """計算三分類情緒分數"""
    if not text:
        return {"positive": 0.0, "negative": 0.0, "neutral": 1.0}
    
    # 分詞
    words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text.lower())
    words = [w for w in words if len(w) > 1]
    total_words = len(words)
    
    if total_words == 0:
        return {"positive": 0.0, "negative": 0.0, "neutral": 1.0}
    
    # 計算匹配數
    pos_matches = sum(1 for w in words if any(pw in w or w in pw for pw in positive_words))
    neg_matches = sum(1 for w in words if any(nw in w or w in nw for nw in negative_words))
    
    # 計算分數
    pos_score = pos_matches / total_words
    neg_score = neg_matches / total_words
    
    # 中性 = 1 - (正面 + 負面)，最小為 0
    neutral_score = max(0.0, 1.0 - pos_score - neg_score)
    
    # 歸一化
    total = pos_score + neg_score + neutral_score
    if total > 0:
        pos_score = pos_score / total
        neg_score = neg_score / total
        neutral_score = neutral_score / total
    
    return {
        "positive": round(pos_score, 2),
        "negative": round(neg_score, 2),
        "neutral": round(neutral_score, 2),
    }


def detect_emotion(text: str) -> Optional[str]:
    """偵測細分情緒"""
    if not text:
        return None
    
    text_lower = text.lower()
    lang = detect_language(text)
    
    # 根據語言選擇詞典
    if lang == "en":
        emotion_dict = EMOTION_KEYWORDS_EN
    else:
        emotion_dict = EMOTION_KEYWORDS
    
    # 計算各情緒匹配數
    emotion_scores = {}
    for emotion, keywords in emotion_dict.items():
        matches = sum(1 for kw in keywords if kw in text_lower)
        if matches > 0:
            emotion_scores[emotion] = matches
    
    # 回傳最高分的情緒
    if emotion_scores:
        primary_emotion = max(emotion_scores, key=emotion_scores.get)
        return primary_emotion
    
    return None


def find_matched_keywords(text: str, positive_words: List[str], negative_words: List[str]) -> Tuple[List[str], List[str]]:
    """找出匹配的正負面關鍵詞"""
    if not text:
        return [], []
    
    text_lower = text.lower()
    pos_matched = []
    neg_matched = []
    
    # 檢查正面詞
    for pw in positive_words:
        if pw in text_lower:
            pos_matched.append(pw)
    
    # 檢查負面詞
    for nw in negative_words:
        if nw in text_lower:
            neg_matched.append(nw)
    
    # 去重
    pos_matched = list(set(pos_matched))
    neg_matched = list(set(neg_matched))
    
    return pos_matched, neg_matched


# ===========================================
# 強化版分析函式（新增）
# ===========================================

def analyze_sentiment_v2(
    text: str,
    industry: str = None,
    custom_dict_path: str = None
) -> Dict:
    """
    P2 強化版情緒分析
    
    輸出格式：
    {
        "sentiment": "negative",      # positive / negative / neutral
        "confidence": 0.87,           # 0.0 ~ 1.0
        "emotion": "anger",          # anger / joy / sadness / surprise / fear / disgust / None
        "positive_keywords": ["推薦"],
        "negative_keywords": ["踩雷", "退貨"],
        "scores": {
            "positive": 0.15,
            "negative": 0.72,
            "neutral": 0.13
        },
        "language": "zh"             # zh / en / mixed
    }
    """
    if not text or not text.strip():
        return {
            "sentiment": "neutral",
            "confidence": 0.0,
            "emotion": None,
            "positive_keywords": [],
            "negative_keywords": [],
            "scores": {"positive": 0.0, "negative": 0.0, "neutral": 1.0},
            "language": "unknown",
        }
    
    # 偵測語言
    lang = detect_language(text)
    
    # 載入自訂詞典
    custom_dict = None
    if custom_dict_path:
        custom_dict = load_custom_dict(custom_dict_path)
    
    # 取得完整詞典
    positive_words, negative_words = get_all_sentiment_words(industry, custom_dict)
    
    # 計算三分類分數
    scores = calculate_sentiment_scores(text, positive_words, negative_words)
    
    # 找出匹配關鍵詞
    pos_keywords, neg_keywords = find_matched_keywords(text, positive_words, negative_words)
    
    # 計算信心分數
    total_matches = len(pos_keywords) + len(neg_keywords)
    total_words = len(re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text.lower()))
    confidence = calculate_confidence(total_matches, total_words)
    
    # 判斷情緒分類
    if scores["positive"] > scores["negative"] and scores["positive"] > scores["neutral"]:
        sentiment = "positive"
    elif scores["negative"] > scores["positive"] and scores["negative"] > scores["neutral"]:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    
    # 偵測細分情緒
    emotion = detect_emotion(text)
    
    return {
        "sentiment": sentiment,
        "confidence": confidence,
        "emotion": emotion,
        "positive_keywords": pos_keywords[:10],  # 最多 10 個
        "negative_keywords": neg_keywords[:10],  # 最多 10 個
        "scores": scores,
        "language": lang,
    }


def analyze_batch(texts: List[str], industry: str = None, custom_dict_path: str = None) -> List[Dict]:
    """批次分析多段文字"""
    results = []
    for text in texts:
        result = analyze_sentiment_v2(text, industry, custom_dict_path)
        results.append(result)
    return results


def compute_nss(pos: int, neg: int, total: int) -> float:
    """
    計算淨情緒分數（保留原有函式）
    NSS = (正面篇數 - 負面篇數) / 總篇數 × 100
    """
    if total <= 0:
        return 0.0
    return round((pos - neg) / total * 100, 1)


def analyze_sentiment_categories(text: str, industry: str = None) -> List[Dict]:
    """
    四維度情感分析（保留原有函式）
    """
    if not text:
        return []
    
    cats = SENTIMENT_CATEGORIES
    result = []
    
    for cat, data in cats.items():
        found = [kw for kw in data["keywords"] if kw in text]
        if found:
            result.append({
                "category": cat,
                "keywords": found,
                "polarity": data["polarity"]
            })
    
    return result


# ===========================================
# 測試入口
# ===========================================

if __name__ == "__main__":
    # 測試範例
    test_texts = [
        "這產品真的太棒了，超級推薦！必買神器，CP值破表！",
        "踩雷了！退貨還要自己出運費，根本垃圾，爛透了！",
        "今天天氣不錯，去散步看看風景。",
        "This product is amazing! Must buy, highly recommend!",
        "Terrible experience, waste of money, avoid at all costs.",
    ]
    
    print("=" * 60)
    print("P2 情緒分析強化版測試")
    print("=" * 60)
    
    for i, text in enumerate(test_texts, 1):
        print(f"\n【測試 {i}】{text[:30]}...")
        result = analyze_sentiment_v2(text)
        print(f"  情緒: {result['sentiment']}")
        print(f"  信心: {result['confidence']}")
        print(f"  細分情緒: {result['emotion']}")
        print(f"  分數: {result['scores']}")
        print(f"  語言: {result['language']}")
        print(f"  匹配正面詞: {result['positive_keywords']}")
        print(f"  匹配負面詞: {result['negative_keywords']}")
