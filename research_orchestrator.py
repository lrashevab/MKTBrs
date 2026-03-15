# -*- coding: utf-8 -*-
"""
競品輿情分析系統 - 指揮中心（research_orchestrator.py）
完整流程：需求定義 → 產業掃描 → 競品雷達 → 關鍵字驗證 → 社群聲量 → 深度分析 → 報告產出
版本：V2.3（新增 CLI 參數支援，相容 n8n 呼叫）
"""

import argparse
import json
import logging
import os
import sys
from typing import List

logger = logging.getLogger(__name__)


def _setup_win_encoding() -> None:
    """Windows 終端機 UTF-8 設定，只在 main() 入口呼叫一次。"""
    if sys.platform != 'win32':
        return
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass


try:
    from google import genai  # noqa: F401
except ImportError:
    print("❌ 請先安裝 google-genai：pip install google-genai")
    sys.exit(1)

try:
    import config  # noqa: F401
except ImportError:
    pass

from orchestrator import ScopeCollector, AIAnalyzer, ScraperCoordinator, ReportPipeline
from orchestrator._utils import _p


def _parse_args():
    """解析 CLI 參數"""
    parser = argparse.ArgumentParser(
        description='MKTBrs 競品輿情分析系統',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--brand',       type=str, help='品牌名稱，例如：OOO')
    parser.add_argument('--service',     type=str, help='主打產品／服務，例如：保濕面霜')
    parser.add_argument('--industry',    type=str, help='產業別，例如：美妝保養')
    parser.add_argument('--audience',    type=str, default='', help='目標受眾，例如：25-35歲女性')
    parser.add_argument('--budget',      type=str, default='中',
                        choices=['低', '中', '高'], help='預算等級（低／中／高），預設：中')
    parser.add_argument('--purpose',     type=str, default='競品分析', help='調查目的，預設：競品分析')
    parser.add_argument('--competitors', type=str, default='',
                        help='手動指定競品（逗號分隔），例如：品牌A,品牌B')
    parser.add_argument('--output-dir',  type=str, default='',
                        help='指定輸出資料夾（選填，預設自動產生）')
    parser.add_argument('--no-browser',  action='store_true',
                        help='完成後不自動開啟報告（n8n 呼叫時建議加此參數）')
    return parser.parse_args()


def _build_scope_from_args(args) -> dict:
    """把 CLI 參數組成 scope dict，格式與 ScopeCollector 一致"""
    manual_competitors = (
        [c.strip() for c in args.competitors.split(',') if c.strip()]
        if args.competitors else []
    )
    return {
        'purpose':            args.purpose,
        'brand':              args.brand,
        'service':            args.service,
        'industry':           args.industry,
        'audience':           args.audience,
        'budget':             args.budget,
        'competitor_source':  'manual' if manual_competitors else 'ai',
        'manual_competitors': manual_competitors,
    }


def _has_cli_args(args) -> bool:
    """判斷使用者是否有傳入必要參數（brand / service / industry 三個都要有）"""
    return bool(args.brand and args.service and args.industry)


class ResearchOrchestrator:
    """完整市場調查流程總指揮，只負責串接各責任類別。"""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def run_full_pipeline(self, args=None) -> None:
        """
        執行完整流程
        - args 有值（CLI模式）：直接用參數，跳過互動
        - args 為 None（互動模式）：維持原本 ScopeCollector 互動流程
        """
        _p("\n" + "═" * 65)
        _p("║" + " " * 20 + "🚀 MKTBrs 完整市場調查流程 🚀" + " " * 20 + "║")
        _p("║" + " " * 15 + "Six-Stage Market Intelligence Pipeline" + " " * 15 + "║")
        _p("═" * 65)
        _p("\n📡 系統初始化完成")
        _p("✅ AI 引擎連線正常")
        _p("🎯 載入行銷專家分析框架")
        _p("\n" + "─" * 65)

        # ── 判斷模式 ──────────────────────────────────────────
        use_cli = args is not None and _has_cli_args(args)
        if use_cli:
            _p("⚡ CLI 模式：使用傳入參數，跳過互動輸入")
        else:
            _p("💬 互動模式：請依提示輸入資訊")

        output_dir = args.output_dir if (use_cli and args.output_dir) else None

        try:
            # ── Stage 0：需求定義 ──────────────────────────────
            if use_cli:
                scope = _build_scope_from_args(args)
                # 若沒指定 output_dir，讓系統自動產生
                if not output_dir:
                    from datetime import datetime
                    ts = datetime.now().strftime("%Y%m%d_%H%M")
                    output_dir = f"campaign_{ts}"
                    os.makedirs(output_dir, exist_ok=True)
                _p(f"\n📋 分析設定：")
                _p(f"   品牌：{scope['brand']}")
                _p(f"   產品：{scope['service']}")
                _p(f"   產業：{scope['industry']}")
                _p(f"   受眾：{scope['audience'] or '未指定'}")
                _p(f"   預算：{scope['budget']}")
                _p(f"   輸出：{output_dir}")
            else:
                scope, output_dir = ScopeCollector().collect()

            ai = AIAnalyzer(api_key=self.api_key, output_dir=output_dir)

            # ── Stage 1：產業掃描 ──────────────────────────────
            ai.scan_industry(industry=scope['industry'], service=scope['service'])

            # ── Stage 2：競品雷達 ──────────────────────────────
            manual_list = (
                scope.get('manual_competitors')
                if scope.get('competitor_source') == 'manual'
                else None
            )
            competitors_file = ai.find_competitors(
                brand=scope['brand'],
                service=scope['service'],
                industry=scope['industry'],
                audience=scope.get('audience', ''),
                manual_competitors=manual_list,
            )

            # ── Stage 3：關鍵字驗證 ────────────────────────────
            competitor_names = self._load_competitor_names(competitors_file)
            keywords_file = ai.validate_keywords(
                brand=scope['brand'],
                competitors=competitor_names,
                industry=scope['industry'],
                service=scope['service'],
            )

            # ── Stage 4：社群聲量 ──────────────────────────────
            all_keywords = self._load_keywords(keywords_file, scope)
            social_results, time_range_days, _ = ScraperCoordinator().run(
                keywords=all_keywords,
                kw_label=scope.get('service', ''),
                industry=scope.get('industry'),
                output_dir=output_dir,
                brand=scope.get('brand', ''),
                competitor_names=competitor_names,
            )

            # ── Stage 5：深度分析 ──────────────────────────────
            analysis_file = ai.deep_analysis(
                scope=scope,
                competitors_file=competitors_file,
                keywords_file=keywords_file,
                social_results=social_results,
                time_range_days=time_range_days,
            )

            # ── Stage 6：最終報告 ──────────────────────────────
            project_files = {
                'competitors_file': competitors_file,
                'keywords_file':    keywords_file,
                'analysis_report':  analysis_file,
                'social_listening': social_results,
            }
            final_file = ReportPipeline().generate(
                scope=scope,
                output_dir=output_dir,
                competitors_file=competitors_file,
                keywords_file=keywords_file,
                social_results=social_results,
                time_range_days=time_range_days,
                project_files=project_files,
            )

            _p("\n" + "═" * 65)
            _p("║" + " " * 22 + "✅ 市場調查完成！" + " " * 22 + "║")
            _p("═" * 65)
            _p("\n📊 產出摘要：")
            _p(f"   📁 輸出資料夾：{output_dir}")
            _p(f"   📄 最終報告：{final_file}")
            _p(f"   📈 分析階段：6 個完整階段")
            _p(f"   🎯 競品數量：{len(self._load_competitor_names(competitors_file)) if competitors_file else 0} 個")
            _p("\n🎯 行銷洞察：")
            _p("   • 完整市場定位分析")
            _p("   • 競品深度對比")
            _p("   • 輿情情緒分析")
            _p("   • 具體行動建議")
            _p("\n" + "─" * 65)

            # 自動開啟報告（CLI 模式可用 --no-browser 關閉）
            no_browser = (use_cli and args.no_browser)
            if not no_browser:
                try:
                    import webbrowser
                    webbrowser.open(f"file://{os.path.abspath(final_file)}")
                    _p("\n✅ 報告已自動開啟")
                except Exception:
                    _p("\n💡 請手動開啟報告檔案")

            # ── CLI 模式：輸出 JSON 供 n8n 讀取 ──────────────
            if use_cli:
                result = {
                    "status": "success",
                    "output_dir": output_dir,
                    "final_report": final_file,
                    "competitor_count": len(self._load_competitor_names(competitors_file)) if competitors_file else 0,
                }
                print("\n__RESULT_JSON__")
                print(json.dumps(result, ensure_ascii=False))

        except KeyboardInterrupt:
            _p("\n\n⚠️ 使用者中斷執行")
            if output_dir:
                _p(f"已產出的檔案位於：{output_dir}")

        except Exception as e:
            import traceback
            _p(f"\n\n❌ 執行失敗：{e}")
            if output_dir:
                _p(f"已產出的檔案位於：{output_dir}")
            if use_cli:
                # CLI 模式也輸出 JSON 錯誤，方便 n8n 判斷
                result = {"status": "error", "message": str(e)}
                print("\n__RESULT_JSON__")
                print(json.dumps(result, ensure_ascii=False))
            try:
                traceback.print_exc()
            except (ValueError, OSError):
                pass

    # ── 私有輔助 ──────────────────────────────────────────────

    def _load_competitor_names(self, competitors_file: str) -> List[str]:
        try:
            with open(competitors_file, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            comp_list = raw.get('competitors', raw) if isinstance(raw, dict) else raw
            if not isinstance(comp_list, list):
                return []
            return [
                c.get('competitor_name', c.get('name', ''))
                for c in comp_list
                if c.get('competitor_name') or c.get('name')
            ]
        except Exception:
            return []

    def _load_keywords(self, keywords_file: str, scope: dict) -> List[str]:
        fallback = [scope.get('brand', ''), scope.get('service', '')]
        try:
            with open(keywords_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            kws: List[str] = []
            kw_obj = data.get('keywords', data)
            if isinstance(kw_obj, dict):
                for kw_list in kw_obj.values():
                    kws.extend(kw_list if isinstance(kw_list, list) else [])
            return kws or fallback
        except Exception:
            return fallback


def main():
    """主程式入口"""
    _setup_win_encoding()
    args = _parse_args()

    try:
        from config import Config
        Config.setup_logging("research_orchestrator.log")
        api_key = Config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
    except ImportError:
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("⚠️ 找不到 GEMINI_API_KEY 環境變數")
        api_key = input("請輸入你的 Gemini API 金鑰：").strip()
        if not api_key:
            print("❌ 未提供 API 金鑰，程式結束")
            return

    ResearchOrchestrator(api_key).run_full_pipeline(args=args)


if __name__ == "__main__":
    main()
