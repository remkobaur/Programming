import os
from glob import iglob
import pathlib
import copy

imageExtensions = ['.png','.PNG','.jpg','.mp4']

rootdir_glob = r'I:\TestData\Ira\**\*' # Note the added asterisks
rootdir_glob = r'\\ir_medserv\photo\DCIM-Handy\Ira\**\*' # Note the added asterisks

# This will return absolute paths
file_list = [f for f in iglob(rootdir_glob, recursive=True) if os.path.isfile(f)]
path_list = [f for f in iglob(rootdir_glob, recursive=True) if not os.path.isfile(f)]
image_list = [f for f in iglob(rootdir_glob, recursive=True) if os.path.isfile(f) and pathlib.Path(f).suffix in imageExtensions]
path_list.sort() 

item_list = image_list

# for item in item_list :
#      print(f"{pathlib.Path(item).stem} --> {pathlib.Path(item).suffix} --> size = {os.path.getsize(item)} -->{item}")
duplicateList = []

search_list = copy.deepcopy(item_list)    
for item in item_list :
    # print(f"{pathlib.Path(item).stem} --> {pathlib.Path(item).suffix} --> size = {os.path.getsize(item)} -->{item}")
    if item not in search_list:
        continue
    if pathlib.Path(item).stem.endswith("_1"):
        searchName = pathlib.Path(item).stem[:-2]
        sameNameList = [f for f in search_list if searchName in f]
        remove_list = []
        if len(searchName)>0:
            print("----------------------")
            for ind,k in enumerate(sameNameList):                
                if os.path.getsize(item) == os.path.getsize(k):
                    if pathlib.Path(k).stem[-2] == "_":                        
                        remove_list.append(k)
                        duplicateList.append(k)
                    print(f" - {k}")
                else:
                    print(f" !!! {k} has not the same Size as {item}")
            for k in remove_list:
                search_list.remove(k)
                pass
        
for item in duplicateList:
    print(f"DELETE FILE: {pathlib.Path(item).stem} --> {pathlib.Path(item).suffix} --> size = {os.path.getsize(item)} -->{item}")
    os.remove(item)