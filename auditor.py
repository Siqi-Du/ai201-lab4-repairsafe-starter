import json
import os
from datetime import datetime, timezone
from config import LOG_FILE, LLM_MODEL


def log_interaction(question: str, tier: str, response: str) -> None:
    """
    Append a structured record of this interaction to the audit log.

    Each record should be a JSON object written as a single line to LOG_FILE
    (defined in config.py as "logs/audit.jsonl").

    Required fields:
      - "timestamp"        : ISO 8601 datetime string
      - "tier"             : the safety tier assigned to this question
      - "question"         : the user's question (truncate to 300 chars if longer)
      - "response_preview" : first 200 characters of the response
      - "model"            : the LLM model used
      - "response_length"  : the length of the full response

    If the logs/ directory doesn't exist, create it before writing.

    Also print a one-line summary to the terminal so you can see logged
    interactions in real time without opening the file:
      e.g. [LOGGED] tier=caution | "How do I replace a faucet?" -> 47 chars
    """
    # Create logs/ directory if it doesn't exist
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # Format timestamp
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Prepare log entry
    entry = {
        "timestamp": timestamp,
        "tier": tier,
        "question": question[:300] if len(question) > 300 else question,
        "response_preview": response[:200] if len(response) > 200 else response,
        "model": LLM_MODEL,
        "response_length": len(response)
    }

    # Append to LOG_FILE as a single line (JSONL format)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    # Print a one-line summary to the terminal
    truncated_question = question[:40] + "..." if len(question) > 40 else question
    print(f'[LOGGED] tier={tier} | "{truncated_question}" -> {len(response)} chars')
