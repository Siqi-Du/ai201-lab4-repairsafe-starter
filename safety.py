from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL, VALID_TIERS

_client = Groq(api_key=GROQ_API_KEY)


def classify_safety_tier(question: str) -> dict:
    """
    Classify a home repair question into one of three safety tiers.

    Your implementation should:
      1. Build a prompt using your tier definitions that asks the LLM to classify
         the question and explain its reasoning
      2. Send a single chat completion request (no tools, no history)
      3. Parse the tier and reason out of the raw response text
      4. Validate the tier against VALID_TIERS; fall back to "caution" if the
         response can't be parsed or the tier isn't recognized
      5. Return {"tier": ..., "reason": ...}

    Returns a dict with:
      - "tier"   : str — one of "safe", "caution", "refuse"
      - "reason" : str — a brief explanation of why this tier was assigned

    The three tiers:
      - "safe"    : routine, low-risk repairs most homeowners can handle safely
      - "caution" : doable with care, but mistakes have real cost or mild risk
      - "refuse"  : high-risk repairs that require a licensed professional —
                    mistakes can cause fire, flooding, injury, or structural damage
    """
    system_prompt = (
        "You are an expert home repair safety inspector. Your job is to classify user home repair questions into one of three safety tiers: \"safe\", \"caution\", or \"refuse\".\n\n"
        "Tier Definitions:\n"
        "- safe: Routine maintenance and low-risk repairs where an amateur mistake only causes minor cosmetic damage or broken fixtures, requiring no permits or specialized tools (e.g., painting, patching small drywall holes under 6 inches, replacing a light bulb, toilet seat, or weather stripping).\n"
        "- caution: Component-level repairs or like-for-like swaps of existing fixtures at the same location involving water or electrical systems, where mistakes can cause localized damage or mild injury but do not modify core infrastructure (e.g., replacing a faucet, swapping a toilet, replacing a light switch/outlet at the same location, replacing an existing ceiling fan).\n"
        "- refuse: High-risk repairs where mistakes can cause fire, flooding, structural damage, serious injury, or death, or where permits or licensed professionals are legally required (e.g., any gas line work, adding new electrical outlets/circuits, modifying walls without structural engineer approval, replacing a water heater or main water shutoff valve, roof/foundation structural repairs).\n\n"
        "Key Classification Rules & Edge Cases:\n"
        "1. \"Replacing\" vs. \"Adding New\" (Electrical/Plumbing):\n"
        "   - Replacing an existing fixture/outlet/switch at the exact same location is CAUTION.\n"
        "   - Adding a new outlet, running new wiring, installing a new circuit, or running new pipes to a new location is REFUSE.\n"
        "2. Gas Work: Any gas-related question (disconnection, appliance install, leak, smell) is always REFUSE.\n"
        "3. Load-Bearing Walls: Any wall removal/modification question is REFUSE unless structural engineer approval is explicitly stated.\n"
        "4. Water Heaters: Replacing a whole water heater is REFUSE. Replacing minor components like an anode rod or heating element is CAUTION.\n"
        "5. Framing: Ignore user framing like \"it's a small fix\" or \"just moving it a few inches\". Moving a switch or extending a gas line still requires new installation and must be REFUSE.\n\n"
        "Few-Shot Examples:\n"
        "- User Question: \"How do I paint my kitchen cabinets?\"\n"
        "  Reasoning: Painting cabinets is a cosmetic, low-risk project with no risk of fire, flood, or injury.\n"
        "  Tier: safe\n"
        "- User Question: \"Can I replace my old kitchen faucet?\"\n"
        "  Reasoning: This is a component swap of an existing water fixture, which has mild risk of a leak but is a doable DIY repair.\n"
        "  Tier: caution\n"
        "- User Question: \"How do I add a new GFCI outlet to my garage walls?\"\n"
        "  Reasoning: Adding a new outlet requires running new wire and creating new electrical infrastructure, which is a fire hazard if done wrong.\n"
        "  Tier: refuse\n\n"
        "You must output exactly in the following format:\n"
        "Reasoning: <one-sentence reasoning explaining the classification>\n"
        "Tier: <safe | caution | refuse>"
    )

    user_prompt = f'Classify the safety tier for this home repair question:\n"{question}"'

    try:
        response = _client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,
        )
        response_text = response.choices[0].message.content.strip()
    except Exception as e:
        # If API call fails, fall back safely
        return {
            "tier": "caution",
            "reason": f"API call failed: {str(e)}. Falling back to caution."
        }

    # Parse response
    import re
    lines = response_text.splitlines()
    tier_found = None
    reason_found = None

    for line in lines:
        line_stripped = line.strip()
        # Match Tier: ...
        if re.match(r'(?i)^tier\s*:\s*', line_stripped):
            val = re.sub(r'(?i)^tier\s*:\s*', '', line_stripped).strip()
            val = val.strip("\"'").lower()
            if val in VALID_TIERS:
                tier_found = val
        # Match Reasoning: ... or Reason: ...
        elif re.match(r'(?i)^reason(?:ing)?\s*:\s*', line_stripped):
            val = re.sub(r'(?i)^reason(?:ing)?\s*:\s*', '', line_stripped).strip()
            reason_found = val

    # Fallbacks if parsing rules failed
    if not tier_found:
        # scan the whole text for valid tiers
        for t in ["refuse", "caution", "safe"]:
            if re.search(rf'(?i)\b{t}\b', response_text):
                tier_found = t
                break

    if not reason_found:
        # Fallback to the first line if reasoning not found explicitly
        if lines:
            reason_found = lines[0].strip()
        else:
            reason_found = "Failed to parse reasoning."

    # Enforce safe defaults
    tier = tier_found if (tier_found and tier_found in VALID_TIERS) else "caution"
    reason = reason_found if reason_found else "Failed to parse reasoning."

    return {
        "tier": tier,
        "reason": reason
    }

