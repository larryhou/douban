#!/usr/bin/env python3

import sqlite3, pyquery, time, requests
from typing import List, Tuple

database_name = 'douban.sqlite'

class commands(object):
    dump_review = 'dump-review'
    dump_subject = 'dump-subject'

    @classmethod
    def option_chocies(cls):
        choice_list = []
        for name, value in vars(cls).items():
            if name.replace('_', '-') == value: choice_list.append(value)
        return choice_list

class tables(object):
    user = 'user'
    review = 'review'
    subject = 'subject'
    comment = 'comment'
    page = 'page'

class ArgumentOptions(object):
    def __init__(self, data):
        self.command = data.command # type:str
        self.douban_url = data.douban_url # type:str
        self.max_count = data.max_count # type: int
        self.count = 0 # type: int

def get_database_connection()->sqlite3.Connection:
    return sqlite3.connect(database_name)

def create_table(name:str, cursor:sqlite3.Cursor):
    schema = ''
    if name == tables.comment:
        schema = '''
                CREATE TABLE {} 
                    (id text NOT NULL UNIQUE ON CONFLICT REPLACE, 
                     text text NOT NULL, 
                     date integer NOT NULL,
                     author_uid text NOT NULL,
                     author_name text NOT NULL,
                     review_aid text NOT NULL,
                     reply_cid text,
                     reply_author_uid text,
                     reply_author_name text)
                '''.format(name)
    elif name == tables.user:
        schema = '''
                CREATE TABLE {} 
                    (id text NOT NULL UNIQUE ON CONFLICT REPLACE, 
                     name text NOT NULL, 
                     state text,
                     link text NOT NULL,
                     avatar text NOT NULL)
                '''.format(name)
    elif name == tables.subject:
        schema = '''
                CREATE TABLE {} 
                    (id text NOT NULL UNIQUE ON CONFLICT IGNORE, 
                     name text NOT NULL, 
                     link text NOT NULL)
                '''.format(name)
    elif name == tables.review:
        schema = '''
                CREATE TABLE {} 
                    (id text NOT NULL UNIQUE ON CONFLICT REPLACE, 
                     title text NOT NULL, 
                     link text NOT NULL,
                     date integer NOT NULL,
                     author_uid text NOT NULL,
                     author_name text NOT NULL,
                     author_link text NOT NULL,
                     subject_name text NOT NULL,
                     subject_rate double NOT NULL,
                     subject_link text NOT NULL)
                '''.format(name)
    elif name == tables.page:
        schema = '''
                CREATE TABLE {} 
                    (link text NOT NULL UNIQUE ON CONFLICT IGNORE,
                     html text NOT NULL)
                '''.format(name)
    result = cursor.execute('SELECT name FROM sqlite_master WHERE type=\'table\' AND name=?', (name,))
    if not result.fetchall() and schema:
        cursor.execute(schema)

def search_table(cursor:sqlite3.Cursor, name:str, id:int)->List[Tuple]:
    search_command = '''
    SELECT * FROM {} WHERE id=?
    '''.format(name)
    return cursor.execute(search_command, (id,)).fetchall()

def insert_table(cursor:sqlite3.Cursor, name:str, data_rows:List[Tuple]):
    create_table(name=name, cursor=cursor)
    if not data_rows: return
    schema = '''
    INSERT INTO {} VALUES ({})
    '''.format(name, ','.join(['?'] * len(data_rows[0])))
    cursor.executemany(schema, data_rows)

def fetch_html_document(cursor:sqlite3.Cursor, url:str)->pyquery.PyQuery:
    result = cursor.execute('SELECT html FROM ? WHERE url=?', (tables.page, url))
    record = result.fetchone()
    if not record:
        time.sleep(2) # douban security restriction
        response = requests.get(url)
        html_content = response.text
        insert_table(cursor=cursor, name=tables.page, data_rows=[
            (url, html_content)
        ])
        if url.split('?')[0].endswith('reviews'):
            options.count += 1
            if options.count > options.max_count: sys.exit()
    else:
        html_content = record[0]
    return pyquery.PyQuery(html_content)

def decode_date(value:str)->int:
    return int(time.mktime(time.strptime(value, '%Y-%m-%d %H:%M:%S')))

