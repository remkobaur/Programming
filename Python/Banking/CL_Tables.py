import pandas as pd 
import os
from IPython.display import display

class CL_Tables:
    DB = []
    DB_Filt = []
    path = ""
    csv_encoding = "ISO-8859-1"
    csv_seperator = ";"
    format_date = '%d.%m.%y'

    def CL_Tables(self):
        self.DB = pd.DataFrame()
        self.DB_Filt = pd.DataFrame()
        pass

    def set_path(self,path):
        self.path = path
        
    def load_csv(self,filename):
        fullfile = os.path.join(self.path,filename)
        if (not os.path.isfile(fullfile)):
            print(f"File not found: {fullfile}")
        else:
            print(f"File okay: {fullfile}")
        self.DB = pd.read_csv(fullfile,encoding = self.csv_encoding, sep=self.csv_seperator)

    def show_colnames(self):
        column_names = self.DB.columns
        print(column_names)      

    def sort_by_date(self,colDate,format='%y%m%d%H%M%S'):
        # self.DB['dttime'] = pd.to_datetime(self.DB[colDate], format=format)
        self.DB['date_mod'] = pd.to_datetime(self.DB[colDate],format=format)
        self.DB=self.DB.sort_values(by='date_mod')    

    def reduce_columns(self,columnNameArray):
        self.DB = self.DB[columnNameArray]

    def filter_column_by_substring(self,colName,subString):
        self.DB_Filt = self.DB[self.DB[colName].str.contains(subString)]        


    def filter_column_by_date(self,colName,start,end):
        self.DB_Filt = self.DB[(pd.to_datetime(self.DB[colName],format=self.format_date) > pd.to_datetime(start,format=self.format_date)) & (pd.to_datetime(self.DB[colName],format=self.format_date) <  pd.to_datetime(end,format=self.format_date))]

    def convert_date(self):
        format='%Y-%m-%d %H:%M:%S.%f'

    def filter_set_df_as_default(self):
        self.DB = self.DB_Filt

    def show_db_size(self,db):
        print(f"size of dataframe: {db.shape[0]} rows |  {db.shape[1]} columns ")

    def show_table(self,db=pd.DataFrame()):
        if (db.shape[0] == 0):
            db=self.DB
        # print(self.DB.to_string()) 
        pd.set_option('display.max_columns', None) 
        pd.set_option('display.max_rows', None)
        pd.set_option("expand_frame_repr", False)
        pd.options.display.max_seq_items = 200000
        display(db)
    def show_table_DBfilt(self):
        self.show_table(db=self.DB_Filt)

#Testing
tab = CL_Tables()
tab.set_path(r"D:\Docs\0_Docs_Remko\Unterlagen\Banking\Sparkasse\KSK export")    
tab.load_csv("20240705-1901055728-umsatz.CSV")
# tab.show_table()
# tab.show_colnames()
tab.reduce_columns(['Buchungstag','Buchungstext','Beguenstigter/Zahlungspflichtiger','Betrag','Waehrung'])
tab.show_colnames()

# tab.show_db_size(tab.DB)
# tab.filter_column_by_substring("Buchungstext","LOHN")
# tab.filter_set_df_as_default()
tab.filter_column_by_date('Buchungstag','01.06.24','30.06.24')
tab.filter_set_df_as_default()
tab.show_table()