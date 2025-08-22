import os
import pandas as pd

Settings = {
'title': 'My Link Collection',
'path': os.path.realpath(os.path.join(os.path.dirname(__file__),r'../../../','HTML')),
'html_file':'Links.html',
'excel_file': 'Links.xlsx'
}

html_file = os.path.join(Settings['path'],Settings['html_file'])
excel_file =  os.path.join(Settings['path'],Settings['excel_file'])

def import_links():    
    print(f'import excel file: {excel_file}')
    df = pd.read_excel(excel_file)
    # print(df)

    # find unique groups
    groups = []
    unique = [groups.append(x) for x in df['Group'] if x not in groups]
    # print(groups)
    DB = {}
    for g in groups:
        # print(g)
        dummy = df[df.Group.str.contains(g)]
        DB[g] = []
        for index, row in dummy.iterrows():
            DB[g].append({'name':row['Name'],'link':row['Link']})
        # print(DB[g]) 
    # print(DB)
    return DB

def create_html_content(DB):
    tab = '\t\t\t'
    # sidebar
    content= '<h1>List of my Links</h1>\n'    
    content += f'{tab}<div class="sidebar">\n{tab}\t<h2>Groups</h2>\n{tab}\t<ul>\n' 
    content += f'{tab}\t\t<li><a href="#search">Google Search</a></li>\n' 
    for groupname in DB:
        content += f'{tab}\t\t<li><a href="#{groupname}">{groupname}</a></li>\n' 
    content += f'{tab}\t<ul>\n{tab}</div>\n' 


    # content
    content += f'<div class="content">\n'
    content += f'{tab}<div class="search-bar-container" id =search>\n'
    content += f'{tab}\t<form action="https://www.google.com/search" method="GET" class="search-bar">\n'
    content += f'{tab}\t\t<input name="q" type="text" placeholder="search anaything">\n'
    content += f'{tab}\t\t<button type="submit"><img src="images/Lupe.png" /></button>\n'
    content += f'{tab}\t</form>\n' 

    for groupname in DB:
        group = DB[groupname]
        content += f'{tab}<div class="container">\n{tab}\t<h2 id ={groupname}>{groupname}</h2>\n{tab}\t<ul>\n' 
        for item in group:
            name = item['name']
            link = item['link']
            content += f'{tab}\t\t<li><a href="{link}">{name}</a></li>\n' 
        content += f'{tab}\t<ul>\n{tab}</div>\n' 
    content += f'</div>\n'
    return content
        
            

def create_html_page(DB):
    html_content = 'Test text'
    html_content = create_html_content(DB)

    html_code = ''
    html_code += '<!DOCTYPE html>\n'
    html_code += '<html>\n'
    html_code += '  <head>\n'
    html_code += '    <meta charset="utf-8">\n'
    html_code += '    <meta name="Link Collection" content="width=device-width, initial-scale=1.0">\n'
    html_code += '    <LINK href="mystyle.css" rel="stylesheet" type="text/css">\n'
    html_code +=f'    <title>{Settings["title"]}</title>\n'
    html_code += '  </head>\n'
    html_code += '  <body>\n'
    html_code +=f'  {html_content}\n'
    html_code += '  </body>\n'
    html_code += '</html>\n'


    print(html_code) 

    #create html file with generated html content
    with open(html_file, 'w') as f:
        f.write(html_code)
        
# -------------------------------------------------------------------------
#                                   Main 
# -------------------------------------------------------------------------
DB = import_links()
create_html_page(DB)


print(html_file)

