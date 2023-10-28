import subprocess
import webbrowser
from pathlib import Path

def home():
    window.destroy()
    subprocess.run(["python", "main.py"])

def converter():
    window.destroy()
    subprocess.run(["python", "converter.py"])

from tkinter import Tk, Canvas, Entry, Text, Button, PhotoImage


OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / Path("assets/settings")


def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)


window = Tk()
window.title("Netflix Cookie Checker - Settings")
# img = PhotoImage(file='assets/netflix.png')
# window.iconphoto(False, img)

window.geometry("1090x645+250+250")
window.configure(bg = "#FFFFFF")


canvas = Canvas(
    window,
    bg = "#FFFFFF",
    height = 645,
    width = 1090,
    bd = 0,
    highlightthickness = 0,
    relief = "ridge"
)

canvas.place(x = 0, y = 0)
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
    command=lambda: print("button_1 clicked"),
    relief="flat"
)
button_1.place(
    x=37.0,
    y=29.0,
    width=87.0,
    height=87.0
)

button_image_2 = PhotoImage(
    file=relative_to_assets("button_2.png"))
button_2 = Button(
    image=button_image_2,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print('enable disable'),
    relief="flat"
)
button_2.place(
    x=400.0,
    y=148.0,
    width=134.0,
    height=44.0
)

button_image_3 = PhotoImage(
    file=relative_to_assets("button_3.png"))
button_3 = Button(
    image=button_image_3,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: window.destroy(),
    relief="flat"
)
button_3.place(
    x=195.0,
    y=574.0,
    width=134.0,
    height=44.0
)

button_image_4 = PhotoImage(
    file=relative_to_assets("button_4.png"))
button_4 = Button(
    image=button_image_4,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("reset"),
    relief="flat"
)
button_4.place(
    x=354.0,
    y=574.0,
    width=134.0,
    height=44.0
)

button_image_5 = PhotoImage(
    file=relative_to_assets("button_5.png"))
button_5 = Button(
    image=button_image_5,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: webbrowser.open("https://github.com/matheeshapathirana/Netflix-cookie-checker"),
    relief="flat"
)
button_5.place(
    x=513.0,
    y=574.0,
    width=134.0,
    height=44.0
)

canvas.create_text(
    195.0,
    160.0,
    anchor="nw",
    text="Use Minimized",
    fill="#FFFFFF",
    font=("SegoeFluentIcons", 20 * -1)
)

button_image_6 = PhotoImage(
    file=relative_to_assets("button_6.png"))
button_6 = Button(
    image=button_image_6,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: home(),
    relief="flat"
)
button_6.place(
    x=42.0,
    y=140.0,
    width=77.0,
    height=77.0
)

button_image_7 = PhotoImage(
    file=relative_to_assets("button_7.png"))
button_7 = Button(
    image=button_image_7,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print('same'),
    relief="flat"
)
button_7.place(
    x=42.0,
    y=357.0,
    width=77.0,
    height=77.0
)

button_image_8 = PhotoImage(
    file=relative_to_assets("button_8.png"))
button_8 = Button(
    image=button_image_8,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: webbrowser.open("https://discord.com/invite/RSCdKeKB5X"),
    relief="flat"
)
button_8.place(
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

button_image_9 = PhotoImage(
    file=relative_to_assets("button_9.png"))
button_9 = Button(
    image=button_image_9,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: converter(),
    relief="flat"
)
button_9.place(
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
window.resizable(False, False)
window.mainloop()
