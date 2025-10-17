#!/bin/bash

# Atlas Cognitive API Validation Script
# Tests all cognitive endpoints for functionality

echo "🧠 Atlas Cognitive API Validation"
echo "=================================="

BASE_URL="http://localhost:8000/api/v1/cognitive"
PASSED=0
FAILED=0

# Test ProactiveSurfacer endpoint
echo "1. Testing ProactiveSurfacer (/surface)..."
RESPONSE=$(curl -w "%{http_code}" -s "${BASE_URL}/surface?limit=2")
STATUS_CODE="${RESPONSE: -3}"
if [ "$STATUS_CODE" = "200" ]; then
    echo "   ✅ PASS - Status: $STATUS_CODE"
    PASSED=$((PASSED + 1))
else
    echo "   ❌ FAIL - Status: $STATUS_CODE"
    FAILED=$((FAILED + 1))
fi

# Test TemporalEngine endpoint
echo "2. Testing TemporalEngine (/temporal)..."
RESPONSE=$(curl -w "%{http_code}" -s "${BASE_URL}/temporal")
STATUS_CODE="${RESPONSE: -3}"
if [ "$STATUS_CODE" = "200" ]; then
    echo "   ✅ PASS - Status: $STATUS_CODE"
    PASSED=$((PASSED + 1))
else
    echo "   ❌ FAIL - Status: $STATUS_CODE"
    FAILED=$((FAILED + 1))
fi

# Test QuestionEngine endpoint
echo "3. Testing QuestionEngine (/socratic)..."
RESPONSE=$(curl -w "%{http_code}" -s -X POST "${BASE_URL}/socratic" -H "Content-Type: application/x-www-form-urlencoded" -d "content=test")
STATUS_CODE="${RESPONSE: -3}"
if [ "$STATUS_CODE" = "200" ]; then
    echo "   ✅ PASS - Status: $STATUS_CODE"
    PASSED=$((PASSED + 1))
else
    echo "   ❌ FAIL - Status: $STATUS_CODE"
    FAILED=$((FAILED + 1))
fi

# Test PatternDetector endpoint
echo "4. Testing PatternDetector (/patterns)..."
RESPONSE=$(curl -w "%{http_code}" -s "${BASE_URL}/patterns")
STATUS_CODE="${RESPONSE: -3}"
if [ "$STATUS_CODE" = "200" ]; then
    echo "   ✅ PASS - Status: $STATUS_CODE"
    PASSED=$((PASSED + 1))
else
    echo "   ❌ FAIL - Status: $STATUS_CODE"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "Results: $PASSED/4 endpoints passing"
if [ "$PASSED" = "4" ]; then
    echo "🎉 All cognitive endpoints are functional!"
    exit 0
else
    echo "⚠️  Some endpoints are failing"
    exit 1
fi