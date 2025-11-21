#!/usr/bin/env python3
"""
Google Custom Search API Setup Guide

This script helps set up Google Custom Search API for Atlas web search functionality.
"""

import os
import sys
import requests
from dotenv import load_dotenv, set_key

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

def setup_google_search_api():
    """Guide through Google Custom Search API setup"""
    print("🔍 Google Custom Search API Setup for Atlas")
    print("=" * 50)

    # Load current environment
    load_dotenv()

    # Check if already configured
    current_api_key = os.getenv('GOOGLE_SEARCH_API_KEY')
    current_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')

    if current_api_key and current_engine_id:
        print(f"📋 Current configuration:")
        print(f"   API Key: {current_api_key[:10]}...")
        print(f"   Engine ID: {current_engine_id}")

        test_current = input("\n🧪 Test current configuration? (y/n): ").strip().lower()
        if test_current == 'y':
            if test_google_search_api(current_api_key, current_engine_id):
                print("✅ Current configuration is working!")
                return True
            else:
                print("❌ Current configuration is not working. Let's set up new credentials.")

    print("\n📝 To set up Google Custom Search API:")
    print("1. Go to: https://console.cloud.google.com/")
    print("2. Create a new project or select existing one")
    print("3. Enable the 'Custom Search API'")
    print("4. Go to 'Credentials' and create an API key")
    print("5. Go to: https://cse.google.com/")
    print("6. Create a new search engine (can search entire web)")
    print("7. Get your Search Engine ID from the control panel")
    print("\n💰 Free tier: 100 searches per day")
    print("💰 Paid tier: $5 per 1000 queries (after free quota)")

    print("\n" + "=" * 50)

    # Get API key
    api_key = input("🔑 Enter your Google API Key: ").strip()
    if not api_key:
        print("❌ API key is required")
        return False

    # Get Search Engine ID
    engine_id = input("🔍 Enter your Search Engine ID: ").strip()
    if not engine_id:
        print("❌ Search Engine ID is required")
        return False

    # Test the credentials
    print("\n🧪 Testing API credentials...")
    if test_google_search_api(api_key, engine_id):
        # Save to .env file
        env_file = '.env'
        set_key(env_file, 'GOOGLE_SEARCH_API_KEY', api_key)
        set_key(env_file, 'GOOGLE_SEARCH_ENGINE_ID', engine_id)

        print(f"✅ Credentials saved to {env_file}")
        print("🔄 Restart the Atlas API server to use new credentials")
        return True
    else:
        print("❌ API test failed. Please check your credentials.")
        return False

if __name__ == "__main__":
    success = setup_google_search_api()
    sys.exit(0 if success else 1)