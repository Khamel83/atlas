#!/usr/bin/env python3
"""
Check Google Custom Search API Status

This script checks if Google Custom Search API is configured and working.
"""

import os
import requests
from dotenv import load_dotenv

def test_google_search_api(api_key, search_engine_id):
    """Test the Google Custom Search API with sample query"""
    test_query = "python programming"
    url = f"https://www.googleapis.com/customsearch/v1"
    params = {
        'key': api_key,
        'cx': search_engine_id,
        'q': test_query,
        'num': 1
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if 'items' in result and len(result['items']) > 0:
                print(f"✅ API test successful! Found result: {result['items'][0]['title']}")
                return True
            else:
                print("❌ API test failed: No search results returned")
                return False
        else:
            print(f"❌ API test failed: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def check_status():
    """Check Google Custom Search API configuration status"""
    print("🔍 Google Custom Search API Status Check")
    print("=" * 50)

    # Load current environment
    load_dotenv()

    # Check if configured
    api_key = os.getenv('GOOGLE_SEARCH_API_KEY')
    engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')

    if not api_key or not engine_id:
        print("❌ Google Custom Search API not configured")
        print(f"   API Key: {'Set' if api_key else 'Not set'}")
        print(f"   Engine ID: {'Set' if engine_id else 'Not set'}")
        print("\n📝 To configure:")
        print("1. Get API key from: https://console.cloud.google.com/")
        print("2. Get Search Engine ID from: https://cse.google.com/")
        print("3. Add to .env file:")
        print("   GOOGLE_SEARCH_API_KEY=your_api_key_here")
        print("   GOOGLE_SEARCH_ENGINE_ID=your_engine_id_here")
        return False

    print(f"✅ Configuration found:")
    print(f"   API Key: {api_key[:10]}...")
    print(f"   Engine ID: {engine_id}")

    # Test the API
    print("\n🧪 Testing API...")
    return test_google_search_api(api_key, engine_id)

if __name__ == "__main__":
    check_status()