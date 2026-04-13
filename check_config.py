#!/usr/bin/env python3
"""
配置检查脚本 - 用于诊断 Web UI 密码问题
"""

import os
from app.config import settings

print("=" * 60)
print("配置检查")
print("=" * 60)

print("\n📋 环境变量:")
print(f"  WEB_PASSWORD (env): {os.getenv('WEB_PASSWORD', '未设置')[:10]}...")
print(f"  WEB_SECRET_KEY (env): {os.getenv('WEB_SECRET_KEY', '未设置')[:20]}...")

print("\n📋 Settings 读取值:")
print(f"  web_password: {settings.web_password[:10]}... (长度: {len(settings.web_password)})")
print(f"  web_secret_key: {settings.web_secret_key[:20]}...")

print("\n📋 密码验证测试:")
test_passwords = ["admin123", "admin", ""]
for pwd in test_passwords:
    result = pwd == settings.web_password
    print(f"  '{pwd}' => {'✅ 正确' if result else '❌ 错误'}")

print("\n" + "=" * 60)
