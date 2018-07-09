#!/usr/bin/env python3
import argparse, sys, os, io, typing, time, pyquery, requests, math, random
from typing import Tuple, List, Dict
from functools import cmp_to_key
import svg
exclude_signs = '。，；：…（）《》？！、“”—[]【】°'
exclude_chars = '的了'

class commands(object):
    dump_hotword = 'dump-hotword'
    dump_graph = 'dump-graph'

    @classmethod
    def option_choices(cls):
        choice_list= []
        for name, value in vars(cls).items():
            if name.replace('_', '-') == value: choice_list.append(value)
        return choice_list

class ArgumentOptions(object):
    def __init__(self, data):
        self.command = data.command # type: str
        self.text_path = data.text_path # type: str
        self.webpage = data.webpage # type:bool
        self.max_num = data.max_num # type: int
        self.depth = data.depth # type: int
        self.debug = data.debug # type: bool
        self.char = data.char # str
        if self.char: self.char = self.char[0]
        self.hide_text = data.hide_text # type:bool
        self.svg_name = data.svg_name # type:str

class TreeNode(object):
    def __init__(self, data:str):
        self.children = []   # type: List[TreeNode]
        self.data = data     # type: str
        self.position = None # type: Tuple[float, float]
        self.rotation = None # type: float
        self.parent = None   # type: TreeNode

    def dump(self, padding:str = '', indent = '  '):
        length = len(self.children)
        for n in range(length):
            node = self.children[n]
            if n < length - 1:
                sep, tab = '│', '├'
            else:
                sep, tab = ' ', '└'
            tab = '{}─'.format(tab)
            print('{}{}{}'.format(padding, tab, node.data))
            node.dump(padding + sep + indent)

    def walk_tree_graph(self, position:Tuple[float, float] = (0, 0), rotation:float = 0):
        self.position = position
        self.rotation = rotation
        length = len(self.children)
        delta = min(2 * math.pi * 5 / 6 / max(2, length), math.pi/6)
        angle_offset, sign = 0, 1 if random.randint(0,1) == 1 else -1
        for n in range(length):
            node = self.children[n]
            jump_radius = 100 + min(20, len(node.children)) * 30
            angle = rotation + angle_offset * sign
            dx = jump_radius * math.cos(angle)
            dy = jump_radius * math.sin(angle)
            node.walk_tree_graph((position[0] + dx, position[1] + dy), angle)
            if n % 2 == 0: angle_offset += delta
            sign *= -1

    def draw_tree_graph(self, path:svg.SvgPath, chain:List[Tuple[float, float]] = None):
        if not chain: chain = [self.position]
        result = [] # type: List[TreeNode]
        length = len(self.children)
        for n in range(length):
            node = self.children[n]
            if not node.position: continue
            child_chain = chain.copy()
            child_chain.append(node.position)
            if len(child_chain) >= 2:
                result.append(node)
                path.catmull_rom_segment(child_chain, interpolate_density=30)
            if node.children:
                point_list = node.draw_tree_graph(path, chain=child_chain)
                result.extend(point_list)
        return result

class elapse_dubugger(object):
    def __init__(self):
        self.__time = time.clock()
        self.enabled = True

    def log(self, name:str):
        if not self.enabled: return
        print('{:7.3f}ms {}'.format(1000*(time.clock() - self.__time), name))
        self.__time = time.clock()

def char_scope_sort(a:str, b:str):
    for n in range(len(a)):
        if a[n] != b[n]: return 1 if a[n] > b[n] else -1
    return 0

def strip_char_map(char_map:Dict[str, List]):
    for char in exclude_chars:
        if char in char_map: del char_map[char]

