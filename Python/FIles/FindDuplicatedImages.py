import os
from glob import iglob
import pathlib
from pathlib import Path
import copy
import pandas as pd
import click # for yes/no dialog

imageExtensions = ['.png','.PNG','.jpg','.mp4','.JPG','.MOV']

config ={
   'sameSizeReq':True ,
   'List_SingleFiles':False ,
   'debugPrint':False,
   'keep_subFolders':[],
   'keep_subFolders':[],
   'Skip_subFolders':[],
   'EnableDeleteFiles':False   
}


def get_ImageList_for_folderTree(rootdir_glob):
    print(f"scanning main folder {rootdir_glob}")
    # This will return absolute paths

    image_list = [f for f in iglob(rootdir_glob+r'\**\*', recursive=True) if os.path.isfile(f) and pathlib.Path(f).suffix in imageExtensions] #'**\*' # Note the added asterisks
    image_list.sort() 
    print(f'\t {len(image_list)} files')
    return image_list

def get_fileDict(fileName):
    return({
        'File':pathlib.Path(fileName).stem+pathlib.Path(fileName).suffix,
        'Ext':pathlib.Path(fileName).suffix,
        'Stem':pathlib.Path(fileName).stem,
        'Path':os.path.dirname(os.path.abspath(fileName)),
        'Size':os.path.getsize(fileName),
        'FullPath':fileName,
        'Tag':'',
        'Delete':''
        })

def findDuplicateList_Dict(item_list,_config = config):
    resultList =[]
    # item_list = sorted(item_list, key=len)
    item_list.sort(key = lambda x:len(os.path.dirname(os.path.abspath(x))))
    
    
    search_list = copy.deepcopy(item_list)    
    for item in item_list :
        # print(f"{pathlib.Path(item).stem} --> {pathlib.Path(item).suffix} --> size = {os.path.getsize(item)} -->{item}")
        if item not in search_list:
            # dummy = get_fileDict(item)
            # dummy['Tag'] = 'notIMSearchList'
            # resultList.append([dummy])
            continue
        
        searchName = pathlib.Path(item).stem
        serchExt = pathlib.Path(item).suffix
        # search_list.remove(item)
        
        # find all files with same name
        sameNameList = [f for f in search_list if searchName in f and serchExt in f]      
        if len(sameNameList)>1:
            sameFileDictList =[]  
            # print(f"\n{item} --------")
            for k in sameNameList:  
                sameFileDictList.append(get_fileDict(k))                
                search_list.remove(k)
            # for k in sameNameList:  
            #     # compare size                        
            #     if os.path.getsize(item) == os.path.getsize(k): # or True:
            #         # print(f" + {k}") 
            #         sameFileDictList.append(get_fileDict(k)) 
            #         # search_list.remove(k)                         
            #     else:
            #         print(f"different size \n\t- {os.path.getsize(item) } : {item} \n\t- {os.path.getsize(k)} : {k} ")
            #         # print(f"\t! Diff Size {k} --> size = {os.path.getsize(k)} --> org size = {os.path.getsize(item)}")
            #         pass
                
            if len(sameFileDictList)==0:
                continue
            
                
            for  k in sameFileDictList:
                # if any remove_subFolder is in path --> tag = remove
                if any( sf in k['Path'] for sf in _config['remove_subFolders']):
                    k['Tag'] = 'removeSF'
                    continue
                # if any keep_subFolder is in path --> tag = keep
                if any( sf in k['Path'] for sf in _config['keep_subFolders']):                    
                    k['Tag'] = 'keep'
                    continue
                if not k['Tag'] =='':
                    continue
                # if k['FullPath'] == item: # identical files
                #     k['Tag'] = 'DuplicateEntry'
                #     continue
                #filename in other filename
                for  f in sameFileDictList:  
                    if f['FullPath'] == k['FullPath'] :
                        continue
                    if f['Tag'] != '':
                        continue          
                    if k['Stem'] in f['File']: 
                        if  k['File'] ==  f['File']:
                            if k['Size'] == f['Size']:
                                f['Tag'] = 'SameFile'
                            elif not _config['sameSizeReq']: 
                                if k['Size'] < f['Size']:
                                    f['Tag'] = 'BiggerFile'                                
                                else:
                                    f['Tag'] = 'SmallerFile'                                                               
                        elif k['Path'] == f['Path'] and (not _config['sameSizeReq'] or k['Size'] == f['Size']):
                            f['Tag'] = 'copy in Path'       
                        else:
                            f['Tag'] = 'Stem in File'             
                        continue     
                              
            if all( f['Tag']=='Delete' for f in sameFileDictList):
                sameFileDictList[0]['Tag'] = 'rescue_keep'
                
            for  k in sameFileDictList:
                if k['Tag'] in ['keep','rescue_keep','BiggerFile']:
                    k['Delete'] = '--'                    
                # elif k['Tag'] in ['SmallerFile','SameFile','removeSF']:
                elif k['Tag'] in ['SameFile','copy in Path','removeSF']:
                    k['Delete'] = 'x'                         
                elif k['Tag']  == '':
                    k['Tag'] ='unTouched'  
                    k['Delete'] = '?'                      
                        
            
                
            # if any( f['Tag'] in ['keep','rescue_keep'] for f in sameFileDictList):
            #     for k in sameFileDictList:
            #         if k['Tag'] in ['keep','rescue_keep']:
            #             k['Delete'] = '-'
            #         else:
            #             k['Delete'] = 'x'
                        
            # for k in sameFileDictList:
            #     if k['Tag']  == '':
            #         k['Tag'] ='unTouched'
            #     else:
            #         search_list.remove(k['FullPath'])  
            #         pass
            if len(sameFileDictList)>=1:
                resultList.append(sameFileDictList)
    
    if len(sameFileDictList)>=1 and _config['List_SingleFiles']:
        sameFileDictList =[]        
        for f in search_list:            
            dummy = get_fileDict(f)
            dummy['Tag'] = 'notProcessed'        
            sameFileDictList.append(dummy)
        resultList.append(sameFileDictList)
    return resultList
   
