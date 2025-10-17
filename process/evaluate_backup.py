# process/evaluate.py

import json
import requests
from typing import Optional

import yaml

from helpers.model_selector import record_model_usage, select_model


def simple_openrouter_call(messages, config, temperature=0.3):
    """Ultra-simple OpenRouter call - auto-select cheapest model"""
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {config.get('OPENROUTER_API_KEY')}",
                "Content-Type": "application/json",
            },
            json={
                "model": "auto",  # Auto-select cheapest
                "messages": messages,
                "temperature": temperature,
            },
        )
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"OpenRouter API error: {e}")
        return None


def get_llm_model_for_provider(
    config: dict,
    task_type: str = "default",
    require_fast: bool = False,
    require_quality: bool = False,
) -> str:
    """Returns the appropriate model string for the configured LLM provider and task type."""
    provider = config.get("llm_provider", "openrouter")
    # Use enhanced model selector for free-first selection
    model = select_model(
        tier=task_type, require_fast=require_fast, require_quality=require_quality
    )
    if provider == "deepseek":
        if task_type == "reasoner":
            return config.get("llm_model_reasoner", "deepseek-ai/deepseek-reasoner")
        elif task_type == "premium":
            return config.get("llm_model_premium", "deepseek-ai/deepseek-chat")
        else:
            return config.get("llm_model", "deepseek-ai/deepseek-chat")
    if provider == "ollama":
        return f"ollama/{model}"
    elif provider == "openrouter":
        return f"openrouter/{model}"
    return model


def summarize_text(text: str, config: dict) -> Optional[str]:
    """Generates a summary for the given text using the configured LLM."""
    provider = config.get("llm_provider", "openrouter")
    if provider == "openrouter" and not config.get("OPENROUTER_API_KEY"):
        return None
    if provider == "deepseek" and not config.get("DEEPSEEK_API_KEY"):
        return None
    model = get_llm_model_for_provider(config, "budget", require_fast=True)
    try:
        kwargs = {}
        if provider == "deepseek":
            kwargs["api_key"] = config.get("DEEPSEEK_API_KEY")
        elif provider == "openrouter":
            kwargs["api_key"] = config.get("OPENROUTER_API_KEY")
        response = openrouter_completion(
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert summarizer. Provide a concise summary of the following text.",
                },
                {"role": "user", "content": text},
            ],
            model="auto",  # Let OpenRouter auto-select cheapest
            temperature=0.3,
            api_key=config.get("OPENROUTER_API_KEY"),
        )
        tokens_used = response.get("usage", {}).get("total_tokens", 0)
        record_model_usage("auto", tokens_used=tokens_used, success=True)
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        record_model_usage(model, success=False)
        print(f"ERROR: Could not get summary from LLM. Details: {e}")
        return None


def extract_entities(text: str, config: dict) -> Optional[dict]:
    """Extracts key entities (people, places, topics) from the text."""
    provider = config.get("llm_provider", "openrouter")
    if provider == "openrouter" and not config.get("OPENROUTER_API_KEY"):
        return None
    if provider == "deepseek" and not config.get("DEEPSEEK_API_KEY"):
        return None
    model = get_llm_model_for_provider(config, "budget", require_fast=True)
    try:
        kwargs = {}
        if provider == "deepseek":
            kwargs["api_key"] = config.get("DEEPSEEK_API_KEY")
        elif provider == "openrouter":
            kwargs["api_key"] = config.get("OPENROUTER_API_KEY")
        response = litellm.completion(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert entity extractor. Extract key people, organizations, locations, and topics from the following text. Return the result as a JSON object with keys 'people', 'organizations', 'locations', and 'topics'.",
                },
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
            max_tokens=500,
            temperature=0.1,
            **kwargs,
        )
        tokens_used = response.usage.total_tokens if hasattr(response, "usage") else 0
        record_model_usage(model, tokens_used=tokens_used, success=True)
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        record_model_usage(model, success=False)
        print(f"ERROR: Could not extract entities from LLM. Details: {e}")
        return None


def classify_content(text: str, config: dict) -> Optional[dict]:
    """Classifies content into the predefined two-tiered taxonomy."""
    provider = config.get("llm_provider", "openrouter")
    if provider == "openrouter" and not config.get("OPENROUTER_API_KEY"):
        return None
    if provider == "deepseek" and not config.get("DEEPSEEK_API_KEY"):
        return None
    categories_yaml = yaml.dump(config.get("categories", {}))
    model = get_llm_model_for_provider(config, "premium", require_quality=True)
    system_prompt = f"""
You are an expert content classifier. Your task is to classify the given text according to the following two-tiered system.
Users will provide a text, and you must select the most relevant Tier 1 and Tier 2 categories.

**Taxonomy:**
{categories_yaml}

**Output Format:**
Return a JSON object with two keys:
1.  `tier_1_categories`: A list of one or more relevant Tier 1 category strings.
2.  `tier_2_sub_tags`: A list of one or more relevant Tier 2 sub-tag strings.

**Rules:**
- You MUST choose at least one category from each tier.
- Be conservative. Only select categories that are strongly supported by the text.
- If no categories fit, return an empty list for both keys.
"""
    try:
        kwargs = {}
        if provider == "deepseek":
            kwargs["api_key"] = config.get("DEEPSEEK_API_KEY")
        elif provider == "openrouter":
            kwargs["api_key"] = config.get("OPENROUTER_API_KEY")
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
            max_tokens=300,
            temperature=0.0,
            **kwargs,
        )
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError as e:
        print(f"ERROR: LLM returned invalid JSON for classification. Details: {e}")
        return None
    except Exception as e:
        print(f"ERROR: Could not classify content from LLM. Details: {e}")
        return None


def diarize_speakers(text: str, config: dict) -> Optional[str]:
    """Identifies and labels different speakers in a transcript."""
    provider = config.get("llm_provider", "openrouter")
    if provider == "openrouter" and not config.get("OPENROUTER_API_KEY"):
        return None
    if provider == "deepseek" and not config.get("DEEPSEEK_API_KEY"):
        return None
    model = get_llm_model_for_provider(config, "premium")
    try:
        kwargs = {}
        if provider == "deepseek":
            kwargs["api_key"] = config.get("DEEPSEEK_API_KEY")
        elif provider == "openrouter":
            kwargs["api_key"] = config.get("OPENROUTER_API_KEY")
        response = litellm.completion(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at speaker diarization. Reformat the following transcript, identifying and labeling each speaker (e.g., 'Speaker 1:', 'Speaker 2:', 'Host:').",
                },
                {"role": "user", "content": text},
            ],
            max_tokens=4000,  # Allow for longer transcripts
            temperature=0.1,
            **kwargs,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"ERROR: Could not perform diarization with LLM. Details: {e}")
        return None
