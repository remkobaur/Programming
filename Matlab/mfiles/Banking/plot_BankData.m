function plot_BankData(Data,FNames,StartDate,EndDate,Mode,PlotMode)
%Style = {'k*-','b*-','r*-','m*-','g*-','k*:','b*:','r*:','m*:','g*:','ko-','bo-','ro-','mo-','go-'};
Style = {'k-','b-','r-','m-','g-','k*:','b*:','r*:','m*:','g*:','ko-','bo-','ro-','mo-','go-'};
SX = Data.SX;
SY = Data.SY;
yy = Data.yy;
mm = Data.mm;
Y_pie = Data.Y_pie;
Leg = Data.Leg;
figh = Data.figh;
switch Mode
  case 'month'  
%    clf;
    for z = 1: numel(SX)
      plot(figh,SX{z},SY{z},Style{mod(z-1,15)+1});hold on;
%      stem(figh,SX{z},SY{z},Style{mod(z-1,15)+1});hold on;
    endfor
%      datetick('x','mm-yy','keepticks');
      ylabel('Betrag [EUR]');
      title('Monatliche Auswertung');
      %xlim([StartDate,EndDate]);
      legend(Leg,'Location','EastOutside','Orientation','vertical');
      grid on
  case 'year'
    switch PlotMode
      case 'pie' 
%      clf;
        N = size(Y_pie,1);     
        c = ceil(sqrt(N));
        r = ceil(N/c); 
        for z =1:N
%          subplot(r,c,z);
          explodes = ones(size(Y_pie(z,:)))*2;
          axes(figh(z));
          pie(Y_pie(z,:),explodes);
          title(num2str(yy(z)));
        endfor
%        legend(Leg,'Location','SouthOutside','Orientation','vertical');
        legend(Leg,'Location','EastOutside','Orientation','vertical');
      otherwise
%        clf;
        for z = 1: numel(SX)
          plot(figh,SX{z},SY{z},Style{mod(z,12)+1});hold on;
        endfor
        hold off;grid on
%        datetick('x','yyyy');  %,'keepticks'
        ylabel('Betrag [EUR]');      
%        xlim([StartDate,EndDate]);
        title('Jaehrliche Auswertung');
        legend(Leg,'Location','EastOutside','Orientation','vertical');
    endswitch

  otherwise
    disp('--> Mode muss "month" ode "year" sein');
    return
endswitch
endfunction