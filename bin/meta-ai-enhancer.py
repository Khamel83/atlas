#!/usr/bin/env python3
"""
Meta-AI Prompt Enhancement System

This tool helps generate better, more structured prompts to send to Claude
by using a meta-AI (like ChatGPT) to expand short requests into detailed,
well-structured prompts that get better results.

Usage:
    python bin/meta-ai-enhancer.py "short request"

The system will:
1. Take your short request
2. Use prompt templates to structure it properly
3. Generate a well-formatted prompt for Claude
4. Optionally send it directly to Claude via API
"""

import sys
import json
import argparse
from pathlib import Path

# Prompt templates for different types of requests
ENHANCEMENT_TEMPLATES = {
    "code_request": """
Please expand this brief coding request into a detailed, structured prompt for Claude:

Original request: "{original_request}"

Please structure your response with:
1. Clear objective and context
2. Specific requirements and constraints
3. Expected deliverables
4. Any relevant technical details or preferences
5. Success criteria

Make it detailed enough (300-500 words) so Claude can provide the most helpful response possible.
""",

    "analysis_request": """
Please expand this brief analysis request into a detailed, structured prompt for Claude:

Original request: "{original_request}"

Please structure your response with:
1. Clear analysis objectives
2. Specific areas to examine
3. Expected depth and scope
4. Output format preferences
5. Any particular methodologies or frameworks to consider

Make it comprehensive (300-500 words) so Claude can provide thorough analysis.
""",

    "documentation_request": """
Please expand this brief documentation request into a detailed, structured prompt for Claude:

Original request: "{original_request}"

Please structure your response with:
1. Documentation purpose and audience
2. Required sections and content
3. Format and style preferences
4. Level of technical detail needed
5. Integration with existing documentation

Make it detailed (300-500 words) so Claude can create exactly what's needed.
""",

    "general_request": """
Please expand this brief request into a detailed, structured prompt for Claude:

Original request: "{original_request}"

Please structure your response with:
1. Clear context and background
2. Specific objectives and requirements
3. Expected deliverables and format
4. Any constraints or preferences
5. Success criteria and validation

Make it comprehensive (300-500 words) so Claude can provide the most helpful response.
"""
}

def classify_request(request_text):
    """Classify the type of request to choose appropriate template"""
    request_lower = request_text.lower()

    code_keywords = ['code', 'implement', 'function', 'class', 'script', 'program', 'debug', 'fix']
    analysis_keywords = ['analyze', 'review', 'examine', 'assess', 'evaluate', 'compare']
    doc_keywords = ['document', 'readme', 'guide', 'manual', 'documentation', 'explain']

    if any(keyword in request_lower for keyword in code_keywords):
        return "code_request"
    elif any(keyword in request_lower for keyword in analysis_keywords):
        return "analysis_request"
    elif any(keyword in request_lower for keyword in doc_keywords):
        return "documentation_request"
    else:
        return "general_request"

def generate_enhanced_prompt(original_request):
    """Generate an enhanced prompt using the appropriate template"""
    request_type = classify_request(original_request)
    template = ENHANCEMENT_TEMPLATES[request_type]

    enhanced_prompt = template.format(original_request=original_request)

    return {
        "original_request": original_request,
        "request_type": request_type,
        "enhanced_prompt": enhanced_prompt,
        "meta_instruction": "Send this enhanced prompt to your meta-AI (ChatGPT) to get a well-structured prompt for Claude"
    }

def save_prompt_history(prompt_data, history_file="~/.oos/prompt_history.json"):
    """Save prompt enhancement history for learning and improvement"""
    history_path = Path(history_file).expanduser()
    history_path.parent.mkdir(parents=True, exist_ok=True)

    history = []
    if history_path.exists():
        try:
            with open(history_path, 'r') as f:
                history = json.load(f)
        except:
            history = []

    history.append(prompt_data)

    # Keep only last 100 entries
    history = history[-100:]

    with open(history_path, 'w') as f:
        json.dump(history, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description='Enhance prompts for better Claude responses')
    parser.add_argument('request', help='Your brief request to enhance')
    parser.add_argument('--output', '-o', help='Output file for enhanced prompt')
    parser.add_argument('--no-history', action='store_true', help='Don\'t save to history')

    args = parser.parse_args()

    # Generate enhanced prompt
    result = generate_enhanced_prompt(args.request)

    # Save to history unless disabled
    if not args.no_history:
        save_prompt_history(result)

    # Output the result
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Enhanced prompt saved to {args.output}")
    else:
        print("="*60)
        print("ENHANCED PROMPT FOR META-AI:")
        print("="*60)
        print(result['enhanced_prompt'])
        print("\n" + "="*60)
        print("INSTRUCTIONS:")
        print("1. Copy the above prompt")
        print("2. Send it to your meta-AI (ChatGPT)")
        print("3. Use the meta-AI's response as your prompt to Claude")
        print("="*60)

if __name__ == "__main__":
    main()