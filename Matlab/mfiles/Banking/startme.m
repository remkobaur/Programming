 function startme
 clc;%clear;
 
LoadPath = 'F:\mfiles\Banking\';

switch 1
case 1
  SourceXls = 'KSK-2015_08_09.xlsx';
  SaveName = 'Eval_KSK.mat';
  TabName = 'KSK-Filter';

  StartDate = datenum('01-JAN-2012');
  EndDate   = datenum('31-DEC-2015');
 
  [Group_Tags,Col_Betrag,Col_Date,Col_Search_Rest] = Load_groups('RB_KSK_Struct');
  
case 2
  SourceXls = 'DKB_Gemein_2016_April.xlsx';
  SaveName = 'Eval_DKB_Gemein.mat';
  TabName = 'DKB_Gemein_2016_April';

  StartDate = datenum('01-JAN-2016');
  EndDate   = datenum('31-APR-2016');

  [Group_Tags,Col_Betrag,Col_Date,Col_Search_Rest] = Load_groups('Gemein_DKB_Struct');
end

b_extract_data_force = 1;


%% ****************  execute evaluation ************************
if ~exist([LoadPath,SaveName],'file')  || b_extract_data_force
  CArray = LoadXLS(LoadPath,SourceXls,TabName);
  Res = extract_BankData(CArray,Group_Tags,Col_Betrag,Col_Date,Col_Search_Rest);
  save([LoadPath,SaveName],'Res')
else
  load([LoadPath,SaveName])
endif  


fun_Disp_fieldnames(Res);

%%% Grafische Darstellung 
%figure(23452);
%N_plots = 4;
%N_year = round(year(EndDate)-year(StartDate))+1;
%for y = 1: N_year
%  figh(y) =subplot(N_plots,N_year,y);
%endfor
%figh(y+1) =subplot(N_plots,N_year,1*N_year+[1:N_year]);
%figh(y+2) =subplot(N_plots,N_year,2*N_year+[1:N_year]);
%figh(y+3) =subplot(N_plots,N_year,3*N_year+[1:N_year]);
%
%%Mode = 'year'; %{'month','year'},
%%PlotMode =  'pie';%{'','pie'}
%
%[res,FNames] = fun_resort_groups(Res,0);
%[data] = eval_BankData(res,FNames,StartDate,EndDate,'year','pie'); 
%data.figh= figh(1:N_year);
%plot_BankData(data,FNames,StartDate,EndDate,'year','pie');
%
%[res,FNames] = fun_resort_groups(Res,1);
%[data] = eval_BankData(res,FNames,StartDate,EndDate,'month'); 
%data.figh= figh(N_year+1);
%plot_BankData(data,FNames,StartDate,EndDate,'month','');
%
%[res,FNames] = fun_resort_groups(Res,2);
%[data] = eval_BankData(res,FNames,StartDate,EndDate,'month'); 
%data.figh= figh(N_year+2);
%plot_BankData(data,FNames,StartDate,EndDate,'month','');
%ylim([0,800])
%
%[res,FNames] = fun_resort_groups(Res,3);
%[data] = eval_BankData(res,FNames,StartDate,EndDate,'month'); 
%data.figh= figh(N_year+3);
%plot_BankData(data,FNames,StartDate,EndDate,'month','');
%ylim([-500,1000])
FNames = fieldnames(Res);
[data] = eval_BankData(Res,FNames,StartDate,EndDate,'month'); 
data.figh = figure(23425);
plot_BankData(data,FNames,StartDate,EndDate,'month','');

disp('finished')
endfunction

%% **************** resort groups *****************************
function [Res,FNames] = fun_resort_groups(Res,Mode)
  switch Mode
    case 0
      FNames = {'Einnahmen','Ausgaben','Sparen'};
      Res.Ausgaben.Value = -1*Res.Ausgaben.Value;
    case 1
      New_Group = {...
        ...'Bestellung',{'AMAZON','PayPal'};...
        'Mobility',{'Tanken','Oeffis'};...
        'Wohnung',{'Miete','Telefon','Wohnen','WohnenWG2','WohnenWG'};...
        ...'Diverses',{'Sparen','Auto', 'Einkauf', 'Kleidung', 'Freunde', 'Familie', 'Geldautomat', 'Bahn','Ira', 'Gesundheit', 'Technik', 'Promotion', 'Rest', 'Bestellung', 'Mobility', 'Wohnung'};...
        };
      Res = re_sort_struct(Res,New_Group);
      FNames = {'Gehalt'};
      case 2
      New_Group = {...
        ...'Bestellung',{'AMAZON','PayPal'};...
        'Mobility',{'Tanken','Oeffis'};...
        'Wohnung',{'Miete','Telefon','Wohnen','WohnenWG2','WohnenWG'};...
        ...'Diverses',{'Sparen','Auto', 'Einkauf', 'Kleidung', 'Freunde', 'Familie', 'Geldautomat', 'Bahn','Ira', 'Gesundheit', 'Technik', 'Promotion', 'Rest', 'Bestellung', 'Mobility', 'Wohnung'};...
        };
      Res = re_sort_struct(Res,New_Group);
      FNames = {'Wohnung','Mobility','Einkauf'};
    case 3
      New_Group = {...
        'Bestellung',{'AMAZON','PayPal'};...            
        };    
      Res = re_sort_struct(Res,New_Group);
      FNames = {'Bestellung','Kleidung','Geldautomat','Auto','Rest'};    % 'Gesundheit',
    case 4
      New_Group = {...
        'Bestellung',{'AMAZON','PayPal'};...
        'Mobility',{'Tanken','Oeffis'};...
        'Wohnung',{'Miete','Telefon','Wohnen','WohnenWG2','WohnenWG'};...     
        };    
      Res = re_sort_struct(Res,New_Group);
      FNames = {'Gehalt','Einkauf','Geldautomat','Wohnung','Mobility','Bestellung','Auto','Rest','Ira'};
      
  %    Res.Ausgaben.Value = -1*Res.Ausgaben.Value;
  %    FNames = {'Einnahmen','Ausgaben','Sparen','Ira'};
    otherwise
      FNames = fieldnames(Res);
      New_Group={};
  endswitch
endfunction

%% **************** show fieldnames in command line *****************************
function fun_Disp_fieldnames(Res)
  F = fieldnames(Res);dummy = '';
  for f =1:numel(F)
    dummy = [dummy,'''',F{f},''', '];
  endfor
  disp(dummy(1:end-2))
endfunction 