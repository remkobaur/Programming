# ref https://www.geeksforgeeks.org/cut-a-mp3-file-in-python/
import os
import numpy as np

from pydub import AudioSegment 
from pydub.silence import split_on_silence, detect_silence
AudioSegment.converter =os.path.realpath(r'D:\Prox\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe')
AudioSegment.ffprobe   = os.path.realpath(r'D:\Prox\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe')

import pandas as pd
# import openpyxl 

path = r'D:\_AudibleFiles\MP3'
filename = 'Weihnachtosaurus_Chap01_23'
# filename = 'Weihnachtosaurus_Chap24_31'
# filename = 'Weihnachtosaurus_Chap32'
filename = 'Weihnachtosaurus_Chap33_end'

mp3file = os.path.realpath(os.path.join(path,f'{filename}.mp3'))
xlsfile = os.path.realpath(os.path.join(path,f'{filename}.xlsx'))

print(mp3file)
print(os.path.isfile(mp3file))
print(AudioSegment.ffmpeg)
# exit(0)

def get_silence_time(song):
    # ref: https://stackoverflow.com/questions/45526996/split-audio-files-using-silence-detection
    chunks = detect_silence (
        # Use the loaded audio.
        song, 
        # Specify that a silent chunk must be at least 2 seconds or 2000 ms long.
        min_silence_len = 750,
        # Consider a chunk silent if it's quieter than -16 dBFS.
        # (You may want to adjust this parameter.)
        silence_thresh = -50,
        seek_step = 50
    )    
    # print(f'len(chunks) = {len(chunks)}')
    silence_timesteps = [((start),(stop)) for start,stop in chunks] #convert to sec
    # print(silence_timesteps)
    return silence_timesteps
    # for part in chunks:

def export_mp3_segment(song,path,start,stop,Name,ID):
    # pydub does things in milliseconds
    start *= 1000 # s->ms
    stop  *= 1000 # s->ms
    # song clip of from start to stop
    segment = song[int(start):int(stop)] 
    # save file 
    segment.export(os.path.join(path,f'{Name}.mp3'), format="mp3") 
    
#create dummy list
def tracklist_create_example():
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

def tracklist_import(xlsfile):
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
def tracklist_print(tracks):
    for t in tracks:
        print(f"{t['id']:03d} | start: {t['start']:6.0f} | stop: {t['stop']:6.0f} s | diff: {t['stop']-t['start']} | duration: {t['duration']}")

def tracklist_modify_wrt_silence(song,tracklist):
    silence_timesteps = get_silence_time(song)

    for index,track in enumerate(tracklist):
        if index>=(len(tracklist)-1):
            break
        if (song.duration_seconds - track['stop']) < 20:
            break 
        oldval = tracklist[index]['stop']
        # index_silence_list = [ (x,y) for x, y in silence_timesteps if (np.abs(x-track['stop']*1000)<(2*1000) ) ]        
        # if len(index_silence_list)==0:
        #     continue        
        # index_silence = index_silence_list[-1]

        index_silence = min([elem for elem in silence_timesteps if np.abs( ((elem[0]+elem[1])/2) -track['stop']*1000)<=(5*1000)  ], key=lambda x: x, default=None)
        if index_silence==None:
            continue       
        index_stop = (index_silence[0]+index_silence[1])/2/1000
        # print(index_stop) 
        tracklist[index]['stop']=index_stop
        newval = tracklist[index]['stop']
        print(f'{index:03d} :: stop ::old = {oldval} | new = {newval} ')
        if len(tracklist)>(index+1):
            tracklist[index+1]['start']=index_stop
    return tracklist
        
# =========================================
#           Execute Main
# =========================================

# tracks = tracklist_create_example()
tracks = tracklist_import(xlsfile=xlsfile)

# Open an mp3 file
print(f"loading file {mp3file} ...")
song = AudioSegment.from_mp3(mp3file) #, format="mp3"
print(f"... done.")

# get_silence_time(song)
tracks = tracklist_modify_wrt_silence(song,tracks)
tracklist_print(tracks)

# exit(0)
for track in tracks:
    if song.duration_seconds<track['stop']:
        print(f"end of Track {track['id']} is longer than audio file --> Abort !")
        break
    # if track['id']>=40:
    #     break
    print(f"cutting track {track['id']} ...")
    export_mp3_segment(song,path=os.path.join(path,'Test2'), start=track['start'], stop=track['stop'], Name=track['title'], ID=track['id'])

print("New Audio file is created and saved") 