import json
import os
import sys
from bs4 import BeautifulSoup
import requests
import time

try:
    working_cookies_path = "working_cookies"
    exceptions = 0
    working_cookies = 0
    expired_cookies = 0
    start = time.time()


    def maximum():
        count = 0
        for root_dir, cur_dir, files in os.walk(r"json_cookies"):
            count += len(files)
            return count


    def load_cookies_from_json(json_cookies_path):
        with open(json_cookies_path, "r", encoding="utf-8") as cookie_file:
            cookie = json.load(cookie_file)
        return cookie


    def open_webpage_with_cookies(link, json_cookies):
        global working_cookies
        global expired_cookies

        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        })

        # Request the page
        response = session.get(link)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Clear all existing cookies
        session.cookies.clear()

        for cookie in json_cookies:
            session.cookies.set(cookie['name'], cookie['value'])

        response = session.get(link)

        if 'Sign In' in response.text or 'btn' in response.text:
            print(f"Cookie Not working - {filename}")
            expired_cookies += 1
        else:
            print(f"Working cookie found! - {filename}")
            try:
                os.mkdir(working_cookies_path)
                with open(f"working_cookies/{filename})", "w", encoding="utf-8") as a:
                    a.write(content)
                working_cookies += 1
            except FileExistsError:
                with open(f"working_cookies/{filename}", "w", encoding="utf-8") as a:
                    a.write(content)
                working_cookies += 1


    for filename in os.listdir("json_cookies"):
        filepath = os.path.join("json_cookies", filename)
        if os.path.isfile(filepath):
            with open(filepath, "r", encoding="utf-8") as file:
                content = file.read()

                url = "https://netflix.com/login"

                try:
                    cookies = load_cookies_from_json(filepath)
                    open_webpage_with_cookies(url, cookies)

                except json.decoder.JSONDecodeError:
                    print(
                        f"Please use cookie_converter.py to convert your cookies to json format! (File: {filename})\n"
                    )
                    exceptions += 1
                    break

                except Exception as e:
                    print(f"Error occurred: {str(e)} - {filename}\n")
                    exceptions += 1

    end = time.time()
    print(
        f"\nSummary:\nTotal cookies: {maximum()}\nWorking cookies: {working_cookies}\nExpired cookies: {maximum() - working_cookies}\nInvalid cookies: {exceptions}\nTime Elapsed: {end - start} Seconds"
    )
except KeyboardInterrupt:
    print("\n\nProgram Interrupted by user")
    sys.exit()
