function Res = re_sort_struct(Res,New_Group)
  for z = 1:size(New_Group,1) 
    F = New_Group{z,2};
    Dummy = [];
    for f =1:numel(F)
      if ~isfield(Res,F{f})
        continue
      endif  
      if f ==1
        Dummy = Res.(F{f});
      else
        FF = fieldnames(Res.(F{f}));
        for ff = 1: numel(FF)
          if iscellstr(Res.(F{f}).(FF{ff}))
            Dummy.(FF{ff}) = union(Dummy.(FF{ff}),Res.(F{f}).(FF{ff}));
          elseif diff(size(Dummy.(FF{ff})))>0            
            Dummy.(FF{ff}) = [Dummy.(FF{ff}),Res.(F{f}).(FF{ff})];
          else
            Dummy.(FF{ff}) = [Dummy.(FF{ff});Res.(F{f}).(FF{ff})];
          endif
        endfor
      endif
    endfor    
    
    Res.(New_Group{z,1}) = Dummy;
    old_fields = New_Group{z,2};
    for f =1:numel(old_fields)
      Res = rmfield(Res,old_fields{f});
    endfor
  endfor


endfunction