def xlsExport_ValidatedDuplicateList(AnalysisResults,OutputFile):      
    if len(AnalysisResults) ==0:
        return      
    df = pd.DataFrame(columns=['File','Ext','Path','Stem','Size','FullPath','Tag','Delete'])
    # create dataframe with all results
    for sameFileDictList in AnalysisResults:
        df = df._append(sameFileDictList, ignore_index=True)    
    
    exportPath = os.path.join(os.path.dirname(os.path.abspath(__file__)),'Data')
    # Export results to excel file
    if not os.path.exists(exportPath):
        print(f'INFO: Export Path <{exportPath}> does not exist! --> It will be created now!')
        os.makedirs(exportPath)
        
    df.to_excel(os.path.join(exportPath,OutputFile))

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

def check_config(_config):    
    if _config['EnableDeleteFiles']:
        if click.confirm('Do you want to continue?', default=True):
            print('\t-> continue with ACTIVE file deletion')
        else:
            _config['EnableDeleteFiles'] = False
            print('\t-> ACTIVE file deletion was disabled by user choise')
        print(f"\t==> _config['EnableDeleteFiles'] = {_config['EnableDeleteFiles']}")
#============================================================================================
#============================================================================================

def testing1():
    _config = copy.deepcopy(config)
    _config['remove_subFolders'] = ['Afterworld','Dias']
    _config['keep_subFolders']= ['Best','best','uswahl']

    item_list = get_ImageList_for_folderTree(rootdir_glob = r'C:\GIT\_TestData')

    AnalysisResults=findDuplicateList_Dict(item_list,_config)
    xlsExport_ValidatedDuplicateList(AnalysisResults,'douplicate_List.xlsx')
    delete_DuplicatedFiles(AnalysisResults,deleteFiles=_config['EnableDeleteFiles']) 
    
def testing2():
    _config = copy.deepcopy(config)
    check_config(_config)   
    _config['remove_subFolders'] = ['Afterworld','Dias']
    _config['keep_subFolders']= []

    item_list=[]
    #item_list += get_ImageList_for_folderTree(rootdir_glob = r'C:\GIT\_TestData')

    item_list += get_ImageList_for_folderTree(rootdir_glob = r'C:\GIT\_TestData\root1')
    item_list += get_ImageList_for_folderTree(rootdir_glob = r'C:\GIT\_TestData\root02')

    AnalysisResults=findDuplicateList_Dict(item_list,_config)
    xlsExport_ValidatedDuplicateList(AnalysisResults,'douplicate_List.xlsx')
    delete_DuplicatedFiles(AnalysisResults,deleteFiles=_config['EnableDeleteFiles']) 

