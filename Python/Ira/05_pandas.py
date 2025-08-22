# use external packages (libraries, classes,...)
# - packeges must be installed before
# - use package with "import <packagename>", or
# - use package with "import <packagename> as <alias which will be used in the following code>"

import pandas as pd # "pandas" has all required methods for handling tables and excel files
import os # "os" (operating system) can handle files and paths

path1 = os.path.abspath(__file__) # use path of this file, it's relative so you can move this file without changing this path
path2 = r"D:\Git\Programming\Python\Ira" # "r" before string is important as now each "\" will be replaced by "\\"

filename = "Test.xlsx" # name of excel file
path = path2 # path of excel file

# join path and filename
full_filename = os.path.join(path,filename)
print(f"join({path},{filename}) = {full_filename}")
#region: create excel file
# create table content as python dictionary
dict = {
    "Col_1": [1,2,3],
    "Col_2": ["Hello","World","!"]
}
# create dataframe from dict
df=pd.DataFrame(dict)
# write data frame to excel file
df.to_excel(full_filename,index=False)
#endregion 

#region:read excel file
# delete Dataframe (override with empty one)
df=pd.DataFrame()
# check if excel file is found
if (not os.path.isfile(full_filename)):
    print(f"ERROR:  File not found: {full_filename}")
else:
    print(f"import excel file: {full_filename}")
    #import excel file to DataFrame
    df=pd.read_excel(full_filename,index_col="Col_1")

# print content of dataframe 
print(df.to_string())
#endregion