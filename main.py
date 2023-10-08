import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import os

driver = webdriver.Firefox()
def load_cookies_from_json(cookie_file_path):
    with open(cookie_file_path, 'r') as cookie_file:
        cookies = json.load(cookie_file)
    return cookies

def open_webpage_with_cookies(url, cookies):
    firefox_options = Options()
    firefox_options.headless = True  # Run Firefox in headless mode

    driver = webdriver.Firefox(options=firefox_options)
    driver.get(url)

    for cookie in cookies:
        driver.add_cookie(cookie)

    # Refresh the page to apply the cookies
    driver.refresh()

    # Do further actions with the opened webpage
    if driver.find_elements(By.CSS_SELECTOR, '.btn'):
        print(f"Cookie Not working - {filename}")
        driver.quit()
    else:
        print(f"Working cookie found! - {filename}")
        a = open(f'working_cookies/working_cookie ({filename})','w')
        a.write(content)
        driver.quit()

# switching cookies
directory_path = 'json_cookies'
for filename in os.listdir(directory_path):
    filepath = os.path.join(directory_path, filename)
    if os.path.isfile(filepath):
        with open(filepath, 'r') as file:
            content = file.read()

    url = 'https://netflix.com/login'

    try:
        cookies = load_cookies_from_json(content)
        open_webpage_with_cookies(url, cookies)
    except:
        driver.quit()
        print(f"Invalid Cookie - {filename}")