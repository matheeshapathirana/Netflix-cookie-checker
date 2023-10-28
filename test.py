import tkinter as tk
from tkinter import Button, Canvas, PhotoImage
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / Path("assets/home")


def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)


class UserInterface:
    def __init__(self, window):
        self.window = window
        self.setup_window()
        self.create_canvas()
        self.create_buttons()
        self.create_elements_on_canvas()

    def setup_window(self):
        self.window.geometry("1090x645")
        self.window.configure(bg="#FFFFFF")
        self.window.resizable(False, False)

    def create_canvas(self):
        self.canvas = Canvas(
            self.window,
            bg="#FFFFFF",
            height=645,
            width=1090,
            bd=0,
            highlightthickness=0,
            relief="ridge"
        )
        self.canvas.place(x=0, y=0)

    def create_buttons(self):
        self.buttons = []
        button_images = [
            "button_1.png",
            "button_2.png",
            "button_3.png",
            "button_4.png",
            "button_5.png",
            "button_6.png",
            "button_7.png",
            "button_8.png"
        ]
        button_commands = [
            lambda: print("button_1 clicked"),
            lambda: print("button_2 clicked"),
            lambda: print("button_3 clicked"),
            lambda: print("button_4 clicked"),
            lambda: print("button_5 clicked"),
            lambda: print("button_6 clicked"),
            lambda: print("button_7 clicked"),
            lambda: print("button_8 clicked")
        ]

        for i in range(8):
            button_image = PhotoImage(file=relative_to_assets(button_images[i]))
            button = Button(
                image=button_image,
                borderwidth=0,
                highlightthickness=0,
                command=button_commands[i],
                relief="flat"
            )
            button.place(x=42.0, y=29.0 + i * 111, width=77.0, height=77.0)
            self.buttons.append(button)

    def create_elements_on_canvas(self):
        image_1 = PhotoImage(file=relative_to_assets("image_1.png"))
        self.canvas.create_image(545.0, 322.0, image=image_1)

        image_2 = PhotoImage(file=relative_to_assets("image_2.png"))
        self.canvas.create_image(341.0, 389.0, image=image_2)

        image_3 = PhotoImage(file=relative_to_assets("image_3.png"))
        self.canvas.create_image(807.0, 373.0, image=image_3)

        self.canvas.create_rectangle(160.0, 0.0, 1098.0, 645.0, fill="#000000", outline="")
        self.canvas.create_rectangle(0.0, 0.0, 160.0, 645.0, fill="#000000", outline="")
        self.canvas.create_rectangle(152.0, -1.0, 153.00003051757812, 645.0, fill="#252525", outline="")

        self.canvas.create_text(201.0, 356.0, anchor="nw", text="Output Path", fill="#000000", font=("SegoeFluentIcons", 20 * -1))
        self.canvas.create_text(201.0, 391.0, anchor="nw", text="FOLDER", fill="#000000", font=("SegoeFluentIcons", 20 * -1))
        self.canvas.create_text(195.0, 29.0, anchor="nw", text="Welcome user", fill="#FFFFFF", font=("Segoe UI Variable", 40 * -1))
        self.canvas.create_text(184.0, 521.0, anchor="nw", text="Cookies Converted:", fill="#FFFFFF", font=("Segoe UI Variable", 24 * -1))
        self.canvas.create_text(414.0, 521.0, anchor="nw", text="--", fill="#FFFFFF", font=("Segoe UI Variable", 24 * -1))
        self.canvas.create_text(554.0, 169.0, anchor="nw", text="---------------", fill="#000000", font=("Segoe UI Variable", 12 * -1))
        self.canvas.create_text(546.0, 104.0, anchor="nw", text="Log", fill="#FFFFFF", font=("Segoe UI Variable", 24 * -1))


if __name__ == "__main__":
    window = tk.Tk()
    user_interface = UserInterface(window)
    window.mainloop()
