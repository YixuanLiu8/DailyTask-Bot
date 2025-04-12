import os
import openai
import requests
import json
from datetime import date,datetime
from dotenv import load_dotenv


today = date.today()
if today.weekday() >= 5:
    print("🛌 Weekend – skipping daily plan.")
    exit()


# 🔧 Load env & config
load_dotenv(dotenv_path="/Users/sandy/dailyTask_bot/.env")

openai.api_key = os.getenv("OPENAI_API_KEY")

with open("/Users/sandy/dailyTask_bot/launchd_test_result.txt", "a") as f:
    f.write(f"[{datetime.now()}] ✅ launchd ran main.py\n")

with open(os.path.join(os.path.dirname(__file__), "log.txt"), "a") as f:
    f.write(f"[{datetime.now()}] ✅ Plan generator ran\n")

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
TRACKER_PAGE_ID = os.getenv("TRACKER_PAGE_ID")
PAGE_PARENT_ID = os.getenv("PAGE_PARENT_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

with open(os.path.join(os.path.dirname(__file__), "period_config.json")) as f:
    period_cfg = json.load(f)

def check_and_update_period_from_tracker(page_id):
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    res = requests.get(url, headers=headers)
    blocks = res.json().get("results", [])

    confirmed = False
    new_start_date = None
    checkbox_block_id = None

    for block in blocks:
        if block["type"] == "to_do" and "Confirmed Period Start" in block["to_do"]["rich_text"][0]["text"]["content"]:
            confirmed = block["to_do"]["checked"]
            checkbox_block_id = block["id"]

        if block["type"] == "paragraph":
            rich_text = block["paragraph"].get("rich_text", [])
            if rich_text and "Start Date:" in rich_text[0]["text"]["content"]:
                new_start_date = rich_text[0]["text"]["content"].split("Start Date:")[1].strip()


    if confirmed and new_start_date:
        period_cfg["last_confirmed_start"] = new_start_date
        with open(os.path.join(os.path.dirname(__file__), "period_config.json"), "w") as f:
            json.dump(period_cfg, f, indent=4)

        print("🩸 Period confirmed for:", new_start_date)

        # 取消勾选
        patch_url = f"https://api.notion.com/v1/blocks/{checkbox_block_id}"
        patch_payload = {
            "to_do": {
                "rich_text": [{"type": "text", "text": {"content": "Confirmed Period Start"}}],
                "checked": False
            }
        }
        requests.patch(patch_url, headers=headers, json=patch_payload)
        return True
    return False

# 🧠 判断状态
today = date.today()
today_str = today.strftime('%B %d, %Y')

confirmed = check_and_update_period_from_tracker(TRACKER_PAGE_ID)
days_since = (today - date.fromisoformat(period_cfg["last_confirmed_start"])).days
is_period_day = confirmed or days_since < period_cfg["period_length"]

# ✨ Prompt
if is_period_day:
    print("🩸 Period mode active – gentle prompt used.")
    prompt = f"""
🩸 Period Mode · Light flow + gentle focus

Create a kind and soft daily plan for Sandy on {today_str}.
Include:
- At most 6 total items
- 2-3 small learning or work-related tasks
- 1-2 self-care or relaxing tasks
- Friendly tone with emoji

Format:
09:30 – Watch 15-min CyberSec video ☁️  
11:00 – Stretch or light yoga 🧘‍♀️  
13:00 – 1 Leetcode easy 🧠  
...

"""
else:
    prompt = f"""
Create a focused but balanced daily plan for Sandy on {today_str}.
Limit to 6–7 items: job searching, studying, journaling, light exercise.
Use emoji for clarity and friendliness.
09:00 – Resume review ✨  
09:45 – 1 Leetcode SQL 🧠  
11:00 – CyberSec course 30min 🔐  
13:00 – 20-min walk 🌿  
...

"""

# 🤖 Ask GPT
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": prompt}]
)

plan_text = response['choices'][0]['message']['content']
print("📋 Generated Plan:\n", plan_text)

# 🧱 Convert to Notion blocks
blocks = []
for line in plan_text.strip().split('\n'):
    if line.strip():
        blocks.append({
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"type": "text", "text": {"content": line.strip()}}],
                "checked": False
            }
        })

# ➕ Add Confirm block at top
period_mode_block = {
    "object": "block",
    "type": "to_do",
    "to_do": {
        "rich_text": [{
            "type": "text",
            "text": {"content": "Period Mode"}
        }],
        "checked": is_period_day
    }
}
blocks.insert(0, period_mode_block)

# 📄 Create Notion page
payload = {
    "parent": {"type": "page_id", "page_id": PAGE_PARENT_ID},
    "properties": {
        "title": [{"type": "text", "text": {"content": f"🗓️ {today_str} Plan"}}]
    },
    "children": blocks
}

res = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
if res.status_code in [200, 201]:
    print("✅ Page created successfully!")

else:
    print("❌ Error creating page:", res.status_code, res.text)

#test
# from datetime import datetime
# with open("/Users/sandy/dailyTask_bot/launchd_test_result.txt", "a") as f:
#     f.write(f"[{datetime.now()}] ✅ launchd ran main.py\n")

