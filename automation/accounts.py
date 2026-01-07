"""
Account configurations for multi-account support
Add new accounts here as needed
"""

ACCOUNTS = {
    "anachronism": {
        "name": "Anachronism (時代錯誤)",
        "theme": """Anachronism - modern technology in historical settings.

## MAXIMUM IMPACT RULE
The humor must be INSTANTLY obvious within 0.5 seconds. No thinking required.

## USE ONLY THESE (universally recognized)
Historical figures:
- Samurai (Japanese warrior with katana, armor)
- Medieval knight (full plate armor, helmet)
- Roman soldier/gladiator (helmet, shield, toga)
- Egyptian pharaoh (gold headdress, eyeliner)
- Caveman/primitive human (fur clothes, club, beard)
- Viking (horned helmet, beard, axe)
- Ancient Greek warrior (Spartan helmet, spear)

Modern devices (everyone knows these):
- iPhone/smartphone (glowing screen)
- VR headset (Meta Quest style)
- Drone (flying, buzzing)
- Robot vacuum (Roomba moving on floor)
- Tesla (doors opening like wings)
- AirPods/wireless earbuds
- Laptop/MacBook
- Electric scooter

## REACTIONS MUST BE BIG AND PHYSICAL
NOT: confused, perplexed, curious (too subtle)
YES:
- Stumbling backwards in shock
- Falling to knees in awe
- Trying to attack it with weapon
- Running away in terror
- Bowing to it like a god
- Jaw dropping, eyes bulging

## HIGH IMPACT EXAMPLES
- Caveman sees Roomba moving → runs away screaming, hides behind rock
- Samurai vs drone → draws katana, takes battle stance, tries to slice it
- Roman emperor puts on VR → sees modern city, staggers back in disbelief
- Knight sees Tesla doors open → drops sword, falls to knees thinking it's magic
- Pharaoh discovers iPhone flashlight → holds it up like divine artifact

## AVOID
- Subtle or "artistic" scenarios
- Obscure historical periods
- Small/unclear reactions
- Any dialogue""",
        "style": "cinematic vintage film aesthetic, warm lighting, shallow depth of field",
        "sheet_name": "prompts",
        "later_profile_id": "",  # Set via env: LATER_PROFILE_ID_ANACHRONISM
    },
    # Add more accounts here:
    # "cute_pets": {
    #     "name": "Cute Pets",
    #     "theme": "Adorable animals doing unexpected things, talking pets with funny dialogue, cats and dogs in humorous situations",
    #     "style": "warm cozy lighting, shallow depth of field",
    #     "sheet_name": "prompts_pets",
    #     "later_profile_id": "",
    # },
}

DEFAULT_ACCOUNT = "anachronism"


def get_account(account_id: str = None) -> dict:
    """Get account config by ID"""
    account_id = account_id or DEFAULT_ACCOUNT
    if account_id not in ACCOUNTS:
        raise ValueError(f"Unknown account: {account_id}. Available: {list(ACCOUNTS.keys())}")
    return ACCOUNTS[account_id]


def list_accounts() -> list:
    """List all available accounts"""
    return list(ACCOUNTS.keys())
