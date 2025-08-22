# ref: https://docs.python.org/3/library/xml.etree.elementtree.html

import xml.etree.ElementTree as ET
# import xmltodict
import os

noteVals={
    "C":1,
    "D":2,
    "E":3,
    "F":4,
    "G":5,
    "A":6,
    "B":7,

}
from xml.etree import cElementTree as ElementTree
class XmlListConfig(list):
    def __init__(self, aList):
        for element in aList:
            if element:
                # treat like dict
                if len(element) == 1 or element[0].tag != element[1].tag:
                    self.append(XmlDictConfig(element))
                # treat like list
                elif element[0].tag == element[1].tag:
                    self.append(XmlListConfig(element))
            elif element.text:
                text = element.text.strip()
                if text:
                    self.append(text)
class XmlDictConfig(dict):
    '''
    Example usage:

    >>> tree = ElementTree.parse('your_file.xml')
    >>> root = tree.getroot()
    >>> xmldict = XmlDictConfig(root)

    Or, if you want to use an XML string:

    >>> root = ElementTree.XML(xml_string)
    >>> xmldict = XmlDictConfig(root)

    And then use xmldict for what it is... a dict.
    '''
    def __init__(self, parent_element):
        if parent_element.items():
            self.update(dict(parent_element.items()))
        for element in parent_element:
            if element:
                # treat like dict - we assume that if the first two tags
                # in a series are different, then they are all different.
                if len(element) == 1 or element[0].tag != element[1].tag:
                    aDict = XmlDictConfig(element)
                # treat like list - we assume that if the first two tags
                # in a series are the same, then the rest are the same.
                else:
                    # here, we put the list in dictionary; the key is the
                    # tag name the list elements all share in common, and
                    # the value is the list itself 
                    aDict = {element[0].tag: XmlListConfig(element)}
                # if the tag has attributes, add those to the dict
                if element.items():
                    aDict.update(dict(element.items()))
                self.update({element.tag: aDict})
            # this assumes that if you've got an attribute in a tag,
            # you won't be having any text. This may or may not be a 
            # good idea -- time will tell. It works for the way we are
            # currently doing XML configuration files...
            elif element.items():
                self.update({element.tag: dict(element.items())})
            # finally, if there are no child tags and no attributes, extract
            # the text
            else:
                self.update({element.tag: element.text})
               
        def example():
            filename = 'Gone Away - Offspring.musicxml'
            tree = ET.parse(os.path.join(Path,filename))
            root = tree.getroot()

            xmldict = XmlDictConfig(root)

            for meas in xmldict['part']['measure']:
                print(meas)
                
Path = os.path.abspath(os.path.dirname(__file__))

filename = 'Gone Away - Offspring.musicxml'
tree = ET.parse(os.path.join(Path,filename))
root = tree.getroot()
 
# tree.write(os.path.join(Path,filename.replace(".","3.")), encoding = "UTF-8", xml_declaration = True)

for part in root.iter('part'):
    if not part.tag == "part":
        continue 
    for meas in part.iter('measure'):
        if not meas.tag == "measure":
            continue
        # print(meas.attrib)
        for note in part.iter('note'):
            if not note.tag == "note":
                continue
            pitch = note.find('pitch')
            if pitch is None:
                continue
            staff = note.find('staff')
            voice = note.find('voice')
            # for pitch in note.iter('pitch'):
            #     if not pitch.tag == "pitch":
            #         continue
            
            step = pitch.find('step')
            octave = int(pitch.find('octave').text)
            
            if staff.text == "1":  # violin
                if octave <= 3 and noteVals[step.text] < noteVals["B"]:
                    print(f"Note: {step.text}{octave}  -  staff= {staff.text}    right -> left")
                    # pitch.set("octave",f"{octave+1}")
                    staff.text="2"
                    voice.text="2"
                    pitch.find('octave').text=str(octave-1)
                # print(f"Note: {step}{octave}")
                # if octave >= 3 and pitch.find('step').text=="E" and voice == "1":
            elif staff.text == "2": 
                if octave >= 3 and  noteVals[step.text] >= noteVals["C"]:
                    print(f"measure={meas.get('number')}\tNote: {step.text}{octave}  -  staff= {staff.text} left -> right")
                    # pitch.set("octave",f"{octave+1}")
                    staff.text="1"
                    voice.text="1"
                    pitch.find('octave').text=str(octave+1)
                # pitch.find('octave').text="5"#str(octave+1)
                    


tree.write(os.path.join(Path,filename.replace(".","2.")), encoding = "UTF-8", xml_declaration = True)

