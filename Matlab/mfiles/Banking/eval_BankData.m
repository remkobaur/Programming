function [data] = eval_BankData(Data,FNames,StartDate,EndDate,Mode,PlotMode)
  if nargin <6
    PlotMode = ' ';
  endif
SX = {}; SY = {};Leg = {};
y_1 = year(StartDate);
y_end = year(EndDate);
Y_pie =[];%zeros((y_end-y_1),numel(FNames));

yy = (y_1:y_end);
mm = 1:12;

for z = 1:numel(FNames)
%  disp(FNames{z});
  ind = find( (Data.(FNames{z}).DateNum>=StartDate) & (Data.(FNames{z}).DateNum<=EndDate) );

  dat = Data.(FNames{z}).DateNum(ind);
  val = Data.(FNames{z}).Value(ind)*Data.(FNames{z}).Gain(1);

  M = month(dat);
  Y = year(dat);
%  mm = unique(M);

  x = []; y=[];
  switch Mode
    case 'month'
      [x,y,Y_pie(:,z)] = get_plotdata_month(Data.(FNames{z}),StartDate,EndDate);
    case 'year'
      [x,y,Y_pie(:,z)] = get_plotdata_year(Data.(FNames{z}),StartDate,EndDate);
    otherwise
      disp('--> Mode muss "month" ode "year" sein');
      return      
  endswitch  
  Leg{z} = FNames{z};
  if isempty(x)
    disp('x is empty')
    SX(z) = 0;
    SY(z) = 0;
  else
    SX(z) = x;
    SY(z) = y;    
  endif  
endfor

if all(ismember({'Ausgaben','Sparen'},Leg)) 
  ind_aus = find(ismember(Leg,'Ausgaben'));
  ind_spa = find(ismember(Leg,'Sparen'));
  
  if (PlotMode == 'pie')
    Y_pie(:,ind_aus) = Y_pie(:,ind_aus) - Y_pie(:,ind_spa); 
    disp('--> Sparen wurde von Ausgaben abgezogen (y_pie)')
  else   
    SY{ind_aus} = SY{ind_aus} - SY{ind_spa};
    disp('--> Sparen wurde von Ausgaben abgezogen (SY)')
  endif
endif

if all(ismember({'Ausgaben','Ira'},Leg)) 
  ind_aus = find(ismember(Leg,'Ausgaben'));
  ind_ira = find(ismember(Leg,'Ira'));
  
  if (PlotMode == 'pie')
    Y_pie(:,ind_aus) = Y_pie(:,ind_aus) - Y_pie(:,ind_ira); 
    disp('--> Ira wurde von Ausgaben abgezogen (y_pie)')
  else   
    SY{ind_aus} = SY{ind_aus} - SY{ind_ira};
    disp('--> Ira wurde von Ausgaben abgezogen (SY)')
  endif
endif


data.SX = SX;
data.SY = SY;
data.Y_pie = Y_pie;
data.Leg = Leg;
data.yy = yy;
data.mm = mm;

%Style = {'k*-','b*-','r*-','m*-','g*-','k*:','b*:','r*:','m*:','g*:','ko-','bo-','ro-','mo-','go-'};
%
%switch Mode
%  case 'month'  
%    figure(1);clf;
%    for z = 1: numel(SX)
%      plot(SX{z},SY{z},Style{mod(z-1,15)+1});hold on;
%    endfor
%%      datetick('x','mm-yy','keepticks');
%      ylabel('Betrag [EUR]');
%      title('Monatliche Auswertung');
%      %xlim([StartDate,EndDate]);
%      legend(Leg,'Location','EastOutside');
%      grid on
%  case 'year'
%    switch PlotMode
%      case 'pie' 
%      figure(2);clf;
%        N = size(Y_pie,1);     
%        c = ceil(sqrt(N));
%        r = ceil(N/c); 
%        for z =1:N
%          subplot(r,c,z);
%          explodes = ones(size(Y_pie(z,:)))*2;
%          pie(Y_pie(z,:),explodes);
%          title(num2str(yy(z)));
%        endfor
%%        legend(Leg,'Location','SouthOutside','Orientation','vertical');
%        legend(Leg,'Location','EastOutside','Orientation','vertical');
%      otherwise
%        figure(3);clf;
%        for z = 1: numel(SX)
%          plot(SX{z},SY{z},Style{mod(z,12)+1});hold on;
%        endfor
%        hold off;grid on
%%        datetick('x','yyyy');  %,'keepticks'
%        ylabel('Betrag [EUR]');      
%%        xlim([StartDate,EndDate]);
%        title('Jaehrliche Auswertung');
%        legend(Leg,'Location','EastOutside');
%    endswitch
%
%  otherwise
%    disp('--> Mode muss "month" ode "year" sein');
%    return
%endswitch

endfunction
%% ============================================================


function [x,y,Y_pie] = get_plotdata_year(Data,StartDate,EndDate)
   
  ind = find( (Data.DateNum>=StartDate) & (Data.DateNum<=EndDate) );

  dat = Data.DateNum(ind);
  val = Data.Value(ind)*Data.Gain(1);
 
  y_1 = year(StartDate);
  y_end = year(EndDate); 
  Y_pie =zeros((y_end-y_1),numel(Data));

  yy = (y_1:y_end);
  mm = 1:12;
  
  M = month(dat);
  Y = year(dat);
  
  x = [];y=[];
      for zy = 1:numel(yy)
          ind = find(Y==yy(zy));
          if isempty(ind)
            x = [x;datenum([sprintf('01-01-%04d',yy(zy))],'dd-mm-yyyy')];            
            y = [y;0];    
          else  
            x = [x;dat(ind(1))];
            y = [y;sum(val(ind))];
          endif  
      endfor     
      x = year(x);
      for zy = 1:numel(yy)
        ind = find(Y==yy(zy));
        if isempty(ind)
          Y_pie(zy) = 0;   
        else  
          Y_pie(zy) = sum(val(ind)) ; 
        endif          
      endfor   
endfunction

function [x,y,Y_pie] = get_plotdata_month(Data,StartDate,EndDate)
   
  ind = find( (Data.DateNum>=StartDate) & (Data.DateNum<=EndDate) );

  dat = Data.DateNum(ind);
  val = Data.Value(ind)*Data.Gain(1);
 
  y_1 = year(StartDate);
  y_end = year(EndDate); 
  Y_pie =zeros((y_end-y_1),numel(Data));

  yy = (y_1:y_end);
  mm = 1:12;
  
  M = month(dat);
  Y = year(dat);
  
  x = [];y=[];
    for zy = 1:numel(yy)
      for zm = 1:numel(mm)
        ind = find(M==mm(zm) & Y==yy(zy));
        if isempty(ind)
          x = [x;datenum([sprintf('01-%02d-%04d',mm(zm),yy(zy))],'dd-mm-yyyy')];            
          y = [y;0];   
        else
          x = [x;dat(ind(1))];
          y = [y;sum(val(ind))];
        endif          
      endfor
    endfor     

    for zy = 1:numel(yy)  % < ================ !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
      ind = find(Y==yy(zy));
      if isempty(ind)
        Y_pie(zy) = 0;   
      else  
        Y_pie(zy) = sum(val(ind)) ; 
      endif          
    endfor   
    
    YEAR = year(x);
    MONTH = month(x);
    x_mon = YEAR +MONTH./12;
    x = x_mon;
endfunction


