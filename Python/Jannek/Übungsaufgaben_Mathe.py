import os
import numpy as np
import random
import Mathe_Class

os.system('cls')
#prevLine = "\033[1A \033[9C "
prevLine = "\t\t"

N = 1
MT = Mathe_Class.Mathe_Class(N)
MT.tasktypes =[1,2,3,4]


okay = 0
for k in range(N):
    if MT.do_task(k):
        okay +=1
print("===========================================")
print(f"Ergebnis: \t {okay} von {N} richtig")
print("===========================================")