# ref : https://stackoverflow.com/questions/8948/accessing-mp3-metadata-with-python

import os
import glob
import re
from mutagen.easyid3 import EasyID3

mp3_path = os.path.realpath(r'D:\_AudibleFiles\MP3\Test2')

tagConfig={
    'album':u'Der Weihnachtosaurus',
    'artist': u'Tom Fletcher',
    'genre': u'Hörbuch',
    'title': u'Tom Fletcher',
    'tracknumber': '0',
    'date': '2017',
    # discnumber, composer, performer 
}

def mp3_changeTags(tags,tagConfig):
    for key in tagConfig.keys():
        tags[key]=tagConfig[key]
    tags.save()

def mp3tag_test(tags):   
    if song is not None:
        print(tags._filename)

def mp3tag_listAllTags():  
     tags = EasyID3.valid_keys.keys()
     for t in sorted(tags): 
        print(f'\t-{t}')


#  ========================================
#               Main Execution
#  ========================================
        
# mp3tag_listAllTags()

songs = glob.glob(os.path.join(mp3_path,'*.mp3'))   # script should be in directory of songs.
for index,song in enumerate(songs):
    # if index >=1:
    #     break

    tags= EasyID3(song)  
        
    # mp3tag_test(tags)
    filename=os.path.basename(song)
    # numbers = re.findall(r'\d+', filename)
    # print(numbers)
    tracknr = re.findall(r'\d+', os.path.splitext(filename)[0])[0]
    print(f"{index:03d}/{len(songs):03d}:  {song} :: basename = {filename} | tracknr = {tracknr}")
    tagConfig['tracknumber']=tracknr
    tagConfig['title']=f'Track {tracknr}'
    mp3_changeTags(tags,tagConfig)