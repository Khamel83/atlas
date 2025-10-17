import argparse
import os
from datetime import datetime
from glob import glob
from typing import List, Optional

try:
    import frontmatter

    FRONTMATTER_AVAILABLE = True
except ImportError:
    FRONTMATTER_AVAILABLE = False

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

try:
    import requests
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def load_categories():
    """Load categories from configuration file"""
    if YAML_AVAILABLE:
        try:
            cfg = yaml.safe_load(open("categories.yaml", "r"))
            return list(cfg.get("tier_1_categories", {}).keys())
        except FileNotFoundError:
            pass

    # Default categories if config file doesn't exist or YAML not available
    return [
        "technology",
        "business",
        "finance",
        "health",
        "science",
        "education",
        "politics",
        "entertainment",
        "sports",
        "personal",
    ]


def choose_category(text: str, categories: List[str]) -> str:
    """
    Intelligently categorize content using AI when available,
    falling back to keyword matching.
    """
    # Try AI categorization first
    if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
        ai_category = _categorize_with_ai(text, categories)
        if ai_category:
            return ai_category

    # Fallback to enhanced keyword matching
    return _categorize_with_keywords(text, categories)


def _categorize_with_ai(text: str, categories: List[str]) -> Optional[str]:
    """Use OpenAI to categorize content intelligently"""
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Truncate text to avoid token limits
        content = text[:4000] if len(text) > 4000 else text

        categories_str = ", ".join(categories)

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a content categorization expert. Analyze the provided content and choose the SINGLE most appropriate category from this list: {categories_str}

Return only the category name, nothing else. If no category fits well, return 'uncategorized'.""",
                },
                {"role": "user", "content": f"Categorize this content:\n\n{content}"},
            ],
            max_tokens=20,
            temperature=0.1,
        )

        category = response.choices[0].message.content.strip().lower()

        # Validate the returned category
        if category in [cat.lower() for cat in categories]:
            return category
        elif category == "uncategorized":
            return "uncategorized"
        else:
            # AI returned invalid category, fall back to keyword matching
            return None

    except Exception as e:
        print(f"AI categorization failed: {e}")
        return None


def _categorize_with_keywords(text: str, categories: List[str]) -> str:
    """Enhanced keyword-based categorization with better matching"""
    text_lower = text.lower()

    # Enhanced keyword mapping
    category_keywords = {
        "technology": [
            "tech",
            "software",
            "ai",
            "artificial intelligence",
            "computer",
            "programming",
            "code",
            "app",
            "digital",
            "internet",
            "web",
            "mobile",
            "startup",
            "silicon valley",
        ],
        "business": [
            "business",
            "company",
            "corporate",
            "enterprise",
            "management",
            "strategy",
            "marketing",
            "sales",
            "revenue",
            "profit",
            "ceo",
            "startup",
            "entrepreneur",
        ],
        "finance": [
            "finance",
            "money",
            "investment",
            "stock",
            "market",
            "trading",
            "cryptocurrency",
            "bitcoin",
            "banking",
            "economy",
            "economic",
            "financial",
            "portfolio",
        ],
        "health": [
            "health",
            "medical",
            "doctor",
            "medicine",
            "hospital",
            "treatment",
            "wellness",
            "fitness",
            "nutrition",
            "mental health",
            "healthcare",
            "disease",
        ],
        "science": [
            "science",
            "research",
            "study",
            "scientific",
            "discovery",
            "experiment",
            "physics",
            "chemistry",
            "biology",
            "climate",
            "environment",
        ],
        "education": [
            "education",
            "learning",
            "school",
            "university",
            "college",
            "student",
            "teacher",
            "academic",
            "course",
            "study",
            "knowledge",
        ],
        "politics": [
            "politics",
            "political",
            "government",
            "policy",
            "election",
            "vote",
            "democracy",
            "law",
            "legislation",
            "congress",
            "senate",
        ],
        "entertainment": [
            "entertainment",
            "movie",
            "film",
            "music",
            "celebrity",
            "hollywood",
            "tv",
            "show",
            "game",
            "gaming",
            "culture",
            "art",
        ],
        "sports": [
            "sports",
            "football",
            "basketball",
            "baseball",
            "soccer",
            "athletic",
            "team",
            "player",
            "game",
            "championship",
            "olympics",
        ],
        "personal": [
            "personal",
            "life",
            "family",
            "relationship",
            "home",
            "lifestyle",
            "diary",
            "journal",
            "memoir",
        ],
    }

    # Score each category
    category_scores = {}
    for category in categories:
        score = 0
        if category.lower() in category_keywords:
            keywords = category_keywords[category.lower()]
            for keyword in keywords:
                if keyword in text_lower:
                    # Weight longer keywords more heavily
                    score += len(keyword.split())

        # Also check if category name appears directly
        if category.lower() in text_lower:
            score += 5

        category_scores[category] = score

    # Return category with highest score
    best_category = max(category_scores, key=category_scores.get)
    if category_scores[best_category] > 0:
        return best_category

    return "uncategorized"


def categorize_file(path, categories):
    """Categorize a file using frontmatter"""
    if not FRONTMATTER_AVAILABLE:
        print("frontmatter library not available")
        return

    post = frontmatter.load(path)
    content = post.content
    cat = choose_category(content, categories)
    post["category"] = cat
    post["category_version"] = "v1.0"
    post["last_tagged_at"] = datetime.utcnow().isoformat() + "Z"
    post.metadata["tags"] = post.metadata.get("tags", []) + [cat]
    post.save(path)


def main(rerun_all=False, fix_missing=False, check=False, diff=False):
    """Main CLI function"""
    if not FRONTMATTER_AVAILABLE:
        print(
            "Error: frontmatter library required. Install with: pip install python-frontmatter"
        )
        return

    categories = load_categories()
    md_files = glob("output/**/*.md", recursive=True)
    for f in md_files:
        post = frontmatter.load(f)
        exists = "category" in post.metadata
        if rerun_all or (fix_missing and not exists):
            categorize_file(f, categories)
        elif check:
            new_cat = choose_category(post.content, categories)
            if diff and new_cat != post.metadata.get("category"):
                print(f"[DIFF] {f}: {post.metadata.get('category')} -> {new_cat}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rerun-all", action="store_true")
    parser.add_argument("--fix-missing", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--diff", action="store_true")
    args = parser.parse_args()
    main(**vars(args))
