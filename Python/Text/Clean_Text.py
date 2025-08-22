import re
text = """ 
Im Falle des Kraftstoffsystems ergeben sich bezüglich der durchströmten Komponenten sehr geringe
Höhenunterschiede, sodass die potentielle Energie hier vernachlässigt werden kann. Durch Umstel-
len von Gl. (2.4) nach der Fluidgeschwindigkeit folgt mit der 
"""

TextFile_in = r'C:\Users\PC_Oxygen\Desktop\Dissertation.txt'.replace('\\','/')
TextFile_in = r'C:\Users\PC_Oxygen\Desktop\Kurzfassung.txt'.replace('\\','/')
TextFile_Out = TextFile_in.replace('.txt','-clean.txt')                                                            


def file_read(fname):
    with open(fname, 'r', encoding='utf-8') as f:
        text = f.read()
        f.close()
    return text

def file_write(fname,text):
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(text)

def clean_text(text):
    # remove line breakes
    text = re.sub('-\n','', text).strip()
    text = re.sub('\n',' ', text).strip()
    text = re.sub('Entwurf: Stand vom 14.07.2023',' ', text).strip()
    
    return text

text=file_read(TextFile_in)
text_clean = clean_text(text)
file_write(TextFile_Out,text_clean)

