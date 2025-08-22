function List = find_all_subfolders(MainPath,SearchDeepth)
  clc
  pkg load all
  cd('F:/mfiles/list_subfolders/')
  warning("off","Octave:num-to-str")
  if nargin == 0
      MainPath= 'z:';
      SearchDeepth = 6;
  end
  disp('start scanning of directories')
  List ={MainPath};
  ID = 1;
  for SD = 1:SearchDeepth        
      disp(sprintf('--> Search Deapth %d of %d -- processing',SD,SearchDeepth));
      [List_New,ID_new]  = generate_list(List,ID);
      List = List_New; ID = ID_new;
  end
  save('F:\mfiles\list_subfolders\Dir_Nas.mat','List','ID');
  XLSname = ['F:\mfiles\list_subfolders\Dir_Nas.xls'];
  if exist(XLSname,'file')
    delete(XLSname);
  end
  xlswrite(XLSname,List); 
   
  if nargout == 0
    clear List
  end 

end

function [List,New_ID] = generate_list(ParentList,ID)
    N = size(ParentList,1);
    List = {};
    New_ID = [];
    for z = 1:N
        Path = [];
        for sf = 1:ID(z)
            if ~isempty(ParentList{z,sf})              
                Path =[Path,ParentList{z,sf}];
                if Path(end)~='\' || Path(end)~='/'
                  Path =[Path,'\'];                  
                end
%                disp(Path)
            end
        end
        SubFolders = get_folders_in_path(Path);      
        s = numel(SubFolders);
        ChildrenList = {};
        if s > 0;       
            for sf = 1: s            
                ChildrenList(sf,1:ID(z)) = ParentList(z,1:ID(z));
                ChildrenList(sf,ID(z)+1) = SubFolders(sf);           
            end      
            if ~isempty(ChildrenList)
                ind = size(List,1);
                List(ind+(1:s),1:(ID(z)+1)) =  ChildrenList((1:s),1:(ID(z)+1)); 
                New_ID(ind+(1:s)) = ID(z)+1; 
            end
        else
            ind = size(List,1);
            List(ind+1,1:(ID(z))) =  ParentList(z,1:ID(z));   
            New_ID(ind+1) = ID(z);         
        end
    end
end

function nameFolds = get_folders_in_path(pathFolder)
    d = dir(pathFolder);
    isub = [d(:).isdir]; %# returns logical vector
    nameFolds = {d(isub).name}';

    % delete {'.','..'}
    nameFolds(ismember(nameFolds,{'.','..'})) = [];
end