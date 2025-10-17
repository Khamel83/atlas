#!/bin/bash
# Smart processing of rambling input - automatically clarifies and optimizes
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🧠 Processing your brain dump...${NC}"

if [[ $# -eq 0 ]]; then
    echo -e "${YELLOW}Please provide your rambling thoughts:${NC}"
    echo "Usage: /brain-dump \"I want to build a chat app but not sure about WebSockets vs polling and also need auth and maybe Docker...\""
    echo ""
    echo "Brain dump will help organize your scattered thoughts into clear structure."
    exit 0
fi

INPUT="$*"
echo -e "${GREEN}Input: $INPUT${NC}"
echo ""

# Extract key concepts and organize them
echo -e "${BLUE}🔍 Analyzing your thoughts...${NC}"

# Simple keyword extraction and categorization
TECHNOLOGIES=""
FEATURES=""
CONCERNS=""
DECISIONS=""

# Look for technology keywords
if echo "$INPUT" | grep -qi "websocket\|socket\.io\|sse\|polling"; then
    TECHNOLOGIES="$TECHNOLOGIES• Real-time communication (WebSocket/SSE/Polling)\n"
fi

if echo "$INPUT" | grep -qi "auth\|login\|oauth\|jwt\|session"; then
    FEATURES="$FEATURES• Authentication system\n"
fi

if echo "$INPUT" | grep -qi "docker\|container\|k8s\|kubernetes"; then
    TECHNOLOGIES="$TECHNOLOGIES• Containerization (Docker/K8s)\n"
fi

if echo "$INPUT" | grep -qi "database\|db\|sql\|nosql\|mongo\|postgres"; then
    TECHNOLOGIES="$TECHNOLOGIES• Database layer\n"
fi

if echo "$INPUT" | grep -qi "chat\|message\|messaging"; then
    FEATURES="$FEATURES• Chat/messaging functionality\n"
fi

if echo "$INPUT" | grep -qi "not sure\|unsure\|maybe\|or\|vs\|versus"; then
    DECISIONS="$DECISIONS• Technology choices need clarification\n"
fi

if echo "$INPUT" | grep -qi "performance\|scale\|scaling\|speed\|fast"; then
    CONCERNS="$CONCERNS• Performance and scalability\n"
fi

if echo "$INPUT" | grep -qi "security\|secure\|safe\|privacy"; then
    CONCERNS="$CONCERNS• Security considerations\n"
fi

# Output organized structure
echo ""
echo -e "${GREEN}📊 Organized Structure:${NC}"
echo ""

if [[ -n "$FEATURES" ]]; then
    echo -e "${BLUE}🎯 Core Features:${NC}"
    echo -e "$FEATURES"
fi

if [[ -n "$TECHNOLOGIES" ]]; then
    echo -e "${BLUE}🛠️ Technologies Mentioned:${NC}"
    echo -e "$TECHNOLOGIES"
fi

if [[ -n "$CONCERNS" ]]; then
    echo -e "${BLUE}⚠️ Concerns & Requirements:${NC}"
    echo -e "$CONCERNS"
fi

if [[ -n "$DECISIONS" ]]; then
    echo -e "${BLUE}❓ Decisions Needed:${NC}"
    echo -e "$DECISIONS"
fi

# Generate clarification questions
echo ""
echo -e "${GREEN}💡 Clarification Questions:${NC}"
echo ""

echo "1. **Scope & Scale:**"
echo "   • How many concurrent users do you expect?"
echo "   • Is this a prototype, MVP, or production system?"
echo ""

echo "2. **Technical Preferences:**"
echo "   • Do you have preferred programming languages/frameworks?"
echo "   • Any existing infrastructure constraints?"
echo ""

echo "3. **Feature Priorities:**"
echo "   • Which features are must-have vs nice-to-have?"
echo "   • What's your timeline for different phases?"
echo ""

echo "4. **Architecture Decisions:**"
if echo "$INPUT" | grep -qi "websocket\|polling"; then
    echo "   • For real-time: WebSockets for bidirectional, SSE for server-to-client, polling for simplicity"
fi

if echo "$INPUT" | grep -qi "docker\|kubernetes"; then
    echo "   • For deployment: Docker for consistency, K8s if you need orchestration"
fi

echo ""
echo -e "${GREEN}🚀 Recommended Next Steps:${NC}"
echo "1. Use /clarify to work through these questions systematically"
echo "2. Use /workflow to plan implementation phases"
echo "3. Use /meta-ai if any technical decisions need external research"

# Generate a structured prompt for further work
echo ""
echo -e "${BLUE}📝 Structured Version for Next Steps:${NC}"
echo "----------------------------------------"

echo "**Project Goal:** $(echo "$INPUT" | head -c 100)..."
echo ""
echo "**Key Components Identified:**"
if [[ -n "$FEATURES" ]]; then echo -e "$FEATURES"; fi
if [[ -n "$TECHNOLOGIES" ]]; then echo -e "$TECHNOLOGIES"; fi
echo ""
echo "**Questions to Resolve:**"
if [[ -n "$DECISIONS" ]]; then echo -e "$DECISIONS"; fi
if [[ -n "$CONCERNS" ]]; then echo -e "$CONCERNS"; fi

echo "----------------------------------------"
echo ""
echo -e "${YELLOW}💡 Copy the structured version above for clearer communication!${NC}"