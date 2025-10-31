#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一报告生成器
提取公共的HTML和Excel报告生成逻辑
"""

import os
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path


class ReportGenerator:
    """统一报告生成器"""
    
    # 统一的CSS样式
    HTML_STYLE = """
        body {
            font-family: system-ui, -apple-system, Segoe UI, Roboto, PingFang SC, 
                         Noto Sans CJK, Microsoft YaHei, Arial, sans-serif;
            margin: 24px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1600px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
            font-size: 24px;
        }
        .summary {
            background: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .summary h3 {
            margin-top: 0;
            color: #34495e;
        }
        .summary p {
            margin: 8px 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            font-size: 13px;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px 10px;
            text-align: left;
        }
        th {
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        tr:hover {
            background-color: #f3f4f6;
        }
        .metric {
            font-weight: bold;
            color: #e74c3c;
        }
        .low-utilization {
            background-color: #fff3cd;
        }
        .num {
            text-align: right;
        }
        .footer {
            margin-top: 30px;
            padding: 15px;
            background: #34495e;
            color: white;
            text-align: center;
            border-radius: 5px;
        }
    """
    
    @staticmethod
    def escape_html(text: Any) -> str:
        """转义HTML特殊字符"""
        if text is None:
            return ''
        text = str(text)
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#39;'))
    
    @classmethod
    def generate_html_report(
        cls,
        resource_type: str,
        idle_instances: List[Dict[str, Any]],
        filename: str,
        tenant_name: Optional[str] = None,
        columns: Optional[List[Dict[str, str]]] = None,
        title_icon: str = "📊",
        header_color: str = "#3498db"
    ) -> str:
        """
        生成统一的HTML报告
        
        Args:
            resource_type: 资源类型（如：RDS, Redis）
            idle_instances: 闲置实例列表
            filename: 输出文件名
            tenant_name: 租户名称（可选）
            columns: 列定义列表 [{'key': '字段名', 'label': '显示名称', 'type': 'text|number|percent'}]
            title_icon: 标题图标
            header_color: 表头颜色
        
        Returns:
            生成的文件路径
        """
        if not idle_instances:
            # 生成空报告
            html_content = cls._generate_empty_html(resource_type, tenant_name, title_icon)
        else:
            html_content = cls._generate_html_content(
                resource_type, idle_instances, tenant_name, 
                columns, title_icon, header_color
            )
        
        # 确保目录存在
        file_path = Path(filename)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filename
    
    @classmethod
    def _generate_empty_html(
        cls,
        resource_type: str,
        tenant_name: Optional[str],
        title_icon: str
    ) -> str:
        """生成空报告HTML"""
        title = f"{title_icon} {resource_type}闲置实例分析报告"
        if tenant_name:
            title = f"{tenant_name} - {title}"
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{resource_type}闲置实例分析报告</title>
    <style>{cls.HTML_STYLE}</style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div class="summary">
            <h3>📊 报告摘要</h3>
            <p><strong>生成时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>闲置实例数量:</strong> 0 个</p>
            <p><strong>状态:</strong> ✅ 没有发现闲置的{resource_type}实例</p>
        </div>
        <div class="footer">
            <p>报告由阿里云资源分析工具自动生成</p>
        </div>
    </div>
</body>
</html>"""
        return html
    
    @classmethod
    def _generate_html_content(
        cls,
        resource_type: str,
        idle_instances: List[Dict[str, Any]],
        tenant_name: Optional[str],
        columns: Optional[List[Dict[str, str]]],
        title_icon: str,
        header_color: str
    ) -> str:
        """生成报告HTML内容"""
        # 计算统计信息
        total_cost = sum(inst.get('月成本(¥)', 0) for inst in idle_instances)
        annual_savings = total_cost * 12
        
        # 构建标题
        title = f"{title_icon} {resource_type}闲置实例分析报告"
        if tenant_name:
            title = f"{tenant_name} - {title}"
        
        # 开始构建HTML
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{resource_type}闲置实例分析报告</title>
    <style>{cls.HTML_STYLE.replace('#3498db', header_color)}</style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        
        <div class="summary">
            <h3>📊 报告摘要</h3>
            <p><strong>生成时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>闲置实例数量:</strong> {len(idle_instances)} 个</p>
            <p><strong>总月成本:</strong> {total_cost:,.2f} 元</p>
            <p><strong>预计年节省:</strong> {annual_savings:,.2f} 元</p>
        </div>
        
        <table>
            <thead>
                <tr>"""
        
        # 生成表头
        if columns:
            for col in columns:
                align_class = 'num' if col.get('type') in ['number', 'percent', 'currency'] else ''
                html += f"\n                    <th class='{align_class}'>{col.get('label', col.get('key', ''))}</th>"
        else:
            # 如果没有指定列，从第一个实例提取键
            if idle_instances:
                for key in idle_instances[0].keys():
                    html += f"\n                    <th>{key}</th>"
        
        html += "\n                </tr>\n            </thead>\n            <tbody>"
        
        # 生成表格行
        for instance in idle_instances:
            html += "\n                <tr>"
            
            if columns:
                for col in columns:
                    key = col.get('key', '')
                    value = instance.get(key, '')
                    col_type = col.get('type', 'text')
                    
                    # 格式化数值
                    if col_type == 'number' and isinstance(value, (int, float)):
                        formatted_value = f"{value:,.0f}"
                    elif col_type == 'percent' and isinstance(value, (int, float)):
                        formatted_value = f"{value:.1f}%"
                    elif col_type == 'currency' and isinstance(value, (int, float)):
                        formatted_value = f"{value:,.2f}"
                    else:
                        formatted_value = cls.escape_html(value)
                    
                    align_class = 'num' if col_type in ['number', 'percent', 'currency'] else ''
                    metric_class = 'metric' if '利用率' in key or '使用率' in key else ''
                    html += f"\n                    <td class='{align_class} {metric_class}'>{formatted_value}</td>"
            else:
                for value in instance.values():
                    html += f"\n                    <td>{cls.escape_html(value)}</td>"
            
            html += "\n                </tr>"
        
        html += """
            </tbody>
        </table>
        
        <div class="footer">
            <p>报告由阿里云资源分析工具自动生成</p>
        </div>
    </div>
</body>
</html>"""
        
        return html
    
    @staticmethod
    def generate_excel_report(
        idle_instances: List[Dict[str, Any]],
        filename: str,
        sheet_name: str = "闲置实例"
    ) -> str:
        """
        生成Excel报告
        
        Args:
            idle_instances: 闲置实例列表
            filename: 输出文件名
            sheet_name: 工作表名称
        
        Returns:
            生成的文件路径
        """
        if not idle_instances:
            # 创建空DataFrame
            df = pd.DataFrame()
        else:
            df = pd.DataFrame(idle_instances)
        
        # 确保目录存在
        file_path = Path(filename)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入Excel
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # 自动调整列宽（如果可能）
            try:
                worksheet = writer.sheets[sheet_name]
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).map(len).max(),
                        len(str(col))
                    )
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)
            except:
                pass  # 忽略列宽调整错误
        
        return filename
    
    @staticmethod
    def generate_combined_report(
        resource_type: str,
        idle_instances: List[Dict[str, Any]],
        output_dir: str = ".",
        tenant_name: Optional[str] = None,
        timestamp: Optional[str] = None
    ) -> Dict[str, str]:
        """
        生成HTML和Excel报告
        
        Args:
            resource_type: 资源类型
            idle_instances: 闲置实例列表
            output_dir: 输出目录
            tenant_name: 租户名称
            timestamp: 时间戳（None则自动生成）
        
        Returns:
            {'html': html_file_path, 'excel': excel_file_path}
        """
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 生成文件名
        prefix = f"{tenant_name}_" if tenant_name else ""
        html_file = os.path.join(output_dir, f"{prefix}{resource_type.lower()}_idle_report_{timestamp}.html")
        excel_file = os.path.join(output_dir, f"{prefix}{resource_type.lower()}_idle_report_{timestamp}.xlsx")
        
        # 生成报告
        ReportGenerator.generate_html_report(
            resource_type, idle_instances, html_file, tenant_name
        )
        ReportGenerator.generate_excel_report(idle_instances, excel_file)
        
        return {'html': html_file, 'excel': excel_file}

