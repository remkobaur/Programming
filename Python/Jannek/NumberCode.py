CodeNumber = [1,3,8,2,1,7,3,9]

def init_dict():
    print("init_dict()")

def show_code():
    code = ""
    for k in CodeNumber:
        code += str(k)
    print("CODE: ***"+ code+"***\n")

def encoder(text):
    code=""
    i = 0
    for letter in text:        
        code += shift_letter(letter, CodeNumber[i])
        i += 1
        i = i%len(CodeNumber)
    #print(code)
    return code

def decoder(code_text):
    text = ""
    i=0
    for letter in code_text:
        text += shift_letter(letter,-CodeNumber[i])
        i+=1
        i = i%len(CodeNumber)
    return text

def shift_letter(letter,num):
    ascii = ord(letter)
    if (ascii >=65) and (ascii <=90):
        offset = 65
    elif ascii >=97 and ascii <=122:
        offset = 97
    else:
        return letter
    shift = chr( (ascii +(num)-offset)%26 +offset) 
    #print(letter+"("+str(ascii)+") -> {"+str(num)+"} -> "+shift +"   offest("+str(offset)+")")
    return shift

def example():
    show_code()
    SecretText = "Hallo Jannek ich habe hunger, Quaki Quak !!!"
    #SecretText = "HELLO WORLD"

    encoded = encoder(SecretText)
    decoded = decoder(encoded)
    print("SecretText = "+SecretText)
    print("The encoded text is: "+encoded)
    print("The decoded code is: "+decoded)

example()
