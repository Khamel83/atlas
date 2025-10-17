#!/usr/bin/env python3
"""
Test Block 5-6: Docker/OCI Deployment
Tests Docker containers build and run successfully
"""

import subprocess
import sys
import time
import requests
from datetime import datetime


def run_command(cmd, description="", timeout=300):
    """Run shell command and return result"""
    print(f"🔧 {description}")
    print(f"   Command: {cmd}")

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )

        if result.returncode == 0:
            print(f"✅ Success: {description}")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()[:200]}...")
            return True, result.stdout
        else:
            print(f"❌ Failed: {description}")
            print(f"   Error: {result.stderr.strip()[:200]}...")
            return False, result.stderr

    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout: {description} took longer than {timeout}s")
        return False, "Timeout"
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False, str(e)


def test_docker_build():
    """Test Docker image build"""
    print("🏗️  TESTING DOCKER BUILD")
    print("=" * 40)

    # Clean any previous builds
    run_command("docker system prune -f", "Clean Docker system")

    # Build the main Atlas image
    success, output = run_command(
        "docker build -t atlas:test .",
        "Building Atlas Docker image",
        timeout=600  # 10 minutes for build
    )

    if not success:
        return False

    # Check image was created
    success, output = run_command(
        "docker images atlas:test",
        "Verify Atlas image exists"
    )

    return success


def test_docker_run():
    """Test Docker container run"""
    print(f"\n🚀 TESTING DOCKER RUN")
    print("=" * 40)

    # Stop any existing containers
    run_command("docker stop atlas-test || true", "Stop existing test container")
    run_command("docker rm atlas-test || true", "Remove existing test container")

    # Start container in detached mode
    success, output = run_command(
        "docker run -d --name atlas-test -p 5001:5000 atlas:test",
        "Start Atlas container"
    )

    if not success:
        return False

    # Wait for container to start
    print("⏳ Waiting 30 seconds for container to start...")
    time.sleep(30)

    # Check container is running
    success, output = run_command(
        "docker ps --filter name=atlas-test",
        "Check container status"
    )

    if not success or "atlas-test" not in output:
        # Show container logs for debugging
        run_command("docker logs atlas-test", "Get container logs")
        return False

    return True


def test_container_health():
    """Test container health check"""
    print(f"\n🏥 TESTING CONTAINER HEALTH")
    print("=" * 40)

    # Test health endpoint
    try:
        response = requests.get("http://localhost:5001/api/capture/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health check endpoint responding")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check exception: {str(e)}")

        # Show container logs for debugging
        run_command("docker logs atlas-test", "Get container logs for debugging")
        return False


def test_docker_compose():
    """Test docker-compose configuration"""
    print(f"\n📦 TESTING DOCKER COMPOSE")
    print("=" * 40)

    # Validate docker-compose file
    success, output = run_command(
        "docker-compose config",
        "Validate docker-compose.yml"
    )

    if not success:
        return False

    print("✅ docker-compose.yml configuration valid")
    return True


def cleanup_test_containers():
    """Clean up test containers"""
    print(f"\n🧹 CLEANUP")
    print("=" * 40)

    run_command("docker stop atlas-test || true", "Stop test container")
    run_command("docker rm atlas-test || true", "Remove test container")
    run_command("docker rmi atlas:test || true", "Remove test image")


def main():
    print("🚀 Starting Block 5-6: Docker/OCI Deployment Test")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)

    test_results = {}

    # Test 1: Docker build
    test_results["build"] = test_docker_build()

    # Test 2: Docker run (only if build succeeded)
    if test_results["build"]:
        test_results["run"] = test_docker_run()

        # Test 3: Health check (only if run succeeded)
        if test_results["run"]:
            test_results["health"] = test_container_health()
        else:
            test_results["health"] = False
    else:
        test_results["run"] = False
        test_results["health"] = False

    # Test 4: Docker compose validation
    test_results["compose"] = test_docker_compose()

    # Cleanup
    cleanup_test_containers()

    # Summary
    print(f"\n📊 BLOCK 5-6 DOCKER TEST SUMMARY")
    print("=" * 60)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.ljust(15)}: {status}")
        if result:
            passed += 1

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print(f"\n🎉 BLOCK 5-6: DOCKER/OCI DEPLOYMENT - COMPLETE!")
        print("✅ Docker image builds successfully")
        print("✅ Container runs and passes health checks")
        print("✅ docker-compose configuration valid")
        return True
    else:
        print(f"\n⚠️  BLOCK 5-6: Partial success - {passed}/{total} tests passed")
        print("🔍 Check logs above for specific failures")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)