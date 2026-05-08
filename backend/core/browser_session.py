"""
BrowserSession — Persistent browser session manager.
Login once manually → reuse session for headless automation.
Supports: YouTube, TikTok, Facebook, Instagram.
"""

import logging
import sqlite3
import sys
import time
from pathlib import Path

logger = logging.getLogger("core.browser_session")

# In-memory TTL cache to avoid excessive SQLite reads from API polling
_CACHE = {}          # {platform: (timestamp, bool)}
_CACHE_TTL = 2       # seconds — balances freshness vs SQLite overhead

SESSION_BASE = Path("data/sessions")

# Cookie names that indicate a real login per platform
# Only if these exist → user actually logged in
AUTH_COOKIES = {
    "youtube": [
        "__Secure-3PSID",   # Google auth session
        "SAPISID",          # Google auth
        "LOGIN_INFO",       # YouTube-specific login
    ],
    "tiktok": [
        "sessionid",        # TikTok login session
    ],
    "facebook": [
        "c_user",           # Facebook user ID = logged in
    ],
}


class BrowserSession:
    """Manage browser login sessions for social platforms"""

    @staticmethod
    def session_dir(platform: str) -> Path:
        return SESSION_BASE / platform

    @staticmethod
    def has_session(platform: str) -> bool:
        """
        Check if a REAL login session exists for platform.
        Reads the Chromium Cookies SQLite database and looks for
        platform-specific auth cookies — not just folder existence.

        Results are cached in-memory for _CACHE_TTL seconds to avoid
        excessive SQLite reads from API polling or repeated checks.
        """
        now = time.time()
        cached = _CACHE.get(platform)
        if cached is not None:
            ts, val = cached
            if now - ts < _CACHE_TTL:
                return val

        sdir = SESSION_BASE / platform
        cookies_db = sdir / "Default" / "Cookies"

        if not cookies_db.exists():
            _CACHE[platform] = (now, False)
            return False

        required_cookies = AUTH_COOKIES.get(platform, [])
        if not required_cookies:
            # Unknown platform — fall back to folder check
            result = sdir.exists() and any(sdir.iterdir())
            _CACHE[platform] = (now, result)
            return result

        try:
            # Chromium locks the DB when browser is open
            # Use URI mode with nolock=1 to avoid lock errors
            uri = f"file:{cookies_db}?nolock=1"
            conn = sqlite3.connect(uri, uri=True)
            try:
                placeholders = ",".join("?" for _ in required_cookies)
                row = conn.execute(
                    f"SELECT 1 FROM cookies WHERE name IN ({placeholders}) LIMIT 1",
                    required_cookies,
                ).fetchone()
                result = row is not None
            finally:
                conn.close()
        except sqlite3.OperationalError as e:
            # DB locked (browser still open) or corrupted
            logger.debug(f"Cookie DB read failed for {platform}: {e}")
            result = False
        except Exception as e:
            logger.warning(f"Unexpected error checking {platform} session: {e}")
            result = False

        _CACHE[platform] = (now, result)
        return result

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
            # Use Chromium (installed via Playwright) for login
            # Chromium works fine for all platforms and is lighter than Chrome
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(sdir),
                headless=False,
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
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
            locale="vi-VN",
            viewport={"width": 1280, "height": 800},
        )
        return context

    @staticmethod
    def bust_cache(platform: str):
        """Clear in-memory cache for a platform — use after login/logout events."""
        _CACHE.pop(platform, None)

    @staticmethod
    def clear_session(platform: str):
        """Remove saved session"""
        import shutil
        _CACHE.pop(platform, None)
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
