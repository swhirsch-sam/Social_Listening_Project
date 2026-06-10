#!/usr/bin/env python3
"""Keep a Streamlit Community Cloud app awake.

Streamlit Cloud puts apps to sleep after a stretch without active sessions.
A plain HTTP request is NOT enough to wake or hold one open: a sleeping app
still serves a normal HTTP 200 page containing a JavaScript
"Yes, get this app back up!" button that has to be clicked, and staying awake
requires a real browser session that opens the Streamlit websocket. So this
script loads the app in a headless browser, clicks the wake-up button if it is
shown, waits for the app shell to render, and holds the session open briefly.
"""
import os
import re
import sys
import time

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

APP_URL = os.environ.get("STREAMLIT_APP_URL", "").strip()

# Text Streamlit shows on the "sleeping" interstitial button.
WAKE_TEXT_RE = re.compile(r"get this app back up|app back up|wake", re.IGNORECASE)

# Markers that the live Streamlit app shell has rendered.
APP_READY_SELECTOR = (
    '[data-testid="stAppViewContainer"], [data-testid="stApp"], .stApp'
)

NAV_TIMEOUT_MS = 60_000
APP_READY_TIMEOUT_MS = 90_000
HOLD_SECONDS = 8


def _click_wake_button(page) -> bool:
    """Return True if a wake-up button was found and clicked."""
    # Preferred: a real <button> with the wake-up label.
    try:
        button = page.get_by_role("button", name=WAKE_TEXT_RE)
        button.wait_for(state="visible", timeout=10_000)
        button.click()
        return True
    except PlaywrightTimeoutError:
        pass

    # Fallback: any clickable element carrying the wake-up text.
    try:
        element = page.get_by_text(WAKE_TEXT_RE).first
        element.wait_for(state="visible", timeout=5_000)
        element.click()
        return True
    except PlaywrightTimeoutError:
        return False


def keep_awake(url: str) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 "
                "streamlit-keepalive-bot"
            )
        )
        page = context.new_page()
        try:
            print(f"Opening {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)

            if _click_wake_button(page):
                woke_it = True
                print("App was asleep -> clicked the wake-up button.")
            else:
                woke_it = False
                print("No wake-up button found (app was already awake).")

            try:
                page.wait_for_selector(
                    APP_READY_SELECTOR, timeout=APP_READY_TIMEOUT_MS
                )
                print("Streamlit app shell rendered.")
            except PlaywrightTimeoutError:
                if woke_it:
                    # A freshly woken app may still be cold-starting; give it
                    # a bit longer rather than failing the run outright.
                    print("Shell not detected yet; waiting for cold start...")
                    time.sleep(20)
                else:
                    raise

            # Hold the session open so Streamlit registers an active viewer.
            time.sleep(HOLD_SECONDS)
            print(f"Done. Page title: {page.title()!r}")
        finally:
            context.close()
            browser.close()


def main() -> int:
    if not APP_URL:
        print(
            "ERROR: STREAMLIT_APP_URL is not set. Set the repository variable "
            "STREAMLIT_APP_URL (or pass the app_url input on a manual run).",
            file=sys.stderr,
        )
        return 2

    last_error = None
    for attempt in range(1, 4):
        try:
            keep_awake(APP_URL)
            return 0
        except Exception as exc:  # best-effort: log, back off, retry
            last_error = exc
            print(f"Attempt {attempt} failed: {exc}", file=sys.stderr)
            time.sleep(5 * attempt)

    print(f"All attempts failed. Last error: {last_error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
