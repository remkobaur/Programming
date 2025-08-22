function rename_photos()
  clc;
  FLT = '.jpg';
  DIALOG_NAME = 'Choose photos to  be renamed';
  DEFAULT_FILE = 'C:\Users\Oxygen2\Desktop\HighResolution\*.jpg';
  DEFAULT_FILE = '\\IR_MEDSERV\photo\UnsereHochzeit\Fotografin_LowRes';
  [FNAME, FPATH, FLTIDX] = uigetfile (FLT,DIALOG_NAME,DEFAULT_FILE,"MultiSelect","on");
  if ~iscell(FNAME)
    FNAME = {FNAME};
  end
  if FPATH == 0
    return
  end
  
  for z = 1: numel(FNAME)
    newname = rename_func(FNAME{z});
%    disp([FNAME{z},' ; ',newname]);
    rename([FPATH,'\',FNAME{z}],[FPATH,'\',newname])
  end
end


function newname = rename_func(name)
 text = 'BaurHz-';
 format = [text,'%d.jpg'];
 number = sscanf(name,format,1);
 newname = sprintf('%s%03d.jpg',text,number);
end