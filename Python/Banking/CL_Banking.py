from CL_Tables import CL_Tables 
import matplotlib.pyplot as plt
import matplotlib.dates
from datetime import datetime
import numpy as np
import copy

class cl_plotdata:
    xdata = []
    ydata = []
    name = ""
    def __init__(self,xdata=[],ydata=[],name=""):
        self.xdata = xdata
        self.ydata = ydata
        self.name  = name      

class CL_Banking:
    tab     = CL_Tables()
    backup  = CL_Tables()
    plotData = [] 
    date_format='%d.%m.%y'


    def __init__(self):
        pass
    
    def data_restore(self):
        self.tab = copy.deepcopy(self.backup)
        
    def data_save(self):
        self.backup = copy.deepcopy(self.tab)

    def load_csv_Sparkasse(self,csv_name):
        self.tab.set_path(r"D:\Docs\0_Docs_Remko\Unterlagen\Banking\Sparkasse\KSK export")    
        self.tab.load_csv(csv_name)
        self.data_save()

    def sort_by_date(self):
        self.tab.sort_by_date('Buchungstag',format=self.date_format)

    def filter_date(self,start,stop,colName='Buchungstag'):
        self.tab.filter_column_by_date(colName,start,stop)
        self.tab.filter_set_df_as_default()

    def filter_default(self):
        self.tab.reduce_columns(['Buchungstag','Buchungstext','Beguenstigter/Zahlungspflichtiger','Betrag','Waehrung'])
        # self.tab.filter_set_df_as_default()

    def filter_col_subString(self,colName,subString):
        self.tab.filter_column_by_substring(colName,subString)
        self.tab.filter_set_df_as_default()

    def get_column_vector(self,colName):
        # return(self.tab.DB[colName].to_numpy())
        return(self.tab.DB[colName])
    
    def plot_data_add(self,colVal,colDate,colSearch,searchString):
        self.data_save()
        self.filter_col_subString(colSearch,searchString)
        dates = bk.get_column_vector(colDate)
        y = bk.get_column_vector(colVal)       
        self.data_restore()

        y = y.replace(regex={',': '.'}).astype(float)        
        y = np.asarray(y, dtype=float)

        x = [datetime.strptime(d, self.date_format) for d in dates]
        xs= matplotlib.dates.date2num(x)
        # hfmt = matplotlib.dates.DateFormatter('%m.%y')
        self.plotData.append(cl_plotdata(xs,y,searchString))

    def plot_all_over_date(self,cumsum=False):
        hfmt = matplotlib.dates.DateFormatter('%m.%y')
        # hfmt = matplotlib.dates.DateFormatter('%Y-%m-%d\n%H:%M:%S')

        fig = plt.figure()
        fig.set_figwidth(12)
        ax = fig.add_subplot(1,1,1)
        ax.patch.set_facecolor('lightgrey')
        ax.xaxis.set_major_formatter(hfmt)
        ax.set_title(' plot_all_over_date()')
        ax.set_xlabel('datum')
        ax.set_ylabel('Wert [Eur]')
        plt.setp(ax.get_xticklabels(), size=8)
        for line in self.plotData:
            if (cumsum):
                line.ydata = np.cumsum(np.absolute(line.ydata))
            ax.plot(line.xdata, line.ydata, label=line.name,linewidth=2)
            ax.scatter(line.xdata, line.ydata)
            # print('---')
            # print(line.ydata)

        plt.legend()
        plt.grid()
        plt.show()

    def plot_over_date(self,col_Date,col_Value,yLabel='y label'):
        dates = bk.get_column_vector(col_Date)
        y = bk.get_column_vector(col_Value)
        # print(dates)
        # print(val)
        x = [datetime.strptime(d, '%d.%m.%y') for d in dates]
        xs= matplotlib.dates.date2num(x)
        hfmt = matplotlib.dates.DateFormatter('%m.%y')
        # hfmt = matplotlib.dates.DateFormatter('%Y-%m-%d\n%H:%M:%S')

        fig = plt.figure()
        fig.set_figwidth(12)
        ax = fig.add_subplot(1,1,1)
        ax.patch.set_facecolor('lightgrey')
        ax.xaxis.set_major_formatter(hfmt)
        ax.set_title(' plot_over_date({col_Date},{col_Value})')
        ax.set_xlabel('datum')
        ax.set_ylabel(yLabel)
        plt.setp(ax.get_xticklabels(), size=8)
        ax.plot(xs, y, linewidth=2)
        plt.legend([yLabel])
        ax.scatter(xs, y)
        plt.grid()
        plt.show()

    def show_header(self):
        self.tab.show_colnames()

    def show_results(self):
        print(' --- ')
        self.tab.show_table()
    

bk = CL_Banking()
bk.load_csv_Sparkasse("20180218-1901055728-umsatz.CSV")
bk.sort_by_date()
# bk.show_results()
# exit()
bk.filter_default()
bk.filter_date('01.01.17','31.12.18',colName='Buchungstag')
bk.data_save()
# bk.filter_col_subString("Buchungstext","LOHN")
# bk.show_results()
# bk.plot_over_date('Buchungstag','Betrag',yLabel='Lohn')
bk.plot_data_add(colVal='Betrag',colDate='Buchungstag',colSearch='Buchungstext',searchString='LOHN')
bk.plot_data_add(colVal='Betrag',colDate='Buchungstag',colSearch='Buchungstext',searchString='ONLINE-UEBERWEISUNG')
bk.plot_data_add(colVal='Betrag',colDate='Buchungstag',colSearch='Buchungstext',searchString='KARTENZAHLUNG')
bk.plot_all_over_date(cumsum=True)