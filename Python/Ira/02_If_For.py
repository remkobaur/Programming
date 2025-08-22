# Ganz wichtig bei Python ist der Tabulator/Einschub
# - für if-elif-else muss alles was z.B. for if == True ausgeführt werden soll, entsprechend eingerückt sein
# - dasselbe gilt für for Schleifen

# Außerdem ganz wichtig:
# - der Doppelpunkt nach if, elif,else, for (ganzer Schleifenkopf)

print("\n# ---- if ---")
a = True # True / False
if a:
    print("a is True")


print("\n# ---- if else ---")
a = True # True / False
if a:
    print("a is True")
else:
    print("a is False")

print("\n# ---- elif ---")
n = 3
if n == 1:
    print("n is 1")
elif n==2:
    print("n is 2")
elif n==3:
    print("n is 3")
else:
    print("n is not 1 or 2 or 3")


print("\n# ---- loop for each element k in defined array ---")
for k in [1,2,3,4]:  # array is defined by [] and contains 1,2,3,4
    print(f"\t k = {k}")

# An array kann contain everything of the same type
my_array = [
    "Hund",
    "Katze",    "Maus",
]
for k in my_array:  # array is defined by [] and contains 1,2,3,4
    print(f"\t k = {k}")

print("\n# ---- loop for k=1 until 10 ---")
n = 10
for k in range(n):  # array is defined by [] and contains 1,2,3,4
    print(f"\t k = {k}")
