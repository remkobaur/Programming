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
   'EnableDeleteFiles':False,
   'DeleteCopyInOtherPath':False
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
        'Path':os.path.dirname(os.path.abspath(fileName)).replace('\\\\IR_MedServ\\photo\\',''),
        'Size':os.path.getsize(fileName),
        'FullPath':fileName,
        'Tag':[],
        'Delete':''
        })
    
def _addTags(item,search_list,_config):
    searchName = pathlib.Path(item).stem
    serchExt = pathlib.Path(item).suffix
    # search_list.remove(item)
    
    # find all files with same name
    sameNameList = [f for f in search_list if searchName in f and serchExt in f]          
    sameFileDictList =[]  
    if len(sameNameList)>=1:
        
        for k in sameNameList:  
            FD = get_fileDict(k)
             # if any remove_subFolder is in path --> tag = remove
            if any( sf in FD['Path'] for sf in _config['remove_subFolders']):
                FD['Tag'].append('removeSF')
            # if any keep_subFolder is in path --> tag = keep
            if any( sf in FD['Path'] for sf in _config['keep_subFolders']):                    
                FD['Tag'] .append('keepSF')
                FD['Delete'] = 'KEEP'
            sameFileDictList.append(FD)                
            search_list.remove(k)        
            
        if len(sameFileDictList)<=1:
            if len(sameFileDictList)==1:
                sameFileDictList[0]['Tag'].append('SingleFile') 
                sameFileDictList[0]['Delete'] = 'KEEP'
            return sameFileDictList        
            
        for  k in sameFileDictList:          
            # if k['Delete'] in ['x']:
            #     continue
            #filename in other filename
            for f in sameFileDictList:  
                if f['FullPath'] == k['FullPath'] :
                    continue # skip element F as it is element K
                
                if f['Delete'] in ['x','KEEP']:
                    continue
                
                _sameFileName = k['File'] == f['File']
                _stemInName = k['Stem'] in f['File']
                _sameSize = k['Size'] == f['Size']
                _samePath = k['Path'] == f['Path']
                _isBigger = k['Size'] < f['Size']
                            
                # --- same size
                if _config['sameSizeReq']:
                    if _sameSize: 
                        if _sameFileName: #same name and size
                            f['Tag'].append('SameFile')
                        elif _samePath and _stemInName: #same path and stem in name 
                            f['Tag'].append('copy in Path')    
                        elif _stemInName: #stem in name, but different path
                            f['Tag'].append('copy in other path') 
                        else:
                            f['Tag'].append('difFile') 
                    else:
                            f['Tag'].append('difSize')  
                # --- different size
                else:
                    if _sameSize:
                        f['Tag'].append('SameSize')
                    elif _isBigger:
                        f['Tag'].append('bigger')
                    else:
                        f['Tag'].append('smaller')
                    if _sameFileName: #same name and size
                        f['Tag'].append('SameFile') 
                    elif _samePath and _stemInName: #same path and stem in name 
                        f['Tag'].append('copy in Path')    
                    elif _stemInName and _sameSize: #stem in name, but different path
                        f['Tag'].append('copy in other path')
                    else:
                        f['Tag'].append('difFile')   
                
                DeleteTags = ['SameFile','copy in Path']
                if _config['DeleteCopyInOtherPath']:
                    DeleteTags.append('copy in other path')
                if any( t in f['Tag'] for t in DeleteTags) and not 'keepSF' in f['Tag']:
                    f['Delete'] = 'x'

                if _config['sameSizeReq']:
                    if 'difSize' in f['Tag']:
                        f['Delete'] = 'KEEP'
            
                 
        if all( f['Delete']=='x' for f in sameFileDictList):
            if all( 'removeSF' in f['Tag'] for f in sameFileDictList):
                # sameFileDictList[0]['Tag'] = 'rescue_keep'
                sameFileDictList[0]['Delete'] = 'rescue'
            else:
                for f in sameFileDictList:
                    if not 'removeSF' in f['Tag']:
                        f['Delete'] = 'rescue'
                        break
                        
            
    return sameFileDictList

def findDuplicateList_Dict(item_list,_config = config):
    resultList =[]

    item_list.sort(key = lambda x:len(pathlib.Path(x).stem))
    
    # for item in item_list :  
    #     print(f' - {pathlib.Path(item).stem}')
    
    search_list = copy.deepcopy(item_list)    
    for item in item_list :        
        if item not in search_list:
            continue
        
        sameFileDictList = _addTags(item,search_list,_config)
        
        if len(sameFileDictList)==0:
            continue      
        else:
            if not _config['List_SingleFiles']:
                if any([f['Delete']=='x' for f in sameFileDictList]):
                    sameFileDictList2 =  [f for f in sameFileDictList if not 'SingleFile' in f['Tag']]   
                    if len(sameFileDictList2)>0:                    
                        resultList.append(sameFileDictList2)
            else:
                resultList.append(sameFileDictList)
             
    if len(search_list)>0 and _config['List_SingleFiles']:
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
    df = pd.DataFrame(columns=['File','Path','Tag','Delete','Size','Ext','Stem','FullPath'])
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
    return del_count

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
    AnalysisResults=findDuplicateList_Dict(item_list,_config)
    fileName = root.replace('\\\\IR_MedServ\\photo\\','').replace('\\',' ')
    xlsExport_ValidatedDuplicateList(AnalysisResults,f'{fileName}.xlsx')
    delete_DuplicatedFiles(AnalysisResults,deleteFiles=_config['EnableDeleteFiles']) 
 
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
    delcount = 0
    for sf in subfolders:
        if sf in _config['skip_subFolders']:
            continue        
        fileName = sf.replace('\\\\IR_MedServ\\photo\\','').replace('\\',' ')
        item_list = get_ImageList_for_folderTree(rootdir_glob = os.path.join(root,sf))
        for secFolder in secondFolderList:
            item_list += get_ImageList_for_folderTree(rootdir_glob = secFolder)
        AnalysisResults=findDuplicateList_Dict(item_list,_config)
        if len(AnalysisResults)>0:
            xlsExport_ValidatedDuplicateList(AnalysisResults,f'{fileName}.xlsx')
            delcount += delete_DuplicatedFiles(AnalysisResults,deleteFiles=_config['EnableDeleteFiles']) 
    print("=======================================") 
    print(f"Total deleted files = {delcount}") 
# testing1()
# testing2()
# testing3()

_config = copy.deepcopy(config)
_config['remove_subFolders'] =['Afterworld','Dias','raw','lowres','usschuss']
_config['keep_subFolders'] =['Best','best','uswahl']
_config['skip_subFolders'] =['0_Remko','0_Ira'] # 
_config['sameSizeReq'] = True
_config['EnableDeleteFiles'] = True   
_config['DeleteCopyInOtherPath'] = True   

# process()
# process_folder(r'\\IR_MedServ\photo\Events\2024_06_13_Promotion_Verteidigung',_config = _config)
process_folder(r'\\IR_MedServ\photo\Familie\Baur_LuM',_config = _config)
# process_folder(r'\\IR_MedServ\Backup\Remko\_TestData',_config = _config)
# process_folder(r'C:\GIT\_TestData',_config = _config)
# process_forEachSubfolder(r'\\IR_MedServ\photo\DCIM-Handy\Remko',_config = _config)
# process_forEachSubfolder_secondRootList(r'\\IR_MedServ\photo\Events',[r'\\IR_MedServ\photo\share'],_config = _config)
# process_forEachSubfolder_secondRootList(r'\\IR_MedServ\photo\Familie\Baur_LuM\Urlaubsfotos',[],_config = _config)