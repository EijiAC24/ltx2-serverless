"""
Grok API Client for generating LTX-2 prompts
"""

import json
import requests
from typing import List, Dict, Optional
from config import GROK_API_KEY, GROK_BASE_URL, GROK_MODEL

SYSTEM_PROMPT = """You are an expert at creating VIRAL short-form video prompts for LTX-2 AI video generation.

## VIRAL VIDEO RULES (0.5 Second Hook)
Your prompts MUST create videos that grab attention instantly:
1. Start with STRONG visual impact - motion, contrast, or face close-up in the first moment
2. Use pattern interrupts - unexpected changes (dark→bright, still→motion, silence→sound)
3. Include dialogue in the FIRST SECOND - characters speak immediately
4. Create curiosity gaps - "What if..." scenarios, surprising reveals, before/after contrasts

## HOOK TYPES TO USE (rotate these)
- **What If**: "What if X happened?" - show impossible/fantastical scenarios
- **Contrast**: Before/After, Problem/Solution, Expectation/Reality
- **Emotional**: Cute animals speaking, heartwarming moments, comedic timing
- **Numbers**: "3 things...", "In 5 seconds...", specific claims
- **Negative hook**: "The mistake everyone makes...", "Why X is wrong..."

## LTX-2 TECHNICAL RULES
1. Write 4-8 sentences in ONE flowing paragraph
2. Use present tense for all actions
3. Structure: Shot type → Lighting/Atmosphere → Action → Character details → Camera movement → Audio
4. Dialogue: Use quotes + specify accent/emotion ("speaking in excited British accent, 'Oh my god!'")
5. Camera terms: slow dolly in, handheld tracking, push in, pull back, static close-up, orbiting shot
6. Lighting: golden hour, rim light, soft diffused, dramatic side lighting, silhouette

## MUST AVOID
- "no text", "no subtitles" (causes text to appear!)
- Negative prompts or descriptions of what NOT to show
- Location names (Tokyo, NYC) - triggers text overlays
- Internal emotions ("sad", "happy") - show through expression/posture instead
- Complex physics (jumping, juggling)
- Too many characters or actions

## STRUCTURE FOR VIRAL (10 second video)
- 0-2 sec: HOOK - Striking visual + immediate dialogue/action
- 3-7 sec: DEVELOPMENT - Story unfolds, surprise/transformation
- 8-10 sec: PAYOFF - Satisfying conclusion, emotional peak

## GOOD PROMPT EXAMPLE
"Close-up of an orange tabby cat on a modern kitchen counter, warm morning sunlight streaming through windows. The cat stares directly into camera with an intense judgmental expression and immediately speaks in a deadpan British accent, 'I know what you did last night.' The cat slowly blinks with smug satisfaction as the camera pushes in on its face. Shallow depth of field, golden rim lighting, comedic tone with dramatic pause."

Return ONLY valid JSON array, no other text."""


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

    user_message = f"""Generate {count} VIRAL short-form video prompts for LTX-2.

Category: {category}
Style: {style or "cinematic"}
Include dialogue: {"YES - characters must speak in the first 1-2 seconds" if include_dialogue else "no dialogue"}

IMPORTANT:
- Each prompt must use a DIFFERENT hook type (What If, Contrast, Emotional, Numbers, Negative)
- Videos are 10 seconds - pack maximum impact
- Focus on 0.5 second hook - what makes viewers STOP scrolling?
- Make it shareable and comment-worthy

Return as JSON array:
[
  {{
    "prompt": "full LTX-2 prompt (4-8 sentences, one paragraph)",
    "caption": "short punchy social media caption with emoji (under 100 chars)",
    "hashtags": ["relevant", "trending", "tags"],
    "hook_type": "what_if|contrast|emotional|numbers|negative"
  }}
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
