import numpy as np
from matplotlib import pyplot as plt


def plot_brutto():
    x = []
    y = []
    y_40 = []
    y_20p= []
    for year in BruttoList.keys():
        x.append(int(year))
        y.append(BruttoList[year]['brutto'])
        y_40.append(BruttoList[year]['brutto']/35.0*40.0)
        y_20p.append(BruttoList[year]['brutto']*1.2)
    
    fig, axs = plt.subplots(1, 1)
    axs.plot(x,y,label='true')
    axs.plot(x,y_40,label='40h week')
    axs.plot(x,y_20p,label='120 %')
    axs.grid(True)
    axs.set_xlabel('year')
    axs.set_ylabel('brutto [€]')
    axs.legend()
    axs.set_ylim([40000,90000])
    plt.show()

BruttoList ={}
# BruttoList['2015'] = {
#     'brutto': 30400
# }
BruttoList['2016'] = {
    'brutto': 41882    
}
BruttoList['2017'] = {
    'brutto': 43070
}
BruttoList['2018'] = {
    'brutto': 48665
}
BruttoList['2019'] = {
    'brutto': 55000
}
BruttoList['2020'] = {
    'brutto': 51596
}
BruttoList['2021'] = {
    'brutto': 50053
}
BruttoList['2022'] = {
    'brutto': 54988,
    'netto': 34792
}


plot_brutto()