
import sys
import os
import logging
from pathlib import Path

# 添加项目路径
project_root = Path("/Users/songqipeng/cloudlens")
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_analyzer_init():
    try:
        from cloudlens.core.discount_analyzer_advanced import AdvancedDiscountAnalyzer
        logger.info("开始初始化 AdvancedDiscountAnalyzer...")
        
        analyzer = AdvancedDiscountAnalyzer()
        
        logger.info(f"analyzer.storage: {analyzer.storage}")
        logger.info(f"analyzer.db: {analyzer.db}")
        
        if analyzer.db is None:
            logger.error("!!! analyzer.db IS NONE !!!")
            # 深入检查 BillStorageManager
            from cloudlens.core.bill_storage import BillStorageManager
            storage = BillStorageManager()
            logger.info(f"New storage instance: {storage}")
            logger.info(f"New storage.db: {storage.db}")
            logger.info(f"New storage._db: {storage._db}")
        else:
            logger.info("analyzer.db 初始化正常")
            
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_analyzer_init()
