function do_for_MultipleFolders
clc
    DIRNAME = 'F:\Bilder\Fotos\Urlaub\2015_05_Slowenien';
    DIR = dir(DIRNAME);
        
    Folders = {};
    for z = 1:numel(DIR)
      if DIR(z).isdir && ~any(strncmp(DIR(z).name,{'.','..'},1) )
        Folders{end+1} = DIR(z).name;
      end
    end
    
    disp('********* Start *****')
    for  z = 1:numel(Folders)
      disp([DIRNAME,'\',Folders{z}]);
      rename_sort_photos([DIRNAME,'\',Folders{z}]);
    end
end