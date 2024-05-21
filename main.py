import json
import os
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
start = time.time()
plan = None
email = None
ID = None

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

max_retries = 5  # Define the maximum number of retries


def load_cookies_from_json(json_cookies_path):
    with open(json_cookies_path, "r", encoding="utf-8") as cookie_file:
        cookie = json.load(cookie_file)
    return cookie


def open_webpage_with_cookies(session, link, json_cookies, filename):
    global working_cookies, expired_cookies, plan, email, duplicate_cookies, ID

    session.cookies.clear()

    for cookie in json_cookies:
        session.cookies.set(cookie["name"], cookie["value"])

    session.headers.update({'Accept-Encoding': 'identity'})

    attempt = 0
    while attempt < max_retries:
        try:
            response = session.get(link)
            response.raise_for_status()
            content = response.text
            soup = BeautifulSoup(content, "lxml")

            if soup.find(string="Sign In") or soup.find(string="Sign in"):
                with lock:
                    print(Fore.RED + f"[❌] Cookie Not working - {filename}" + Fore.RESET)
                    expired_cookies += 1
                return False
            else:
                with lock:
                    try:
                        plan = soup.select_one(
                            "div.account-section:nth-child(2) > section:nth-child(2) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > b:nth-child(1)").text or soup.select_one(
                            ".default-ltr-cache-10ajupv").text or soup.select_one(
                            "html.js-focus-visible body div#appMountPoint div div.default-ltr-cache-0 div.default-ltr-cache-1w02yd5.el0v7282 section div.default-ltr-cache-1fhvoso.eslj5pt1 div.default-ltr-cache-1grpxuk.eslj5pt0 div.default-ltr-cache-1tmwau.ew2l6qe0 div.default-ltr-cache-1fhvoso.eslj5pt1 div.default-ltr-cache-1u7ywyk.eslj5pt0 div.default-ltr-cache-1rlft14.e1bbao1b0 div.default-ltr-cache-16dvsg3.el0v7280 section.default-ltr-cache-1d3w5wq div.default-ltr-cache-1nca7k1.e19xx6v36 div.default-ltr-cache-q8smu4.e19xx6v35 div.default-ltr-cache-1cr1i8r.e19xx6v33 h3.default-ltr-cache-10ajupv.e19xx6v32").text or soup.select_one(
                            "/html/body/div[1]/div/div/div/section/div[2]/div/div/div/div/div/div[2]/section/div[2]/div/div[2]/h3").text
                        email = soup.select_one(".account-section-email").text
                    except AttributeError:
                        plan = (
                            "Premium"
                            if soup.find(string="Premium")
                            else (
                                "Basic"
                                if soup.find(string="Basic")
                                else "Standard" if soup.find(string="Standard") else "Unknown"
                            )
                        )
                os.makedirs(working_cookies_path, exist_ok=True)
                return True
        except (RequestException, ConnectionError, RemoteDisconnected) as e:
            with lock:
                print(
                    Fore.RED + f"[⚠️] Request error occurred: {str(e)} - {filename} (Attempt {attempt + 1}/{max_retries})" + Fore.RESET)
            attempt += 1
            time.sleep(1)

    with lock:
        print(Fore.RED + f"[❌] Failed after {max_retries} attempts - {filename}" + Fore.RESET)
    return False


def process_cookie_file(filename):
    global duplicate_cookies, working_cookies, exceptions
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
                        "Special Thanks": "- To all the contributors who have helped improve this project by submitting pull requests.\n- To everyone who has starred the project and supported our work",
                        "Disclaimer": "This project is for educational purposes only. The authors and contributors are not responsible for how it is used.",
                        "Support": "If you find this project helpful, consider supporting it by starring the project on GitHub, contributing to the code, or making a donation on Ko-fi. Your support helps keep the project alive and encourages further improvements!",
                    }
                    cookies.append(additional_json)
                    working_cookie_path = os.path.join(working_cookies_path, f"[{email}] - {plan}.json")

                    with lock:
                        if os.path.isfile(working_cookie_path):
                            print(
                                Fore.YELLOW
                                + f"[⚠️] Duplicate Cookie - {filename} | Plan: {plan} | Email: {email} | ID: {filename}"
                                + Fore.RESET
                            )
                            duplicate_cookies += 1
                        else:
                            with open(working_cookie_path, "w", encoding="utf-8") as json_file:
                                json.dump(cookies, json_file, indent=4)
                                working_cookies += 1

                            print(
                                Fore.GREEN
                                + f"[✔️] Cookie Working - {filename} | Plan: {plan} | Email: {email}"
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
                print(
                    Fore.RED + f"[⚠️] Error occurred: {str(e)} - {filename}" + Fore.RESET
                )
                exceptions += 1


def main():
    try:
        if os.path.isdir("json_cookies"):
            entries = os.listdir("json_cookies")
            files = [entry for entry in entries if os.path.isfile(os.path.join("json_cookies", entry))]
            if len(files) == 0:
                print(
                    Fore.RED
                    + "[⚠️] Error Occurred: 'json_cookies' directory is empty. Please use cookie_converter.py to convert cookies. if you already have json cookies place them inside \"json_cookies\" folder.\n"
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
        + f"==================================="
          f"\nSummary:\nTotal Cookies: {len(os.listdir('json_cookies'))}\nWorking Cookies: {working_cookies}\nExpired Cookies: {expired_cookies}\nDuplicate Cookies: {duplicate_cookies}\nInvalid Cookies: {exceptions}\nTime Elapsed: {round((end - start))} Seconds"
          f"\n================================="
        + Fore.RESET
    )
except KeyboardInterrupt:
    print(Fore.RED + "\n\n[⚠️] Program Interrupted by user" + Fore.RESET)
    sys.exit()
