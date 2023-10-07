import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options

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
        print(f"Cookie Not working - No. {num}")
        driver.quit()
    else:
        print(f"Working cookie found! - No. {num}")
        a = open(f'working_cookies/working_cookie ({num})','w')
        a.write(cookie_file_path)
        driver.quit()

# Usage example
num=1
while (num != 195):
    cookie_file_path = f'json_cookies/jsoncookie ({num}).txt'
    url = 'https://netflix.com/login'

    cookies = load_cookies_from_json(cookie_file_path)
    open_webpage_with_cookies(url, cookies)
    num+=1