def testing3():
    _config = copy.deepcopy(config)
    check_config(_config)   
    _config['remove_subFolders'] = ['Afterworld','Dias']
    _config['keep_subFolders']= []
    rootdir_glob = r'C:\GIT\_TestData'

    keep_subFolders= []

    item_list=[]
    item_list += get_ImageList_for_folderTree(rootdir_glob = r'C:\GIT\_TestData1')
    item_list += get_ImageList_for_folderTree(rootdir_glob = r'C:\GIT\_TestData2')

    AnalysisResults=findDuplicateList_Dict(item_list,_config)
    xlsExport_ValidatedDuplicateList(AnalysisResults,'douplicate_List.xlsx')
    delete_DuplicatedFiles(AnalysisResults,deleteFiles=_config['EnableDeleteFiles']) 
 
def process_folder(root = r'\\IR_MedServ\photo\Events\2014_09_27_Detmerode_Wald',_config = config):
    check_config(_config)   
    item_list = get_ImageList_for_folderTree(rootdir_glob = root)
    fileName = root.replace('\\\\IR_MedServ\\photo\\','').replace('\\',' ')
    AnalysisResults=findDuplicateList_Dict(item_list,_config)
    xlsExport_ValidatedDuplicateList(AnalysisResults,f'{fileName}.xlsx')
    # delete_DuplicatedFiles(AnalysisResults,deleteFiles=_config['EnableDeleteFiles']) 
 
def process_forEachSubfolder(root =r'\\IR_MedServ\photo\Events',_config = config):
    check_config(_config)           
    dirname = Path(root)
    subfolders = [f.name for f in dirname.iterdir() if f.is_dir()]
    subfolders.sort()
    for sf in subfolders:
        if sf in _config['skip_subFolders']:
            continue        
        item_list = get_ImageList_for_folderTree(rootdir_glob = os.path.join(root,sf))
        AnalysisResults=findDuplicateList_Dict(item_list,_config)
        delete_DuplicatedFiles(AnalysisResults,deleteFiles=_config['EnableDeleteFiles']) 
        
def process_forEachSubfolder_secondRootList(root =r'\\IR_MedServ\photo\Events', secondFolderList=[r'\\IR_MedServ\photo\share'],_config = config):

    check_config(_config)  
    dirname = Path(root)
    subfolders = [f.name for f in dirname.iterdir() if f.is_dir()]
    subfolders.sort()
    for sf in subfolders:
        if sf in _config['skip_subFolders']:
            continue        
        fileName = sf.replace('\\\\IR_MedServ\\photo\\','').replace('\\',' ')
        item_list = get_ImageList_for_folderTree(rootdir_glob = os.path.join(root,sf))
        for secFolder in secondFolderList:
            item_list += get_ImageList_for_folderTree(rootdir_glob = secFolder)
        AnalysisResults=findDuplicateList_Dict(item_list,_config)
        xlsExport_ValidatedDuplicateList(AnalysisResults,f'{fileName}.xlsx')
        delete_DuplicatedFiles(AnalysisResults,deleteFiles=_config['EnableDeleteFiles']) 
        
# testing1()
# testing2()
# testing3()

_config = copy.deepcopy(config)
_config['remove_subFolders'] =['Afterworld','Dias','raw','lowres']
_config['keep_subFolders'] =['Best','best','uswahl']
_config['skip_subFolders'] =['0_Remko','0_Ira']
_config['sameSizeReq'] = True
_config['EnableDeleteFiles'] = False   



# process()
process_folder(r'\\IR_MedServ\photo\Events\2024_06_13_Promotion_Verteidigung',_config = _config)
# process_folder(r'\\IR_MedServ\Backup\Remko\_TestData',_config = _config)
# process_folder(r'C:\GIT\_TestData',_config = _config)
# process_forEachSubfolder(r'\\IR_MedServ\photo\DCIM-Handy\Remko',_config = _config)
# process_forEachSubfolder_secondRootList(r'\\IR_MedServ\photo\Events',[r'\\IR_MedServ\photo\share'],_config = _config)
# process_forEachSubfolder_secondRootList(r'\\IR_MedServ\photo\Events',[],_config = _config)