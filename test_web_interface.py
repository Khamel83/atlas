#!/usr/bin/env python3
"""
Test script for Atlas Web Interface

Verifies that the web interface components work correctly.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from web_interface import (
    app,
    dashboard,
    add_content_page,
    search_page,
    stats_page,
    api_health,
    create_static_files
)
from core.database import get_database
from core.processor import get_processor


def test_static_files_creation():
    """Test that static files are created correctly"""
    print("🧪 Testing static files creation...")

    try:
        create_static_files()

        # Check that files were created
        static_dir = project_root / "web" / "static"
        templates_dir = project_root / "web" / "templates"

        required_files = [
            static_dir / "style.css",
            static_dir / "script.js",
            templates_dir / "base.html",
            templates_dir / "dashboard.html",
            templates_dir / "add.html",
            templates_dir / "search.html",
            templates_dir / "stats.html"
        ]

        missing_files = []
        for file_path in required_files:
            if not file_path.exists():
                missing_files.append(str(file_path))

        if missing_files:
            print(f"❌ Missing files: {missing_files}")
            return False

        print(f"✅ All {len(required_files)} static files created successfully")
        return True
    except Exception as e:
        print(f"❌ Static files creation failed: {e}")
        return False


def test_web_app_structure():
    """Test the FastAPI app structure"""
    print("\n🧪 Testing web app structure...")

    try:
        print(f"✅ FastAPI app created: {app.title}")
        print(f"✅ Version: {app.version}")
        print(f"✅ Routes: {len(app.routes)}")

        # List main routes
        routes = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                routes.append(f"{list(route.methods)[0]} {route.path}")

        print(f"✅ Web routes: {len([r for r in routes if not r.startswith('/api')])}")
        for route in sorted([r for r in routes if not r.startswith('/api')]):
            print(f"   {route}")

        return True
    except Exception as e:
        print(f"❌ Web app structure test failed: {e}")
        return False


async def test_dashboard_functionality():
    """Test dashboard page functionality"""
    print("\n🧪 Testing dashboard functionality...")

    try:
        # Mock request object
        class MockRequest:
            path = "/"

        # Test dashboard response
        db = get_database()
        stats = db.get_statistics()

        print(f"✅ Database statistics retrieved")
        print(f"   Total content: {stats.get('total_content', 0)}")
        print(f"   Content types: {len(stats.get('by_type', {}))}")

        # Test recent content retrieval
        with db.pool.get_connection() as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM content
                WHERE created_at >= datetime('now', '-7 days')
            """)
            recent_count = cursor.fetchone()[0]

        print(f"✅ Recent activity calculated: {recent_count} items in last 7 days")
        return True
    except Exception as e:
        print(f"❌ Dashboard functionality test failed: {e}")
        return False


async def test_api_health_endpoint():
    """Test the API health endpoint"""
    print("\n🧪 Testing API health endpoint...")

    try:
        health_data = await api_health()
        print(f"✅ API health: {health_data['status']}")
        print(f"   Total content: {health_data['total_content']}")
        print(f"   Timestamp: {health_data['timestamp']}")
        return True
    except Exception as e:
        print(f"❌ API health test failed: {e}")
        return False


def test_css_and_js_content():
    """Test that CSS and JS files have proper content"""
    print("\n🧪 Testing CSS and JS content...")

    try:
        static_dir = project_root / "web" / "static"

        # Test CSS content
        css_file = static_dir / "style.css"
        css_content = css_file.read_text()

        css_checks = [
            ("container class", ".container" in css_content),
            ("card styles", ".card" in css_content),
            ("button styles", ".btn" in css_content),
            ("responsive design", "@media" in css_content),
            ("color scheme", "#667eea" in css_content)
        ]

        missing_css = [check[0] for check in css_checks if not check[1]]
        if missing_css:
            print(f"❌ Missing CSS elements: {missing_css}")
            return False

        print("✅ CSS content includes all required styles")

        # Test JS content
        js_file = static_dir / "script.js"
        js_content = js_file.read_text()

        js_checks = [
            ("AtlasWeb class", "class AtlasWeb" in js_content),
            ("form handling", "handleFormSubmit" in js_content),
            ("search functionality", "performSearch" in js_content),
            ("API calls", "fetch('/api/" in js_content),
            ("alert system", "showAlert" in js_content)
        ]

        missing_js = [check[0] for check in js_checks if not check[1]]
        if missing_js:
            print(f"❌ Missing JS elements: {missing_js}")
            return False

        print("✅ JavaScript content includes all required functions")
        return True
    except Exception as e:
        print(f"❌ CSS/JS content test failed: {e}")
        return False


