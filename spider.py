#!/usr/bin/env python3

import sqlite3, pyquery, time, requests, sys
from typing import List, Tuple

class WebpageSpider(object):
    def __init__(self, connection:sqlite3.Connection):
        self.__connection = connection
        self.__cursor = connection.cursor()
        self.__table_name = 'page'
        self.create_table(name=self.__table_name, fields=[
            'link text NOT NULL UNIQUE ON CONFLICT REPLACE',
            'html text NOT NULL'
        ])

    def create_table(self, name:str, fields:List[str]):
        create_command = '''
        CREATE TABLE {} ({})
        '''.format(name, ','.join(fields))
        result = self.__cursor.execute('SELECT name FROM sqlite_master WHERE type=\'table\' AND name=?', (name,))
        if not result.fetchall():
            self.__cursor.execute(create_command)

    def search_table(self, name: str, id: int) -> List[Tuple]:
        search_command = '''
        SELECT * FROM {} WHERE id=?
        '''.format(name)
        return self.__cursor.execute(search_command, (id,)).fetchall()

    def insert_table(self, name: str, data_rows: List[Tuple]):
        if not data_rows: return
        insert_command = '''
        INSERT INTO {} VALUES ({})
        '''.format(name, ','.join(['?'] * len(data_rows[0])))
        self.__cursor.executemany(insert_command, data_rows)

    def commit(self, close:bool = False):
        self.__connection.commit()
        if close: self.__connection.close()

    def fetch_html_document(self, url:str, headers = None, dont_cache:bool = False, sleep_time:float = 0.5)->pyquery.PyQuery:
        command = 'SELECT html FROM {} WHERE link=?'.format(self.__table_name)
        result = self.__cursor.execute(command, (url,))
        record = result.fetchone()
        if not record or dont_cache:
            time.sleep(sleep_time) # douban security restriction
            if not headers:
                headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.0 Safari/605.1.15'}
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                print(response.status_code, response.headers)
                print(response.text)
                self.commit()
                sys.exit(1)
            html_content = response.text
            self.insert_table(name=self.__table_name, data_rows=[
                (url, html_content)
            ])
        else:
            html_content = record[0]
        return pyquery.PyQuery(html_content)

if __name__ == '__main__':
    connection = sqlite3.connect('spider.sqlite')
    spider = WebpageSpider(connection)
    html = spider.fetch_html_document('https://movie.douban.com/review/9434975/')
    print(html.text())
    spider.commit(close=True)