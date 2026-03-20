import os
import sys
import requests
from datetime import datetime, timezone, timedelta

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# 可在 GitHub Variables 裡改
LOBSTER_PROMPT = os.getenv(
    "LOBSTER_PROMPT",
    "請用繁體中文，簡潔整理今天值得注意的3件事，分點列出。"
).strip()

LOBSTER_MODEL = os.getenv("LOBSTER_MODEL", "openrouter/free").strip()


def validate_env():
    missing = []
    if not OPENROUTER_API_KEY:
        missing.append("OPENROUTER_API_KEY")
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHAT_ID:
        missing.append("TELEGRAM_CHAT_ID")

    if missing:
        raise RuntimeError(f"缺少必要環境變數: {', '.join(missing)}")


def ask_llm(prompt: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # 這兩個 header 不是必填，但有助於 OpenRouter 識別你的應用
        "HTTP-Referer": "https://github.com/",
        "X-Title": "free-lobster",
    }

    payload = {
        "model": LOBSTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是一個精準、簡潔的助理。"
                    "輸出使用繁體中文。"
                    "避免空話，重點條列。"
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.5
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=90)
    resp.raise_for_status()

    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )


def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    # 用 HTML parse_mode，比較穩
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text[:4000],  # 預防過長
        "parse_mode": "HTML"
    }

    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()


def main():
    validate_env()

    tw_time = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
    title = tw_time.strftime("%Y-%m-%d %H:%M")

    try:
        answer = ask_llm(LOBSTER_PROMPT)
        message = (
            f"<b>🦞 免費版龍蝦回報</b>\n"
            f"<b>時間：</b>{title}\n"
            f"<b>模型：</b>{escape_html(LOBSTER_MODEL)}\n\n"
            f"{escape_html(answer)}"
        )
        send_telegram(message)
        print("Success: message sent to Telegram.")

    except Exception as e:
        error_text = (
            f"<b>🦞 龍蝦出錯</b>\n"
            f"<b>時間：</b>{title}\n"
            f"<b>錯誤：</b>{escape_html(str(e))}"
        )
        try:
            send_telegram(error_text)
        except Exception:
            pass
        print(f"Error: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
