# ref https://www.geeksforgeeks.org/cut-a-mp3-file-in-python/
import os
import numpy as np

from pydub import AudioSegment 
AudioSegment.converter =os.path.realpath(r'D:\Prox\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe')
AudioSegment.ffprobe   = os.path.realpath(r'D:\Prox\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe')

import pandas as pd
# import openpyxl 

path = r'D:\_AudibleFiles\MP3'
# filename = 'Weihnachtosaurus_Chap01_23'
# filename = 'Weihnachtosaurus_Chap24_31'
# filename = 'Weihnachtosaurus_Chap32'
filename = 'Weihnachtosaurus_Chap33_end'

mp3file = os.path.realpath(os.path.join(path,f'{filename}.mp3'))
xlsfile = os.path.realpath(os.path.join(path,f'{filename}.xlsx'))

print(mp3file)
print(os.path.isfile(mp3file))
print(AudioSegment.ffmpeg)
# exit(0)

def export_mp3_segment(song,path,start,stop,Name,ID):
    # pydub does things in milliseconds
    start *= 1000 # s->ms
    stop  *= 1000 # s->ms
    # song clip of from start to stop
    segment = song[int(start):int(stop)] 
    # save file 
    segment.export(os.path.join(path,f'{Name}.mp3'), format="mp3") 
    
#create dummy list
def create_example_list():
    tracks = []
    start = 0.0
    for k in range(10):
        dur = np.random.uniform(10,20)
        stop = start+dur
        track = {
            'title':f'Track_{k:03d}',
            'id':k,
            'start':start,
            'stop':stop,
            'duration':dur
        }
        start = stop
        tracks.append(track)
    return tracks

def import_tracklist(xlsfile):
    tab = pd.read_excel(xlsfile,   "Tabelle1")

    tracks =[]
    _start = 0.0
    # loop over rows
    for index, row in tab.iterrows():
        # if index ==0:
        #     continue
        stop = _start+row[2]
        print(f"row {index:03d} :: {row[0]} | {row[1]} | {row[2]} | {row[3]} | ")
        track={
            'title':f'Track_{row[3]:03d}',
            'id':row[3],
            'start':_start,
            'stop':stop,
            'duration':row[1]
        }
        _start = stop
        tracks.append(track)
   
    return tracks
# =========================================
#           Execute Main
# =========================================

# tracks = create_example_list()
tracks = import_tracklist(xlsfile=xlsfile)
# exit(0)
for t in tracks:
    print(f"{t['id']:03d} | start: {t['start']:6.0f} | stop: {t['stop']:6.0f} s | diff: {t['stop']-t['start']} | duration: {t['duration']}")
# exit()
# Open an mp3 file
print(f"loading file {mp3file} ...")
song = AudioSegment.from_mp3(mp3file) #, format="mp3"
print(f"... done.")

# exit(0)
for track in tracks:
    if song.duration_seconds<track['stop']:
        print(f"end of Track {track['id']} is longer than audio file --> Abort !")
        break
    # if track['id']>=40:
    #     break
    print(f"cutting track {track['id']} ...")
    export_mp3_segment(song,path=os.path.join(path,'Test'), start=track['start'], stop=track['stop'], Name=track['title'], ID=track['id'])

print("New Audio file is created and saved") 