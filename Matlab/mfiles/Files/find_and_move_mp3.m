function find_and_move_mp3()
clc
  SearchPath = 'F:\Hoerspiel\Tintenwelt\';
  DstPath =   [SearchPath,'Music\']
  SearchTag = 'Musik';
  
  SubPaths = find_subpaths(SearchPath);
  SubPaths(end+1) = {SearchPath};
%  disp(SearchPath)
  if ~exist(DstPath,'dir')
    mkdir(DstPath)
  end  
  
  
  for d = 1:numel(SubPaths)
    Files = find_FilesWithStr(SubPaths{d},SearchTag);   
    for f = 1:numel(Files)
      Src = [SubPaths{d},Files{f}];
      Dst = [DstPath,Files{f}];
%      disp(Src)
%      disp(Files(f))
%      copyfile(Src,Dst,f);
      movefile(Src,Dst);
    end    
  end
  
end

function SubPaths = find_subpaths(Path)
  allFiles = dir(Path);
  SubPaths = {};
  if ~isfield(allFiles,'isdir') || 3>numel(allFiles)
    return
  end
  ind = [];
  for d = 3:numel(allFiles)
    if allFiles(d).isdir
      ind(end+1) = d;
    end
  end
  if isempty(ind)    
    return
  end
%  SubPaths(1:numel(ind),1) = allFiles(ind).name;
  for z = 1 : numel(ind)
    SubPaths(z) = {[Path,allFiles(ind(z)).name,'\']};
  end
end

function Files = find_FilesWithStr(Path,Tag)
  allFiles = dir([Path,'\*.mp3']);
  Files = {};
  ind = [];  
  for f = 1: numel(allFiles)
    if ~isempty(strfind(allFiles(f).name,Tag))
      ind(end+1) = f;
    end
  end
  if isempty(ind)  
    return
  end
  for z = 1 : numel(ind)
    Files(z) = {allFiles(ind(z)).name};
  end
%  if ~iscell(Files)
%    Files = {Files};
%  end
%  disp(Files)
end