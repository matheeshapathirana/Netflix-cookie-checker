import json
import os
import random
import shutil
import subprocess
import webbrowser
from pathlib import Path
import tkinter
from tkinter import filedialog, Tk, Canvas, Entry, Text, Button, PhotoImage

input_folder = ""
output_folder = ""


def import_cookies():
    global input_folder
    while True:
        import tkinter
        from tkinter import filedialog
        tkinter.Tk().withdraw()
        input_folder = filedialog.askdirectory()
        if input_folder == "":
            print("Trying to use default folder 'cookies'\n")
            input_folder = "cookies"
            break
        break


def output_cookies():
    global output_folder
    while True:
        import tkinter
        from tkinter import filedialog
        tkinter.Tk().withdraw()
        output_folder = filedialog.askdirectory()
        if output_folder == "":
            print("Trying to use default export folder 'json_cookies'\n")
            output_folder = "json_cookies"
            break
        break


def check():
    if not input_folder:
        tkinter.messagebox.showerror(
            title="Invalid cookie Folder", message="Please select a valid folder to import cookies")
        return

    if not output_folder:
        tkinter.messagebox.showerror(
            title="Invalid output Folder", message="Please select a valid folder to export cookies")
        return

    else:
        start()


def start():
    rand_number = random.randint(1, 99999)

    if input_folder == '':
        window.messagebox.showerror(
            title="Invalid Folder", message="Please select a valid folder to import cookies")
        import_cookies()

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

        JSON_DATA = json.dumps(cookies, indent=4)
        return JSON_DATA

    path = output_folder

    for filename in os.listdir(input_folder):
        filepath = os.path.join(input_folder, filename)
        if os.path.isfile(filepath):
            with open(filepath, "r", encoding="utf-8") as file:
                content = file.read()

            json_data = convert_netscape_cookie_to_json(content)

            with open(f"{output_folder}/{filename}", "w", encoding="utf-8") as f:
                f.write(json_data)
                print(f"{filename} - DONE!")

    tkinter.messagebox.showinfo(title="Conversion Completed", message="Conversion completed successfully!")

def home():
    window.destroy()
    subprocess.run(["python", "main.py"])


def settings():
    window.destroy()
    subprocess.run(["python", "settings.py"])


OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / Path("assets/converter")


def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)


window = Tk()
window.title("Netflix Cookie Checker - Cookie Converter")
# img = PhotoImage(file='assets/netflix.png')
# window.iconphoto(False, img)
window.geometry("1090x645+250+250")
window.configure(bg="#FFFFFF")

canvas = Canvas(
    window,
    bg="#FFFFFF",
    height=645,
    width=1090,
    bd=0,
    highlightthickness=0,
    relief="ridge"
)

canvas.place(x=0, y=0)
image_image_1 = PhotoImage(
    file=relative_to_assets("image_1.png"))
image_1 = canvas.create_image(
    545.0,
    322.0,
    image=image_image_1
)

canvas.create_rectangle(
    160.0,
    0.0,
    1098.0,
    645.0,
    fill="#000000",
    outline="")

canvas.create_rectangle(
    0.0,
    0.0,
    160.0,
    645.0,
    fill="#000000",
    outline="")

button_image_1 = PhotoImage(
    file=relative_to_assets("button_1.png"))
button_1 = Button(
    image=button_image_1,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: webbrowser.open("https://netflix.com"),
    relief="flat"
)
button_1.place(
    x=37.0,
    y=29.0,
    width=87.0,
    height=87.0
)

image_image_2 = PhotoImage(
    file=relative_to_assets("image_2.png"))
image_2 = canvas.create_image(
    341.0,
    389.0,
    image=image_image_2
)

button_image_2 = PhotoImage(
    file=relative_to_assets("button_2.png"))
button_2 = Button(
    image=button_image_2,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: import_cookies(),
    relief="flat"
)
button_2.place(
    x=184.0,
    y=132.0,
    width=230.0,
    height=60.0
)

button_image_3 = PhotoImage(
    file=relative_to_assets("button_3.png"))
button_3 = Button(
    image=button_image_3,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: check(),
    relief="flat"
)
button_3.place(
    x=184.0,
    y=247.0,
    width=230.0,
    height=60.0
)

canvas.create_text(
    201.0,
    356.0,
    anchor="nw",
    text="Output Path",
    fill="#000000",
    font=("SegoeFluentIcons", 20 * -1)
)

canvas.create_text(
    201.0,
    391.0,
    anchor="nw",
    text="Select a folder",
    fill="#000000",
    font=("SegoeFluentIcons", 20 * -1)
)

button_image_4 = PhotoImage(
    file=relative_to_assets("button_4.png"))
button_4 = Button(
    image=button_image_4,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: home(),
    relief="flat"
)
button_4.place(
    x=42.0,
    y=140.0,
    width=77.0,
    height=77.0
)

button_image_5 = PhotoImage(
    file=relative_to_assets("button_5.png"))
button_5 = Button(
    image=button_image_5,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: settings(),
    relief="flat"
)
button_5.place(
    x=42.0,
    y=357.0,
    width=77.0,
    height=77.0
)

button_image_6 = PhotoImage(
    file=relative_to_assets("button_6.png"))
button_6 = Button(
    image=button_image_6,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: webbrowser.open("https://discord.com/invite/RSCdKeKB5X"),
    relief="flat"
)
button_6.place(
    x=42.0,
    y=466.0,
    width=77.0,
    height=77.0
)

canvas.create_text(
    195.0,
    29.0,
    anchor="nw",
    text="Welcome user",
    fill="#FFFFFF",
    font=("Segoe UI Variable", 40 * -1)
)

button_image_7 = PhotoImage(
    file=relative_to_assets("button_7.png"))
button_7 = Button(
    image=button_image_7,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("same"),
    relief="flat"
)
button_7.place(
    x=42.0,
    y=249.0,
    width=77.0,
    height=77.0
)

canvas.create_rectangle(
    152.0,
    -1.0,
    153.00003051757812,
    645.0,
    fill="#252525",
    outline="")

canvas.create_text(
    184.0,
    521.0,
    anchor="nw",
    text="Cookies Converted:",
    fill="#FFFFFF",
    font=("Segoe UI Variable", 24 * -1)
)

canvas.create_text(
    414.0,
    521.0,
    anchor="nw",
    text="--",
    fill="#FFFFFF",
    font=("Segoe UI Variable", 24 * -1)
)

button_image_8 = PhotoImage(
    file=relative_to_assets("button_8.png"))
button_8 = Button(
    image=button_image_8,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: output_cookies(),
    relief="flat"
)
button_8.place(
    x=438.4193420410156,
    y=390.1693420410156,
    width=36.29570007324219,
    height=34.56182861328125
)

image_image_3 = PhotoImage(
    file=relative_to_assets("image_3.png"))
image_3 = canvas.create_image(
    807.0,
    373.0,
    image=image_image_3
)

canvas.create_text(
    554.0,
    169.0,
    anchor="nw",
    text="---------------",
    fill="#000000",
    font=("Segoe UI Variable", 12 * -1)
)

canvas.create_text(
    546.0,
    104.0,
    anchor="nw",
    text="Log",
    fill="#FFFFFF",
    font=("Segoe UI Variable", 24 * -1)
)
window.resizable(False, False)
window.mainloop()
