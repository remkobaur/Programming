#import os
import numpy as np
import random

class Exercise:
    task = ''
    result = 0
    guess = 0
    check = True

    def __init__(self,_t,_r):
        self.task = _t
        self.result = _r

class Mathe_Class:
    tasktypes =[1,2,3,4]
    N = 10

    tasklist = {}


    def __init__(self,_N):
        self.N = _N
        self.tasktypes =[1,2,3,4]

    def clear_tasklist(self):
        self.tasklist=[]
    
    def create_tasklist(self):
        for k in range(self.N):
            self.create_task()

    def create_task(self):
        i = random.randint(1,len(self.tasktypes))
        type = self.tasktypes[i-1]
        match type: 
            case 1:
                task,r=self.add()
            case 2:
                task,r=self.sub()
            case 3:
                task,r=self.mult()
            case 4:
                task,r=self.div()
            case _:
                print("unknown task type ")
                task = "??? "
                r = 0
        E = Exercise(task,r)
        # print(E)
        self.tasklist.append(E)
        return task,r
    
    def do_task(self,k):
        status = True
        task = ""
        r =0
        task,r =self.create_task()
        print(f"Aufgabe {k+1} von {self.N}: {task} = ")

        inp =""
        while not inp.isdigit():
            inp = input(task)
        if r == int(inp):
            print(f"\t\t --> \t Korrekt")
            
        else:
            print(f"\t\t --> \t Falsch: richtiges Ergebnis {task} = {r}")
            status = False
        #input()
        #os.system('cls')
        return status

    def add(self):
        a = random.randint(1,100)
        b = random.randint(1,100)
        r = a+b

        task = f"{a} + {b} "
        return task,r

    def sub(self):
        z = random.randint(1,10)*10
        a = random.randint(1,10)+z
        b = random.randint(1,a)
        r = a-b

        task = f"{a} - {b} "
        return task,r

    def mult(self):
        a = random.randint(1,10)
        b = random.randint(1,10)
        r = a*b
        task = f"{a} x {b} "
        return task,r

    def div(self):
        a = random.randint(1,10)
        b = random.randint(1,10)
        r = a*b

        task = f"{r} : {b} "
        return task,a

