# -*- coding: utf-8 -*-
"""
V2 SQLite 資料庫管理器
- 文章去重（URL UNIQUE）
- 跨次查詢支援
- Campaign 追蹤
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class DbManager:
    """SQLite 資料庫管理器，負責文章去重與持久化。"""

    # ===== DDL =====
    _DDL = """
    CREATE TABLE IF NOT EXISTS campaigns (
        id          TEXT PRIMARY KEY,
        brand       TEXT,
        industry    TEXT,
        created_at  TEXT,
        config_json TEXT
    );

    CREATE TABLE IF NOT EXISTS articles (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        url          TEXT    UNIQUE,
        source       TEXT,
        keyword      TEXT,
        title        TEXT,
        content      TEXT    DEFAULT '',
        date         TEXT    DEFAULT '',
        author       TEXT    DEFAULT '',
        engagement   INTEGER DEFAULT 0,
        campaign_id  TEXT    DEFAULT '',
        scraped_at   TEXT,
        FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
    );

    CREATE TABLE IF NOT EXISTS comments (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id INTEGER NOT NULL,
        text       TEXT,
        rank       INTEGER DEFAULT 0,
        FOREIGN KEY (article_id) REFERENCES articles(id)
    );

    CREATE INDEX IF NOT EXISTS idx_articles_url      ON articles(url);
    CREATE INDEX IF NOT EXISTS idx_articles_source   ON articles(source);
    CREATE INDEX IF NOT EXISTS idx_articles_campaign ON articles(campaign_id);
    """

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """建立資料表（若不存在）。"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(self._DDL)

    # =========================================================
    #  Campaign
    # =========================================================

    def create_campaign(self, campaign_id: str, brand: str,
                        industry: str, config: Dict) -> None:
        """建立或更新 campaign 記錄。"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO campaigns (id, brand, industry, created_at, config_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (campaign_id, brand, industry,
                 datetime.now().isoformat(),
                 json.dumps(config, ensure_ascii=False))
            )

    def list_campaigns(self) -> List[Dict]:
        """列出所有 campaigns。"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, brand, industry, created_at FROM campaigns ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    # =========================================================
    #  Articles
    # =========================================================

    def upsert_article(
        self,
        url: str,
        source: str,
        keyword: str = '',
        title: str = '',
        content: str = '',
        date: str = '',
        author: str = '',
        engagement: int = 0,
        campaign_id: str = '',
    ) -> Optional[int]:
        """
        新增或更新文章。若 URL 已存在：
        - 內文：保留較長的版本
        - 互動數：使用最新值
        回傳 article id，若 URL 為空則回傳 None。
        """
        if not url or not url.strip():
            return None

        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO articles
                       (url, source, keyword, title, content, date, author,
                        engagement, campaign_id, scraped_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(url) DO UPDATE SET
                       title      = excluded.title,
                       content    = CASE
                                      WHEN length(excluded.content) > length(articles.content)
                                      THEN excluded.content
                                      ELSE articles.content
                                    END,
                       engagement = excluded.engagement,
                       scraped_at = excluded.scraped_at""",
                (url.strip(), source, keyword, title, content,
                 date, author, engagement, campaign_id, now)
            )
            # lastrowid is 0 on UPDATE; fetch the actual id
            row = conn.execute(
                "SELECT id FROM articles WHERE url = ?", (url.strip(),)
            ).fetchone()
            return row[0] if row else None

    def is_url_exists(self, url: str) -> bool:
        """檢查 URL 是否已在資料庫中。"""
        if not url:
            return False
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM articles WHERE url = ?", (url.strip(),)
            ).fetchone()
        return row is not None

    def get_article_count(
        self,
        source: Optional[str] = None,
        campaign_id: Optional[str] = None,
    ) -> int:
        """查詢文章數（可依來源 / campaign 過濾）。"""
        q = "SELECT COUNT(*) FROM articles WHERE 1=1"
        params: List = []
        if source:
            q += " AND source = ?"
            params.append(source)
        if campaign_id:
            q += " AND campaign_id = ?"
            params.append(campaign_id)
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute(q, params).fetchone()[0]

    _ALLOWED_ORDER_BY = frozenset({
        'engagement DESC', 'engagement ASC',
        'scraped_at DESC', 'scraped_at ASC',
        'date DESC', 'date ASC',
    })

    def get_articles(
        self,
        source: Optional[str] = None,
        campaign_id: Optional[str] = None,
        limit: int = 100,
        order_by: str = 'engagement DESC',
    ) -> List[Dict]:
        """查詢文章清單。"""
        if order_by not in self._ALLOWED_ORDER_BY:
            raise ValueError(
                f"不允許的排序欄位：{order_by!r}。"
                f"允許的值：{sorted(self._ALLOWED_ORDER_BY)}"
            )
        q = "SELECT * FROM articles WHERE 1=1"
        params: List = []
        if source:
            q += " AND source = ?"
            params.append(source)
        if campaign_id:
            q += " AND campaign_id = ?"
            params.append(campaign_id)
        q += f" ORDER BY {order_by} LIMIT ?"
        params.append(limit)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]

    # =========================================================
    #  Comments
    # =========================================================

    def add_comments(self, article_id: int, comments: List[str]) -> None:
        """新增留言（不去重，直接 INSERT）。"""
        if not article_id or not comments:
            return
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                "INSERT INTO comments (article_id, text, rank) VALUES (?, ?, ?)",
                [(article_id, text, rank) for rank, text in enumerate(comments, 1)]
            )

    def get_comments(self, article_id: int) -> List[str]:
        """取得某篇文章的留言清單（依 rank 排序）。"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT text FROM comments WHERE article_id = ? ORDER BY rank",
                (article_id,)
            ).fetchall()
        return [r[0] for r in rows]

    # =========================================================
    #  統計
    # =========================================================

    def stats(self, campaign_id: Optional[str] = None) -> Dict:
        """回傳簡易統計資訊。"""
        sources = ['dcard', 'ptt', 'google_news', 'threads']
        result: Dict = {}
        for src in sources:
            result[src] = self.get_article_count(source=src, campaign_id=campaign_id)
        result['total'] = sum(result.values())
        result['campaigns'] = len(self.list_campaigns())
        return result


