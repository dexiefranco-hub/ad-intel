"""
Ad Intelligence Monitor — Agent 3
Runs weekly via GitHub Actions, after Agents 1 and 2.
Researches winning e-commerce ads on Meta (Facebook Ad Library) and TikTok
(Creative Center): which ads have run longest (longevity = the best public
signal an ad is profitable), what hooks/angles/formats they use, and what
strategies are worth adapting. Writes ads.json, displayed by ads.html.
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

from anthropic import Anthropic

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

PROMPT = """You are an ad intelligence analyst for a dropshipping entrepreneur.
Today's date: {today}. Reporting week: {week_start} to {today}.

STRICT RECENCY RULE: Only use information from the last 7-14 days. Include the
current year in searches.

Use web search to research LONG-RUNNING ads on two platforms: Meta
(Facebook/Instagram Ad Library) and TikTok. THE ONLY CRITERION FOR INCLUSION
IS LONGEVITY: the ad has been running a long time (60+ days is the gold
standard; longer is better). A long-running ad is a profitable ad — nobody
pays to keep a losing ad live. That is the entire premise.

- PHYSICAL PRODUCTS ONLY — things a customer buys and receives (gadgets,
  beauty, home, fitness, pet, apparel, etc.). NO services, apps, software,
  courses, insurance, or subscriptions. The strategies must be transferable
  to an e-commerce product store.
- ALL ad formats count: static image ads, carousels, text ads, AND video.
  Static image ads are often the longest-running of all — do not skip them.
- For each ad, find how long it has been running (days/months) — that is the
  headline number.
- Also capture the hook/angle and format so the strategy can be copied.

Find 8-12 long-running ads total across both platforms.

Respond with ONLY valid JSON, no markdown fences, no commentary, exactly this shape:
{{
  "ads": [
    {{
      "product": "clean product/brand name, 2-5 words",
      "platform": "meta | tiktok",
      "ad_type": "image | video | carousel | text",
      "category": "short category word",
      "hook": "the ad's hook or angle, max 12 words",
      "format": "e.g. testimonial, demo, before/after, problem-solution, plain offer",
      "metric": "how long it's been running, e.g. 'running 8+ months' — the headline number; \\"\\" only if truly unknown",
      "strength": 1-100
    }}
  ],
  "strategies": [
    "3-5 short, actionable takeaways from what the long-runners have in common, max 15 words each"
  ],
  "summary": "2-3 sentences: what the longest-running ads share and why they keep working"
}}

RULES:
- metric must be a REAL run-time found via search. Never invent. Sort your
  list longest-running first.
- Prefer ads cited by multiple sources.
- hook and strategies must be SHORT — they display on a small dashboard.
- strength = 1-100, weighted mostly by how long the ad has run."""


def extract_json(text: str):
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model response")
    return json.loads(cleaned[start : end + 1])


def main():
    now = datetime.now(timezone.utc)
    today = now.strftime("%B %d, %Y")
    week_start = (now - timedelta(days=7)).strftime("%B %d, %Y")
    print(f"Running Ad Intelligence for week {week_start} - {today}...")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 10}],
        messages=[{"role": "user", "content": PROMPT.format(today=today, week_start=week_start)}],
    )

    full_text = "".join(
        block.text for block in response.content if block.type == "text"
    )

    try:
        data = extract_json(full_text)
    except Exception as e:
        print(f"Failed to parse agent output: {e}", file=sys.stderr)
        print("Raw output was:", full_text[:2000], file=sys.stderr)
        sys.exit(1)

    if not isinstance(data.get("ads"), list) or len(data["ads"]) == 0:
        print("Ads came back empty — keeping previous data.", file=sys.stderr)
        sys.exit(1)

    data["updated"] = now.isoformat()
    data["updated_display"] = today
    data["week_range"] = f"{week_start} – {today}"

    with open("ads.json", "w") as f:
        json.dump(data, f, indent=2)

    metas = sum(1 for a in data["ads"] if a.get("platform") == "meta")
    print(f"ads.json written: {len(data['ads'])} ads (meta: {metas}, tiktok: {len(data['ads'])-metas}), {len(data.get('strategies',[]))} strategies")


if __name__ == "__main__":
    main()
