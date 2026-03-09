# -*- coding: utf-8 -*-
"""
Fallout 風格 UI 工具模組
提供復古終端機風格的介面元素
"""

import time
import random
import sys
from typing import Optional, List

class FalloutUI:
    """Fallout 風格 UI 工具類"""
    
    # Fallout 風格顏色代碼（ANSI）
    COLORS = {
        'green': '\033[92m',
        'yellow': '\033[93m',
        'red': '\033[91m',
        'blue': '\033[94m',
        'cyan': '\033[96m',
        'magenta': '\033[95m',
        'reset': '\033[0m',
        'dim': '\033[2m',
        'bold': '\033[1m',
    }
    
    # Fallout ASCII 藝術
    ASCII_ART = {
        'header': """
    ╔══════════════════════════════════════════════════════╗
    ║  ███╗   ███╗██╗  ██╗████████╗██████╗ ██████╗ ███████╗║
    ║  ████╗ ████║██║ ██╔╝╚══██╔══╝██╔══██╗██╔══██╗██╔════╝║
    ║  ██╔████╔██║█████╔╝    ██║   ██████╔╝██████╔╝███████╗║
    ║  ██║╚██╔╝██║██╔═██╗    ██║   ██╔══██╗██╔══██╗╚════██║║
    ║  ██║ ╚═╝ ██║██║  ██╗   ██║   ██║  ██║██║  ██║███████║║
    ║  ╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝║
    ╚══════════════════════════════════════════════════════╝
        """,
        
        'pipboy': """
          ╔══════════════════════════════════╗
          ║  ╔══════════════════════════╗    ║
          ║  ║   [PIP-BOY 3000]         ║    ║
          ║  ║   STATUS: ONLINE         ║    ║
          ║  ║   VERSION: MKTBrs v2.0   ║    ║
          ║  ║   SYSTEM: OPERATIONAL    ║    ║
          ║  ╚══════════════════════════╝    ║
          ╚══════════════════════════════════╝
        """,
        
        'error': """
    ╔══════════════════════════════════════════════════════╗
    ║  ⚠ SYSTEM MALFUNCTION ⚠                             ║
    ║  CRITICAL ERROR DETECTED                            ║
    ║  PLEASE CHECK CONNECTION AND RETRY                  ║
    ╚══════════════════════════════════════════════════════╝
        """,
        
        'success': """
    ╔══════════════════════════════════════════════════════╗
    ║  ✅ MISSION ACCOMPLISHED ✅                         ║
    ║  ALL SYSTEMS OPERATIONAL                            ║
    ║  DATA ACQUISITION COMPLETE                          ║
    ╚══════════════════════════════════════════════════════╝
        """,
        
        'loading': [
            "[■□□□□□□□□□]",
            "[■■□□□□□□□□]",
            "[■■■□□□□□□□]",
            "[■■■■□□□□□□]",
            "[■■■■■□□□□□]",
            "[■■■■■■□□□□]",
            "[■■■■■■■□□□]",
            "[■■■■■■■■□□]",
            "[■■■■■■■■■□]",
            "[■■■■■■■■■■]",
        ]
    }
    
    @classmethod
    def print_header(cls, title: str, subtitle: Optional[str] = None) -> None:
        """顯示 Fallout 風格標頭"""
        print(cls.COLORS['green'] + "═" * 65 + cls.COLORS['reset'])
        print(cls.COLORS['green'] + "║" + cls.COLORS['reset'], end="")
        padding = (65 - len(title) - 2) // 2
        print(" " * padding + cls.COLORS['bold'] + title + cls.COLORS['reset'], end="")
        print(" " * (65 - len(title) - padding - 2) + cls.COLORS['green'] + "║" + cls.COLORS['reset'])
        
        if subtitle:
            print(cls.COLORS['green'] + "║" + cls.COLORS['reset'], end="")
            padding = (65 - len(subtitle) - 2) // 2
            print(" " * padding + cls.COLORS['dim'] + subtitle + cls.COLORS['reset'], end="")
            print(" " * (65 - len(subtitle) - padding - 2) + cls.COLORS['green'] + "║" + cls.COLORS['reset'])
        
        print(cls.COLORS['green'] + "═" * 65 + cls.COLORS['reset'])
    
    @classmethod
    def print_section(cls, title: str) -> None:
        """顯示區段標題"""
        print(f"\n{cls.COLORS['yellow']}【{title}】{cls.COLORS['reset']}")
        print(f"{cls.COLORS['dim']}{'─' * 65}{cls.COLORS['reset']}")
    
    @classmethod
    def print_step(cls, step_num: int, description: str) -> None:
        """顯示步驟"""
        print(f"\n{cls.COLORS['cyan']}▶ 步驟 {step_num}: {description}{cls.COLORS['reset']}")
    
    @classmethod
    def print_status(cls, status: str, message: str) -> None:
        """顯示狀態訊息"""
        status_colors = {
            'info': 'cyan',
            'success': 'green',
            'warning': 'yellow',
            'error': 'red',
            'system': 'magenta'
        }
        
        color = status_colors.get(status, 'cyan')
        icon = {
            'info': 'ℹ',
            'success': '✅',
            'warning': '⚠',
            'error': '❌',
            'system': '⚙'
        }.get(status, '•')
        
        print(f"  {cls.COLORS[color]}{icon} {message}{cls.COLORS['reset']}")
    
    @classmethod
    def print_data(cls, label: str, value: str, indent: int = 2) -> None:
        """顯示數據"""
        spaces = " " * indent
        print(f"{spaces}{cls.COLORS['dim']}├─ {label}:{cls.COLORS['reset']} {value}")
    
    @classmethod
    def print_pipboy_loading(cls, message: str, duration: float = 2.0) -> None:
        """顯示 PIP-BOY 風格載入動畫"""
        print(f"\n{cls.COLORS['green']}{cls.ASCII_ART['pipboy']}{cls.COLORS['reset']}")
        print(f"{cls.COLORS['cyan']}  {message}{cls.COLORS['reset']}")
        
        frames = cls.ASCII_ART['loading']
        frame_delay = duration / len(frames)
        
        for frame in frames:
            print(f"\r{cls.COLORS['green']}  {frame}{cls.COLORS['reset']}", end="", flush=True)
            time.sleep(frame_delay)
        
        print()  # 換行
    
    @classmethod
    def print_error(cls, error_type: str, message: str, details: Optional[str] = None) -> None:
        """顯示錯誤訊息"""
        print(f"\n{cls.COLORS['red']}{cls.ASCII_ART['error']}{cls.COLORS['reset']}")
        print(f"{cls.COLORS['red']}⚠ {error_type.upper()}: {message}{cls.COLORS['reset']}")
        if details:
            print(f"{cls.COLORS['dim']}  詳細資訊: {details}{cls.COLORS['reset']}")
    
    @classmethod
    def print_success(cls, message: str, details: Optional[str] = None) -> None:
        """顯示成功訊息"""
        print(f"\n{cls.COLORS['green']}{cls.ASCII_ART['success']}{cls.COLORS['reset']}")
        print(f"{cls.COLORS['green']}✅ {message}{cls.COLORS['reset']}")
        if details:
            print(f"{cls.COLORS['dim']}  {details}{cls.COLORS['reset']}")
    
    @classmethod
    def print_progress_bar(cls, current: int, total: int, label: str = "進度") -> None:
        """顯示進度條"""
        bar_length = 40
        filled_length = int(bar_length * current // total)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        percent = 100 * current // total
        
        print(f"\r{cls.COLORS['cyan']}{label}: [{bar}] {percent}% ({current}/{total}){cls.COLORS['reset']}", end="", flush=True)
        
        if current == total:
            print()  # 完成時換行
    
    @classmethod
    def input_with_prompt(cls, prompt: str, default: Optional[str] = None) -> str:
        """帶有 Fallout 風格提示的輸入"""
        if default:
            prompt_text = f"{cls.COLORS['yellow']}👉 {prompt} [{default}]: {cls.COLORS['reset']}"
        else:
            prompt_text = f"{cls.COLORS['yellow']}👉 {prompt}: {cls.COLORS['reset']}"
        
        user_input = input(prompt_text).strip()
        return user_input if user_input else (default or "")
    
    @classmethod
    def print_competitor_card(cls, competitor: dict, index: int) -> None:
        """顯示競品卡片"""
        name = competitor.get('competitor_name', competitor.get('name', '未知'))
        label = competitor.get('label', '未分類')
        price = competitor.get('price_range', '未標示')
        
        print(f"\n{cls.COLORS['yellow']}【競品 #{index}】{cls.COLORS['reset']}")
        print(f"{cls.COLORS['bold']}{name}{cls.COLORS['reset']}")
        print(f"{cls.COLORS['dim']}標籤: {label} | 價格: {price}{cls.COLORS['reset']}")
        
        if 'strengths' in competitor:
            print(f"  {cls.COLORS['green']}✓ 優勢: {competitor['strengths']}{cls.COLORS['reset']}")
        if 'weaknesses' in competitor:
            print(f"  {cls.COLORS['red']}✗ 弱點: {competitor['weaknesses']}{cls.COLORS['reset']}")
    
    @classmethod
    def print_executive_summary(cls, summary: dict) -> None:
        """顯示執行摘要"""
        print(f"\n{cls.COLORS['bold']}{'═' * 65}{cls.COLORS['reset']}")
        print(f"{cls.COLORS['bold']}📊 執行摘要 (Executive Summary){cls.COLORS['reset']}")
        print(f"{cls.COLORS['bold']}{'═' * 65}{cls.COLORS['reset']}")
        
        for key, value in summary.items():
            print(f"{cls.COLORS['cyan']}• {key}:{cls.COLORS['reset']} {value}")
    
    @classmethod
    def print_actionable_insights(cls, insights: List[str]) -> None:
        """顯示行動建議"""
        print(f"\n{cls.COLORS['bold']}{'═' * 65}{cls.COLORS['reset']}")
        print(f"{cls.COLORS['bold']}🎯 行動建議 (Actionable Insights){cls.COLORS['reset']}")
        print(f"{cls.COLORS['bold']}{'═' * 65}{cls.COLORS['reset']}")
        
        for i, insight in enumerate(insights, 1):
            print(f"{cls.COLORS['green']}{i}. {insight}{cls.COLORS['reset']}")

# 簡化導入
def print_header(title: str, subtitle: Optional[str] = None) -> None:
    FalloutUI.print_header(title, subtitle)

def print_section(title: str) -> None:
    FalloutUI.print_section(title)

def print_step(step_num: int, description: str) -> None:
    FalloutUI.print_step(step_num, description)

def print_status(status: str, message: str) -> None:
    FalloutUI.print_status(status, message)

def print_data(label: str, value: str, indent: int = 2) -> None:
    FalloutUI.print_data(label, value, indent)

def print_pipboy_loading(message: str, duration: float = 2.0) -> None:
    FalloutUI.print_pipboy_loading(message, duration)

def print_error(error_type: str, message: str, details: Optional[str] = None) -> None:
    FalloutUI.print_error(error_type, message, details)

def print_success(message: str, details: Optional[str] = None) -> None:
    FalloutUI.print_success(message, details)

def print_progress_bar(current: int, total: int, label: str = "進度") -> None:
    FalloutUI.print_progress_bar(current, total, label)

def input_with_prompt(prompt: str, default: Optional[str] = None) -> str:
    return FalloutUI.input_with_prompt(prompt, default)

def print_competitor_card(competitor: dict, index: int) -> None:
    FalloutUI.print_competitor_card(competitor, index)

def print_executive_summary(summary: dict) -> None:
    FalloutUI.print_executive_summary(summary)

def print_actionable_insights(insights: List[str]) -> None:
    FalloutUI.print_actionable_insights(insights)