# =========================================================
#  全域單例（給爬蟲模組用）
# =========================================================

_global_db: Optional[DbManager] = None


def get_db(db_path: str) -> DbManager:
    """取得（或建立）全域 DbManager 實例。"""
    global _global_db
    if _global_db is None or str(_global_db.db_path) != str(Path(db_path)):
        _global_db = DbManager(db_path)
    return _global_db


if __name__ == '__main__':
    import io
    import sys as _sys
    import tempfile as _tempfile
    import os as _os
    # 確保 Windows 終端機可輸出 UTF-8
    _sys.stdout = io.TextIOWrapper(_sys.stdout.buffer, encoding='utf-8')

    with _tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        test_db = f.name

    try:
        db = DbManager(test_db)
        db.create_campaign('test_001', '測試品牌', '科技業', {'purpose': '競品分析'})
        aid = db.upsert_article('https://example.com/article1', 'dcard', '品牌A',
                                 '測試文章標題', '測試內文', '2026-03-01', 'user1', 42, 'test_001')
        print(f'[OK] 新增文章 id={aid}')
        db.add_comments(aid, ['留言一', '留言二', '留言三'])

        # 重複 upsert（測試去重）
        aid2 = db.upsert_article('https://example.com/article1', 'dcard', '品牌A',
                                  '測試文章標題（更新）', '更長的內文內容', '2026-03-01',
                                  'user1', 55, 'test_001')
        print(f'[OK] 更新文章 id={aid2}（與 id={aid} 相同，互動數已更新）')
        assert aid == aid2, '去重失敗：應回傳相同 id'
        assert db.get_article_count() == 1, '去重失敗：文章數應為 1'
        print(f'[OK] 文章總數：{db.get_article_count()}')
        print(f'[OK] 統計：{db.stats()}')
        print('[OK] DbManager 測試全部通過')
    finally:
        del db  # 關閉所有連線
        try:
            _os.unlink(test_db)
        except OSError:
            pass  # Windows 可能暫時鎖定，忽略即可
