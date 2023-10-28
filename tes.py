from tkinter import *
from PIL import Image, ImageTk

root = Tk()

# Open an image with Pillow
image = Image.open("assets/home/button_4.png")
tk_image = ImageTk.PhotoImage(image)

label = Label(root, image=tk_image)
label.pack()

root.mainloop()
