#!/usr/bin/env python3
"""
Complete API Cleanup for Atlas

This script彻底清除所有缓存的API实例和全局变量，
确保Google Search不会被意外使用。

1. 清除环境变量
2. 清除Python模块缓存
3. 强制重新导入所有模块
4. 验证Google Search确实被禁用
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def clean_environment():
    """清除所有API相关的环境变量"""
    print("🧹 清理环境变量...")

    api_keys = [
        'GOOGLE_SEARCH_API_KEY',
        'GOOGLE_SEARCH_ENGINE_ID',
        'OPENAI_API_KEY',
        'OPENAI_API_BASE_URL',
        'ANTHROPIC_API_KEY',
        'ANTHROPIC_BASE_URL',
        'ANTHROPIC_AUTH_TOKEN',
        'YOUTUBE_API_KEY'
    ]

    cleared_count = 0
    for key in api_keys:
        if key in os.environ:
            del os.environ[key]
            cleared_count += 1
            print(f"  🚫 已清除: {key}")

    print(f"✅ 清除了 {cleared_count} 个环境变量")

def clear_python_cache():
    """清除Python模块缓存"""
    print("🧹 清理Python模块缓存...")

    cache_dirs = [
        Path("/home/ubuntu/dev/atlas/__pycache__"),
        Path("/home/ubuntu/dev/atlas/helpers/__pycache__"),
    ]

    cleared_count = 0
    for cache_dir in cache_dirs:
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            cleared_count += 1
            print(f"  🗑️  已删除: {cache_dir}")

    print(f"✅ 清除了 {cleared_count} 个缓存目录")

def kill_python_processes():
    """杀死所有Python进程以清除全局实例"""
    print("🔪 杀死Python进程...")

    try:
        result = subprocess.run(
            ["pkill", "-f", "python"],
            capture_output=True,
            text=True
        )
        print("  ✅ 已杀死所有Python进程")
    except Exception as e:
        print(f"  ⚠️  杀死进程时出错: {e}")

def test_fresh_environment():
    """在全新的环境中测试API使用"""
    print("🧪 在新环境中测试...")

    test_script = '''
import os
import sys
import json

# 确保环境干净
for key in ["GOOGLE_SEARCH_API_KEY", "GOOGLE_SEARCH_ENGINE_ID", "OPENAI_API_KEY"]:
    if key in os.environ:
        del os.environ[key])

print("环境检查:")
for key in ["GOOGLE_SEARCH_API_KEY", "GOOGLE_SEARCH_ENGINE_ID"]:
    print(f"  {key}: {bool(os.getenv(key))}")

# 测试新的API管理器
print("\\n测试API管理器...")
from helpers.api_manager import api_manager

print("服务状态:")
services = api_manager.list_all_services()
for name, info in services.items():
    status = "✅" if info["status"] == "enabled" else "🚫"
    print(f"  {status} {name}: {info['status']}")

# 测试转录查找
print("\\n测试转录查找...")
from helpers.podcast_transcript_lookup_v2 import PodcastTranscriptLookupV2
lookup = PodcastTranscriptLookupV2()

# 测试几个ATP剧集
test_episodes = [
    ("Accidental Tech Podcast", "657: Ears Are Weird"),
    ("Accidental Tech Podcast", "656: A Lot of Apple Stuff")
]

for podcast, episode in test_episodes:
    print(f"\\n测试: {podcast} - {episode}")
    result = lookup.lookup_transcript(podcast, episode)
    print(f"  成功: {result.success}")
    print(f"  来源: {result.source}")
    print(f"  错误: {result.error_message}")

    if result.source == "google_search":
        print("  ❌ 仍然在使用Google Search!")
        return False
    elif result.success:
        print("  ✅ 使用了正确的来源!")
    else:
        print("  ⚠️  查找失败")

print("\\n✅ 所有测试通过 - Google Search已被禁用!")
return True
'''

    # 在子进程中运行测试，确保完全干净的环境
    result = subprocess.run(
        [sys.executable, "-c", test_script],
        capture_output=True,
        text=True,
        cwd="/home/ubuntu/dev/atlas",
        timeout=60
    )

    print("测试输出:")
    print(result.stdout)

    if result.stderr:
        print("测试错误:")
        print(result.stderr)

    return result.returncode == 0

def disable_expensive_services():
    """禁用所有昂贵服务"""
    print("🚫 禁用昂贵服务...")

    disable_script = '''
from helpers.api_manager import api_manager
api_manager.disable_all_expensive_services()
print("✅ 已禁用所有昂贵服务")
'''

    result = subprocess.run(
        [sys.executable, "-c", disable_script],
        capture_output=True,
        text=True,
        cwd="/home/ubuntu/dev/atlas"
    )

    print(result.stdout)
    if result.stderr:
        print(result.stderr)

def main():
    """主清理函数"""
    print("🧨 开始完整的API清理...")
    print("=" * 50)

    # 步骤1: 清理环境
    clean_environment()

    # 步骤2: 清理缓存
    clear_python_cache()

    # 步骤3: 杀死进程
    kill_python_processes()

    # 步骤4: 禁用昂贵服务
    disable_expensive_services()

    # 步骤5: 等待一下
    import time
    print("⏳ 等待系统稳定...")
    time.sleep(2)

    # 步骤6: 测试
    print("🧪 测试清理结果...")
    success = test_fresh_environment()

    if success:
        print("\\n🎉 清理成功! Google Search已被完全禁用!")
        return 0
    else:
        print("\\n❌ 清理失败! Google Search仍在被使用!")
        return 1

if __name__ == "__main__":
    sys.exit(main())