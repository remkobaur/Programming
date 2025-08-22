# Conde Abschnitte die mehrfach verwendet werden sollten in "Methoden" / Funktionen ausgelagert werden
# - eine Funktion wird mit "def <function name>(parameter1,...):"  definiert

# Defintion der Methoden
def my_fun1(text):
    print(f">>> {text} <<< ;)")


def add1(a,b):
    print(f"{a} + {b} = {a+b}")

def add2(a,b):
    c = a+b
    return c   # Funktion übergibt Ergebnis <c> zurück an Aufrufer



# Verwendung der Methoden

my_fun1("Dies ist ein toller Text") 
add1(1,2)

add1("Apfel","Baum")

print(add2("Apfel","Baum"))   # Rückgabewert von add2 wird auf Console ausgegeben