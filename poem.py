#!/usr/bin/env python3
import sqlite3, commens, requests, time
from pyquery import PyQuery
from commens import fetch_html_document, insert_table
from typing import Tuple, List

class tables(object):
    song = 'song'
    poem = 'poem'

class commands(object):
    dump_poem = 'dump-poem'
    dump_song = 'dump-song'

    @classmethod
    def option_chocies(cls):
        choice_list = []
        for name, value in vars(cls).items():
            if name.replace('_', '-') == value: choice_list.append(value)
        return choice_list

def create_table(name:str, cursor:sqlite3.Cursor):
    schema = ''
    if name == tables.song:
        schema = '''
                CREATE TABLE {} 
                    (title text NOT NULL UNIQUE ON CONFLICT REPLACE, 
                     author text,
                     poem text NOT NULL,
                     note text,
                     review text)
                '''.format(name)
    elif name == tables.poem:
        schema = '''
                CREATE TABLE {} 
                    (title text NOT NULL UNIQUE ON CONFLICT REPLACE, 
                     author text,
                     poem text NOT NULL,
                     note text,
                     explain text,
                     review text,
                     tags text)
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
    def __init__(self, data):
        self.sleep_time = data.sleep_time
        self.dont_cache = data.dont_cache
        self.command = data.command

def get_request_headers(referer:str):
    return {
        'Referer': referer,
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.0 Safari/605.1.15'
    }

def dump_songs():
    book = fetch_html_document(cursor=cursor, url='https://www.gushiwen.org/guwen/shijing.aspx')
    book = PyQuery(book.html())
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
        headers = get_request_headers(referer=poem_url)
        response = requests.get('https://so.gushiwen.org/shiwen2017/ajaxfanyi.aspx?id=1', headers=headers)
        note_node = PyQuery(response.text).find('div.contyishang')
        note_node.find('a').remove()
        note_text = note_node.text()
        time.sleep(1)
        response = requests.get('https://so.gushiwen.org/shiwen2017/ajaxshangxi.aspx?id=4', headers=headers)
        review_node = PyQuery(response.text).find('div.contyishang')
        review_node.find('a').remove()
        review_text = review_node.text()
        print('{} {}\n{}'.format(title, author, poem_text))
        insert_table(cursor=cursor, name=tables.song, data_rows=[
            (title, author, poem_text, note_text, review_text)
        ])
        connection.commit()

def dump_author_poems(url:str):
    pattern = 'https://so.gushiwen.org/shiwen2017/ajaxshiwencont.aspx?id={}&value={}';
    html = fetch_html_document(cursor=cursor, url=url)
    for item in html.find('div.main3 div.left div.sons'):
        node = PyQuery(item)
        content_node = node.find('div.cont')
        title = content_node.find('div.yizhu').next().text()
        author = content_node.find('p.source').text().replace('：','-')
        poem_text = content_node.find('div.contson').text()
        tags = node.find('div.tag').text().replace(' ', '').replace('，', ';')
        id = node.find('div.yizhu img').attr('onclick').split('\'')[1]
        print(title, author, tags, id)
        headers = get_request_headers(url)
        try:
            note_text = fetch_html_document(cursor=cursor, url=pattern.format(id, 'zhu'), headers=headers).text()
        except RuntimeError:
            note_text = None
        try:
            explain_text = fetch_html_document(cursor=cursor, url=pattern.format(id, 'yi'), headers=headers).text()
        except RuntimeError:
            explain_text = None
        try:
            review_text = fetch_html_document(cursor=cursor, url=pattern.format(id, 'shang'), headers=headers).text()
        except RuntimeError:
            review_text = None
        insert_table(cursor=cursor, name=tables.poem, data_rows=[
            (title, author, poem_text, note_text, explain_text, review_text, tags)
        ])
    connection.commit()
    paginator = html.find('div.pagesright a.amore')
    if paginator and paginator.attr('href'):
        next_page_link = paginator.attr('href') # type: str
        if not next_page_link.startswith('http'):
            next_page_link = 'https://so.gushiwen.org' + next_page_link
        dump_author_poems(url=next_page_link)

def dump_poems():
    html = fetch_html_document(cursor=cursor, url='https://so.gushiwen.org/authors/')
    for item in html.find('div.main3 div.right div.cont a'):
        node = PyQuery(item)
        author_url = node.attr('href') # type: str
        author_name = node.text()
        print(author_name, author_url)
        author_uid = author_url.split('_')[-1].split('.')[0]
        dump_author_poems(url='https://so.gushiwen.org/authors/authorvsw.aspx?page=1&id={}'.format(author_uid))
        connection.commit()
        break

if __name__ == '__main__':
    import argparse, sys
    arguments = argparse.ArgumentParser()
    arguments.add_argument('--command', '-c', default=commands.dump_poem, choices=commands.option_chocies())
    arguments.add_argument('--dont-cache', '-d', action='store_true')
    arguments.add_argument('--sleep-time', '-t', default=0.5)
    options = commens.options = ArgumentOptions(data=arguments.parse_args(sys.argv[1:]))
    global connection, cursor
    connection = sqlite3.connect('poem.sqlite')
    cursor = connection.cursor()
    if options.command == commands.dump_poem:
        dump_poems()
    elif options.command == commands.dump_song:
        dump_songs()
    connection.commit()
    connection.close()
