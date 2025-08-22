#Sieb des Eratosthenes

import numpy as np
N_max = 1000

x=[]
for i in range(2,N_max+1):
    x.append(i)

ind_rm=[]
for d in range(2,N_max):
    ind_rm=[]
    for i,k in enumerate(x):
        if not k==d and k%d == 0 :
            ind_rm.append(i)
    for i in sorted(ind_rm, reverse=True):
        del x[i]
print(ind_rm,sep=", ")


print("Prime numbers computed by <sieve of eratosthenes>")
print(x, sep=", ")

