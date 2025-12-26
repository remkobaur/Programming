from CL_DuplicatedFilesFinder import CL_DuplicatedFilesFinder 
import os
import copy

DFF = CL_DuplicatedFilesFinder()

_config = copy.deepcopy(DFF.config)
_config['remove_subFolders'] =[]
_config['fileExtensions'] = ['.pdf','.ppt','.PDF','.txt','.lnk','.doc']
_config['keep_subFolders'] =[ r'\\ir_medserv\Backup\Remko\Docs\Studium Remko E-Tech' ] #'Best','best','uswahl',
_config['skip_subFolders'] =[] # 
_config['sameSizeReq'] = True
_config['EnableDeleteFiles'] = True   
_config['DeleteCopyInOtherPath'] = True   
_config['List_SingleFiles'] =False


item_list = DFF.get_FileList_for_folderTree(rootdir_glob = r'\\ir_medserv\Backup\Remko\Docs\Studium Remko E-Tech',_config=_config)
item_list += DFF.get_FileList_for_folderTree(rootdir_glob = r'\\ir_medserv\Backup\Remko\Docs\Promotion\Literatur\Citavi 5',_config=_config)

AnalysisResults = DFF.findDuplicateList_Dict(item_list,_config = _config)
if len(AnalysisResults)>0:
    fileName = 'DuplicatedLiterature'
    DFF.xlsExport_ValidatedDuplicateList(AnalysisResults,f'{fileName}.xlsx')
    DFF.delete_DuplicatedFiles(AnalysisResults,deleteFiles=_config['EnableDeleteFiles']) 