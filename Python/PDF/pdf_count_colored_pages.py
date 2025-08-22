
import numpy as np
import os
file_pdf = "D:/GIT/Latex/Dissertation/Dissertation.pdf"

file_log = file_pdf.replace(".pdf",".log").replace("D:/GIT/Latex/Dissertation/","D:/GIT/Programming/Python/PDF/")

cmd = f"D:/Prox/gs/gs10.02.0/bin/gswin64.exe -q  -o {file_log} -sDEVICE=inkcov {file_pdf}"
os.system(f'cmd /c "{cmd}"')


with open(file_log, "r") as data:
    r= [line.split() for line in data]

pages_black=0
pages_color=0
for i,l in enumerate(r):
    b=l[0]=='0.00000'and l[1]=='0.00000' and l[2]=='0.00000'
    if b:
        pages_black +=1
    else:
        pages_color +=1
        print(f"page {i+1} is colored")

print(f"the PDF <{file_pdf}> has {pages_black} black and {pages_color} colored pages")