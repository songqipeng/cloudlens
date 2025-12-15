#!/bin/bash
# 启动后端服务
uvicorn main:app --reload --host 127.0.0.1 --port 8000
