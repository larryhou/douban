#!/usr/bin/env python3
import sqlite3, commens, requests, time
from pyquery import PyQuery
from commens import fetch_html_document, insert_table
from typing import Tuple, List

class tables(object):
    poem = 'poem'

def create_table(name:str, cursor:sqlite3.Cursor):
    schema = ''
    if name == tables.poem:
        schema = '''
                CREATE TABLE {} 
                    (title text NOT NULL UNIQUE ON CONFLICT REPLACE, 
                     author text,
                     poem text NOT NULL,
                     note text,
                     review text)
                '''.format(name)
    result = cursor.execute('SELECT name FROM sqlite_master WHERE type=\'table\' AND name=?', (name,))
    if not result.fetchall() and schema:
        cursor.execute(schema)

def insert_table(cursor:sqlite3.Cursor, name:str, data_rows:List[Tuple]):
    create_table(name=name, cursor=cursor)
    if not data_rows: return
    schema = '''
    INSERT INTO {} VALUES ({})
    '''.format(name, ','.join(['?'] * len(data_rows[0])))
    cursor.executemany(schema, data_rows)

class ArgumentOptions(object):
    def __init__(self):
        self.sleep_time = 0.1
        self.dont_cache = False

if __name__ == '__main__':
    global connection
    connection = sqlite3.connect('poem.sqlite')
    cursor = connection.cursor()
    commens.options = ArgumentOptions()
    book = fetch_html_document(cursor=cursor, url='https://www.gushiwen.org/guwen/shijing.aspx')
    book = PyQuery(book.html())
    record_list = []
    for item in book.find('div.sons span a'):
        node = PyQuery(item)
        poem_url = node.attr('href')
        if not poem_url: continue
        print(poem_url)
        poem_html = fetch_html_document(cursor=cursor, url=poem_url)
        content = poem_html.find('div.main3 div.sons div.cont')
        title = content.find('h1').text()
        author = PyQuery(content.find('p.source')[0]).text()
        poem_text = content.find('div.contson').text()
        headers = {
            'Referer':poem_url,
            'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.0 Safari/605.1.15'
        }
        response = requests.get('https://so.gushiwen.org/shiwen2017/ajaxfanyi.aspx?id=1', headers = headers)
        note_node = PyQuery(response.text).find('div.contyishang')
        note_node.find('a').remove()
        note_text = note_node.text()
        time.sleep(1)
        response = requests.get('https://so.gushiwen.org/shiwen2017/ajaxshangxi.aspx?id=4', headers=headers)
        review_node = PyQuery(response.text).find('div.contyishang')
        review_node.find('a').remove()
        review_text = review_node.text()
        print('{} {}\n{}'.format(title, author, poem_text))
        insert_table(cursor=cursor, name=tables.poem, data_rows=[
            (title, author, poem_text, note_text, review_text)
        ])
        connection.commit()
    connection.commit()
    connection.close()
