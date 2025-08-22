 SavePath = 'F:\mfiles\list_subfolders\';
 SaveName = 'Dir_Nas';
 save([SavePath,SaveName,'.mat'],'List','ID');
  XLSname = [SavePath,SaveName,'.xls'];
  if exist(XLSname,'file')
    delete(XLSname);
  end
  xlswrite(XLSname,List); 
   