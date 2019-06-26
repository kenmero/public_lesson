#スクレイピング
from bs4 import BeautifulSoup as bs
import urllib.request
#db
import sqlite3
from contextlib import closing
import csv

#翻訳
from googletrans import Translator

#定数
DBNAME = 'ansible.db'
SITE = 'https://docs.ansible.com/ansible/latest/reference_appendices/config.html'

def insert_common_option():
    #html情報取得
    r = urllib.request.urlopen(SITE)
    html = r.read()
    parser = 'html.parser'
    sp = bs(html, parser)

    id_common = sp.find('div', {'id': 'common-options'})
    #セクションタグ内の要素取得
    for section in id_common.find_all('div', {'class': 'section'}):

        option = section.find("h3").text
        print('***********************************')
        print(option)
        insert_dict = {'Option': option}
        #table要素取得
        for table in section.find_all('tbody', {'valign': 'top'}):

            # #使用されている見出しを全パターン検出
            # for th in table.find_all('th', {'class': 'field-name'}):
            #     if th.text in column:
            #         continue
            #     column.append(th.text)
            #     print(th.text)

            #レコード毎に処理
            iter_table = iter(table.find_all('tr'))
            for tr in iter_table:
                try:
                    th_text = tr.find('th').text
                    td = tr.find('td')
                    if td is None:
                        td = iter_table.__next__()
                    td_text = td.text

                    if 'Default' in th_text:
                        th_text = 'Df'
                    insert_dict.update({th_text.replace(' ', '_').replace(':', ''): td_text})
                except Exception as e:
                    print(th_text)
                    print(tr.find('td'), str(e.args))

            #登録用にデータ成型
            # insert_key  = ','.join(insert_dict.keys())
            # insert_data = ','.join(insert_dict.values())
            max_val = len(insert_dict.keys()) - 1
            for i, key in enumerate(insert_dict):
                if i == 0:
                    insert_key  = '"' + key + '"'
                    insert_data = '"' + insert_dict[key] + '"'
                    continue
                insert_key += ',"' + key + '"'
                insert_data += ',"' + insert_dict[key] + '"'
            # print(insert_key)
            # print(insert_data)
            # テーブルに登録
            insert_sql = 'insert into Ansible_Cfg ({0}) values ({1})'
            insert_sql = insert_sql.format(insert_key, insert_data)
            print(insert_sql)

            with closing(sqlite3.connect(DBNAME)) as con:
                try:
                    cur = con.cursor()
                    cur.execute(insert_sql)
                    con.commit()
                except Exception as e:
                    with open('insert_db_error.log', 'a') as f:
                        print(str(e.args))

def insert_environment():
    #翻訳オブジェクト
    tl = Translator()
    #環境変数セクション取得
    try:
        r = urllib.request.urlopen(SITE)
    except Exception as e:
        print('error')
        raise Exception
    html = r.read()
    parser = 'html.parser'
    sp = bs(html, parser)

    #INSERTデータ取得
    key_op = 'Option'
    key_des = 'Description'
    key_ja_des = 'ja_description'
    insert_data = []
    env_section = sp.find('div', {'id': 'environment-variables'})
    for envvar in env_section.find_all('dl', {'class': 'envvar'}):
        #環境変数名取得
        env_name = envvar.find('code', {'class': 'descname'}).text
        #概要取得
        text = ''
        for p in envvar.find_all('p'):
            text += p.text + '\n'

        ja_text = tl.translate(text, dest='ja').text
        # ja_text = '@@@'

        #""で囲まないとindert時にエラーが発生する為、対応実施
        env_name = '"' + env_name + '"'
        text = '"' + text + '"'
        ja_text = '"' + ja_text + '"'
        insert_data.append({key_op: env_name, key_des: text, key_ja_des: ja_text})
        print(env_name)
        # print(ja_text)

    #登録
    with closing(sqlite3.connect(DBNAME)) as con:
        cur = con.cursor()
        # insert_sql = 'insert into Ansible_Cfg (?,?,?) values (?,?,?)'
        insert_sql = 'insert into Ansible_Cfg ({0}) values ({1})'
        for dict in insert_data:
            try:
                # keys   = (key_op, key_des, key_ja_des)
                # values = (dict[key_op], dict[key_des], dict[key_ja_des])
                # value = keys + values
                keys = ', '.join([key_op, key_des, key_ja_des])
                values = ', '.join([dict[key_op], dict[key_des], dict[key_ja_des]])
                sql = insert_sql.format(keys, values)
                print(sql)

                cur.execute(sql)
                con.commit()
            except Exception as e:
                print(str(e.args), dict[key_op])
                with open('env_insert_err.log', 'w') as f:
                    f.write(dict[key_op] + '\n')

def translate_cfg():

    select_sql = 'select Option, Description from Ansible_Cfg'
    update_sql = '''
                update Ansible_Cfg 
                set trans_flg = 1, 
                    ja_description = ?
                where Option = ?
                '''


    with closing(sqlite3.connect(DBNAME)) as con:
        select_cur = con.cursor()

        for line in select_cur.execute(select_sql ):
            try:
                option = line[0]
                description = line[1]

                #翻訳
                tl = Translator()
                text = tl.translate(description, dest='ja').text
                print(option, text)

                #更新
                values = (text, option)
                update_cur = con.cursor()
                update_cur.execute(update_sql, values)
                con.commit()
            except Exception as e:
                print('エラー発生\n')
                print(option, str(e.args))


