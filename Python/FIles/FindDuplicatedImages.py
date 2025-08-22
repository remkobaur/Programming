import os
from glob import iglob
import pathlib
from pathlib import Path
import copy
import pandas as pd
imageExtensions = ['.png','.PNG','.jpg','.mp4','.JPG','.MOV']

year = '2023'
keep_subFolders = ['Best','best','uswahl',f'{year}\\{year}',f'{year}\\0',f'{year}\\1']

year = '2025'
keep_subFolders = ['Best','best','uswahl']
rootdir_glob = r'\\ir_medserv\photo\DCIM-Handy\Remko' +f'\\{year}'




print(rootdir_glob)

# rootdir_glob = r'\\ir_medserv\photo\Events\2022_12_24_Weihnachten_Dresden\
remove_subFolders = ['Afterworld','Dias']


# This will return absolute paths
# file_list = [f for f in iglob(rootdir_glob, recursive=True) if os.path.isfile(f)]
# path_list = [f for f in iglob(rootdir_glob, recursive=True) if not os.path.isfile(f)]
# path_list.sort() 
image_list = [f for f in iglob(rootdir_glob+r'\**\*', recursive=True) if os.path.isfile(f) and pathlib.Path(f).suffix in imageExtensions] #'**\*' # Note the added asterisks

item_list = image_list

# for item in item_list :
#      print(f"{pathlib.Path(item).stem} --> {pathlib.Path(item).suffix} --> size = {os.path.getsize(item)} -->{item}")
del_count = 0
duplicateList = []
def get_fileDict(fileName):
    return({'File':pathlib.Path(fileName).stem+pathlib.Path(fileName).suffix,'Stem':pathlib.Path(fileName).stem,'Path':os.path.dirname(os.path.abspath(fileName)),
            'Size':os.path.getsize(fileName),'FullPath':fileName,'Tag':'','Delete':''})
df = pd.DataFrame(columns=['File','Path','Stem','Size','FullPath','Tag','Delete'])
search_list = copy.deepcopy(item_list)    
for item in item_list :
    # print(f"{pathlib.Path(item).stem} --> {pathlib.Path(item).suffix} --> size = {os.path.getsize(item)} -->{item}")
    if item not in search_list:
        continue
    
    searchName = pathlib.Path(item).stem
    # search_list.remove(item)
    # find all files with same name
    sameNameList = [f for f in search_list if searchName in f]      
    
    if len(sameNameList)>1:
        removeFromList = []   
        # print(f"\n{item} --------")  
        for k in sameNameList:  
            # compare size                        
            if os.path.getsize(item) == os.path.getsize(k): # or True:
                # print(f" + {k}") 
                removeFromList.append(k)       
            else:
                # print(f"\t! Diff Size {k} --> size = {os.path.getsize(k)} --> org size = {os.path.getsize(item)}")
                pass
            
        new_rows =[]
        # new_rows.append(get_fileDict(item))
        targetName = item
        for k in removeFromList:
            search_list.remove(k)
            new_rows.append(get_fileDict(k))            
            pass  
        for  k in new_rows:
            # if any remove_subFolder is in path --> tag = remove
            for rm_sf in remove_subFolders:
                if rm_sf in k['Path']:
                    k['Tag'] = 'removeSF'
                    continue
            # if any keep_subFolder is in path --> tag = keep
            for sf in keep_subFolders:
                if sf in k['Path']:
                    k['Tag'] = 'keep'
        
        for  k in new_rows:
            if k['Tag'] == 'removeSF' or k['Delete'] == 'x':
                k['Delete'] = 'x'
                continue
            for f in new_rows:
                if k['FullPath'] == f['FullPath']: # identical files
                    continue
                if f['Delete'] == 'x':
                    continue
                if f['Tag'] == 'removeSF':
                    f['Delete'] = 'x'
                    continue
                if f['Tag'] == 'keep':
                    continue                                
                #filename in other filename              
                if k['Stem'] in f['File'] :        
                    #same folder       
                    if k['Path'] == f['Path']:
                        pass     
                    f['Delete'] = 'x'
                    continue               
                
                # # if is in parallel folder
                # if Path(k['Path']).parent.absolute() == Path(f['Path']).parent.absolute(): 
                #     f['Delete'] = 'Delete'
        if all( f['Tag']=='Delete' for f in new_rows):
            new_rows[0]['Tag'] = 'rescue_keep'
        if any( f['Tag'] in ['keep','rescue_keep'] for f in new_rows):
            for k in new_rows:
                if not k['Tag'] in ['keep','rescue_keep']:
                    k['Delete'] = 'x'
        for  k in new_rows:
            if k['Delete'] == 'x':
                print(f"Delete: {k['FullPath']}")
                # os.remove(k['FullPath'])
                # os.remove(os.path.join(k['Path'],k['File']))
                del_count+=1
                pass
        if len(new_rows)>1:
            df = df._append(new_rows, ignore_index=True)    

# print(df)
print(f"{del_count} images deleted")
df.to_excel(os.path.join(os.path.dirname(os.path.abspath(__file__)),'douplicate_List.xlsx'))
        
    
# for item in duplicateList:
#     print(f"DELETE FILE: {pathlib.Path(item).stem} --> {pathlib.Path(item).suffix} --> size = {os.path.getsize(item)} -->{item}")
#     # os.remove(item)