function [Group_Tags,Col_Betrag,Col_Date,Col_Search_Rest] = Load_groups(Profile)
if nargin == 0
  Profile = 'RB_KSK_Struct';
endif

switch Profile
  case 'RB_KSK'
    Group_Tags = {...
      6,'Gehalt',{'IAV','OFD-LBV'},1;...
      6,'AMAZON',{'AMAZON','LOVEFILM','Amazon Instant Video'},-1;...
      6,'PayPal',{'PayPal','PAYPAL'},-1;...
      6,'Telefon',{'1u1','HB-HANDY-LADEN','Vodafone','VODAFONE','CONGSTAR'},-1;...  
      6,'Tanken',{'HEM-','SHELL','ARAL','TOTAL-'},-1;...
      6,'Auto',{'Fahrzeughaus','A.T.U','AUTOHAUS','AUTO '},-1;...
      6,'Oeffis',{'DEUTSCHE BAHN','DB VERTRIEB','KARTE 6'},-1;...
      5,'Miete',{'Miet','MIETE','SVWZ+Miete','GBH-HANNOVER','LIEBER','STADTWERKE'},-1;... 
 ... %      6,'Miete',{'Miete','GBH-HANNOVER','LIEBER','STADTWERKE'},1;...
      6,'Einkauf',{'ALDI','REWE','EDEKA','PENNY','NETTO','REAL','LIDL','TRINKGUT'},-1;...
      6,'Bauspar',{'Deutsche Bank'},-1;...
      6,'Kleidung',{'ESPRIT','BOSS ','BROOXX','C&A','TOM TAILOR','DESIGNER OUTLETS','H&M','JACK & JONES','JEANS FRITZ','HEMPEL','SPORT SCHECK','SPORT VOSWINKEL','SHOE 4 U','HERRENMODE','GLOBETROTTER'},-1;...
      6,'Freunde&Familie',{'MARTIN WILD','Andre behrens','ANDRE BEHRENS','BEESE','BOMM','HELENE MAERZHAEUSER','BAUR, LUDWIG'},-1;...
      6,'Wohnen',{'HAGEBAU','IKEA','MAX BAHR','HORNBACH','OBI ','Buhl '},-1;...
      6,'Geldautomat',{'GA NR'},-1;...
      6,'Ira',{'Ira','IRA '},-1 ...
    };
    Col_Betrag = 9;
    Col_Date = 3;
    Col_Search_Rest  = 6;
    
    case 'RB_KSK_Struct'
    Group_Tags.Gehalt = {6,+1,{'IAV','OFD-LBV','Bundesagentur fuer Arbeit'}};
    Group_Tags.AMAZON = {6,-1,{'AMAZON','LOVEFILM','Amazon Instant Video'}};
    Group_Tags.PayPal = {6,-1,{'PayPal','PAYPAL'}};
    Group_Tags.Telefon = {6,-1,{'1u1','HB-HANDY-LADEN','Vodafone','VODAFONE','CONGSTAR'}};
    Group_Tags.WohnenWG = {5,-1,{'VODAFONE DES LAUFENDEN MONATS','Vodafone des laufenden','VODAFONE','TELEFON','ENERCITY ZUM ','SVWZ+Vodafone des laufenden ','AUSZAHLUNG RESTBETRAG VOM WG-KONTO','ANTEILIG GUTSCHRIFT ISTA','SVWZ+Weihnachtsbonus'}};
    Group_Tags.WohnenWG2 = {6,-1,{'BOMM'}};
    Group_Tags.Tanken = {6,-1,{'HEM-','SHELL','ARAL','TOTAL-','SB-TANK','STAR '}};
    Group_Tags.Auto = {6,-1,{'Oeffentliche Sach BS','Sachversicherun g Braunschweig','Fahrzeughaus','A.T.U','AUTOHAUS','AUTO ','REIFEN COM'}};
    Group_Tags.Oeffis = {6,-1,{'KARTE 6','UESTRA AG','AUTOMATENVERK'}};
    Group_Tags.Bahn = {6,-1,{'DEUTSCHE BAHN','DB VERTRIEB'}};
    Group_Tags.Miete = {5,-1,{'Miet','MIETE','SVWZ+Miete','GBH-HANNOVER','30900504-S','HAV25730'}};%,'LIEBER','MIETSICHERHEIT'
    Group_Tags.Einkauf = {6,-1,{'ALDI','REWE','EDEKA','PENNY','NETTO','REAL','LIDL','TRINKGUT','HOLAB','ROSSMANN','KAUFLAND ','MUELLER SAGT'}};
    Group_Tags.Sparen = {6,-1,{'Deutsche Bank','DEUTSCHE BANK','BAUSPAR','Remko Baur','REMKO BAUR'}};
    Group_Tags.Kleidung = {6,-1,{'ESPRIT','BOSS ','BROOXX','C&A','TOM TAILOR',...
      'DESIGNER OUTLETS','H&M','JACK & JONES','JEANS FRITZ','HEMPEL','SPORT SCHECK',...
      'SPORT VOSWINKEL','SHOE 4 U','HERRENMODE','GLOBETROTTER','LO + GO','OLYMP','SALAMANDER ',...
      'P&C DANKT'}};
    Group_Tags.Freunde = {6,-1,{'MARTIN WILD','Martin Wild','Franzi Schmidt','ULRICH, TONI','TONI ULRICH','MATTHIAS HOLL','Andre behrens','ANDRE BEHRENS','BEESE','BOMM','HELENE MAERZHAEUSER','Helene M',''}};
    Group_Tags.Familie = {6,-1,{'BAUR, LUDWIG','Baur, Ludwig'}};
    Group_Tags.Wohnen = {6,-1,{'HAGEBAU','IKEA','MAX BAHR','HORNBACH','OBI ','BUHL ','GLOBUS','DAENISCHES BETTENLAGER'}};
    Group_Tags.Geldautomat = {6,-1,{'GA NR'}};
    Group_Tags.Ira = {6,-1,{'Ira','IRA ','LIEBER'}};
    Group_Tags.Gesundheit = {6,-1,{'BKK SALZGITTER','CENTRAL','Central','ZAHNARZTPRAXIS','HENDRIK HOFFMANN','APOTHEKE'}};
    Group_Tags.Technik = {6,-1,{'SATURN','CONRAD','CYBERPORT','MEDIMAX'}};
    Group_Tags.Promotion = {6,-1,{'Clau sthal','TU Clausthal'}};
    
    Col_Betrag = 9;
    Col_Date = 3;
    Col_Search_Rest  = 6;
              
    case 'Gemein_DKB_Struct'
    Group_Tags.Gehalt = {4,+1,{'IAV','OFD-LBV','Bundesagentur fuer Arbeit'}};
    Group_Tags.AMAZON = {4,-1,{'AMAZON','LOVEFILM','Amazon Instant Video'}};
    Group_Tags.Telefon = {4,-1,{'1u1','HB-HANDY-LADEN','Vodafone','VODAFONE','CONGSTAR'}};
    Group_Tags.Tanken = {4,-1,{'HEM-','SHELL','ARAL','TOTAL-','SB-TANK','STAR '}};
    Group_Tags.Auto = {4,-1,{'Oeffentliche Sach BS','Sachversicherun g Braunschweig','Fahrzeughaus','A.T.U','AUTOHAUS','AUTO ','REIFEN COM'}};
    Group_Tags.Miete = {4,-1,{'Miet','MIETE','Volkswagen'}};
    Group_Tags.Einkauf = {4,-1,{'ALDI','REWE','EDEKA','PENNY','NETTO','REAL','LIDL','TRINKGUT','HOLAB','ROSSMANN','KAUFLAND ','MUELLER SAGT'}};
    Group_Tags.Familie = {4,-1,{'BAUR, LUDWIG','Baur, Ludwig'}};
    Group_Tags.Wohnen = {4,-1,{'HAGEBAU','IKEA','MAX BAHR','HORNBACH','OBI ','BUHL ','GLOBUS','DAENISCHES BETTENLAGER'}};
    Group_Tags.Geldautomat = {4,-1,{'GA NR'}};
