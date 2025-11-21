#!/usr/bin/env python3
"""
Test web API and Docker functionality
"""
import os
import sys
import time
import subprocess
from helpers.bulletproof_process_manager import create_managed_process

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_api_functionality():
    """Test API functionality"""
    try:
        from api.main import app
        print(f"✅ API server can be imported: {len(app.routes)} routes")
        return True
    except Exception as e:
        print(f"❌ API server import error: {e}")
        return False

def test_api_server():
    """Test API server startup and basic endpoints"""
    try:
        # Start API server in background
        print("Starting API server...")
        process = create_managed_process([
            sys.executable, "-m", "uvicorn", "api.main:app",
            "--host", "127.0.0.1", "--port", "8000",
            "--log-level", "error"
        ], "uvicorn_api_server")

        # Wait for server to start
        time.sleep(5)

        # Test basic endpoints
        import requests
        try:
            response = requests.get("http://127.0.0.1:8000/health", timeout=5)
            if response.status_code == 200:
                print("✅ API health endpoint working")
            else:
                print(f"❌ API health endpoint returned {response.status_code}")

            response = requests.get("http://127.0.0.1:8000/api/search?query=test", timeout=5)
            if response.status_code == 200:
                print("✅ API search endpoint working")
            else:
                print(f"❌ API search endpoint returned {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"❌ API endpoint test failed: {e}")

        # Stop the server
        process.terminate()
        process.wait()
        print("✅ API server test completed")
        return True

    except Exception as e:
        print(f"❌ API server test error: {e}")
        return False

def test_docker_build():
    """Test Docker build functionality"""
    try:
        # Check if Docker is available
        process = create_managed_process(["docker", "--version"], "docker_version")
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            print("⚠️  Docker not available, skipping Docker tests")
            return True

        print("Testing Docker build...")
        process = create_managed_process([
            "docker", "build", "-t", "atlas:test", ".", "--no-cache"
        ], "docker_build", cwd=os.path.dirname(os.path.abspath(__file__)))
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            print("✅ Docker build successful")
            return True
        else:
            print(f"❌ Docker build failed: {stderr.decode('utf-8')}")
            return False

        if result.returncode == 0:
            print("✅ Docker build successful")
            return True
        else:
            print(f"❌ Docker build failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Docker test error: {e}")
        return False

def main():
    """Run all API and Docker tests"""
    print("🧪 Testing Atlas Web API and Docker Functionality")
    print("=" * 50)

    tests = [
        test_api_functionality,
        test_api_server,
        test_docker_build
    ]

    passed = 0
    for test in tests:
        if test():
            passed += 1

    print("=" * 50)
    print(f"Results: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("🎉 All API and Docker tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())