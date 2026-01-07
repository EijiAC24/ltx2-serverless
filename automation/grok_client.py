"""
Grok API Client for generating LTX-2 prompts
"""

import json
import requests
from typing import List, Dict, Optional
from config import GROK_API_KEY, GROK_BASE_URL, GROK_MODEL

SYSTEM_PROMPT = """You are an expert at writing prompts for LTX-2 video generation AI.

Follow these rules strictly:
1. Write in English only
2. Use present tense for actions
3. Structure: Shot setup -> Scene -> Action -> Character -> Camera work
4. For dialogue: use quotes and specify accent (e.g., speaking in British accent, "Hello there")
5. Keep to 1-2 actions maximum
6. NEVER use "no text", "no subtitles" or similar - this causes text to appear
7. NEVER use negative phrases
8. Avoid specific location names that might trigger text (Tokyo, NYC, etc.)
9. Keep it cinematic and visual

Good example:
"Close-up of an orange tabby cat sitting on a modern kitchen counter in warm morning sunlight. The cat stares directly into camera with an intense judgmental expression and speaks in a deadpan British accent, 'I know what you did last night.' The cat slowly blinks with smug satisfaction. The camera slowly pushes in on the cat's face. Shallow depth of field, cinematic lighting, comedic tone."

Return ONLY valid JSON array of prompts, no other text."""


def generate_prompts(
    category: str,
    count: int = 5,
    style: Optional[str] = None,
    include_dialogue: bool = False,
) -> List[Dict]:
    """
    Generate video prompts using Grok API

    Args:
        category: Theme category (pets, vintage, nature, etc.)
        count: Number of prompts to generate
        style: Visual style (cinematic, documentary, etc.)
        include_dialogue: Whether to include spoken dialogue

    Returns:
        List of prompt dictionaries with 'prompt' and 'caption' keys
    """

    if not GROK_API_KEY:
        raise ValueError("GROK_API_KEY not set")

    user_message = f"""Generate {count} unique LTX-2 video prompts.

Category: {category}
Style: {style or "cinematic"}
Include dialogue: {"yes" if include_dialogue else "no"}

Return as JSON array:
[
  {{"prompt": "full prompt text", "caption": "short social media caption", "hashtags": ["tag1", "tag2"]}}
]"""

    response = requests.post(
        f"{GROK_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {GROK_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROK_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.8,
        },
        timeout=60,
    )

    response.raise_for_status()
    result = response.json()

    content = result["choices"][0]["message"]["content"]

    # Parse JSON from response
    # Handle potential markdown code blocks
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    prompts = json.loads(content.strip())

    # Validate structure
    validated = []
    for p in prompts:
        if isinstance(p, dict) and "prompt" in p:
            validated.append({
                "prompt": p.get("prompt", ""),
                "caption": p.get("caption", ""),
                "hashtags": p.get("hashtags", []),
                "category": category,
            })

    return validated


def generate_prompt_batch(categories: List[str], count_per_category: int = 2) -> List[Dict]:
    """Generate prompts for multiple categories"""
    all_prompts = []

    for category in categories:
        try:
            prompts = generate_prompts(category, count_per_category)
            all_prompts.extend(prompts)
            print(f"Generated {len(prompts)} prompts for '{category}'")
        except Exception as e:
            print(f"Error generating prompts for '{category}': {e}")

    return all_prompts


if __name__ == "__main__":
    # Test
    import os
    os.environ["GROK_API_KEY"] = os.environ.get("GROK_API_KEY", "")

    prompts = generate_prompts("cute animals", count=2, include_dialogue=True)
    for i, p in enumerate(prompts, 1):
        print(f"\n--- Prompt {i} ---")
        print(f"Prompt: {p['prompt'][:100]}...")
        print(f"Caption: {p['caption']}")
        print(f"Hashtags: {p['hashtags']}")
