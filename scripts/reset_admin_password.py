#!/usr/bin/env python3
"""
在服务器上创建或重置管理员密码（用户数据在 ~/.cloudlens/users.json）。
用法（在项目根目录或已设置 PYTHONPATH 时）:
  python3 scripts/reset_admin_password.py
  python3 scripts/reset_admin_password.py admin MyNewPassword
在 EC2 上通过 Docker 执行:
  docker exec -it cloudlens-backend python -c "
import sys; sys.path.insert(0, '/app');
from pathlib import Path;
exec(open('/app/scripts/reset_admin_password.py').read());
main()
" -- admin CloudLensAdmin2024!
或直接复制本脚本内容在容器内执行。
"""
import json
import sys
from datetime import datetime
from pathlib import Path

from cloudlens.core.auth import _hash_password

# 默认管理员账号与密码（首次部署或忘记密码时使用）
DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASS = "CloudLensAdmin2024!"

USERS_FILE = Path.home() / ".cloudlens" / "users.json"


def main():
    username = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ADMIN_USER
    password = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_ADMIN_PASS

    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    users = {}
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                users = json.load(f)
        except Exception as e:
            print(f"读取用户文件失败: {e}")
            sys.exit(1)

    users[username] = {
        "username": username,
        "email": None,
        "role": "admin",
        "created_at": users.get(username, {}).get("created_at", datetime.now().isoformat()),
        "last_login": None,
        "enabled": True,
    }
    users[username].update(_hash_password(password))
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"写入用户文件失败: {e}")
        sys.exit(1)

    print(f"已设置用户: {username}, 角色: admin")
    print("请使用新密码登录，登录后建议在「设置」中修改密码。")


if __name__ == "__main__":
    main()
