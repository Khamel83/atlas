# process/evaluate.py

import json

import litellm
import yaml



def get_llm_model_for_provider(config: dict) -> str:
    """Returns the appropriate model string for the configured LLM provider."""
    provider = config.get("llm_provider", "openrouter")
    model = config.get("llm_model", "mistralai/mistral-7b-instruct")
    if provider == "ollama":
        return f"ollama/{model}"
    return model


def summarize_text(text: str, config: dict) -> str | None:
    """Generates a summary for the given text using the configured LLM."""
    if (
        not config.get("OPENROUTER_API_KEY")
        and config.get("llm_provider") == "openrouter"
    ):
        return None

    model = get_llm_model_for_provider(config)
    try:
        response = litellm.completion(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert summarizer. Provide a concise summary of the following text.",
                },
                {"role": "user", "content": text},
            ],
            max_tokens=500,
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"ERROR: Could not get summary from LLM. Details: {e}")
        return None


def extract_entities(text: str, config: dict) -> dict | None:
    """Extracts key entities (people, places, topics) from the text."""
    if (
        not config.get("OPENROUTER_API_KEY")
        and config.get("llm_provider") == "openrouter"
    ):
        return None

    model = get_llm_model_for_provider(config)
    try:
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
        )
        # The return value is a string, so we need to parse it
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"ERROR: Could not extract entities from LLM. Details: {e}")
        return None


def classify_content(text: str, config: dict) -> dict | None:
    """Classifies content into the predefined two-tiered taxonomy."""
    if (
        not config.get("OPENROUTER_API_KEY")
        and config.get("llm_provider") == "openrouter"
    ):
        return None

    categories_yaml = yaml.dump(config.get("categories", {}))
    model = get_llm_model_for_provider(config)

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
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
            max_tokens=300,
            temperature=0.0,
        )
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError as e:
        print(f"ERROR: LLM returned invalid JSON for classification. Details: {e}")
        return None
    except Exception as e:
        print(f"ERROR: Could not classify content from LLM. Details: {e}")
        return None


def diarize_speakers(text: str, config: dict) -> str | None:
    """Identifies and labels different speakers in a transcript."""
    if (
        not config.get("OPENROUTER_API_KEY")
        and config.get("llm_provider") == "openrouter"
    ):
        return None

    model = get_llm_model_for_provider(config)
    try:
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
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"ERROR: Could not perform diarization with LLM. Details: {e}")
        return None
