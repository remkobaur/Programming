import tkinter as tk
from tkinter import ttk
import os
import numpy as np
import random

from Class_GUI import Class_GUI 
from Mathe_Class import Mathe_Class

os.system('cls')


N = 10
ErrorRate = int(3)

GUI = Class_GUI('Correction Test',N,3,"Exercise")
# GUI.create_Table_Example()
GUI.Header = ["Aufgabe","Ergebnis","Lösung"]
GUI.colalign = ['e','w','e'] 
GUI.coltype = ['label','edit','label']
GUI.colwidth = [15]*GUI.Cols
GUI.colwidth[1] = 9 


Test = Mathe_Class(N)
Test.tasktypes =[1,2,3,4]
Test.clear_tasklist()
Test.create_tasklist()

# print("Tasklist:")
# print(Test.tasklist)


for r in range(0,GUI.Rows):
    val = r+1
   
    t= Test.tasklist[r]
    # manupulate result
  
    rowdata =[None]*GUI.Cols
    rowdata[0] = f"{t.task} = "
    rowdata[1] = f"{t.result}"     
    GUI.TableData[r] = rowdata

# GUI.print_table()

GUI.create_Table()
GUI.create_Control_Buttons()
GUI.window.mainloop()