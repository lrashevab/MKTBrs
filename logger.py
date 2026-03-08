# -*- coding: utf-8 -*-
"""
統一日誌系統：記錄所有操作與錯誤
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from config import Config

class SystemLogger:
    """系統日誌管理器"""
    
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """取得或建立 logger"""
        
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        # 避免重複添加 handler
        if logger.handlers:
            return logger
        
        # 控制台輸出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # 檔案輸出
        log_file = Config.LOGS_DIR / f"{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(Config.LOG_FORMAT)
        file_handler.setFormatter(file_formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        cls._loggers[name] = logger
        return logger

# 便捷函式
def get_logger(name: str = "system") -> logging.Logger:
    return SystemLogger.get_logger(name)
