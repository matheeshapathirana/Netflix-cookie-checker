import json
import os
import re
import sys
import time
import requests
from requests.exceptions import RequestException, ConnectionError
from http.client import RemoteDisconnected
from bs4 import BeautifulSoup
from colorama import init, Fore
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

init()

print(Fore.YELLOW + "Initializing!, Please wait...\n" + Fore.RESET)
working_cookies_path = "working_cookies"
exceptions = 0
working_cookies = 0
expired_cookies = 0
duplicate_cookies = 0
extra_memberships = 0
start = time.time()
plan = None
email = None
ID = None
info = None
extra_members = None
country = None

lock = Lock()
num_threads = 5  # Define the maximum number of threads here

# ___________________________________________
# | Network Speed | Recommended no. threads |
# |---------------|-------------------------|
# | < 5 Mbps      | 1-3                     |
# | 5-20 Mbps     | 3-5                     |
# | 20-100 Mbps   | 5-10                    |
# | > 100 Mbps    | 10-20                   |
# |_________________________________________|

max_retries = 3  # Define the maximum number of retries


def decode_hex_escapes(s):
    """Decode \\xNN hex escapes (e.g. \\x40 -> @) and unicode escapes."""
    if not s:
        return s
    # Decode \xNN sequences
    s = re.sub(
        r'\\x([0-9A-Fa-f]{2})',
        lambda m: chr(int(m.group(1), 16)),
        s
    )
    # Decode \uNNNN sequences
    s = re.sub(
        r'\\u([0-9A-Fa-f]{4})',
        lambda m: chr(int(m.group(1), 16)),
        s
    )
    return s


def extract_info(response_text):
    """
    Extract plan, email, and country directly from the reactContext JSON
    embedded in the Netflix page HTML.
    """
    result = {
        "localizedPlanName": None,
        "emailAddress": None,
        "countryOfSignup": None,
    }

    patterns = {
        # Matches: "localizedPlanName":{"fieldType":"String","value":"Standard"}
        "localizedPlanName": r'"localizedPlanName"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,\s*"value"\s*:\s*"([^"]+)"',
        # Matches: "emailAddress":"user\x40gmail.com"
        "emailAddress":      r'"emailAddress"\s*:\s*"([^"]+)"',
        # Matches: "countryOfSignup":"BE"
        "countryOfSignup":   r'"countryOfSignup"\s*:\s*"([^"]+)"',
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, response_text)
        if match:
            value = match.group(1)
            result[key] = decode_hex_escapes(value)

    return result


def load_cookies_from_json(json_cookies_path):
    with open(json_cookies_path, "r", encoding="utf-8") as cookie_file:
        cookie = json.load(cookie_file)
    return cookie


def open_webpage_with_cookies(session, link, json_cookies, filename):
    global working_cookies, expired_cookies, plan, email, duplicate_cookies, ID, info, extra_memberships, extra_members, country

    session.cookies.clear()

    for cookie in json_cookies:
        session.cookies.set(cookie["name"], cookie["value"])

    session.headers.update({"Accept-Encoding": "identity"})

    attempt = 0
    while attempt < max_retries:
        try:
            response = session.get(link)
            response.raise_for_status()
            content = response.text
            info = extract_info(content)
            soup = BeautifulSoup(content, "lxml")

            # Check for extra membership access
            em_response = session.get(
                "https://www.netflix.com/accountowner/addextramember",
                allow_redirects=False,
            )
            if em_response.status_code == 200:
                extra_memberships += 1
                extra_members = True
            else:
                extra_members = False

            # Detect logged-out state
            if soup.find(string="Sign In") or soup.find(string="Sign in"):
                with lock:
                    print(Fore.RED + f"[❌] Cookie Not working - {filename}" + Fore.RESET)
                    expired_cookies += 1
                return False

            # ── Extract plan ──────────────────────────────────────────────
            raw_plan = info.get("localizedPlanName")
            if raw_plan:
                # Normalize extra-member label
                plan = raw_plan.replace("miembro\xa0extra", "(Shared Extra Member)")
            else:
                # Fallback: look for known plan names in the page text
                page_text = soup.get_text()
                for candidate in ("Premium", "Standard", "Basic"):
                    if candidate in page_text:
                        plan = candidate
                        break
                else:
                    plan = "Unknown"

            # ── Extract email ─────────────────────────────────────────────
            raw_email = info.get("emailAddress")
            if raw_email:
                email = raw_email
            else:
                # Fallback: CSS selector (only present on /YourAccount page)
                el = soup.select_one(".account-section-email")
                email = el.text.strip() if el else "Unknown"

            # ── Extract country ───────────────────────────────────────────
            country = info.get("countryOfSignup") or "Unknown"

            os.makedirs(working_cookies_path, exist_ok=True)
            return True

        except (RequestException, ConnectionError, RemoteDisconnected) as e:
            with lock:
                print(
                    Fore.RED
                    + f"[⚠️] Request error occurred: {str(e)} - {filename} (Attempt {attempt + 1}/{max_retries})"
                    + Fore.RESET
                )
            attempt += 1
            time.sleep(1)

    with lock:
        print(Fore.RED + f"[❌] Failed after {max_retries} attempts - {filename}" + Fore.RESET)
    return False


