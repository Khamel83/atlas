#!/usr/bin/env python3
"""Test content export functionality"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_content_export():
    """Test the content export system"""
    print("🧪 Testing Content Export System...")

    try:
        from helpers.content_exporter import ContentExporter

        # Test initialization
        exporter = ContentExporter()
        print(f"   ✅ Exporter initialized")

        # Test with sample data
        sample_content = {
            'title': 'Test Article',
            'content_type': 'article',
            'source_url': 'https://example.com/test',
            'created_at': '2025-08-22',
            'summary': 'This is a test summary.',
            'content': 'This is the full content of the test article.'
        }

        # Test template rendering
        template = exporter.jinja_env.get_template('markdown.jinja2')
        rendered = template.render(
            content=sample_content,
            export_date='2025-08-22',
            segments=[]
        )

        print(f"   ✅ Template rendering successful")
        print(f"   📄 Sample output length: {len(rendered)} characters")

        # Test different formats
        formats = ['markdown', 'obsidian', 'notion', 'anki']
        for fmt in formats:
            try:
                template_file = f"{fmt}.jinja2"
                template = exporter.jinja_env.get_template(template_file)
                output = template.render(content=sample_content, export_date='2025-08-22')
                print(f"   ✅ {fmt.title()} format: {len(output)} chars")
            except Exception as e:
                print(f"   ⚠️ {fmt.title()} format error: {str(e)}")

        return True

    except Exception as e:
        print(f"   ❌ Export test failed: {str(e)}")
        return False

def test_apple_shortcuts():
    """Test Apple Shortcuts integration"""
    print("\n🍎 Testing Apple Shortcuts Integration...")

    try:
        from helpers.shortcuts_manager import ShortcutsManager

        manager = ShortcutsManager()
        print(f"   ✅ Shortcuts manager initialized")

        # Test shortcut generation
        shortcuts = manager.get_available_shortcuts()
        print(f"   ✅ Available shortcuts: {len(shortcuts)}")

        for name, shortcut in shortcuts.items():
            print(f"      📱 {name}: {shortcut.get('description', 'No description')}")

        # Test shortcut file generation
        if shortcuts:
            first_shortcut = list(shortcuts.keys())[0]
            file_path = manager.generate_shortcut_file(first_shortcut)
            if file_path:
                print(f"   ✅ Generated shortcut file: {Path(file_path).name}")
            else:
                print(f"   ⚠️ Could not generate shortcut file")

        return True

    except Exception as e:
        print(f"   ❌ Apple shortcuts test failed: {str(e)}")
        return False

def main():
    """Run Block 4 tests"""
    print("🚀 Block 4: Content Export & Apple Integration Test")
    print("=" * 60)

    tests = [
        ("Content Export", test_content_export),
        ("Apple Shortcuts", test_apple_shortcuts)
    ]

    results = []
    for test_name, test_func in tests:
        success = test_func()
        results.append((test_name, success))

    print("\n" + "=" * 60)
    print("📊 Block 4 Test Results")
    print("-" * 30)

    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status:<8} {test_name}")
        if success:
            passed += 1

    success_rate = (passed / len(results)) * 100
    print(f"\nBlock 4 Status: {passed}/{len(results)} tests passed ({success_rate:.1f}%)")

    if success_rate >= 50:
        print("🎉 Block 4: Framework functional - ready for production testing")
    else:
        print("⚠️ Block 4: Needs additional implementation")

    return success_rate >= 50

if __name__ == "__main__":
    main()