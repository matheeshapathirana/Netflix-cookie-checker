import json
import os
import shutil
import sys
from colorama import init, Fore

init()

def identify_file(file_name):
    try:
        with open(file_name, "r") as file_content:
            # Try to parse the file as JSON
            json.load(file_content)
            return "json"
    except json.JSONDecodeError:
        # If it fails to parse as JSON, assume it's a Netscape file
        return "netscape"
    except Exception as e:
        # If any other error occurred, print it
        print(f"An error occurred while processing {file_name}: {str(e)}")
        return "error"


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

    path = "json_cookies"
    try:
        os.mkdir(path)
        print(Fore.RED + f"Folder {path} created!\n" + Fore.RESET)
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
        else:
            print(
                Fore.RED
                + "[⚠️] Error Occurred: Failed to create 'json_cookies' folder, Exiting..."
                + Fore.RESET
            )
            sys.exit()

    for filename in os.listdir(folder_path):
        filepath = os.path.join(folder_path, filename)
        if os.path.isfile(filepath):
            file_type = identify_file(filepath)
            if file_type == "json":
                shutil.copy(filepath, os.path.join(path, filename))
                print(
                    Fore.GREEN
                    + f"[✔️] {filename} - Copied to 'json_cookies' folder!"
                    + Fore.RESET
                )
            elif file_type == "netscape":
                with open(filepath, "r", encoding="utf-8") as file:
                    content = file.read()

                json_data = convert_netscape_cookie_to_json(content)

                with open(f"json_cookies/{filename}", "w", encoding="utf-8") as f:
                    f.write(json_data)
                    print(Fore.GREEN + f"[✔️] {filename} - DONE!" + Fore.RESET)
                    no_of_cookies += 1
            else:
                print(
                    Fore.RED
                    + f"[⚠️] {filename} - Error: File type could not be identified!"
                    + Fore.RESET
                )

    print(
        Fore.YELLOW
        + f"\nConverted {no_of_cookies} cookies to JSON format\n"
        + Fore.RESET
    )
except KeyboardInterrupt:
    print(Fore.RED + "\n\nProgram Interrupted by user" + Fore.RESET)
    sys.exit()