%    Group_Tags.Ira = {4,-1,{'Ira','IRA ','LIEBER'}};
    Group_Tags.Gesundheit = {4,-1,{'BKK SALZGITTER','CENTRAL','Central','ZAHNARZTPRAXIS','HENDRIK HOFFMANN','APOTHEKE'}};
    
    Col_Betrag = 8;
    Col_Date = 2;     
    Col_Search_Rest  = 4;
    otherwise
endswitch


if nargout ==0
  disp(fieldnames(Group_Tags))
 clear Group_Tags Col_Betrag Col_Date Sort_ID
endif
endfunction




% ========================================================================
%case 'RB_KSK_Struct'
%    Group_Tags.Gehalt = {6,+1,{'IAV','OFD-LBV','Bundesagentur fuer Arbeit'}};
%    Group_Tags.AMAZON = {6,-1,{'AMAZON','LOVEFILM','Amazon Instant Video'}};
%    Group_Tags.PayPal = {6,-1,{'PayPal','PAYPAL'}};
%    Group_Tags.Telefon = {6,-1,{'1u1','HB-HANDY-LADEN','Vodafone','VODAFONE','CONGSTAR'}};
%    Group_Tags.WohnenWG = {5,-1,{'VODAFONE DES LAUFENDEN MONATS','Vodafone des laufenden','VODAFONE','TELEFON','ENERCITY ZUM ','SVWZ+Vodafone des laufenden ','AUSZAHLUNG RESTBETRAG VOM WG-KONTO','ANTEILIG GUTSCHRIFT ISTA','SVWZ+Weihnachtsbonus'}};
%    Group_Tags.WohnenWG2 = {6,-1,{'BOMM'}};
%    Group_Tags.Tanken = {6,-1,{'HEM-','SHELL','ARAL','TOTAL-','SB-TANK','STAR '}};
%    Group_Tags.Auto = {6,-1,{'Oeffentliche Sach BS','Sachversicherun g Braunschweig','Fahrzeughaus','A.T.U','AUTOHAUS','AUTO ','REIFEN COM'}};
%    Group_Tags.Oeffis = {6,-1,{'KARTE 6','UESTRA AG','AUTOMATENVERK'}};
%    Group_Tags.Bahn = {6,-1,{'DEUTSCHE BAHN','DB VERTRIEB'}};
%    Group_Tags.Miete = {5,-1,{'Miet','MIETE','SVWZ+Miete','GBH-HANNOVER','30900504-S','HAV25730'}};%,'LIEBER','MIETSICHERHEIT'
%    Group_Tags.Einkauf = {6,-1,{'ALDI','REWE','EDEKA','PENNY','NETTO','REAL','LIDL','TRINKGUT','HOLAB','ROSSMANN','KAUFLAND ','MUELLER SAGT'}};
%    Group_Tags.Sparen = {6,-1,{'Deutsche Bank','DEUTSCHE BANK','BAUSPAR','Remko Baur','REMKO BAUR'}};
%    Group_Tags.Kleidung = {6,-1,{'ESPRIT','BOSS ','BROOXX','C&A','TOM TAILOR',...
%      'DESIGNER OUTLETS','H&M','JACK & JONES','JEANS FRITZ','HEMPEL','SPORT SCHECK',...
%      'SPORT VOSWINKEL','SHOE 4 U','HERRENMODE','GLOBETROTTER','LO + GO','OLYMP','SALAMANDER ',...
%      'P&C DANKT'}};
%    Group_Tags.Freunde = {6,-1,{'MARTIN WILD','Martin Wild','Franzi Schmidt','ULRICH, TONI','TONI ULRICH','MATTHIAS HOLL','Andre behrens','ANDRE BEHRENS','BEESE','BOMM','HELENE MAERZHAEUSER','Helene M',''}};
%    Group_Tags.Familie = {6,-1,{'BAUR, LUDWIG','Baur, Ludwig'}};
%    Group_Tags.Wohnen = {6,-1,{'HAGEBAU','IKEA','MAX BAHR','HORNBACH','OBI ','BUHL ','GLOBUS','DAENISCHES BETTENLAGER'}};
%    Group_Tags.Geldautomat = {6,-1,{'GA NR'}};
%    Group_Tags.Ira = {6,-1,{'Ira','IRA ','LIEBER'}};
%    Group_Tags.Gesundheit = {6,-1,{'BKK SALZGITTER','CENTRAL','Central','ZAHNARZTPRAXIS','HENDRIK HOFFMANN','APOTHEKE'}};
%    Group_Tags.Technik = {6,-1,{'SATURN','CONRAD','CYBERPORT','MEDIMAX'}};
%    Group_Tags.Promotion = {6,-1,{'Clau sthal','TU Clausthal'}};
%    
%    Col_Betrag = 9;
%    Col_Date = 3;
%       