import tkinter as tk
from tkinter import ttk

# tk._test()
 
def create_sized_window(title='my window',window_width = 300,window_height = 200):

    window = tk.Tk()
    window.title(title)

    # get the screen dimension
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    # find the center point
    center_x = int(screen_width/2 - window_width / 2)
    center_y = int(screen_height/2 - window_height / 2)

    # set the position of the window to the center of the screen
    window.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
    return window

def create_Table(win,R=3,C=2):
    pad_x= 1
    pad_y= 5
    frame = ttk.Frame(win)
    frame.pack(padx=10, pady=10,expand=True)
    frame.columnconfigure(C-1, weight=1)
    frame.columnconfigure(R-1, weight=1)

    for c in range(C):
        ttk.Label(frame, text=f"Title ({c})",
                background="yellow", foreground="blue",width=25).grid(column=c, row=0, sticky=tk.EW, padx=pad_x, pady=pad_y)


    for r in range(2,R):
        for c in range(C):
            username_label = ttk.Label(frame, text=f"Cell ({r},{c})",
                                       background="blue", foreground="yellow",width=25)
            username_label.grid(column=c, row=r, sticky=tk.EW, padx=pad_x, pady=pad_y)


def evhan_return_pressed(event):
    print('Return key was pressed')
def log(event):
    print(event)

def event_buttonA(val):
    print(f'Button {val} clicked')

def create_Gui():
    # win = tk.Tk()
    # win.title('My tkinter Demo')
    win = create_sized_window('My tkinter Demo',800,600)
    win.attributes('-alpha', 0.9)

    ttk.Label(win, text='Hi, there').pack()
    ttk.Button(win, text='Button A',command=lambda: event_buttonA('A')).pack()

    frame = ttk.Frame(win)
    frame.pack(padx=10, pady=10,fill='x',expand=True)

    email_label = ttk.Label(frame, text="Email Address:")
    email_label.pack(fill=tk.BOTH, expand=False,side=tk.LEFT)

    email = tk.StringVar()
    email_entry = ttk.Entry(frame, textvariable=email)
    email_entry.pack(fill=tk.BOTH, expand=False,side=tk.LEFT)
    email_entry.focus()

    # multi event handling SAVE Button
    btn = ttk.Button(win, text='Save')
    btn.bind('<Return>', evhan_return_pressed)
    btn.bind('<Return>', log, add='+')
    btn.focus()
    btn.pack()


    # win = tk.Label(win, text="Hello, world!")
    # win = tk.Label(win,text="Hello, Tkinter", fg="white", bg="black")

    # win = tk.Button(win,
    #     text="Click me!",
    #     width=25,
    #     height=5,
    #     bg="blue",
    #     fg="yellow",
    # )
    # win = tk.Entry(win)
    # win.pack
    win.mainloop()
    # label = tk.Label(text="Hello, Tkinter", fg="white", bg="black")
    # button = tk.Button(
    #     text="Click me!",
    #     width=25,
    #     height=5,
    #     bg="blue",
    #     fg="yellow",
    # )
    # entry = tk.Entry()
    return win

def create_Gui_Table():
    win = create_sized_window('Table Demo',800,600)
    create_Table(win,10,4)
    win.mainloop()
    return win

# window = create_Gui()
window = create_Gui_Table()
