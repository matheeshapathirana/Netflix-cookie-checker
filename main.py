import json
import os
import sys
import config
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options

working_cookies_path = "working_cookies"

if os.name == "posix":
    try:
        folder_path = "json_cookies"
        os.path.isdir(folder_path)
    except FileNotFoundError:
        print("Error Occurred :Default 'json_cookies' folder not found, please run cookie_converter.py first")
        sys.exit()


else:
    import tkinter
    from tkinter import filedialog

    if config.use_folder_selector:
        tkinter.Tk().withdraw()
        folder_path = filedialog.askdirectory()
        if folder_path == "":
            folder_path = "json_cookies"
            print("Using default path")
        else:
            print(f"Using path: {folder_path}")


def load_cookies_from_json(json_cookies_path):
    with open(json_cookies_path, "r", encoding="utf-8") as cookie_file:
        cookie = json.load(cookie_file)
    return cookie


def open_webpage_with_cookies(link, json_cookies):
    firefox_options = Options()
    firefox_options.add_argument("--headless")
    driver = webdriver.Firefox(options=firefox_options)
    driver.get(link)

    for cookie in json_cookies:
        driver.add_cookie(cookie)

    driver.refresh()

    if driver.find_elements(By.CSS_SELECTOR, ".btn"):
        print(f"Cookie Not working - {filename}")
        driver.quit()
    else:
        print(f"Working cookie found! - {filename}")
        try:
            os.mkdir(working_cookies_path)
            with open(f"working_cookies/{filename})", "w", encoding="utf-8") as a:
                a.write(content)
            driver.quit()

        except FileExistsError:
            with open(f"working_cookies/{filename}", "w", encoding="utf-8") as a:
                a.write(content)
            driver.quit()


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
                print("Please use cookie_converter.py to convert your cookies to json format\n")
                break

            except Exception as e:
                print(f"Error occurred: {str(e)} - {filename}\n")
