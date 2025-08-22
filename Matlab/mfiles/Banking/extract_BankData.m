function Res = extract_BankData(CArray,Group_Tags,Col_Betrag,Col_Date,Col_Search_Rest);
  XLS_Name = 'F:\mfiles\Banking\Export.xls';
  
  FN =fieldnames(Group_Tags);
  for z = 1:numel(FN)
   dummy=(~cellfun(@ischar,CArray(:,Group_Tags.(FN{z}){1})));
   IND = find(dummy);
   CArray(IND,Group_Tags.(FN{z}){1}) = ' ';
  end
  ind = [];
  XLS_Cells=[];
  [Res.Einnahmen,~] = get_GroupStruct(CArray,Group_Tags,FN{1},Col_Betrag,Col_Date,'>0');
  [Res.Ausgaben,~] = get_GroupStruct(CArray,Group_Tags,FN{1},Col_Betrag,Col_Date,'<=0');
  for z = 1:numel(FN)        
%    Col_ID = Group_Tags.(FN{z}){1};
%    Col = CArray(:,Col_ID);
%    dummy=(~cellfun(@ischar,Col));
%    IND = find(dummy);
%    Col(IND) = {' '}; 
%    matches =[];
%    Tags = Group_Tags.(FN{z}){3};
%    for t = 1:numel(Tags)      
%      Tag = Tags{t};
%      matches = [matches; find(~cellfun(@isempty,strfind(Col,Tag)))]; 
%%      if ~isempty(matches)
%%        for k = 1: numel(matches)
%%          disp(sprintf('%30s -> %.2f',Col{matches(k)},(CArray{matches(k),Col_Betrag})));
%%        end
%%      end      
%    end  
%    matches = unique(matches);
%    Res.(FN{z}).Tags = Tags;
%    Res.(FN{z}).SearchColNum = Col_ID;
%    Res.(FN{z}).SearchColTxt = CArray{1,Col_ID};
%    Res.(FN{z}).Ind = matches';
%    Res.(FN{z}).Value = cell2mat(CArray(matches,Col_Betrag))';
%%    find(~cellfun(@isempty,strfind(Col,Tag)))
%    Res.(FN{z}).DateNum = cell2mat(CArray(matches,Col_Date))+datenum('30-Dec-1899');
%    Res.(FN{z}).Date = cellstr(datestr(Res.(FN{z}).DateNum));  
%    Res.(FN{z}).Sum = sum(Res.(FN{z}).Value);
%    Res.(FN{z}).Gain = Group_Tags.(FN{z}){2};
    
     [S,matches]= get_GroupStruct(CArray,Group_Tags,FN{z},Col_Betrag,Col_Date);
     Res.(FN{z})=S;
    
    XLS_Cells.(FN{z}) = CArray(matches,:);
    CArray(matches,:) =[];
  end
    %Col_Search_Rest = 6;
    Res.Rest.Tags = {};
    Res.Rest.SearchColNum = Col_Search_Rest;
    Res.Rest.SearchColTxt = CArray{1,Col_Search_Rest};
    Res.Rest.Ind = 2:size(CArray,1);
    Res.Rest.Value = cell2mat(CArray(Res.Rest.Ind,Col_Betrag))';
    Res.Rest.DateNum = cell2mat(CArray(Res.Rest.Ind,Col_Date))+datenum('30-Dec-1899');
    Res.Rest.Date = cellstr(datestr(Res.Rest.DateNum));  
    Res.Rest.Sum = sum(Res.Rest.Value);
    Res.Rest.Gain = -1;
  rest = [];
  for z = 1:size(CArray,1)
    rest{z} = CArray{z,Col_Search_Rest};
  end
  UNI =unique( rest );
%  Res = CArray(ind,9);
  XLS_Cells.('Rest') = CArray;
  
  %export group entries to XLS_Cells
  if exist(XLS_Name,'file')
    delete(XLS_Name);
  else
    disp(['File not found <',XLS_Name,'> --> could not be deleted'])  
  endif
  F =fieldnames(XLS_Cells);
  for z = 1: numel(F)
    for k = 1: size(XLS_Cells.(F{z}),1)
      XLS_Cells.(F{z}){k,Col_Date} = datestr(XLS_Cells.(F{z}){k,Col_Date}+datenum('30-Dec-1899'),'dd.mm.yyyy');
    endfor
    xlswrite(XLS_Name,XLS_Cells.(F{z}),F{z});
  end
  xlswrite(XLS_Name,UNI,'unique');
end


function [S,matches] = get_GroupStruct(CArray,Group_Tags,Fieldname,Col_Betrag,Col_Date,Math)
    Col_ID = Group_Tags.(Fieldname){1};
    Col = CArray(:,Col_ID);
    dummy=(~cellfun(@ischar,Col));
    IND = find(dummy);
    Col(IND) = {' '}; 
    Tags = Group_Tags.(Fieldname){3};
    matches =[];
    if nargin == 6
      Val = cell2mat(CArray(2:end,Col_Betrag));
      matches = find(eval(['Val ',Math]))+1;
    else      
      for t = 1:numel(Tags)      
        Tag = Tags{t};
        matches = [matches; find(~cellfun(@isempty,strfind(Col,Tag)))]; 
  %      if ~isempty(matches)
  %        for k = 1: numel(matches)
  %          disp(sprintf('%30s -> %.2f',Col{matches(k)},(CArray{matches(k),Col_Betrag})));
  %        end
  %      end      
      end        
      matches = unique(matches);      
    endif
    S.Tags = Tags;
    S.SearchColNum = Col_ID;
    S.SearchColTxt = CArray{1,Col_ID};
    S.Ind = matches';
    S.Value = cell2mat(CArray(matches,Col_Betrag))';
%    find(~cellfun(@isempty,strfind(Col,Tag)))
    S.DateNum = cell2mat(CArray(matches,Col_Date))+datenum('30-Dec-1899');
    S.Date = cellstr(datestr(S.DateNum));  
    S.Sum = sum(S.Value);
    S.Gain =  Group_Tags.(Fieldname){2};
endfunction 
