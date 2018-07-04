#!/usr/bin/env python3
import argparse, sys, os, io, typing, time, pyquery, requests
from typing import Tuple, List
from functools import cmp_to_key
excludes = tuple('。，；：…（）《》？！、“”—[]【】°的个')

class elapse_dubugger(object):
    def __init__(self):
        self.__time = time.clock()
        self.enabled = True

    def log(self, name:str):
        if not self.enabled: return
        print('{:7.3f}ms {}'.format(1000*(time.clock() - self.__time), name))
        self.__time = time.clock()

def caculate_hotwords(buffer:io.StringIO):
    char_map = {}
    while True:
        char = buffer.read(1) # type:str
        if not char: break
        if ord(char) <= 0x7F or char in excludes: continue
        if char not in char_map: char_map[char] = [0, []]
        position = buffer.tell()
        scope = buffer.read(HOTWORD_SEARCH_DEPTH)
        buffer.seek(position)
        item = char_map[char]
        item[1].append(scope)
        item[0] += 1
    debug.log('char')
    char_list = list(char_map.keys())
    temp_list = []
    for char in char_list:
        if char_map[char][0] > 2: temp_list.append(char)
    char_list = temp_list
    def char_rank_sort(a, b):
        return -1 if char_map[a][0] > char_map[b][0] else 1
    char_list.sort(key=cmp_to_key(char_rank_sort))
    debug.log('char-sort')
    strip_map = {}
    for char in char_list:
        item = char_map[char]
        data_list = item[1] # type: list[str]
        result = iterate_search(data_list, char)
        for word in result:
            if word not in strip_map: strip_map[word] = 0
            strip_map[word] += 1
    word_list = []
    debug.log('search-hotword')
    for word in strip_map.keys():
        num = strip_map[word]
        if num == 1: continue
        word_list.append((word, num))
    debug.log('strip-none')
    word_list = strip_redundants(data_list=word_list)
    debug.log('strip-redundants')
    def hotword_rank_sort(a:Tuple[str, int], b:Tuple[str, int]):
        if a[1] != b[1]: return 1 if a[1] > b[1] else -1
        if len(a[0]) != len(b[0]): return 1 if len(a[0]) > len(b[0]) else -1
        return 1 if a[0] > b[0] else -1
    word_list.sort(key=cmp_to_key(hotword_rank_sort))
    debug.log('sort')
    length = len(word_list)
    output_limit = MAX_RESULT_NUM if MAX_RESULT_NUM > 0 else length
    offset = length - output_limit
    for n in range(offset, length):
        word, num = word_list[n]
        print(word, num)
        if n + 1 - offset >= output_limit: break

def strip_redundants(data_list:List[Tuple[str, int]]):
    temp_list = [] # type: list[tuple[str, str, int]]
    for item in data_list:
        temp_list.append((item[0][-1:-3:-1], item[0], item[1]))
    def reverse_rank_sort(a, b):
        if a[0] != b[0]: return 1 if a[0] > b[0] else -1
        if a[-1] != b[-1]: return -1 if a[-1] > b[-1] else 1
        return -1 if len(a[1]) > len(b[1]) else 1
    temp_list.sort(key=cmp_to_key(reverse_rank_sort))
    result, keytag, depth = [], None, 0
    for n in range(len(temp_list)):
        tag, word, num = temp_list[n]
        if keytag != tag: keytag, depth = tag, 0
        depth += 1
        redundant = False
        for r in range(0, min(depth, len(result))):
            hotword, _ = result[r] # type: str
            if hotword.endswith(word):
                redundant = True
                break
        if not redundant:
            result.insert(0, (word, num))
    return result

def iterate_search(data_list:typing.List[str], hotword:str):
    concat_map = {}
    hotword_list = []
    for r in range(len(data_list)):
        scope = data_list[r]
        if not scope:
            if len(hotword) >= 2: hotword_list.append(hotword)
            continue
        char = scope[0]
        if not char or ord(char) <= 0x7F or char in excludes:
            if len(hotword) >= 2: hotword_list.append(hotword)
            continue
        if char not in concat_map: concat_map[char] = [0, []]
        concat_map[char][0] += 1
        concat_map[char][1].append(scope[1:])
    for char in concat_map.keys():
        num, data_list = concat_map.get(char)
        if num == 1 and len(hotword) > 1:
            hotword_list.append(hotword)
            continue
        hotword_list += iterate_search(data_list, hotword + char)
    return hotword_list

if __name__ == '__main__':
    arguments = argparse.ArgumentParser()
    arguments.add_argument('--text-path', '-p', required=True)
    arguments.add_argument('--webpage', '-w', action='store_true')
    arguments.add_argument('--max-num', '-m', type=int, default=0)
    arguments.add_argument('--depth', '-d', type=int, default=10)
    arguments.add_argument('--debug', '-g', action='store_true')
    options = arguments.parse_args(sys.argv[1:])
    text_path = options.text_path
    global debug
    debug = elapse_dubugger()
    debug.enabled = options.debug

    global HOTWORD_SEARCH_DEPTH, MAX_RESULT_NUM
    HOTWORD_SEARCH_DEPTH = options.depth
    MAX_RESULT_NUM = options.max_num

    if options.webpage:
        response = requests.get(url=text_path)
        if response.status_code == 200:
            html = pyquery.PyQuery(response.text)
            douban_article_content = html.find('div.article div.main')
            if douban_article_content:
                content = douban_article_content
            else:
                content = html.find('body')
            content.find('script').remove()
            content.find('style').remove()
            debug.log('load')
            caculate_hotwords(buffer=io.StringIO(content.text()))
        else:
            print(pyquery.PyQuery(response.text).find('body').text())
    else:
        assert os.path.exists(text_path)
        with open(text_path, 'r+') as fp:
            data = io.StringIO(fp.read())
            debug.log('read')
            caculate_hotwords(buffer=data)
