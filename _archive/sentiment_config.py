# -*- coding: utf-8 -*-
"""跨產業輿情配置：通用負評庫 + 四維度情感分析 + 產業擴充"""

# 通用負評詞（所有產業共用）
NEGATIVE_WORDS_BASE = [
    "雷", "爛", "騙", "貴", "沒效", "後悔", "盤子", "割韭菜", "退費", "假", "套路",
    "話術", "PUA", "直銷", "浪費錢", "不值得", "噱頭", "誇大", "廣告不實",
    "客服差", "態度差", "敷衍", "推銷", "強迫推銷", "罐頭", "背稿", "制式",
    "失望", "不推", "踩雷", "地雷", "噁心", "猥瑣", "噁", "反感", "討厭",
]

# 產業專屬負評/痛點詞（key 為產業別名，可多選合併）
INDUSTRY_WORDS = {
    "餐飲": ["油", "鹹", "甜", "膩", "份量少", "貴", "CP值", "衛生", "服務慢", "等很久", "雷", "地雷", "不推"],
    "電商": ["出貨慢", "退貨", "瑕疵", "假貨", "盜版", "客服", "包裝", "遲到", "缺貨", "取消訂單"],
    "課程": ["學費", "沒效", "退費", "話術", "PUA", "割韭菜", "盤子", "背稿", "罐頭", "套路"],
    "旅遊": ["踩雷", "雷", "貴", "行程", "導遊", "住宿", "衛生", "延誤", "取消"],
    "美妝保養": ["過敏", "沒效", "雷", "假貨", "盜版", "成分", "廣告不實"],
    "預設": [],  # 不擴充
}

# 相容：直接使用 NEGATIVE_WORDS 時等同通用庫
NEGATIVE_WORDS = NEGATIVE_WORDS_BASE.copy()


def get_negative_words(industry=None):
    """取得負評詞列表，可選產業擴充。industry 可為 '餐飲','電商','課程','旅遊','美妝保養' 或 None"""
    out = list(NEGATIVE_WORDS_BASE)
    if industry and industry.strip():
        key = industry.strip()
        if key in INDUSTRY_WORDS:
            for w in INDUSTRY_WORDS[key]:
                if w not in out:
                    out.append(w)
    return out


# 四維度情感（通用）
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


def get_sentiment_categories(industry=None):
    """取得四維度設定（目前通用版，industry 保留供未來擴充）"""
    return SENTIMENT_CATEGORIES


def analyze_sentiment_categories(text, industry=None):
    """對一段文字做四維度輿情分析，回傳 [{category, keywords, polarity}, ...]"""
    if not text:
        return []
    cats = get_sentiment_categories(industry)
    result = []
    for cat, data in cats.items():
        found = [kw for kw in data["keywords"] if kw in text]
        if found:
            result.append({"category": cat, "keywords": found, "polarity": data["polarity"]})
    return result


STOP_WORDS = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一個", "上", "也", "很", "到", "說", "要", "去", "你", "會", "著", "沒有", "看", "好", "自己", "這", "那", "什麼", "怎麼", "可以", "覺得", "大家", "問題", "分享"}

# ── 正面詞庫（供 NSS 計算使用）──────────────────────────────
POSITIVE_WORDS_BASE = [
    # 推薦/好評
    "推薦", "好用", "讚", "棒", "超棒", "很棒", "厲害", "強", "神", "完美",
    # 滿意
    "滿意", "喜歡", "愛用", "必買", "值得", "CP值高", "划算", "超值", "物超所值",
    # 效果
    "有效", "有用", "實用", "方便", "好用", "順手", "流暢", "自然",
    # 情感
    "開心", "舒服", "安心", "放心", "期待", "感謝", "謝謝", "讚讚",
    # 品質
    "品質好", "高品質", "用料好", "做工好", "質感", "精緻",
]

# 相容：直接使用 POSITIVE_WORDS 時等同通用庫
POSITIVE_WORDS = POSITIVE_WORDS_BASE.copy()


def get_positive_words(industry=None):
    """取得正面詞列表（目前通用版，industry 保留供未來擴充）"""
    return list(POSITIVE_WORDS_BASE)


def compute_nss(pos: int, neg: int, total: int) -> float:
    """
    計算淨情緒分數（Net Sentiment Score）。

    NSS = (正面篇數 - 負面篇數) / 總篇數 × 100
    回傳範圍：-100 ~ +100
    正值代表正面情緒佔優，負值代表負面情緒佔優。
    """
    if total <= 0:
        return 0.0
    return round((pos - neg) / total * 100, 1)
