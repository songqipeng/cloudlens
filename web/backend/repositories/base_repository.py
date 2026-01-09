"""
Repository基类
"""
from abc import ABC
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class BaseRepository(ABC):
    """Repository基类"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def handle_error(self, error: Exception, operation: str) -> None:
        """统一错误处理"""
        self.logger.error(f"{operation} failed: {error}", exc_info=True)
        raise error
