
import json
import os
import sys
import config
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import progressbar
import psutil
import threading
import queue



try:
    working_cookies_path = "working_cookies"
    exceptions = 0
    working_cookies = 0
    expired_cookies = 0
    lock = threading.Lock()

    def kill_driver():
        process_name = "geckodriver"
        for proc in psutil.process_iter():
            if proc.name() == process_name:
                proc.kill()

    if os.name == "posix":
        folder_path = "json_cookies"
        if not os.path.isdir(folder_path):
            print(
                "Error Occurred :Default 'json_cookies' folder not found, please run cookie_converter.py first"
            )
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


    def maximum():
        count = 0
        for root_dir, cur_dir, files in os.walk(r"json_cookies"):
            count += len(files)
        return count


    progress = 0
    pbar = progressbar.ProgressBar(maxval=maximum())
    pbar.start()


    def load_cookies_from_json(json_cookies_path):
        with open(json_cookies_path, "r", encoding="utf-8") as cookie_file:
            cookie = json.load(cookie_file)
        return cookie


    def open_webpage_with_cookies(link, json_cookies, filename, content):
        global progress
        global working_cookies
        global expired_cookies
        firefox_options = Options()
        # firefox_options.add_argument("--headless")
        firefox_options.add_argument("--width=800")
        firefox_options.add_argument("--height=600")
        firefox_options.add_argument("--start-minimized")
        driver = webdriver.Firefox(options=firefox_options)
        driver.get(link)

        for cookie in json_cookies:
            driver.add_cookie(cookie)

        driver.refresh()
        with lock:
            pbar.update(progress)
            progress += 1

        # Check if redirected to login page (cookie not working)
        if driver.current_url.strip("/") == "https://www.netflix.com/in/login":
            print(f"Cookie Not working - {filename}")
            driver.quit()
            kill_driver()
            with lock:
                expired_cookies += 1
        else:
            print(f"Working cookie found! - {filename}")
            try:
                os.mkdir(working_cookies_path)
                with open(f"working_cookies/{filename}", "w", encoding="utf-8") as a:
                    a.write(content)
                driver.quit()
                kill_driver()
                with lock:
                    working_cookies += 1

            except FileExistsError:
                with open(f"working_cookies/{filename}", "w", encoding="utf-8") as a:
                    a.write(content)
                driver.quit()
                kill_driver()
                with lock:
                    working_cookies += 1

    # Thread worker function
    def worker(q):
        global exceptions
        while True:
            item = q.get()
            if item is None:
                break
            filename, filepath = item
            if os.path.isfile(filepath):
                with open(filepath, "r", encoding="utf-8") as file:
                    content = file.read()
                    url = "https://netflix.com/login"
                    try:
                        cookies = load_cookies_from_json(filepath)
                        open_webpage_with_cookies(url, cookies, filename, content)
                    except json.decoder.JSONDecodeError:
                        print(
                            f"Please use cookie_converter.py to convert your cookies to json format! (File: {filename})\n"
                        )
                        with lock:
                            exceptions += 1
                        break
                    except Exception as e:
                        print(f"Error occurred: {str(e)} - {filename}\n")
                        with lock:
                            exceptions += 1
            q.task_done()


    # Create a queue and add all cookie files
    q = queue.Queue()
    for filename in os.listdir("json_cookies"):
        filepath = os.path.join("json_cookies", filename)
        q.put((filename, filepath))


    # Start 6 worker threads for faster processing
    threads = []
    thread_count = 6
    for _ in range(thread_count):
        t = threading.Thread(target=worker, args=(q,))
        t.start()
        threads.append(t)

    # Wait for all tasks to be done
    q.join()


    # Stop workers
    for _ in range(thread_count):
        q.put(None)
    for t in threads:
        t.join()

    pbar.finish()
    print(
        f"\nSummary:\nTotal cookies: {maximum()}\nWorking cookies: {working_cookies}\nExpired cookies: {maximum() - working_cookies}\nInvalid cookies: {exceptions}"
    )
except KeyboardInterrupt:
    print("\n\nProgram Interrupted by user")
    sys.exit()
