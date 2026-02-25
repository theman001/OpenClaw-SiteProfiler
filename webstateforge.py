import asyncio
import hashlib
import json
import requests
import numpy as np
import time
import os
from playwright.async_api import async_playwright

# ==========================
# 설정
# ==========================

MAX_STATES = 30
HEADLESS = True

OLLAMA_URL = "https://api.ollama.com/v1/chat/completions"
API_KEY = "YOUR_OLLAMA_API_KEY"

LIGHT_MODEL = "qwen2.5:3b"
HEAVY_MODEL = "qwen2.5:14b"

MAX_RETRIES = 3
BACKOFF_BASE = 2

CACHE_FILE = "ollama_cache.json"

DANGEROUS_KEYWORDS = ["delete", "remove", "logout", "sign out", "탈퇴", "삭제"]

ACTION_PRIORITY = {
    "submit_auth": 10,
    "open_list": 8,
    "open_detail": 7,
    "submit_form": 6,
    "paginate_next": 3
}

# ==========================
# 캐시 로드
# ==========================

if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        CACHE = json.load(f)
else:
    CACHE = {}

def save_cache():
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(CACHE, f, indent=2)

def make_cache_key(model, prompt):
    key_raw = model + prompt
    return hashlib.sha256(key_raw.encode()).hexdigest()


# ==========================
# Ollama 호출 (캐시 + 재시도)
# ==========================

def call_ollama(model, prompt):

    cache_key = make_cache_key(model, prompt)

    # 🔥 캐시 히트
    if cache_key in CACHE:
        return CACHE[cache_key]

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a deterministic web UI structure analyzer."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0,
        "top_p": 0.1
    }

    # 🔥 재시도 로직
    for attempt in range(MAX_RETRIES):
        try:
            res = requests.post(OLLAMA_URL, headers=headers, json=payload, timeout=30)

            if res.status_code == 200:
                result = res.json()["choices"][0]["message"]["content"]

                CACHE[cache_key] = result
                save_cache()

                return result

            else:
                print(f"API 오류 {res.status_code}, 재시도 {attempt+1}")

        except Exception as e:
            print(f"API 호출 실패: {e}, 재시도 {attempt+1}")

        sleep_time = BACKOFF_BASE ** attempt
        time.sleep(sleep_time)

    raise Exception("Ollama API 호출 실패 (최대 재시도 초과)")


# ==========================
# Feature Vector
# ==========================

async def extract_features(page):
    return {
        "password_input": await page.locator("input[type='password']").count() > 0,
        "text_input_count": await page.locator("input[type='text']").count(),
        "textarea_count": await page.locator("textarea").count(),
        "file_input": await page.locator("input[type='file']").count() > 0,
        "button_count": await page.locator("button").count(),
        "table_count": await page.locator("table").count(),
        "pagination": await page.locator("a:has-text('Next')").count() > 0,
        "search_like_input": await page.locator("input[placeholder*='search' i]").count() > 0,
        "form_count": await page.locator("form").count()
    }


# ==========================
# 상태 분류
# ==========================

def rule_classify(features):

    if features["password_input"]:
        return "authentication"

    if features["table_count"] > 0 and features["pagination"]:
        return "list_view"

    if features["textarea_count"] > 0 and features["form_count"] > 0:
        return "create_or_edit_form"

    if features["search_like_input"]:
        return "search_view"

    if features["button_count"] > 5:
        return "dashboard"

    return "unknown"


def light_ai_classify(features):

    prompt = f"""
상태 타입 하나만 선택:
authentication / dashboard / list_view / detail_view / search_view / create_or_edit_form / settings / unknown

규칙:
1. password_input true → authentication
2. table_count>0 & pagination → list_view
3. 모호 → unknown

JSON 형식:
{{"state_type":"..."}}

{features}
"""

    try:
        result = call_ollama(LIGHT_MODEL, prompt)
        parsed = json.loads(result)
        return parsed.get("state_type", "unknown")
    except:
        return "unknown"


# ==========================
# 행동 일반화
# ==========================

def generalize_actions(features):

    actions = []

    if features["password_input"]:
        actions.append("submit_auth")

    if features["table_count"] > 0:
        actions.append("open_detail")

    if features["pagination"]:
        actions.append("paginate_next")

    if features["textarea_count"] > 0:
        actions.append("submit_form")

    return sorted(actions, key=lambda x: ACTION_PRIORITY.get(x, 0), reverse=True)


# ==========================
# 탐색
# ==========================

async def explore(start_url):

    visited = []
    state_graph = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(start_url)
        await page.wait_for_load_state("networkidle")

        input("로그인 완료 후 Enter: ")

        while len(state_graph) < MAX_STATES:

            features = await extract_features(page)

            state_type = rule_classify(features)
            if state_type == "unknown":
                state_type = light_ai_classify(features)

            duplicate = any(
                np.dot(list(features.values()), list(s["features"].values()))
                / (np.linalg.norm(list(features.values())) * np.linalg.norm(list(s["features"].values())) + 1e-8)
                > 0.8
                for s in visited
            )

            if duplicate:
                break

            actions = generalize_actions(features)

            state_data = {
                "state_type": state_type,
                "features": features,
                "actions": actions
            }

            visited.append(state_data)
            state_graph.append(state_data)

            buttons = await page.query_selector_all("button")

            for btn in buttons[:5]:
                try:
                    text = await btn.inner_text()
                    if any(k in text.lower() for k in DANGEROUS_KEYWORDS):
                        continue
                    await btn.click(timeout=1500)
                    await page.wait_for_timeout(1500)
                except:
                    continue

        await browser.close()

    return state_graph


# ==========================
# DSL 생성
# ==========================

def generate_dsl(state_graph):

    prompt = f"""
입력 데이터 기반으로만 Markdown DSL 생성.
창작 금지.

{json.dumps(state_graph, indent=2)}
"""

    return call_ollama(HEAVY_MODEL, prompt)


# ==========================
# 메인
# ==========================

async def main():

    start_url = input("URL 입력: ")

    graph = await explore(start_url)

    with open("state_graph.json", "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)

    print("상태 그래프 저장 완료")

    if input("DSL 생성할까요? (y/n): ") == "y":
        dsl = generate_dsl(graph)
        with open("site_profile.md", "w", encoding="utf-8") as f:
            f.write(dsl)
        print("DSL 생성 완료")


if __name__ == "__main__":
    asyncio.run(main())
