function CArray = LoadXLS(LoadPath,XlsFile,Tabname)
if nargin <3 
  Tabname = 1;
end
if isempty(strfind(XlsFile,'.xls'))
  XlsFile = [XlsFile,'.xls'];
end

[numarr, txtarr, rawarr, limits] = xlsread([LoadPath,XlsFile],Tabname,[],'oct'); 


CArray = rawarr;