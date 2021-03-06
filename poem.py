#!/usr/bin/env python3
import sqlite3, requests, time, re
from pyquery import PyQuery
from spider import WebpageSpider
from typing import Dict

class tables(object):
    song = 'song'
    poem = 'poem'

class commands(object):
    dump_poem = 'dump-poem'
    dump_song = 'dump-song'
    dump_disk = 'dump-disk'

    @classmethod
    def option_chocies(cls):
        choice_list = []
        for name, value in vars(cls).items():
            if name.replace('_', '-') == value: choice_list.append(value)
        return choice_list

def create_sqlite_tables():
    spider.create_table(name=tables.song, fields=[
        'title text NOT NULL UNIQUE ON CONFLICT REPLACE',
        'author text',
        'poem text NOT NULL',
        'note text',
        'review text'
    ])
    spider.create_table(name=tables.poem, fields=[
        'id text NOT NULL UNIQUE ON CONFLICT REPLACE',
        'title text NOT NULL',
        'author text NOT NULL',
        'poem text NOT NULL',
        'tags text'
    ])

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
    book = spider.fetch_html_document(url='https://www.gushiwen.org/guwen/shijing.aspx')
    book = PyQuery(book.html())
    for item in book.find('div.sons span a'):
        node = PyQuery(item)
        poem_url = node.attr('href')
        if not poem_url: continue
        print(poem_url)
        poem_html = spider.fetch_html_document(url=poem_url)
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
        spider.insert_table(name=tables.song, data_rows=[
            (title, author, poem_text, note_text, review_text)
        ])
        spider.commit()

def decode_params(url:str)->Dict[str, str]:
    result = {}
    for name, value in [tuple(x.split('=')) for x in url.split('?')[-1].split('&')]:
        result[name] = value
    return result

def dump_author_poems(url:str):
    if url.rfind('?') > 0:
        params = decode_params(url)
        uid = params['id']
        pid = params['page']
    else:
        data = url.split('/')[-1].split('_')[-1].split('.')[0]
        pattern = re.compile(r'A(\d+)$')
        uid = pattern.sub('', data)
        pid = pattern.search(data).group(1)

    html = spider.fetch_html_document(url=url)
    for item in html.find('div.main3 div.left div.sons'):
        node = PyQuery(item)
        content_node = node.find('div.cont')
        title = PyQuery(content_node.find('div.yizhu')[0]).next().text()
        author = PyQuery(content_node.find('p.source')[0]).text().replace('：','-')
        poem_text = PyQuery(content_node.find('div.contson')[0]).text()
        tags_node = node.find('div.tag')
        if tags_node:
            tags = PyQuery(tags_node[0]).text().replace(' ', '').replace('，', ';')
        else:
            tags = None
        id = node.find('div.yizhu img').attr('onclick').split('\'')[1]
        print(title, author, tags, id)
        spider.insert_table(name=tables.poem, data_rows=[
            (id, title, author, poem_text, tags, pid, uid)
        ])
    spider.commit()
    paginator = html.find('div.pagesright a.amore')
    if paginator and paginator.attr('href'):
        next_page_link = paginator.attr('href') # type: str
        if not next_page_link.startswith('http'):
            next_page_link = 'https://so.gushiwen.org' + next_page_link
        dump_author_poems(url=next_page_link)

def dump_poems():
    html = spider.fetch_html_document(url='https://so.gushiwen.org/authors/')
    for item in html.find('div.main3 div.right div.cont a'):
        node = PyQuery(item)
        author_url = node.attr('href') # type: str
        author_name = node.text()
        print(author_name, author_url)
        author_uid = author_url.split('_')[-1].split('.')[0]
        dump_author_poems(url='https://so.gushiwen.org/authors/authorvsw.aspx?page=1&id={}'.format(author_uid))
        spider.commit()

def dump_poems_to_disk():
    import os
    from pypinyin import lazy_pinyin as pinyin
    connection = sqlite3.connect('poem.sqlite')
    cursor = connection.cursor()
    output_path = 'poem'
    if not os.path.exists(output_path): os.mkdir(output_path)
    os.chdir(output_path)
    for author, uid in cursor.execute('SELECT DISTINCT author,uid FROM poem').fetchall():
        author = author.split('-')[-1]
        file_name = '{}.txt'.format('_'.join(pinyin(author)))
        fp = open(file_name, 'w+')
        for poem_text, in cursor.execute('SELECT poem FROM poem WHERE uid=?', (uid,)).fetchall():
            fp.write(poem_text)
            fp.write('\n\n')
        fp.close()
        print(author, os.path.abspath(file_name))

if __name__ == '__main__':
    import argparse, sys
    arguments = argparse.ArgumentParser()
    arguments.add_argument('--command', '-c', default=commands.dump_poem, choices=commands.option_chocies())
    arguments.add_argument('--dont-cache', '-d', action='store_true')
    arguments.add_argument('--sleep-time', '-t', default=0, type=float)
    options = ArgumentOptions(data=arguments.parse_args(sys.argv[1:]))
    global spider
    spider = WebpageSpider(connection=sqlite3.connect('b.sqlite'))
    create_sqlite_tables()
    if options.command == commands.dump_poem:
        dump_poems()
    elif options.command == commands.dump_song:
        dump_songs()
    elif options.command == commands.dump_disk:
        dump_poems_to_disk()
    spider.commit(True)
