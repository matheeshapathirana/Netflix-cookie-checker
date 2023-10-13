import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By

working_cookies_path = "working_cookies"


def load_cookies_from_json(FILEPATH):
    with open(FILEPATH, "r") as cookie_file:
        cookie = json.load(cookie_file)
    return cookie


def open_webpage_with_cookies(URL, COOKIES):
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)

    driver.get(URL)

    for cookie in COOKIES:
        driver.add_cookie(cookie)
    driver.refresh()
    driver.get_cookies()

    if driver.find_elements(By.CSS_SELECTOR, ".btn"):
        print(f"Cookie Not working - {filename}")
        driver.quit()
    else:
        print(f"Working cookie found! - {filename}")
        try:
            os.mkdir(working_cookies_path)
            with open(f"working_cookies/{filename})", "w") as a:
                a.write(content)
            driver.quit()

        except FileExistsError:
            with open(f"working_cookies/{filename}", "w") as a:
                a.write(content)
            driver.quit()

try:
    for filename in os.listdir("json_cookies"):
        filepath = os.path.join("json_cookies", filename)
        if os.path.isfile(filepath):
            with open(filepath, "r") as file:
                content = file.read()

                url = "https://netflix.com/login"

                try:
                    cookies = load_cookies_from_json(filepath)
                    open_webpage_with_cookies(url, cookies)
                except Exception as e:
                    print(f"Error occurred {str(e)} - {filename}")

except FileNotFoundError:
    print("Error occurred : 'json_cookies' folder not found!. Please read README.md")