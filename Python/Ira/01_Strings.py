# mit <#> kann man Kommentare schreiben, diese Zeilen werde nicht ausgeführt

# Text auf der Console ausgeben
print('Say: Hello World!')
print('') # Leerzeile in console

# Variablen erzeugen und Werte zuweisen
var1 = 1        # integer
var2 = 1.0      # float
var3 = "Text1"  # string
var4 = 'Text2'  # string

# Variablen in Console ausgeben (via print)
print(var1)
print(var2)
print(var3)
print(var4)
print('') # Leerzeile in console

# strings zusammen fügen
s1 = "String1"
s2 = "String2"
s = s1+s2
print(s+'\n')  # neuer string mit Leerzeile <\n> am Ende

# formatierten String ausgeben
#  \t = tab, \n Zeilenumbruch
# f"{var}": mit dem f for dem String können Variablen einbettet werden. Diese müssen in {...} stehen  
formated_string = f"formated f-string::\t{s1} ; {s2} \n" 
print(formated_string)
