import json
import os
import tkinter
from tkinter import filedialog


tkinter.Tk().withdraw() # prevents an empty tkinter window from appearing
folder_path = filedialog.askdirectory()

def convert_netscape_cookie_to_json(cookie_file_content):
    cookies = []
    for line in cookie_file_content.splitlines():
        fields = line.strip().split('\t')
        if len(fields) >= 7:
            cookie = {
                'domain': fields[0],
                'flag': fields[1],
                'path': fields[2],
                'secure': fields[3] == 'TRUE',
                'expiration': fields[4],
                'name': fields[5],
                'value': fields[6]
            }
            cookies.append(cookie)

    json_data = json.dumps(cookies, indent=4)
    return json_data


for filename in os.listdir(folder_path):
    filepath = os.path.join(folder_path, filename)
    if os.path.isfile(filepath):
        with open(filepath, 'r') as file:
            content = file.read()


# Usage example
# num = 1
# while (num != 195):
#     cookie_file_path = f'{folder_path}/cookie ({num}).txt'
#     with open(cookie_file_path, 'r') as cookie_file:
#         cookie_file_content = cookie_file.read()

        json_data = convert_netscape_cookie_to_json(content)
        f = open(f"new/jsoncookie ({filename}).txt", 'w')
        f.write(json_data)
        print(f'Cookie no. {filename} DONE!')

