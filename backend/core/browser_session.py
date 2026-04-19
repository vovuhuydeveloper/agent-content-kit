"""
BrowserSession — Persistent browser session manager.
Login once manually → reuse session for headless automation.
Supports: YouTube, TikTok, Facebook, Instagram.
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger("core.browser_session")

SESSION_BASE = Path("data/sessions")


class BrowserSession:
    """Manage browser login sessions for social platforms"""

    @staticmethod
    def session_dir(platform: str) -> Path:
        return SESSION_BASE / platform

    @staticmethod
    def has_session(platform: str) -> bool:
        """Check if a saved session exists for platform"""
        sdir = SESSION_BASE / platform
        return sdir.exists() and any(sdir.iterdir())

    @staticmethod
    def login(platform: str):
        """
        Open browser with UI → user logs in manually → session saved.
        Run this ONCE per platform. After that, headless mode works.
        """
        from playwright.sync_api import sync_playwright

        sdir = SESSION_BASE / platform
        sdir.mkdir(parents=True, exist_ok=True)

        urls = {
            "youtube": "https://studio.youtube.com/",
            "tiktok": "https://www.tiktok.com/login",
            "facebook": "https://www.facebook.com/login",
            "instagram": "https://www.instagram.com/accounts/login/",
        }

        url = urls.get(platform, f"https://{platform}.com/login")

        logger.info(f"Opening browser for {platform} login...")
        logger.info("Login manually, then CLOSE the browser window to save session.")

        with sync_playwright() as p:
            # Use REAL Chrome (not Playwright Chromium) to avoid Google blocking
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(sdir),
                headless=False,
                channel="chrome",  # Use real Chrome installation
                args=[
                    "--start-maximized",
                    "--disable-blink-features=AutomationControlled",
                ],
                no_viewport=True,
                locale="vi-VN",
            )

            page = context.pages[0] if context.pages else context.new_page()
            page.goto(url, wait_until="domcontentloaded")

            # Wait for user to login and close browser
            try:
                page.wait_for_event("close", timeout=300_000)  # 5 min
            except Exception:
                pass

            context.close()

        if BrowserSession.has_session(platform):
            logger.info(f"✅ {platform} session saved at {sdir}")
            return True
        else:
            logger.warning(f"❌ {platform} session not saved")
            return False

    @staticmethod
    def get_context(platform: str, playwright_instance=None, headless=True):
        """
        Get a persistent browser context with saved session.
        Used by uploaders for headless automation.
        """
        sdir = SESSION_BASE / platform
        if not BrowserSession.has_session(platform):
            raise RuntimeError(
                f"No session for {platform}. Run: "
                f"python -m backend.core.browser_session login {platform}"
            )

        context = playwright_instance.chromium.launch_persistent_context(
            user_data_dir=str(sdir),
            headless=headless,
            channel="chrome",  # Use real Chrome
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
            locale="vi-VN",
            viewport={"width": 1280, "height": 800},
        )
        return context

    @staticmethod
    def clear_session(platform: str):
        """Remove saved session"""
        import shutil
        sdir = SESSION_BASE / platform
        if sdir.exists():
            shutil.rmtree(sdir)
            logger.info(f"Session cleared for {platform}")


# CLI support: python -m backend.core.browser_session login youtube
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 3:
        print("Usage: python -m backend.core.browser_session <login|status|clear> <platform>")
        print("Platforms: youtube, tiktok, facebook, instagram")
        sys.exit(1)

    action = sys.argv[1]
    platform = sys.argv[2]

    if action == "login":
        print(f"🌐 Opening browser for {platform} login...")
        print("👉 Login manually, then CLOSE the browser to save session.")
        BrowserSession.login(platform)
    elif action == "status":
        connected = BrowserSession.has_session(platform)
        status = "✅ Connected" if connected else "❌ Not connected"
        print(f"{platform}: {status}")
    elif action == "clear":
        BrowserSession.clear_session(platform)
        print(f"🗑️ Session cleared for {platform}")
    else:
        print(f"Unknown action: {action}")