def process_cookie_file(filename):
    global duplicate_cookies, working_cookies, exceptions, extra_memberships
    filepath = os.path.join("json_cookies", filename)
    if os.path.isfile(filepath):
        url = "https://www.netflix.com/YourAccount"
        try:
            cookies = load_cookies_from_json(filepath)
            with requests.Session() as session:
                if open_webpage_with_cookies(session, url, cookies, filename):
                    additional_json = {
                        "_comment": "Cookie Checked by https://github.com/matheeshapathirana/Netflix-cookie-checker",
                        "Credits": "Matheesha Pathirana",
                        "Discord Server": "https://discord.gg/RSCdKeKB5X",
                        "Special Thanks": "To all the contributors who have helped improve this project by submitting pull requests and to everyone who has starred the project and supported our work",
                        "Disclaimer": "This project is for educational purposes only. The authors and contributors are not responsible for how it is used.",
                        "Support": "If you find this project helpful, consider supporting it by starring the project on GitHub, contributing to the code, or making a donation on Ko-fi. Your support helps keep the project alive and encourages further improvements!",
                    }
                    cookies.append(additional_json)

                    if extra_members:
                        working_cookie_path = os.path.join(
                            working_cookies_path,
                            f"[{country}] [{email}] - {plan} - Extra Membership.json",
                        )
                        extra_memberships += 1
                    else:
                        working_cookie_path = os.path.join(
                            working_cookies_path,
                            f"[{country}] [{email}] - {plan}.json",
                        )

                    with lock:
                        if os.path.isfile(working_cookie_path):
                            print(
                                Fore.YELLOW
                                + f"[⚠️] Duplicate Cookie - {filename} | Plan: {plan} | Email: {email}"
                                + Fore.RESET
                            )
                            duplicate_cookies += 1
                        else:
                            with open(working_cookie_path, "w", encoding="utf-8") as json_file:
                                json.dump(cookies, json_file, indent=4)
                                working_cookies += 1

                            print(
                                Fore.GREEN
                                + f"[✔️] Cookie Working - [{country}] {filename} | Plan: {plan} | Email: {email} | Extra membership: {extra_members}"
                                + Fore.RESET
                            )

        except json.decoder.JSONDecodeError:
            with lock:
                print(
                    Fore.RED
                    + f"[⚠️] Please use cookie_converter.py to convert your cookies to json format! (File: {filename})\n"
                    + Fore.RESET
                )
                exceptions += 1

        except Exception as e:
            with lock:
                print(Fore.RED + f"[⚠️] Error occurred: {str(e)} - {filename}" + Fore.RESET)
                exceptions += 1


def main():
    try:
        if os.path.isdir("json_cookies"):
            entries = os.listdir("json_cookies")
            files = [
                entry
                for entry in entries
                if os.path.isfile(os.path.join("json_cookies", entry))
            ]
            if len(files) == 0:
                print(
                    Fore.RED
                    + '[⚠️] Error Occurred: \'json_cookies\' directory is empty. Please use cookie_converter.py to convert cookies. if you already have json cookies place them inside "json_cookies" folder.\n'
                    + Fore.RESET
                )
                sys.exit()
            if os.path.isdir("working_cookies"):
                print(
                    Fore.RED
                    + "[⚠️] working_cookies folder already exists, new cookies will be appended.\n"
                    + Fore.RESET
                )

            filenames = os.listdir("json_cookies")
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                executor.map(process_cookie_file, filenames)
        else:
            print(
                Fore.RED
                + "[⚠️] Error Occurred: 'json_cookies' directory not found. Please use cookie_converter.py to convert cookies. if you already have json cookies, please create a folder named 'json_cookies' and place them in it."
                + Fore.RESET
            )
            sys.exit()
    except FileNotFoundError:
        print(
            Fore.RED
            + "[⚠️] Error Occurred: Please use cookie_converter.py to convert cookies."
            + Fore.RESET
        )
        sys.exit()


try:
    main()
    end = time.time()
    print(
        Fore.YELLOW
        + f"===================================\n"
          f"Summary:\n"
          f"Total Cookies: {len(os.listdir('json_cookies'))}\n"
          f"Working Cookies: {working_cookies}\n"
          f"Extra Membership Cookies: {extra_memberships}\n"
          f"Expired Cookies: {expired_cookies}\n"
          f"Duplicate Cookies: {duplicate_cookies}\n"
          f"Invalid Cookies: {exceptions}\n"
          f"Time Elapsed: {round((end - start))} Seconds\n"
          f"================================="
        + Fore.RESET
    )
except KeyboardInterrupt:
    print(Fore.RED + "\n\n[⚠️] Program Interrupted by user" + Fore.RESET)
    sys.exit()