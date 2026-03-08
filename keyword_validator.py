# -*- coding: utf-8 -*-
"""
關鍵字驗證器：讓使用者確認、修改、新增關鍵字
支援互動式編輯與批次匯入
"""

import json
import os
from typing import List, Dict
from google import genai

class KeywordValidator:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.confirmed_keywords = []
        
    def generate_keywords(self, brand: str, competitors: List[str], 
                         industry: str, service: str) -> Dict:
        """
        第一階段：AI 生成關鍵字建議
        """
        prompt = f"""
你是關鍵字策略專家。針對以下資訊，生成搜尋關鍵字：

【品牌資訊】
- 自有品牌：{brand}
- 競品：{', '.join(competitors)}
- 產業：{industry}
- 核心服務：{service}

【任務】
請分類生成以下三種關鍵字（每類 5-8 個）：

1. 品牌直稱類（Brand Direct）
   - 品牌正式名稱
   - 常見簡稱/暱稱
   例：星巴克 → 星冰樂、小綠人

2. 產品功能類（Product Function）
   - 核心服務的描述詞
   - 使用者會搜尋的痛點詞
   例：把妹課程 → 搭訕技巧、脫單攻略

3. 情境討論類（Context Discussion）
   - 鄉民討論時的用語
   - 負面/爭議關鍵字
   例：把妹 → PUA、話術、套路

請以 JSON 格式回傳：
{{
  "brand_direct": ["關鍵字1", "關鍵字2", ...],
  "product_function": ["關鍵字1", "關鍵字2", ...],
  "context_discussion": ["關鍵字1", "關鍵字2", ...]
}}
"""
        
        try:
            from config import Config
            model = Config.GEMINI_MODEL
        except ImportError:
            model = "gemini-2.5-flash"
        response = self.client.models.generate_content(
            model=model,
            contents=prompt
        )
        if not response or not getattr(response, "text", None):
            raise ValueError("Gemini 未回傳有效內容")
        # 解析 JSON
        text = response.text.strip()
        if text.startswith("```json"):
            text = text.split("```json")[1].split("```")[0].strip()
        elif text.startswith("```"):
            text = text.split("```")[1].split("```")[0].strip()
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("關鍵字回傳格式錯誤")
        return data
    
    def interactive_review(self, keywords_dict: Dict) -> Dict:
        """
        第二階段：互動式確認與編輯
        """
        print("\n" + "="*60)
        print("🔍 關鍵字確認與編輯")
        print("="*60)
        
        confirmed = {}
        
        for category, keywords in keywords_dict.items():
            category_name = {
                "brand_direct": "品牌直稱類",
                "product_function": "產品功能類",
                "context_discussion": "情境討論類"
            }.get(category, category)
            
            print(f"\n【{category_name}】")
            print(f"AI 建議的關鍵字：")
            for i, kw in enumerate(keywords, 1):
                print(f"  {i}. {kw}")
            
            print("\n請選擇操作：")
            print("  1. 全部保留")
            print("  2. 選擇性保留（輸入編號，例如：1,3,5）")
            print("  3. 全部刪除")
            print("  4. 手動新增關鍵字")
            
            choice = input("請輸入選項 (1-4)：").strip()
            
            selected = []
            
            if choice == "1":
                selected = keywords.copy()
            elif choice == "2":
                indices = input("請輸入要保留的編號（逗號分隔）：").strip()
                try:
                    selected = [keywords[int(i)-1] for i in indices.split(",")]
                except:
                    print("⚠️ 輸入格式錯誤，已略過此類別")
            elif choice == "3":
                selected = []
            elif choice == "4":
                manual = input("請輸入關鍵字（逗號分隔）：").strip()
                selected = [k.strip() for k in manual.split(",")]
            
            # 詢問是否新增額外關鍵字
            if selected:
                add_more = input(f"\n是否新增更多關鍵字到「{category_name}」？(y/n)：").strip().lower()
                if add_more == 'y':
                    extra = input("請輸入額外關鍵字（逗號分隔）：").strip()
                    selected.extend([k.strip() for k in extra.split(",")])
            
            confirmed[category] = list(set(selected))  # 去重
            print(f"✅ 已確認 {len(confirmed[category])} 個關鍵字")
        
        return confirmed
    
    def save_keywords(self, keywords_dict: Dict, output_dir: str):
        """
        第三階段：儲存確認後的關鍵字
        """
        output_file = os.path.join(output_dir, "confirmed_keywords.json")
        
        # 加入時間戳與說明
        output_data = {
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "keywords": keywords_dict,
            "total_count": sum(len(v) for v in keywords_dict.values()),
            "usage_note": "這些關鍵字將用於 Dcard/PTT 輿情搜尋"
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 關鍵字已儲存至：{output_file}")
        return output_file
    
    def batch_import(self, csv_file: str) -> Dict:
        """
        進階功能：從 CSV 批次匯入關鍵字
        CSV 格式：category,keyword
        """
        import csv
        keywords_dict = {
            "brand_direct": [],
            "product_function": [],
            "context_discussion": []
        }
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                category = row.get('category', 'context_discussion')
                keyword = row.get('keyword', '').strip()
                if keyword and category in keywords_dict:
                    keywords_dict[category].append(keyword)
        
        return keywords_dict


def run_keyword_validation(brand: str, competitors: List[str], 
                          industry: str, service: str, 
                          api_key: str, output_dir: str) -> str:
    """
    執行完整的關鍵字驗證流程。
    在 Streamlit 後台執行時，input() 已被 pipeline 替換為自動回應，會自動「全部保留」。
    """
    validator = KeywordValidator(api_key)
    
    print("\n🤖 AI 正在生成關鍵字建議...")
    try:
        keywords_dict = validator.generate_keywords(brand, competitors, industry, service)
    except Exception as e:
        print(f"⚠️ 關鍵字生成失敗：{e}")
        raise
    if not keywords_dict or not isinstance(keywords_dict, dict):
        raise ValueError("關鍵字生成回傳為空或格式錯誤")
    
    print("\n📋 生成完成！共 {} 個關鍵字".format(
        sum(len(v) for v in keywords_dict.values() if isinstance(v, list))
    ))
    
    # 互動式確認（在 pipeline 中 input 會自動回 "1" = 全部保留）
    confirmed = validator.interactive_review(keywords_dict)
    
    # 儲存結果
    output_file = validator.save_keywords(confirmed, output_dir)
    
    # 顯示摘要
    print("\n" + "="*60)
    print("📊 最終關鍵字摘要")
    print("="*60)
    for category, keywords in (confirmed or {}).items():
        category_name = {
            "brand_direct": "品牌直稱類",
            "product_function": "產品功能類",
            "context_discussion": "情境討論類"
        }.get(category, category)
        print(f"\n{category_name}：")
        for kw in (keywords or []):
            print(f"  • {kw}")
    
    total = sum(len(v) for v in (confirmed or {}).values() if isinstance(v, list))
    print(f"\n✅ 總計：{total} 個關鍵字將用於輿情搜尋")
    
    return output_file
