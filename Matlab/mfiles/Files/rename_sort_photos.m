function rename_sort_photos(DIRNAME)
  clc;
  
  if nargin == 0
    FLT = '.jpg';
    DIALOG_NAME = 'get dir - rename sorted photos';
    DEFAULT_FILE = 'F:\Bilder\Fotos\Urlaub\2015_05_Slowenien';

    DIRNAME = uigetdir (DEFAULT_FILE,DIALOG_NAME);
    if DIRNAME == 0
      return
    end  
  end
%  disp(DIRNAME);return
  
  Pics = find_photos([DIRNAME]);  
  [New,Old,List] = get_SortedPhotoNames(Pics,DIRNAME);
  
  if nargin ==0
   [sel, ok] = listdlg ("ListString", List,"ListSize", [1000,600]);
  else
   ok = 1;
  end
  
   if ok 
      rename_photos(New,Old);
   end
end

function Pics = find_photos(DIRNAME)
  Files = dir(DIRNAME);
  Date = {};
  Name = {};
  Format_in  = 'yyyy:mm:dd HH:MM:SS';
  Format_out = 'yyyy:mm:dd HH:MM:SS';
  EXT = {'.jpg','.JPG','.jpeg'};
  for z=1:numel(Files)
    if Files(z).isdir
      continue
    end
    [dir, name, ext] = fileparts ([DIRNAME,'\',Files(z).name]);
    if ~ismember(ext,EXT)
       disp('übersprungen')
      continue
    end
    
    INFO = imfinfo ([DIRNAME,'\',Files(z).name]);
    dummy = datevec(INFO.DigitalCamera.DateTimeOriginal,Format_in);
%    dummy = datevec(Files(z).date);
    if Files(z).name(1)=='P' % Kamera Einstellungen falsch: +1 Tag
        dummy(3) = dummy(3)+1; 
    end
    Date{end+1} = datestr(dummy,Format_out);
%    disp(Date{end})
    Name{end+1} = Files(z).name;
  end 
  Pics.Name = Name;
  Pics.Date = Date;  
end

function [New,Old,List] = get_SortedPhotoNames(Struct,Dir)
  ind = unique([strfind(Dir,'/'),strfind(Dir,'\')]);
  Range = (ind(end)+1):numel(Dir); 
  Prefix = Dir(Range);

  [D,ind] = sort(Struct.Date);
  List = {}; 
  New  = {};
  Old  = {};
  for z = 1:numel(Struct.Name)
    k = ind(z);
    dummy = sprintf('%s-%03d.jpg',Prefix,z);    
    oldname = [Dir,'\',Struct.Name{k}];
    newname = [Dir,'\',dummy];
    
    List{z} = sprintf('%s \t\t %s \t %d',Struct.Name{k},dummy,z);    
    New{z} = newname;
    Old{z} = oldname; 
  end
end

function rename_photos(New,Old)
  for z = 1:numel(New)
      [ERR, MSG]=rename(Old{z},New{z});    
      if ERR ~=0
        disp(MSG)
      end
  end
end