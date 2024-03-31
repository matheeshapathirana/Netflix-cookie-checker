import json
import os
import random
import shutil
import sys
from colorama import Fore

no_of_cookies = 0

try:
    if os.name == "posix":
        folder_path = "cookies"

    else:
        while True:
            import tkinter
            from tkinter import filedialog

            print(
                Fore.YELLOW
                + "\n<<< Select Netscape cookies folder >>>\n\n"
                + Fore.RESET
            )
            tkinter.Tk().withdraw()
            folder_path = filedialog.askdirectory()
            if folder_path == "":
                if os.path.isdir("cookies"):
                    folder_path = "cookies"
                    print(
                        Fore.YELLOW
                        + "Trying to use default folder 'cookies'\n"
                        + Fore.RESET
                    )
                    break
                else:
                    print(
                        Fore.RED
                        + "[⚠️] No folder selected or default 'cookies' folder not found, Exiting..."
                        + Fore.RESET
                    )
                    sys.exit()

            else:
                break

    rand_number = random.randint(1, 99999)

    def convert_netscape_cookie_to_json(cookie_file_content):
        cookies = []
        for line in cookie_file_content.splitlines():
            fields = line.strip().split("\t")
            if len(fields) >= 7:
                cookie = {
                    "domain": fields[0].replace("www", ""),
                    "flag": fields[1],
                    "path": fields[2],
                    "secure": fields[3] == "TRUE",
                    "expiration": fields[4],
                    "name": fields[5],
                    "value": fields[6],
                }
                cookies.append(cookie)

        json_content = json.dumps(cookies, indent=4)
        return json_content

    path = "json_cookies"
    try:
        os.mkdir(path)
        print(Fore.RED + f"Folder {path} created!\n" + Fore.RESET)
        try:
            for filename in os.listdir(folder_path):
                filepath = os.path.join(folder_path, filename)
                if os.path.isfile(filepath):
                    with open(filepath, "r", encoding="utf-8") as file:
                        content = file.read()

                    json_data = convert_netscape_cookie_to_json(content)

                    with open(f"json_cookies/{filename}", "w", encoding="utf-8") as f:
                        f.write(json_data)
                        print(Fore.GREEN + f"[✔️] {filename} - DONE!" + Fore.RESET)
                        no_of_cookies += 1

        except FileNotFoundError:
            print(
                Fore.RED
                + "[⚠️] Error Occurred: Default 'cookies' folder not found, please select a valid folder"
                + Fore.RESET
            )
            os.rmdir(path)

    except FileExistsError:
        if (
            input(
                Fore.YELLOW
                + "Do you want to remove old cookies folder? (y/n)\n [y] Recommended \n [n] New cookies will be appended > : "
                + Fore.RESET
            )
            == "y"
        ):
            shutil.rmtree(path)
            os.mkdir(path)
            for filename in os.listdir(folder_path):
                filepath = os.path.join(folder_path, filename)
                if os.path.isfile(filepath):
                    with open(filepath, "r", encoding="utf-8") as file:
                        content = file.read()

                    json_data = convert_netscape_cookie_to_json(content)

                    with open(f"json_cookies/{filename}", "w", encoding="utf-8") as f:
                        f.write(json_data)
                        print(Fore.GREEN + f"[✔️] {filename} - DONE!" + Fore.RESET)
                        no_of_cookies += 1

        else:
            for filename in os.listdir(folder_path):
                filepath = os.path.join(folder_path, filename)
                if os.path.isfile(filepath):
                    with open(filepath, "r") as file:
                        content = file.read()

                    json_data = convert_netscape_cookie_to_json(content)

                    with open(f"json_cookies/{filename}", "w", encoding="utf-8") as f:
                        f.write(json_data)
                        print(Fore.GREEN + f"[✔️] {filename} - DONE!" + Fore.RESET)
                        no_of_cookies += 1

    print(
        Fore.YELLOW
        + f"\nConverted {no_of_cookies} cookies to JSON format\n"
        + Fore.RESET
    )
except KeyboardInterrupt:
    print(Fore.RED + "\n\nProgram Interrupted by user" + Fore.RESET)
    sys.exit()
