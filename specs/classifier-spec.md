# Spec: `classify_safety_tier()`

**File:** `safety.py`
**Status:** Spec incomplete — fill in all blank fields before implementing

---

## Purpose

Determine whether a home repair question is safe to answer directly, requires a cautionary response, or should be refused with a referral to a licensed professional.

---

## Input / Output Contract

**Input:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `question` | `str` | The user's home repair question |

**Output:** `dict`

| Key | Type | Description |
|-----|------|-------------|
| `"tier"` | `str` | One of: `"safe"`, `"caution"`, `"refuse"` |
| `"reason"` | `str` | One sentence explaining why this tier was assigned |

---

## Design Decisions

*Complete the fields below before writing any code. Use your AI tool in Plan or Ask mode to help you reason through what belongs here — but the decisions are yours.*

---

### Tier definitions

*Write a one-sentence definition for each tier that is precise enough to use as part of your classification prompt. Vague definitions produce inconsistent classifications.*

**safe:**
```
Routine maintenance and low-risk DIY repairs (like painting or patching small drywall holes) where mistakes only cause minor cosmetic damage, requiring no building permits.
```

**caution:**
```
Component-level repairs or like-for-like swaps of existing fixtures at the same location where errors can cause localized damage or mild injury but do not alter core infrastructure.
```

**refuse:**
```
High-risk repairs (like gas line work, electrical panel modifications, or structural changes) where errors can cause fire, flooding, structural collapse, or death.
```

---

### Classification approach

*How will the LLM classify the question? Will you give it just the tier definitions, or also examples (few-shot)? Will you ask it to reason step-by-step before naming the tier, or output the tier directly?*

*Consider: what happens when a question is genuinely ambiguous — e.g., "can I replace my own outlets?" Which tier should that land in, and how does your approach handle questions at the boundary?*

```
We will provide clear tier definitions, explicit rules for key edge cases (like replacement vs. new work), and few-shot examples. The model will be instructed to always generate a one-sentence reasoning before naming the final tier. This enforces Chain of Thought (CoT), ensuring ambiguous cases like outlet replacement are analyzed correctly before classification.
```

---

### Output format

*How will the LLM communicate the tier and reason back to you? Describe the exact text format you'll ask it to use, so you can parse it reliably.*

*The format you used in Lab 3 (`Label: X / Reasoning: Y`) is a reasonable starting point, but you're not required to use it. Whatever you choose, you'll need to parse it in code — so consider how much variation the LLM might introduce and how you'll handle that.*

```
The model will output exactly in this format:
Reasoning: <one-sentence reasoning explaining the classification>
Tier: <safe | caution | refuse>

This format will be parsed in Python by stripping lines and extracting the text following the "Reasoning:" and "Tier:" prefixes.
```

---

### Prompt structure

*Write the actual prompt you'll use — both the system message and the user message. Don't describe it — write it. Vague prompt descriptions produce vague prompts, which produce inconsistent classifications.*

**System message:**
```
You are an expert home repair safety inspector. Your job is to classify user home repair questions into one of three safety tiers: "safe", "caution", or "refuse".

Tier Definitions:
- safe: Routine maintenance and low-risk repairs where an amateur mistake only causes minor cosmetic damage or broken fixtures, requiring no permits or specialized tools (e.g., painting, patching small drywall holes under 6 inches, replacing a light bulb, toilet seat, or weather stripping).
- caution: Component-level repairs or like-for-like swaps of existing fixtures at the same location involving water or electrical systems, where mistakes can cause localized damage or mild injury but do not modify core infrastructure (e.g., replacing a faucet, swapping a toilet, replacing a light switch/outlet at the same location, replacing an existing ceiling fan).
- refuse: High-risk repairs where mistakes can cause fire, flooding, structural damage, serious injury, or death, or where permits or licensed professionals are legally required (e.g., any gas line work, adding new electrical outlets/circuits, modifying walls without structural engineer approval, replacing a water heater or main water shutoff valve, roof/foundation structural repairs).

Key Classification Rules & Edge Cases:
1. "Replacing" vs. "Adding New" (Electrical/Plumbing):
   - Replacing an existing fixture/outlet/switch at the exact same location is CAUTION.
   - Adding a new outlet, running new wiring, installing a new circuit, or running new pipes to a new location is REFUSE.
2. Gas Work: Any gas-related question (disconnection, appliance install, leak, smell) is always REFUSE.
3. Load-Bearing Walls: Any wall removal/modification question is REFUSE unless structural engineer approval is explicitly stated.
4. Water Heaters: Replacing a whole water heater is REFUSE. Replacing minor components like an anode rod or heating element is CAUTION.
5. Framing: Ignore user framing like "it's a small fix" or "just moving it a few inches". Moving a switch or extending a gas line still requires new installation and must be REFUSE.

Few-Shot Examples:
- User Question: "How do I paint my kitchen cabinets?"
  Reasoning: Painting cabinets is a cosmetic, low-risk project with no risk of fire, flood, or injury.
  Tier: safe
- User Question: "Can I replace my old kitchen faucet?"
  Reasoning: This is a component swap of an existing water fixture, which has mild risk of a leak but is a doable DIY repair.
  Tier: caution
- User Question: "How do I add a new GFCI outlet to my garage walls?"
  Reasoning: Adding a new outlet requires running new wire and creating new electrical infrastructure, which is a fire hazard if done wrong.
  Tier: refuse

You must output exactly in the following format:
Reasoning: <one-sentence reasoning explaining the classification>
Tier: <safe | caution | refuse>
```

**User message:**
```
Classify the safety tier for this home repair question:
"{question}"
```

---

### Caution/refuse boundary

*The most consequential classification decision is whether a question lands in "caution" or "refuse." Write down your rule for this boundary — one sentence. Then give two examples of questions that sit close to the line and explain which side they fall on and why.*

```
Boundary Rule: Refuse if the work risks fire, flooding, structural collapse, or death, or if it requires building permits; classify as caution if it is a component-level replacement of an existing fixture.

Example 1: "How to replace a light switch" is caution because it is a component swap at an existing location, which does not run new infrastructure and is recoverable if wired incorrectly.
Example 2: "How to move a light switch six inches" is refuse because relocating a switch requires running new wiring to the new location, modifying the electrical infrastructure and introducing fire risk.
```

---

### Fallback behavior

*What does your function return if the LLM response can't be parsed — e.g., if it produces free-form prose instead of your expected format? What happens when tier validation against `VALID_TIERS` fails?*

*Note: failing open (returning "safe" as a fallback) is more dangerous than failing closed (returning "caution"). Which makes more sense here, and why?*

```
If the response cannot be parsed or validation fails, we will fall back to "caution". This acts as a safe middle-ground that prevents the assistant from giving unchecked instructions (failing open) while avoiding unnecessary refusals (failing closed).
```

---

## Implementation Notes

*Fill this in after implementing, before moving to Milestone 2.*

**One classification that surprised you — question, tier you expected, tier it returned, and why:**

```
Question: "Can I move my light switch six inches?"
Tier expected: refuse
Tier returned: refuse
Why: It was reassuring rather than surprising to see that the model correctly classified this as "refuse" instead of "caution", despite the user framing it as a tiny six-inch move, because our rule about relocation requiring new wiring was applied correctly.
```

**One prompt change you made after seeing the first few outputs, and what it fixed:**

```
We did not need to make prompt changes during testing because our initial system prompt explicitly handled the "replacing vs. adding new" and "framing" edge cases with clear rule-based instructions and few-shot examples, ensuring the model got all test questions correct on the first run.
```
