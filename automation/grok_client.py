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
3. Create curiosity gaps - "What if..." scenarios, surprising reveals, before/after contrasts
4. Focus on VISUAL storytelling - the humor/impact should be obvious without explanation

## HOOK TYPES TO USE (rotate these)
- **What If**: "What if X happened?" - show impossible/fantastical scenarios
- **Contrast**: Before/After, Problem/Solution, Expectation/Reality
- **Emotional**: Cute animals, heartwarming moments, comedic timing
- **Numbers**: "3 things...", "In 5 seconds...", specific claims
- **Negative hook**: "The mistake everyone makes...", "Why X is wrong..."

## LTX-2 TECHNICAL RULES
1. Write 4-8 sentences in ONE flowing paragraph
2. Use present tense for all actions
3. Structure: Shot type → Lighting → Action → Character → Camera movement → Sound

## CAMERA INSTRUCTIONS (be specific)
- Shot types: extreme close-up, medium shot, wide establishing shot, over-the-shoulder
- Camera movement: slow dolly in, smooth tracking shot, push in, pull back, static locked-off, 360 orbit, crane up/down, handheld slight shake
- Focus: shallow depth of field with bokeh, rack focus between subjects, deep focus
- Speed: slow motion 0.5x, normal speed, slight speed ramp

## LIGHTING & ATMOSPHERE
- Natural: golden hour warm glow, overcast soft diffused, harsh midday sun, blue hour twilight
- Artificial: rim light from behind, dramatic side lighting, soft key light, practical lights in frame
- Mood: high contrast cinematic, low-key moody, bright and airy, warm nostalgic film grain

## SOUND DESIGN (always include)
- Ambient: room tone, wind, crowd murmur, nature sounds, city ambience
- Effects: whoosh, impact, reveal sting, comedic timing beat, dramatic bass drop
- Music mood: tense underscore, whimsical playful, epic orchestral swell, lo-fi chill

## MUST AVOID
- "no text", "no subtitles" (causes text to appear!)
- Negative prompts or descriptions of what NOT to show
- Internal emotions ("sad", "happy") - show through expression/posture instead
- Complex physics (jumping, juggling, throwing/catching)
- Too many characters or simultaneous actions

## STRUCTURE FOR VIRAL (10 second video)
- 0-2 sec: HOOK - Striking visual that stops the scroll
- 3-7 sec: DEVELOPMENT - Story unfolds, surprise/transformation
- 8-10 sec: PAYOFF - Satisfying conclusion, emotional peak

## GOOD PROMPT EXAMPLE
"Extreme close-up of an orange tabby cat on a modern kitchen counter, golden hour sunlight streaming through windows creating warm lens flares. Shallow depth of field with creamy bokeh background. The cat stares directly into camera with an intense judgmental expression, whiskers twitching slightly. Camera slowly pushes in on its face as dramatic orchestral sting plays. Ambient kitchen sounds, refrigerator hum, then sudden silence for comedic beat. Film grain texture, cinematic 2.39:1 aspect ratio feel."

Return ONLY valid JSON array, no other text."""


def generate_prompts(
    count: int = 1,
    style: Optional[str] = None,
    include_dialogue: bool = False,
    theme: Optional[str] = None,
    past_prompts: Optional[List[str]] = None,
) -> List[Dict]:
    """
    Generate video prompts using Grok API

    Args:
        count: Number of prompts to generate
        style: Visual style (cinematic, documentary, etc.)
        include_dialogue: Whether to include spoken dialogue
        theme: Theme description
        past_prompts: List of past prompts to avoid repetition

    Returns:
        List of prompt dictionaries with 'prompt' and 'caption' keys
    """

    if not GROK_API_KEY:
        raise ValueError("GROK_API_KEY not set")

    theme_instruction = f"Theme: {theme}\n" if theme else ""

    # Build past prompts section
    past_section = ""
    if past_prompts and len(past_prompts) > 0:
        past_list = "\n".join(f"- {p[:150]}..." if len(p) > 150 else f"- {p}" for p in past_prompts[-100:])
        past_section = f"""
PAST PROMPTS (DO NOT REPEAT these concepts, create something NEW and DIFFERENT):
{past_list}

"""

    user_message = f"""Generate {count} VIRAL short-form video prompt(s) for LTX-2.

{theme_instruction}
Style: {style or "cinematic"}
Include dialogue: {"YES - characters must speak in the first 1-2 seconds" if include_dialogue else "no dialogue"}
{past_section}
IMPORTANT:
- Create FRESH concepts not seen in past prompts
- Use DIFFERENT hook type (What If, Contrast, Emotional, Numbers, Negative)
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
                "hook_type": p.get("hook_type", ""),
            })

    return validated


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
