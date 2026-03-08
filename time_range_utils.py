# -*- coding: utf-8 -*-
"""
共用搜尋期間選項：供 Dcard、PTT、Threads、Google 新聞等爬蟲統一使用
"""

# 選項：(顯示名稱, 天數, 對應年數用於 PTT，PTT 以 days/365 計算)
TIME_RANGE_OPTIONS = {
    "1": ("1 週", 7, 7 / 365),
    "2": ("1 個月", 30, 30 / 365),
    "3": ("3 個月", 90, 90 / 365),
    "4": ("半年", 180, 180 / 365),
    "5": ("1 年", 365, 1),
    "6": ("全部", 99999, 10),
}


def ask_time_range():
    """
    詢問使用者搜尋期間，回傳 (days, years)。
    - days: 用於 Dcard / Google 新聞 / Threads（篩選 N 天內）
    - years: 用於 PTT（篩選 N 年內）
    """
    print("\n請選擇搜尋期間：")
    for k, (label, _, _) in TIME_RANGE_OPTIONS.items():
        print(f"  {k}. {label}")
    choice = input("請輸入 1~6 (預設 4=半年)：").strip() or "4"
    opt = TIME_RANGE_OPTIONS.get(choice, TIME_RANGE_OPTIONS["4"])
    days = int(opt[1])
    years = opt[2]
    if years >= 1:
        years = int(years)
    print(f"  已選擇：{opt[0]}（{days} 天內 / 約 {years} 年內）")
    return days, years
