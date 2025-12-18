#!/usr/bin/env python3
"""
测试MySQL连接
"""
import mysql.connector
from mysql.connector import Error

def test_mysql_connection():
    """测试MySQL连接"""
    try:
        # 连接配置
        config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'cloudlens',
            'password': 'cloudlens123',
            'database': 'cloudlens',
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci'
        }
        
        print("=" * 60)
        print("测试MySQL连接")
        print("=" * 60)
        
        # 建立连接
        connection = mysql.connector.connect(**config)
        
        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f"✅ 成功连接到MySQL服务器")
            print(f"   MySQL版本: {db_info}")
            
            # 获取当前数据库
            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE()")
            database = cursor.fetchone()[0]
            print(f"   当前数据库: {database}")
            
            # 测试查询
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            print(f"   服务器版本: {version}")
            
            # 显示字符集
            cursor.execute("SHOW VARIABLES LIKE 'character_set_database'")
            charset = cursor.fetchone()[1]
            print(f"   字符集: {charset}")
            
            cursor.close()
            connection.close()
            print("\n✅ MySQL连接测试成功！")
            return True
        else:
            print("❌ 连接失败")
            return False
            
    except Error as e:
        print(f"❌ 连接错误: {e}")
        print("\n提示：")
        print("1. 确保MySQL服务正在运行: brew services start mysql")
        print("2. 检查用户名和密码是否正确")
        print("3. 如果未安装mysql-connector-python，请运行: pip install mysql-connector-python")
        return False
    except ImportError:
        print("❌ 未安装mysql-connector-python")
        print("\n请运行: pip install mysql-connector-python")
        return False

if __name__ == "__main__":
    test_mysql_connection()