def create_table_ansible_cfg():
    with closing(sqlite3.connect(DBNAME)) as con:
        cur = con.cursor()

        #ansible.cfgテーブル作成
        create_ansible_cfg = '''
                        create table Ansible_Cfg(
                            Cfg_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            Option text,
                            Description text,
                            Type text,
                            Df text,
                            Version_Added text,
                            Ini_Section text,
                            Ini_Key text,
                            Environment text,
                            Deprecated_in text,
                            Deprecated_detail text,
                            Deprecated_alternatives,
                            UNIQUE(Option))
                        '''

        # カラム名追加
        add_sql = 'alter table Ansible_Cfg add column ja_description'
        #select
        select_sql = 'select Option, Description from Ansible_Cfg'
        #Drop_table
        sql = 'drop table Ansible_Cfg'
        cur.execute(add_sql)
            # print(line)
        con.commit()


def select_db():
    with closing(sqlite3.connect(DBNAME)) as con:
        cur = con.cursor()
        sql = 'select Deprecated_alternatives from Ansible_Cfg' #where Type is Null and Df is Null and Version_Added is Null'

        max_value = "a"
        for line in cur.execute(sql):
            # opetion = line[0]
            # print(opetion.replace('¶', ''))
            hoge = line[0]
            if hoge is None:
                continue
            if len(hoge) > len(max_value):
                max_value = hoge

        print(max_value)
        print(len(max_value))


def output_csv():
    sql = 'select Option,ja_description,Type,Df,Version_Added,Ini_Section,Ini_Key,\
                  Environment,Deprecated_in,Deprecated_detail,Deprecated_alternatives \
          from Ansible_Cfg'
    with closing(sqlite3.connect(DBNAME)) as con:
        cur = con.cursor()
        with open('ansible_cfg.csv', 'w') as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(['オプション','説明','タイプ','デフォルト','追加されたバージョン','Iniセクション',\
                             'Iniキー','環境','廃止予定','詳細廃止','代替廃止予定'])
            for line in cur.execute(sql):
                hoge_list = []
                for i, data in enumerate(line):
                    # print(data)
                    # if i == 1:
                    data2 = str(data).replace('\xa0', '').replace('\u2013', '').replace('\u200b', '')
                        # print(type(data))
                    hoge_list.append(data2)
                writer.writerow(hoge_list)

def qiita_table(kbn='common'):



    if kbn == 'common':
        table_hed = '|{0} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|{1} &nbsp;&nbsp;&nbsp; |{2} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |{3} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |{4} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |{5} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |{6} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |{7} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |{8} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |{9} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |{10} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |'
        table_fmt = '|{0}  |{1}  |{2}  |{3}  |{4}  |{5}  |{6}  |{7}  |{8}  |{9}  |{10}  |'
        table_dfine = '|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--|'
        sql = 'select Option,ja_description,Type,Df,Version_Added,Ini_Section,Ini_Key,\
                   Environment,Deprecated_in,Deprecated_detail,Deprecated_alternatives \
               from Ansible_Cfg \
               where Type is not null or  Df is not null or Version_Added is not null'
        table = table_hed.format('オプション', '説明', 'タイプ', 'デフォルト', '追加されたバージョン', 'Iniセクション', \
                        'Iniキー', '環境', '廃止予定', '詳細廃止', '代替廃止予定')

    elif kbn == 'env':
        table_hed = '|{0} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|{1}  |'
        table_fmt = '|{0}  |{1}  |'
        table_dfine = '|:--|:--|'
        # table_dfine = table_dfine.format('-'*50, '-'*550)
        sql = 'select Option, ja_description \
              from Ansible_Cfg \
              where Type is null and Df is null and Version_Added is null'
        table = table_hed.format('オプション', '説明')

    with closing(sqlite3.connect(DBNAME)) as con:
        cur = con.cursor()
        table += '\n' + table_dfine + '\n'
        row = ""
        for line in cur.execute(sql):
            hoge = []
            for data in line:
                if data is None:
                    data = 'None'
                print(type(data))
                if '\n' in data:
                    hoge.append(data.strip())
                    continue
                hoge.append(data)
            print(len(data))
            if kbn == 'common':
                table += table_fmt.format(hoge[0].replace('¶', ''), hoge[1], hoge[2], hoge[3], hoge[4]\
                                        , hoge[5], hoge[6], hoge[7], hoge[8], hoge[9], hoge[10]) + '\n'
            elif kbn == 'env':
                table += table_fmt.format(hoge[0], hoge[1].replace('\n', '\t')) + '\n'
        print(table)

if __name__ == '__main__':
    # scrape_ansible_cfg()
    # create_table_ansible_cfg()
    # translate_cfg()
    # output_csv()
    select_db()
    # insert_environment()
    qiita_table('common')