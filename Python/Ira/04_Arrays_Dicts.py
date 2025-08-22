# Ein array fasst mehrere Elemente eines Typs in einer variable zusammen
# arrays werden definiert mit []

wait_activated = True

def my_title(title):
    print(f"\n>>> {title} <<<")

def wait():
    if wait_activated:
        input(" * press key to continue *  ")  # wait for keyboard button press and print text before
    else:
        pass # pass means do nothing, but after ":" some command is required

my_title("Print string array")
A = ["Pizza","Nudel","Reis"]
for k,val in enumerate(A): # Schleife über alle Elemente von Array A, wobei k der Index und val der Wert des Elements ist.
    print(f"{k} = {val} ")
wait()


my_title("Print range() array")
B = range(20)
for k,val in enumerate(B): # Schleife über alle Elemente von Array B, wobei k der Index und val der Wert des Elements ist.
    print(f"{k} = {val} ")
wait()


my_title("Print modified Array")
C = [   k+100 for k in B ]
for k,val in enumerate(C): # Schleife über alle Elemente von Array C, wobei k der Index und val der Wert des Elements ist.
    print(f"{k} = {val} ")
wait()


my_title("Print nested Arrays") # z.B. Matrix oder Tabelle 
D = [
    [1,2,3],
    [4,5,6],
    [7,8,9],
]
for r,row in enumerate(D): 
    s = "" # leerer String
    for c,val in enumerate(row): 
        s+=f"\t{val}"
    print(f"row {r} = [{s}] ")
    
# dictionary, alias dict ist eine Erweiterung des des Array ähnlich einer Tabelle
# - eine dict wird mit {...} deklariert 
my_title("definition of a dict") # z.B. Matrix oder Tabelle 

dict_empty = {}
print(f"'dict_empty' ={dict_empty}") # ! string im string muss unterschiedliche quotes haben, sonst fehler: "'Zitat'" oder '"Zitat"' 

dict_predefined = {
    "Feld1":"Name",
    "Feld2":[1,2,3],
    "Feld3":7.0,
    }
print(f"'dict_predefined' ={dict_predefined}")

dict_append = dict_empty
dict_append["Feld4"] = "neu hinzugefügt"
dict_append[2] = 12.0  # key bezeichnung muss kein String sein, sondern kann auch eine Zahl sein
print(f"'dict_append' ={dict_append}")

print(f"keys of dict 'dict_append' ={dict_append.keys()}")

my_title("iterate over dict keys") # z.B. Matrix oder Tabelle 
d = dict_append
for key,value in d.items():
    print(f"dict['{key}'] = {value}")