#!/usr/bin/env python3
"""独立运行聊天机器人后端服务的脚本，用于调试。"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from backend import config

if __name__ == "__main__":
    print("=" * 60)
    print("启动 Chatbot 后端服务")
    print("=" * 60)
    print(f"服务地址: http://0.0.0.0:8001")
    print(f"API 文档: http://localhost:8001/docs")
    print(f"日志级别: {config.LOG_LEVEL}")
    print("=" * 60)
    print("按 Ctrl+C 停止服务")
    print()

    uvicorn.run(
        "backend.chatbot_main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,  # 开发模式：代码变更自动重载
        log_level=config.LOG_LEVEL.lower(),
        access_log=True,  # 显示访问日志
    )