def crawl_review_comments(url:str):
    print('>>> {}'.format(url))
    cursor = connection.cursor()
    review_url = url.split('?')[0]
    review_aid = review_url.split('/')[-2]
    html = fetch_html_document(cursor=cursor, url=url)
    review_title = html.find('div.article h1 span').text()
    pointer = html.find('header.main-hd').children('a span')
    review_author = pointer.text()
    pointer = pointer.parent()
    review_author_url = pointer.attr('href') # type: str
    print(review_author_url)
    review_author_uid = review_author_url.split('/')[-2]
    pointer = pointer.next()
    review_subject = pointer.text()
    review_subject_url = pointer.attr('href') # type: str
    review_subject_sid = review_subject_url.split('/')[-2]
    pointer = pointer.next()
    if pointer.parent().find('.main-title-rating'):
        pointer = pointer.next()
        review_subject_pts = pointer.text()
        review_subject_pts = float(review_subject_pts) if review_subject_pts else 0
        pointer = pointer.next()
    else:
        review_subject_pts = -1
    review_time = decode_date(value=pointer.text())
    insert_table(name=tables.subject, cursor=cursor, data_rows=[
        (review_subject_sid, review_subject, review_subject_url)
    ])
    insert_table(name=tables.review, cursor=cursor, data_rows=[
        (review_aid, review_title, review_url, review_time,
         review_author_uid,review_author,review_author_url,
         review_subject,review_subject_pts,review_subject_url)
    ])
    comment_list, user_list = [], []
    for item in html.find('.comment-item'):
        node = pyquery.PyQuery(item)
        comment_cid = node.attr('data-cid')
        comment_text = node.find('.comment-text').text()
        reply_cid = node.attr('data-ref_cid').strip()
        if not reply_cid or reply_cid == '0': reply_cid = None
        reply_author_uid, reply_author = None, None
        if reply_cid:
            reply_node = node.find('span.pubdate a')
            reply_author_url = reply_node.attr('href') # type: str
            reply_author_uid = reply_author_url.split('/')[-2]
            reply_author = reply_node.text()
        review_aid = node.attr('data-target_id')
        comment_author_avatar = node.find('div.avatar img').attr('src')
        header_node = node.find('div.header')
        comment_author_url = node.attr('data-user_url')
        comment_author_uid = comment_author_url.split('/')[-2]
        comment_author = header_node.find('a').text()
        comment_author_state = header_node.contents()[2].strip()
        if not comment_author_state: comment_author_state = None
        comment_time_value = header_node.find('span').text()
        comment_time = decode_date(value=comment_time_value)
        comment_record = (comment_cid, comment_text, comment_time,
                comment_author_uid, comment_author,
                review_aid,
                reply_cid, reply_author_uid, reply_author)
        comment_list.append(comment_record)
        user_record = (comment_author_uid, comment_author, comment_author_state, comment_author_url, comment_author_avatar)
        user_list.append(user_record)
        print('[{}]{!s} {!r}'.format(comment_time_value, comment_author, comment_text))
    insert_table(name=tables.comment, cursor=cursor, data_rows=comment_list)
    insert_table(name=tables.user, cursor=cursor, data_rows=user_list)
    connection.commit()
    paginator = html.find('div.paginator span.next a')
    if paginator:
        next_page_url = url.split('?')[0] + paginator.attr('href')
        crawl_review_comments(url=next_page_url)

def crawl_subject_comments(url:str):
    cursor = connection.cursor()
    html = fetch_html_document(cursor=cursor, url=url)
    for review in html.find('div.review-list div.review-item'):
        node = pyquery.PyQuery(review)
        review_url = node.find('.main-bd h2 a').attr('href')
        crawl_review_comments(url=review_url)
    paginator = html.find('div.paginator span.next a')
    if paginator:
        next_page_url = url.split('?')[0] + paginator.attr('href')
        crawl_subject_comments(url=next_page_url)

if __name__ == '__main__':
    global connection
    connection = get_database_connection()
    import argparse, sys
    arguments = argparse.ArgumentParser()
    arguments.add_argument('--command', '-c', default=commands.dump_review)
    arguments.add_argument('--douban-url', '-u', required=True)
    arguments.add_argument('--max-count', '-m', type=int, default=5)
    global options
    options = ArgumentOptions(data=arguments.parse_args(sys.argv[1:]))
    douban_url = options.douban_url  # type: str
    douban_url = douban_url.split('?')[0]
    if options.command == commands.dump_review:
        crawl_review_comments(url=douban_url)
    elif options.command == commands.dump_subject:
        if not douban_url.endswith('reviews'):
            douban_url = '{}reviews'.format(douban_url)
        crawl_subject_comments(url=douban_url)
    connection.commit()
    connection.close()