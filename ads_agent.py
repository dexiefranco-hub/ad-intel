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

Use web search to research WINNING e-commerce ads right now on two platforms:
Meta (Facebook/Instagram Ad Library) and TikTok (Creative Center / top ads).
Key principle: ad LONGEVITY is the best public signal of profitability — an ad
still running after 60+ days is making money. Look for:
- Long-running e-commerce/dropshipping ads and what they sell
- Top-performing TikTok ad creatives and formats right now
- Winning hooks, angles, and creative patterns being reported
- Which product categories are getting heavy ad spend

Find 6-10 winning ads/campaigns total across both platforms.

Respond with ONLY valid JSON, no markdown fences, no commentary, exactly this shape:
{{
  "ads": [
    {{
      "product": "clean product/brand name, 2-5 words",
      "platform": "meta | tiktok",
      "category": "beauty / home / fitness / gadget / pet / other",
      "hook": "the ad's opening hook or angle, max 12 words",
      "format": "e.g. UGC testimonial, demo video, before/after, problem-solution",
      "metric": "real figure, 6 words max, e.g. 'running 90+ days' or '12M views' — never invent; \\"\\" if none",
      "strength": 1-100
    }}
  ],
  "strategies": [
    "3-5 short, actionable takeaways a dropshipper can apply this week, max 15 words each"
  ],
  "summary": "2-3 sentences: what's winning in e-commerce ads right now and why"
}}

RULES:
- metric must be REAL figures found via search (days running, views, engagement). Never invent.
- Prefer ads/patterns cited by multiple sources over one-off mentions.
- hook and strategies must be SHORT — they display on a small dashboard.
- strength = your 1-100 estimate of how proven/strong this ad approach is."""


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
