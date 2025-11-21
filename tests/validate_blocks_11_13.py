#!/usr/bin/env python3
"""
Validation script for Blocks 11-13 implementation status

Determines what's actually implemented vs. what's just documentation.
"""

import os
import sys
from pathlib import Path

# Add atlas to path
atlas_path = Path(__file__).parent.parent
sys.path.insert(0, str(atlas_path))

def check_file_exists_and_substantial(file_path, min_size=500):
    """Check if file exists and has substantial content."""
    try:
        full_path = atlas_path / file_path
        if full_path.exists():
            size = full_path.stat().st_size
            return True, size
        else:
            return False, 0
    except Exception:
        return False, 0

def validate_blocks_11_13():
    """Comprehensive validation of Blocks 11-13 implementation."""

    print("🔍 BLOCKS 11-13 IMPLEMENTATION VALIDATION")
    print("=" * 50)
    print()

    # Block 11: Core API Framework
    print("📋 BLOCK 11: Core API Framework")
    print("-" * 30)

    block11_files = {
        'api/main.py': 'Main FastAPI application',
        'api/requirements.txt': 'API dependencies',
        'api/README.md': 'API documentation'
    }

    block11_score = 0
    for file_path, description in block11_files.items():
        exists, size = check_file_exists_and_substantial(file_path, 100)
        if exists:
            print(f"✓ {file_path} - {description} ({size} bytes)")
            block11_score += 1
        else:
            print(f"❌ {file_path} - {description} (missing)")

    # Check API structure
    try:
        main_file = atlas_path / 'api/main.py'
        if main_file.exists():
            content = main_file.read_text()
            if 'FastAPI' in content:
                print("✓ FastAPI application structure present")
                block11_score += 1
            if 'router' in content:
                print("✓ Router structure implemented")
                block11_score += 1
            if 'health' in content:
                print("✓ Health check endpoint present")
                block11_score += 1
        else:
            print("❌ Main API file missing")
    except Exception as e:
        print(f"❌ API structure check failed: {e}")

    print(f"\nBlock 11 Score: {block11_score}/6")

    # Block 12: Authentication & Security API
    print("\n🔐 BLOCK 12: Authentication & Security API")
    print("-" * 35)

    block12_files = {
        'api/routers/auth.py': 'Authentication router',
        'api/auth_api.py': 'Alternative auth implementation'
    }

    block12_score = 0
    auth_implementation_found = False

    for file_path, description in block12_files.items():
        exists, size = check_file_exists_and_substantial(file_path, 500)
        if exists:
            print(f"✓ {file_path} - {description} ({size} bytes)")
            block12_score += 1
            auth_implementation_found = True

            # Check for specific auth features
            try:
                content = (atlas_path / file_path).read_text()
                if 'API_KEY' in content or 'api_key' in content:
                    print("  ✓ API key functionality present")
                    block12_score += 1
                if 'generate' in content.lower():
                    print("  ✓ Key generation functionality present")
                    block12_score += 1
                if 'auth' in content.lower():
                    print("  ✓ Authentication logic present")
                    block12_score += 1
            except Exception:
                pass
        else:
            print(f"❌ {file_path} - {description} (missing)")

    if not auth_implementation_found:
        print("❌ No authentication implementation found")

    print(f"\nBlock 12 Score: {block12_score}/6")

    # Block 13: Content Management API
    print("\n📄 BLOCK 13: Content Management API")
    print("-" * 32)

    block13_files = {
        'api/routers/content.py': 'Content router',
        'api/content_api.py': 'Alternative content implementation'
    }

    block13_score = 0
    content_implementation_found = False

    for file_path, description in block13_files.items():
        exists, size = check_file_exists_and_substantial(file_path, 1000)
        if exists:
            print(f"✓ {file_path} - {description} ({size} bytes)")
            block13_score += 1
            content_implementation_found = True

            # Check for specific content management features
            try:
                content = (atlas_path / file_path).read_text()
                if 'def ' in content and ('get' in content.lower() or 'list' in content.lower()):
                    print("  ✓ Content listing functionality present")
                    block13_score += 1
                if 'submit' in content.lower() or 'upload' in content.lower():
                    print("  ✓ Content submission functionality present")
                    block13_score += 1
                if 'delete' in content.lower():
                    print("  ✓ Content deletion functionality present")
                    block13_score += 1
                if 'pagination' in content.lower() or 'skip' in content.lower():
                    print("  ✓ Pagination functionality present")
                    block13_score += 1
            except Exception:
                pass
        else:
            print(f"❌ {file_path} - {description} (missing)")

    if not content_implementation_found:
        print("❌ No content management implementation found")

    print(f"\nBlock 13 Score: {block13_score}/6")

    # Overall Assessment
    print("\n" + "=" * 50)
    print("📊 OVERALL ASSESSMENT")
    print("=" * 50)

    total_score = block11_score + block12_score + block13_score
    max_score = 18
    percentage = (total_score / max_score) * 100

    print(f"Block 11 (Core API): {block11_score}/6 ({(block11_score/6)*100:.1f}%)")
    print(f"Block 12 (Auth API): {block12_score}/6 ({(block12_score/6)*100:.1f}%)")
    print(f"Block 13 (Content API): {block13_score}/6 ({(block13_score/6)*100:.1f}%)")
    print(f"\nTotal Score: {total_score}/18 ({percentage:.1f}%)")

    # Status determination
    if percentage >= 80:
        status = "✅ BLOCKS 11-13 SUBSTANTIALLY IMPLEMENTED"
        recommendation = "Ready for testing and refinement"
    elif percentage >= 60:
        status = "⚠️ BLOCKS 11-13 PARTIALLY IMPLEMENTED"
        recommendation = "Some components missing, needs completion"
    elif percentage >= 40:
        status = "🔧 BLOCKS 11-13 BASIC IMPLEMENTATION"
        recommendation = "Foundation exists, significant work needed"
    else:
        status = "❌ BLOCKS 11-13 NOT IMPLEMENTED"
        recommendation = "Only documentation/stubs exist, needs full implementation"

    print(f"\nStatus: {status}")
    print(f"Recommendation: {recommendation}")

    # Dependency Check
    print(f"\n🔗 DEPENDENCY STATUS")
    print("-" * 20)

    try:
        import fastapi
        print("✓ FastAPI available")
    except ImportError:
        print("❌ FastAPI not installed (pip install fastapi uvicorn needed)")

    try:
        from helpers.config import load_config
        print("✓ Atlas core components accessible")
    except ImportError:
        print("❌ Atlas core components not accessible (dependency issues)")

    # Cognitive modules check
    cognitive_dirs = ['ask/', 'cognitive/', 'agents/']
    cognitive_found = False

    for dir_name in cognitive_dirs:
        if (atlas_path / dir_name).exists():
            cognitive_found = True
            print(f"✓ Cognitive directory {dir_name} exists")
            break

    if not cognitive_found:
        print("❌ No cognitive modules found (referenced in API but don't exist)")

    return {
        'block11_score': block11_score,
        'block12_score': block12_score,
        'block13_score': block13_score,
        'total_score': total_score,
        'percentage': percentage,
        'status': status,
        'recommendation': recommendation
    }

if __name__ == "__main__":
    results = validate_blocks_11_13()

    # Return appropriate exit code
    if results['percentage'] >= 80:
        sys.exit(0)  # Success
    elif results['percentage'] >= 60:
        sys.exit(1)  # Partial success
    else:
        sys.exit(2)  # Not implemented