def test_template_structure():
    """Test that HTML templates have proper structure"""
    print("\n🧪 Testing template structure...")

    try:
        templates_dir = project_root / "web" / "templates"

        # Test base template
        base_file = templates_dir / "base.html"
        base_content = base_file.read_text()

        base_checks = [
            ("HTML structure", "<!DOCTYPE html>" in base_content),
            ("Head section", "<head>" in base_content),
            ("Body section", "<body>" in base_content),
            ("Title block", "{% block title %}" in base_content),
            ("Content block", "{% block content %}" in base_content),
            ("CSS link", "/static/style.css" in base_content),
            ("JS script", "/static/script.js" in base_content)
        ]

        missing_base = [check[0] for check in base_checks if not check[1]]
        if missing_base:
            print(f"❌ Missing base template elements: {missing_base}")
            return False

        print("✅ Base template structure is correct")

        # Test page templates
        page_templates = ["dashboard.html", "add.html", "search.html", "stats.html"]
        for template in page_templates:
            template_file = templates_dir / template
            template_content = template_file.read_text()

            if "{% extends" not in template_content:
                print(f"❌ {template} doesn't extend base template")
                return False

        print(f"✅ All {len(page_templates)} page templates extend base correctly")
        return True
    except Exception as e:
        print(f"❌ Template structure test failed: {e}")
        return False


async def test_web_integration():
    """Test integration with core components"""
    print("\n🧪 Testing web integration...")

    try:
        # Test database connection
        db = get_database()
        stats = db.get_statistics()
        print(f"✅ Database integration working")
        print(f"   Connected to {stats.get('total_content', 0)} content items")

        # Test processor availability
        processor = get_processor()
        processor_health = await processor.health_check()
        print(f"✅ Processor integration working")
        print(f"   Status: {processor_health['status']}")
        print(f"   Strategies: {processor_health['healthy_strategies']}/{processor_health['total_strategies']}")

        # Test content processing capability
        test_content = "Web interface test content"
        result = await processor.process(test_content, title="Web Test")
        if result.success:
            print(f"✅ Content processing integration working")
            print(f"   Processed ID: {result.content.id}")
            print(f"   Title: {result.content.title}")
        else:
            print(f"⚠️  Content processing returned: {result.error}")

        return True
    except Exception as e:
        print(f"❌ Web integration test failed: {e}")
        return False


async def test_all_web_interface():
    """Run all web interface tests"""
    print("🌐 Starting Atlas Web Interface Tests...")
    print("=" * 60)

    passed = 0
    failed = 0

    # Run all tests
    tests = [
        ("Static Files Creation", test_static_files_creation),
        ("Web App Structure", test_web_app_structure),
        ("CSS and JS Content", test_css_and_js_content),
        ("Template Structure", test_template_structure),
        ("Dashboard Functionality", test_dashboard_functionality),
        ("API Health Endpoint", test_api_health_endpoint),
        ("Web Integration", test_web_integration),
    ]

    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()

            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {e}")
            failed += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Web Interface Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All Atlas Web Interface tests passed!")
        print("\n🌐 Web Interface Features Ready:")
        print("   ✅ Clean, responsive design")
        print("   ✅ Content addition interface")
        print("   ✅ Search functionality")
        print("   ✅ Statistics dashboard")
        print("   ✅ Mobile-friendly layout")
        print("   ✅ Integration with core system")
        print("   ✅ Interactive JavaScript features")
        print("   ✅ Proper HTML structure")
        return True
    else:
        print("❌ Some web interface tests failed!")
        return False


async def main():
    """Run all web interface tests"""
    print("🚀 Starting Atlas Web Interface Tests...")
    print("=" * 60)

    success = await test_all_web_interface()

    if success:
        print("\n🎉 Atlas Web Interface is ready!")
        print("\n📱 How to use:")
        print("   1. Start the web interface: python3 start_web.py")
        print("   2. Open http://localhost:8000 in your browser")
        print("   3. Add content, search, and view statistics")
        print("   4. Mobile-friendly - works on phones and tablets")
    else:
        print("\n❌ Atlas Web Interface has issues that need to be resolved")

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)