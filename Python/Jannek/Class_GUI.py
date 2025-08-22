import tkinter as tk
from tkinter import ttk

class Class_GUI:
    Rows = 10
    Cols = 2
    Header=[]
    TableData=[]

    colwidth =[]
    colalign =[]
    coltype = []
    tab_pad_x= 1
    tab_pad_y= 5
    window =None

    check_vars = []
    status_vars = []
    inputs=[]

    def __init__(self,title='my window',_r=10,_c=3,_mode = "Correction"):
        self.window = self.create_sized_window(title,600,800)
        self.Rows = _r # +1 for table header
        self.Cols = _c
        self.colwidth = [25]*_c
        self.colalign = ['e']*_c
        self.coltype = ['label']*_c
        self.Header = [None]*_c
        self.TableData = [['']*_c]*_r 
        self.check_vars = [-1]*_r
        self.status_vars = [True]*_r
        self.inputs = ['']*_r
        self.mode = _mode

    def create_sized_window(self,title='my window',window_width = 300,window_height = 200):
        win = tk.Tk()
        win.title(title)

        # get the screen dimension
        screen_width = win.winfo_screenwidth()
        screen_height = win.winfo_screenheight()

        # find the center point
        center_x = int(screen_width/2 - window_width / 2)
        center_y = int(screen_height/2 - window_height / 2)

        # set the position of the window to the center of the screen
        win.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        return win
    
    def create_Table(self):
        frame = ttk.Frame(self.window)
        frame.pack(padx=10, pady=10,expand=True)
        frame.columnconfigure(self.Cols, weight=1)
        frame.rowconfigure(self.Rows+1, weight=1)

      
        for c in range(0,self.Cols):
            ttk.Label(frame, text=self.Header[c],
                    background="grey", foreground="black",font="Helvetica 16 bold",width=self.colwidth[c]).grid(column=c, row=0, sticky=tk.EW, padx=self.tab_pad_x, pady=self.tab_pad_y)


        for r in range(0,self.Rows):
            for c in range(0,self.Cols):
                match self.coltype[c]:
                    case "label":
                        username_label = ttk.Label(frame, text=self.TableData[r][c],
                                                background="lightgray", foreground="black",font="Helvetica 14 ",width=self.colwidth[c],anchor=self.colalign[c])
                        username_label.grid(column=c, row=r+1, sticky=tk.EW, padx=self.tab_pad_x, pady=self.tab_pad_y)
                        
                    case "check":
                        self.check_vars[r] = tk.IntVar()
                        self.check_vars[r].set(-1)
                        # ttk.Checkbutton(frame, text="Korrekt", variable=var2).grid(column=c, row=r+1, sticky=tk.EW, padx=self.tab_pad_x, pady=self.tab_pad_y)
                        frameRB = ttk.Frame(frame)
                        frameRB.columnconfigure(2, weight=1)
                        frameRB.rowconfigure(1, weight=1)
                        ttk.Radiobutton(frameRB, text="richtig", variable=self.check_vars[r], value=1).grid(column=0, row=1, sticky=tk.EW, padx=self.tab_pad_x, pady=self.tab_pad_y)
                        ttk.Radiobutton(frameRB, text="falsch",  variable=self.check_vars[r], value=0).grid(column=1, row=1, sticky=tk.EW, padx=self.tab_pad_x, pady=self.tab_pad_y)                        
                        frameRB.grid(column=c, row=r+1, sticky=tk.EW, padx=self.tab_pad_x, pady=self.tab_pad_y)
                    case "edit":
                        self.inputs[r] = tk.Entry(frame,justify='center')
                        self.inputs[r].grid(column=c, row=r+1, sticky=tk.EW, padx=self.tab_pad_x, pady=self.tab_pad_y)
                    case _:
                        print(f"unknown column type <{self.coltype[c]}>") 
    def check_missing_answers(self):  
        cnt = 0
        for r in range(self.Rows):
            if self.check_vars[r].get() == -1:
                cnt +=1        
        if cnt > 0:
            var = tk.IntVar()
            win = tk.Toplevel()
            win.title("Fehlende Antworten")
            message = f"Du hast {cnt} Aufgaben noch nicht beantwortet. Trotzdem Bewerten?"
            tk.Label(win, text=message).pack()
            tk.Button(win, text='Ja', command=lambda: var.set(1)).pack(side="left")
            tk.Button(win, text='Nein', command=lambda: var.set(0)).pack(side="left")

            win.wait_variable(var)
            win.destroy()
            if var.get()==1:
                return True
            else:
                return False
        else:
            return True
            
    def actionEval_Correct(self):
        if not self.check_missing_answers():
            return

        cnt = 0
       
        for r in range(self.Rows):
            match self.check_vars[r].get():
                case -1:                  
                        self.log(f"{r} : Keine Auswahl erfolgt ! -> value = {self.check_vars[r].get()}")
                case 0:
                    if not self.status_vars[r]:
                        self.log(f"{r} : Richtig ! -> Wahl = {self.check_vars[r].get()} ; Status = {self.status_vars[r]}")
                        cnt +=1
                    else:
                        self.log(f"{r} : Falsch ! -> Wahl = {self.check_vars[r].get()} ; Status = {self.status_vars[r]}")
                case 1:
                    if self.status_vars[r]:
                        self.log(f"{r} : Richtig ! -> Wahl = {self.check_vars[r].get()} ; Status = {self.status_vars[r]}")
                        cnt +=1
                    else:
                        self.log(f"{r} : Falsch ! -> Wahl = {self.check_vars[r].get()} ; Status = {self.status_vars[r]}")
                case _:
                    print(f"{r} : unknown value !! -> value = {self.check_vars[r].get()}")
        return cnt
    
    def actionEval_Exercise(self):
        cnt = 0
        for r in range(self.Rows):
            inp = self.inputs[r].get()
            if not inp.isdigit():
                print(f"{r} : input is no int --> {inp}")
                continue
            else: 
                inp = int(inp)
                result = self.TableData[r][1]
                print(f"{r} : input = {inp} | result = {result}")
                if inp==int(result):
                    cnt +=1        
            
        return cnt
        
    def actionEval(self):
        print("Bewertung gestartet:")
        match self.mode:
            case "correction":
                cnt = self.actionEval_Correct()
            case "Exercise":
                cnt = self.actionEval_Exercise()
            case _: 
                print(f"actionEval() : unknown mode!! -> value = {self.mode}")   

        self.resul_label.config(text =f"{cnt} / {self.Rows}")

    def actionExit(self):
        print("Test Beenden")
        self.window.destroy()
    
    def log(self,msg):
        pass
        # print(msg)

    def create_Control_Buttons(self):
        frameCB = ttk.Frame(self.window)
        frameCB.pack(padx=10, pady=10,expand=True)
        frameCB.columnconfigure(2, weight=1)
        frameCB.rowconfigure(2, weight=1)
        B_Eval = tk.Button(frameCB, text="Test Bewerten", command=self.actionEval).grid(column=0, row=0, sticky=tk.EW, padx=self.tab_pad_x, pady=self.tab_pad_y)
        B_Exit = tk.Button(frameCB, text="Beenden", command=self.actionExit).grid(column=1, row=0, sticky=tk.EW, padx=self.tab_pad_x, pady=self.tab_pad_y)
        tk.Label(frameCB, text="Ergebnis:").grid(column=0, row=1, sticky=tk.EW, padx=self.tab_pad_x, pady=self.tab_pad_y)
        self.resul_label=tk.Label(frameCB, text=f"? / {self.Rows}")
        self.resul_label.grid(column=1, row=1, sticky=tk.EW, padx=self.tab_pad_x, pady=self.tab_pad_y)
        frameCB.pack()

    def print_table(self):        
        print(self.Header)
        for r in range(1,self.Rows):
            print(self.TableData[r])

    def create_Table_Example(self):
        for c in range(0,self.Cols):
            self.Header[c] = f"Title ({c})"
        for r in range(0,self.Rows):
            row = [None]*self.Cols
            for c in range(self.Cols):
                row[c] =f"Cell ({r},{c})"                                       
            self.TableData[r] = row
    def create_Table_exercises(self):
        R = self.Rows
        C = self.Cols
        frame = ttk.Frame(self.window)
        frame.pack(padx=10, pady=10,expand=True)
        frame.columnconfigure(C, weight=1)
        frame.columnconfigure(R, weight=1)

        for c in range(C):
            ttk.Label(frame, text=self.Header[c],
                    background="yellow", foreground="blue",width=25).grid(column=c, row=0, sticky=tk.EW, padx=self.tab_pad_x, pady=self.tab_pad_y)


        for r in range(2,R):
            for c in range(C):
                username_label = ttk.Label(frame, text=f"Cell ({r},{c})",
                                        background="blue", foreground="yellow",width=25)
                username_label.grid(column=c, row=r, sticky=tk.EW, padx=self.tab_pad_x, pady=self.tab_pad_y)