def create_hotword_network(buffer:io.StringIO):
    char_map = {}
    while True:
        char = buffer.read(1) # type:str
        if not char: break
        if ord(char) <= 0x7F or char in exclude_signs: continue
        if char not in char_map: char_map[char] = [0, []]
        position = buffer.tell()
        scope = buffer.read(HOTWORD_SEARCH_DEPTH)
        buffer.seek(position)
        item = char_map[char]
        item[1].append(scope)
        item[0] += 1
    strip_char_map(char_map)
    root = TreeNode(options.char)
    # data_list = char_map.get(root.data)[1]
    # data_list.sort(key=cmp_to_key(char_scope_sort))
    # print('\n'.join(data_list))
    create_search_tree(char_map.get(root.data)[1], root)
    # root.dump()
    root.walk_tree_graph(position=(0, 0), rotation=0)
    graphics = svg.SvgGraphics()
    path = svg.SvgPath()
    node_list = root.draw_tree_graph(path)
    node_list.insert(0, root)
    graphics.new_group()
    graphics.draw_path(path).stroke(1, 'red').fill('none')
    rect, font_size = [0,0,0,0], 10
    for node in node_list:
        pt = node.position
        graphics.draw_circle(2, pt).fill('red')
        if not options.hide_text:
            graphics.draw_text(node.data, (-font_size / 2, font_size / 2 - 1)).font('Arial', font_size).move(*pt).fill('black')
        rect[0] = min(pt[0], rect[0])
        rect[1] = min(pt[1], rect[1])
        rect[2] = max(pt[0], rect[2])
        rect[3] = max(pt[1], rect[3])
    graphics.end_group()
    margin = 10
    rect[0] -= margin
    rect[1] -= margin
    rect[2] += margin * 2
    rect[3] += margin * 2
    rect[2] = rect[2] - rect[0]
    rect[3] = rect[3] - rect[1]
    graphics.set_view_box(*rect)
    svg_name = options.svg_name if options.svg_name else options.char
    with open('{}.svg'.format(svg_name), 'w+') as fp:
        fp.write(repr(graphics))
        fp.close()

def caculate_hotwords(buffer:io.StringIO):
    char_map = {}
    while True:
        char = buffer.read(1) # type:str
        if not char: break
        if ord(char) <= 0x7F or char in exclude_signs: continue
        if char not in char_map: char_map[char] = [0, []]
        position = buffer.tell()
        scope = buffer.read(HOTWORD_SEARCH_DEPTH)
        buffer.seek(position)
        item = char_map[char]
        item[1].append(scope)
        item[0] += 1
    strip_char_map(char_map)
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
        if not char or ord(char) <= 0x7F or char in exclude_signs:
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

def create_search_tree(data_list:typing.List[str], parent:TreeNode):
    concat_map = {}
    for r in range(len(data_list)):
        scope = data_list[r]
        if not scope:continue
        char = scope[0]
        if not char or ord(char) <= 0x7F or char in exclude_signs:continue
        if char not in concat_map: concat_map[char] = [0, []]
        concat_map[char][0] += 1
        concat_map[char][1].append(scope[1:])
    for char in concat_map.keys():
        num, data_list = concat_map.get(char)
        node = TreeNode(char)
        node.parent = parent
        parent.children.append(node)
        if len(data_list) <= 1: continue
        create_search_tree(data_list, node)

if __name__ == '__main__':
    arguments = argparse.ArgumentParser()
    arguments.add_argument('--command', '-c', default=commands.dump_hotword, choices=commands.option_choices())
    arguments.add_argument('--text-path', '-p', required=True)
    arguments.add_argument('--webpage', '-w', action='store_true')
    arguments.add_argument('--max-num', '-m', type=int, default=0)
    arguments.add_argument('--depth', '-d', type=int, default=10)
    arguments.add_argument('--debug', '-g', action='store_true')
    arguments.add_argument('--hide-text', '-t', action='store_true')
    arguments.add_argument('--char', '-r')
    arguments.add_argument('--svg-name', '-n')
    global debug, options
    options = ArgumentOptions(data=arguments.parse_args(sys.argv[1:]))
    text_path = options.text_path
    debug = elapse_dubugger()
    debug.enabled = options.debug

    global HOTWORD_SEARCH_DEPTH, MAX_RESULT_NUM
    HOTWORD_SEARCH_DEPTH = options.depth
    MAX_RESULT_NUM = options.max_num

    assert options.text_path
    buffer = None # type: io.StringIO
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
            buffer = io.StringIO(content.text())
        else:
            print(pyquery.PyQuery(response.text).find('body').text())
            sys.exit(1)
    else:
        assert os.path.exists(text_path)
        with open(text_path, 'r+') as fp:
            buffer = io.StringIO(fp.read())
            debug.log('read')

    if options.command == commands.dump_graph:
        assert options.char
        create_hotword_network(buffer)
    elif options.command == commands.dump_hotword:
        caculate_hotwords(buffer)
