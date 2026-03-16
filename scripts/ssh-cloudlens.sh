#!/usr/bin/env bash
# 使用 Homebrew OpenSSH 连接香港 CloudLens 实例（便于 Cursor/终端下开发）
# 依赖: brew install openssh
# 请确保 ~/.ssh/config 中有 Host cloudlens-aws，且 Hostname 为当前实例公网 IP（见 terraform output instance_public_ip，当前为 18.167.167.25）。
set -e
SSH_BIN="/opt/homebrew/bin/ssh"
CONFIG="${HOME}/.ssh/config"
HOST="cloudlens-aws"
if [[ ! -x "$SSH_BIN" ]]; then
  echo "未找到 Homebrew OpenSSH，请先执行: brew install openssh"
  exit 1
fi
exec "$SSH_BIN" -F "$CONFIG" "$HOST" "$@"
