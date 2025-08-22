import os
from glob import iglob
import pathlib
from pathlib import Path
import copy
import pandas as pd


imageExtensions = ['.png','.PNG','.jpg','.mp4','.JPG','.MOV']

def get_ImageList_for_folderTree(rootdir_glob):
    print(f"scanning main folder {rootdir_glob}")
    # This will return absolute paths

    image_list = [f for f in iglob(rootdir_glob+r'\**\*', recursive=True) if os.path.isfile(f) and pathlib.Path(f).suffix in imageExtensions] #'**\*' # Note the added asterisks
    image_list.sort() 
    return image_list

def get_fileDict(fileName):
    return({
        'File':pathlib.Path(fileName).stem+pathlib.Path(fileName).suffix,
        'Stem':pathlib.Path(fileName).stem,
        'Path':os.path.dirname(os.path.abspath(fileName)),
        'Size':os.path.getsize(fileName),
        'FullPath':fileName,
        'Tag':'','Delete':''
        })

def findDuplicateList_Dict(item_list,keep_subFolders,remove_subFolders):
    resultDict ={}
    
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
            sameFileDictList =[]  
            # print(f"\n{item} --------")  
            for k in sameNameList:  
                # compare size                        
                if os.path.getsize(item) == os.path.getsize(k): # or True:
                    # print(f" + {k}") 
                    sameFileDictList.append(get_fileDict(k))
                    search_list.remove(k)       
                else:
                    # print(f"\t! Diff Size {k} --> size = {os.path.getsize(k)} --> org size = {os.path.getsize(item)}")
                    pass
                
            for  k in sameFileDictList:
                # if any remove_subFolder is in path --> tag = remove
                if any( sf in k['Path'] for sf in remove_subFolders):
                    k['Tag'] = 'removeSF'
                    continue
                # if any keep_subFolder is in path --> tag = keep
                if any( sf in k['Path'] for sf in keep_subFolders):                    
                        k['Tag'] = 'keep'
            
            for  k in sameFileDictList:
                if k['Tag'] == 'removeSF' or k['Delete'] == 'x':
                    k['Delete'] = 'x'
                    continue
                for f in sameFileDictList:
                    if k['FullPath'] == f['FullPath']: # identical files
                        continue
                    elif f['Delete'] == 'x' or  f['Tag'] == 'keep':
                        continue
                    elif f['Tag'] == 'removeSF':
                        f['Delete'] = 'x'                        
                    else:
                        pass                                
                    #filename in other filename              
                    if k['Stem'] in f['File'] :  
                        f['Tag'] = 'Stem in File'
                        f['Delete'] = 'x'
                        continue               
                        
            if all( f['Tag']=='Delete' for f in sameFileDictList):
                sameFileDictList[0]['Tag'] = 'rescue_keep'
            if any( f['Tag'] in ['keep','rescue_keep'] for f in sameFileDictList):
                for k in sameFileDictList:
                    if not k['Tag'] in ['keep','rescue_keep']:
                        k['Delete'] = 'x'
            
            if len(sameFileDictList)>1:
                resultDict[pathlib.Path(item).stem]=sameFileDictList
                
    return resultDict
   
def xlsExport_ValidatedDuplicateList(AnalysisResults,OutputFile):             
    df = pd.DataFrame(columns=['File','Path','Stem','Size','FullPath','Tag','Delete'])
    # create dataframe with all results
    for stem,sameFileDictList in AnalysisResults.items():
        df = df._append(sameFileDictList, ignore_index=True)    
    # Export results to excel file
    df.to_excel(os.path.join(os.path.dirname(os.path.abspath(__file__)),'douplicate_List.xlsx'))

def delete_DuplicatedFiles(AnalysisResults,deleteFiles):
    del_count = 0
    for sameFileDictList in AnalysisResults:
        for  k in sameFileDictList:
            if k['Delete'] == 'x':
                print(f"Delete: {k['FullPath']}")
                if deleteFiles:
                    os.remove(k['FullPath'])
                del_count+=1
    print(f"{del_count} images deleted")

remove_subFolders = ['Afterworld','Dias']
keep_subFolders = ['Best','best','uswahl']
rootdir_glob = r'C:\GIT\_TestData'

# year = '2023'
# keep_subFolders = ['Best','best','uswahl',f'{year}\\{year}',f'{year}\\0',f'{year}\\1']
# rootdir_glob = r'\\ir_medserv\photo\DCIM-Handy\Remko' +f'\\{year}'

item_list = get_ImageList_for_folderTree(rootdir_glob)
AnalysisResults=findDuplicateList_Dict(item_list,keep_subFolders,remove_subFolders)
xlsExport_ValidatedDuplicateList(AnalysisResults,'douplicate_List.xlsx')
# delete_DuplicatedFiles(AnalysisResults,deleteFiles=False)


        
