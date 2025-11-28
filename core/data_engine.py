# -*- coding: utf-8 -*-
"""
Data Engine
基于 Pandas 的高级数据分析引擎
"""

import logging
from typing import List, Dict, Any, Optional
import pandas as pd

logger = logging.getLogger("DataEngine")

class DataEngine:
    """数据分析引擎"""

    @staticmethod
    def analyze(data: List[Dict[str, Any]], query: str) -> Optional[str]:
        """
        分析数据
        
        Args:
            data: 资源数据列表
            query: 分析查询语句 (e.g. "groupby:region|count", "sort:created_time|top:5")
            
        Returns:
            格式化后的分析结果字符串 (表格形式)
        """
        if not data:
            return "No data to analyze."
            
        if not query:
            return None

        try:
            df = pd.DataFrame(data)
            
            # 解析查询管道
            # 格式: op:arg|op:arg...
            stages = query.split('|')
            
            for stage in stages:
                if ':' not in stage:
                    continue
                    
                op, arg = stage.split(':', 1)
                op = op.strip().lower()
                arg = arg.strip()
                
                if op == 'groupby':
                    # groupby:field  (默认count)
                    # groupby:field,sum:metric
                    if ',' in arg:
                        # 复杂聚合: groupby:region,sum:cpu
                        group_field, agg_expr = arg.split(',', 1)
                        agg_op, agg_field = agg_expr.split(':', 1)
                        
                        if agg_op == 'sum':
                            df = df.groupby(group_field)[agg_field].sum().reset_index()
                        elif agg_op == 'mean':
                            df = df.groupby(group_field)[agg_field].mean().reset_index()
                        elif agg_op == 'max':
                            df = df.groupby(group_field)[agg_field].max().reset_index()
                        elif agg_op == 'min':
                            df = df.groupby(group_field)[agg_field].min().reset_index()
                    else:
                        # 简单计数: groupby:region
                        df = df.groupby(arg).size().reset_index(name='count')
                        
                elif op == 'sort':
                    # sort:field (默认升序)
                    # sort:-field (降序)
                    ascending = True
                    if arg.startswith('-'):
                        arg = arg[1:]
                        ascending = False
                    
                    if arg in df.columns:
                        df = df.sort_values(by=arg, ascending=ascending)
                        
                elif op == 'top':
                    # top:N
                    n = int(arg)
                    df = df.head(n)
                    
                elif op == 'filter':
                    # filter:field=value (简单过滤，建议用 --filter 参数，这里作为补充)
                    # 仅支持简单的相等判断，复杂的建议在 FilterEngine 处理
                    if '=' in arg:
                        k, v = arg.split('=', 1)
                        df = df[df[k].astype(str) == v]

            # 格式化输出
            return df.to_markdown(index=False, tablefmt="github")
            
        except ImportError:
            return "Error: pandas is not installed. Please run 'pip install pandas'."
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return f"Analysis failed: {e}"
