import numpy as np
a = 1
b = 1
N = 30

x=[1,1]
for i in range(2,N):
    x.append( x[i-2]+x[i-1] )

print(x)

q =[]
for i in range(0,N-1):
    q.append(x[i+1]/x[i])

print("----------------")
print(q)


print(f"Calc:  {(1+np.sqrt(5))/2}")
print(f"Perc:  {1/((1+np.sqrt(5))/2)*100}")