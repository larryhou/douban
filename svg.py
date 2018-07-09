#!/usr/bin/env python3
import io, enum
from typing import Tuple, List
from lxml import etree

class SvgPath(object):
    def __init__(self):
        self.__data = io.StringIO()

    def clear(self):
        self.__data = io.StringIO()

    def move_to(self, x:float, y:float, absolute:bool = True):
        self.__data.write('{} {} {} '.format('M' if absolute else 'm', x, y))

    def line_to(self, x:float, y:float, absolute:bool = True):
        self.__data.write('{} {} {} '.format('L' if absolute else 'l', x, y))

    def line_xto(self, x:float, absolute:bool = True):
        self.__data.write('{} {} '.format('H' if absolute else 'h', x))

    def line_yto(self, y:float, absolute:bool = True):
        self.__data.write('{} {} '.format('V' if absolute else 'v', y))

    '''
    Draws a cubic Bézier curve from the current point to (x,y) using (x1,y1) as the control point at the beginning of the curve and (x2,y2) as the control point at the end of the curve. C (uppercase) indicates that absolute coordinates will follow; c (lowercase) indicates that relative coordinates will follow. Multiple sets of coordinates may be specified to draw a polybézier. At the end of the command, the new current point becomes the final (x,y) coordinate pair used in the polybézier.
    '''
    def cubic_curve_to(self, c1:Tuple[float, float], c2:Tuple[float, float], e:Tuple[float, float], absolute:bool = True):
        self.__data.write('{} {},{} {},{} {},{} '.format('C' if absolute else 'c',
                                                         c1[0], c1[1], c2[0], c2[1], e[0], e[1]))

    '''
    Draws a cubic Bézier curve from the current point to (x,y). The first control point is assumed to be the reflection of the second control point on the previous command relative to the current point. (If there is no previous command or if the previous command was not an C, c, S or s, assume the first control point is coincident with the current point.) (x2,y2) is the second control point (i.e., the control point at the end of the curve). S (uppercase) indicates that absolute coordinates will follow; s (lowercase) indicates that relative coordinates will follow. Multiple sets of coordinates may be specified to draw a polybézier. At the end of the command, the new current point becomes the final (x,y) coordinate pair used in the polybézier.
    '''
    def append_cubic_curve_to(self, c:Tuple[float, float], e:Tuple[float, float], absolute:bool = True):
        self.__data.write('{} {},{} {},{} '.format('S' if absolute else 's',
                                                   c[0], c[1], e[0], e[1]))

    '''
    Draws a quadratic Bézier curve from the current point to (x,y) using (x1,y1) as the control point. Q (uppercase) indicates that absolute coordinates will follow; q (lowercase) indicates that relative coordinates will follow. Multiple sets of coordinates may be specified to draw a polybézier. At the end of the command, the new current point becomes the final (x,y) coordinate pair used in the polybézier.
    '''
    def curve_to(self, c:Tuple[float, float], e:Tuple[float, float], absolute:bool = True):
        self.__data.write('{} {},{} {},{} '.format('Q' if absolute else 'q',
                                                   c[0], c[1], e[0], e[1]))

    '''
    Draws a quadratic Bézier curve from the current point to (x,y). The control point is assumed to be the reflection of the control point on the previous command relative to the current point. (If there is no previous command or if the previous command was not a Q, q, T or t, assume the control point is coincident with the current point.) T (uppercase) indicates that absolute coordinates will follow; t (lowercase) indicates that relative coordinates will follow. At the end of the command, the new current point becomes the final (x,y) coordinate pair used in the polybézier.
    '''
    def append_curve_to(self, e:Tuple[float, float], absolute:bool = True):
        self.__data.write('{} {},{} '.format('T' if absolute else 't', e[0], e[1]))

    '''
    Draws an elliptical arc from the current point to (x, y). The size and orientation of the ellipse are defined by two radii (rx, ry) and an x-axis-rotation, which indicates how the ellipse as a whole is rotated relative to the current coordinate system. The center (cx, cy) of the ellipse is calculated automatically to satisfy the constraints imposed by the other parameters. large-arc-flag and sweep- flag contribute to the automatic calculations and help determine how the arc is drawn.
    '''
    def arc(self, radius:Tuple[float, float], e:Tuple[float, float], axis_rotation:float = 0, large_arc:bool = True, clockwise:bool = True, absolute:bool = True):
        self.__data.write('{} {},{} {} {},{} {},{} '.format('A' if absolute else 'a',
                                                            radius[0], radius[1], axis_rotation, int(large_arc), int(clockwise), e[0], e[1]))

    '''
    Close the current subpath by drawing a straight line from the current point to current subpath's initial point.
    '''
    def close_path(self):
        self.__data.write('z')

    def catmull_rom_segment(self, points:List[Tuple[float, float]], interpolate_density:int = 10):
        points = points.copy()
        if len(points) == 2: points.insert(0, points[0])
        if len(points) <= 1: return
        self.move_to(*points[-2])
        points.append(points[-1])
        control_points = points[-4:]
        for i in range(interpolate_density + 1):
            position = interpolate_with_catmull_rom(*control_points, t=i / interpolate_density)
            self.line_to(*position)

    def catmull_rom(self, points:List[Tuple[float, float]], interpolate_density:int = 10):
        points = points.copy()
        self.move_to(*points[0])
        points.insert(0, points[0])
        points.append(points[-1])
        for m in range(1, len(points) - 2):
            control_points = points[m - 1], points[m], points[m + 1], points[m + 2]
            for i in range(interpolate_density + 1):
                position = interpolate_with_catmull_rom(*control_points, t=i / interpolate_density)
                self.line_to(*position)

    def __repr__(self):
        position = self.__data.tell()
        self.__data.seek(0)
        data = self.__data.read()
        self.__data.seek(position)
        return data

# @see http://www.mvps.org/directx/articles/catmull/
def interpolate_with_catmull_rom(p0:Tuple[float, float], p1:Tuple[float, float], p2:Tuple[float, float], p3:Tuple[float, float], t:float):
    t1 = t
    t2 = t1 * t
    t3 = t2 * t
    c0 = 0 - t1 + 2 * t2 -     t3
    c1 = 2      - 5 * t2 + 3 * t3
    c2 = 0 + t1 + 4 * t2 - 3 * t3
    c3 = 0      -     t2 +     t3
    return (0.5 * (c0 * p0[0] + c1 * p1[0] + c2 * p2[0] + c3 * p3[0]),
            0.5 * (c0 * p0[1] + c1 * p1[1] + c2 * p2[1] + c3 * p3[1]))

class spread_methods(object):
    # spreadMethod = "pad | reflect | repeat"
    repeat = 'repeat'
    reflect = 'reflect'
    pad = 'pad'

class transforms(object):
    translate = 'translate'
    matrix = 'matrix'
    rotate = 'rotate'
    scale = 'scale'
    skewX = 'skewX'
    skewY = 'skewY'

class SvgElement(object):
    def __init__(self, element:etree._Element):
        self.__element = element

    @property
    def id(self)->str:
        return self.__element.get('id')

    def stroke(self, thickness:float, color:str):
        self.__element.set('stroke', color)
        self.__element.set('stroke-width', repr(thickness))
        return self

    def stroke_gradient(self, thickness:float, gradient_ref:str):
        self.__element.set('stroke', 'url(#{})'.format(gradient_ref))
        self.__element.set('stroke-width', repr(thickness))
        return self

    def fill(self, color:str, alpha:float = 1.0):
        self.__element.set('fill', color)
        if alpha != 1: self.__element.set('opacity', repr(alpha))
        return self

    def fill_gradient(self, gradient_ref:str):
        self.__element.set('fill', 'url(#{})'.format(gradient_ref))
        return self

    def move(self, x:float, y:float):
        self.__element.set('x', repr(x))
        self.__element.set('y', repr(y))
        return self

    def size(self, width:float, height:float):
        self.__element.set('width', repr(width))
        self.__element.set('height', repr(height))
        return self

    def font(self, font:str, size:float, rotate:float = 0):
        if font: self.__element.set('font-family', font)
        self.__element.set('font-size', repr(size))
        if rotate != 0: self.__element.set('rotate', repr(rotate))
        return self

    def css(self, style:str):
        self.__element.set('style', style)
        return self

    def __get(self, name:str):
        value = self.__element.get(name)
        if value is None:
            value = ''
            self.__element.set(name, value)
        return value

    def __set_transform(self, name:str, *params:float):
        transform = self.__get('transform')
        data_map = {}
        closed, action_name, action_params = True, '', []
        for char in transform:
            if closed:
                if char == '(':
                    closed = False
                    action_params = []
                    item = ''
                    continue
                action_name += char
            else:
                if char == ')':
                    closed = True
                    action_name = action_name.strip()
                    data_map[action_name] = action_params
                    action_name = ''
                if char not in ' ,)':
                    item += char
                else:
                    if not item: continue
                    action_params.append(float(item))
                    item = ''
        action_params = data_map.get(name)
        if name in (transforms.scale, transforms.translate):
            if action_params:
                if len(params) == 1 and len(action_params) == 2:
                    params = (params[0] + action_params[0], action_params[1])
                else:
                    params = (params[0] + action_params[0], action_params[1] + params[1])
        elif name == transforms.rotate:
            if action_params:
                if len(params) == 1 and len(action_params) == 3:
                    params = (params[0] + action_params[0], action_params[1], action_params[2])
                else:
                    params = (params[0] + action_params[0],)
        data_map[name] = params
        transform = ''
        for name, params in data_map.items():
            value = ''
            params = [repr(x) for x in params]
            if name in (transforms.translate,
                        transforms.matrix,
                        transforms.scale):
                value = ','.join(params)
            elif name in (transforms.skewX, transforms.skewY):
                value = params[0]
            elif name == transforms.rotate:
                if len(params) == 1:
                    value = '{}'.format(params[0])
                else:
                    value = '{} {},{}'.format(*params)
            if not transform:
                transform = '{}({})'.format(name, value)
            else:
                transform = '{} {}({})'.format(transform, name, value)
        # print(transform)
        self.__element.set('transform', transform)

    def matrix(self, a:float, b:float, c:float, d:float, e:float, f:float):
        self.__set_transform('matrix', a, b, c, d, e, f)
        return self

    def scale(self, x:float, y:float):
        self.__set_transform('scale', x, y)
        return self

    def translate(self, x:float, y:float):
        self.__set_transform('translate', x, y)
        return self

    def rotate(self, angle:float, anchor:Tuple[float, float] = None):
        if anchor is None:
            self.__set_transform('rotate', angle)
        else:
            self.__set_transform('rotate', angle, *anchor)
        return self

    def skewX(self, angle:float):
        self.__set_transform('skewX', angle)
        return self

    def skewY(self, angle:float):
        self.__set_transform('skewY', angle)
        return self

class SvgGraphics(object):
    def __init__(self):
        self.__context = etree.fromstring('''
        <svg version="1.1" 
             xmlns:xlink="http://www.w3.org/1999/xlink"><defs/></svg>
        ''') # type: etree._Element
        self.__defs = self.__context.xpath('//defs')[0] # type: etree._Element
        self.__ref_counter = 1
        self.__groups = [] # type: List[etree._Element]
        self.__mask = None  # type: etree._Element

    def __create_ref(self, name:str):
        element_ref = '{}-{:03d}'.format(name, self.__ref_counter)
        self.__ref_counter += 1
        return element_ref

    def __append_element(self, element, visible:bool):
        node = self.__context
        if self.__mask is not None:
            node = self.__mask
        elif len(self.__groups) > 0:
            node = self.__groups[-1]
        node.append(element) if visible else self.__defs.append(element)

    def set_view_box(self, x:float, y:float, width:float, height:float):
        self.__context.set('viewBox', '{} {} {} {}'.format(x, y, width, height))

    def set_size(self, width:float, height:float):
        self.__context.set('width', repr(width))
        self.__context.set('height', repr(height))

    def create_linear_gradient(self, pt1:Tuple[float, float], pt2:Tuple[float, float], stops:List[Tuple[float, str, float]], spread_method:str = spread_methods.repeat):
        style_ref = self.__create_ref('linear-gradient')
        gradient = etree.fromstring('<linearGradient id="{}" gradientUnits="userSpaceOnUse" x1="{}" y1="{}" x2="{}" y2="{}" spreadMethod="{}"/>'.format(style_ref, *pt1, *pt2, spread_method)) # type: etree._Element
        for position, color, alpha in stops:
            gradient.append('<stop offset="{}" stop-color="{}" stop-opacity="{}"/>'.format(position, color, alpha))
        self.__defs.append(gradient)
        return style_ref

    def create_radial_gradient(self, radius:float, center:Tuple[float, float], focal:Tuple[float, float], stops:List[Tuple[float, str, float]], spread_method:str = spread_methods.repeat):
        style_ref = self.__create_ref('radial-gradient')
        gradient = etree.fromstring('<linearGradient id="{}" gradientUnits="userSpaceOnUse" r="{}" cx="{}" cy="{}" fx="{}" fy="{}" spreadMethod="{}"/>'.format(style_ref, radius, *center, *focal, spread_method))  # type: etree._Element
        for position, color, alpha in stops:
            gradient.append('<stop offset="{}" stop-color="{}" stop-opacity="{}"/>'.format(position, color, alpha))
        self.__defs.append(gradient)
        return style_ref

    def new_group(self):
        group_ref = self.__create_ref('group')
        group = etree.fromstring('<g id="{}"/>'.format(group_ref))
        if len(self.__groups) > 0:
            self.__groups[-1].append(group)
        else:
            self.__context.append(group)
        self.__groups.append(group)
        return SvgElement(group)

    def end_group(self, exhaustive:bool = False):
        if len(self.__groups) > 0:
            if exhaustive:
                self.__groups.clear()
            else:
                del self.__groups[-1]

    def new_clip_path(self):
        if self.__mask is not None: return
        self.__mask = etree.fromstring('<clipPath id="{}"/>') # type: etree._Element
        self.__defs.append(self.__mask)

    def end_clip_path(self):
        self.__mask = None

    def draw_path(self, path:SvgPath, visible:bool = True)->SvgElement:
        element = etree.fromstring('<path id="{}" d="{}"/>'.format(self.__create_ref('path'), path))
        self.__append_element(element, visible)
        return SvgElement(element)

    def draw_rect(self, width:float, heigth:float, visible:bool = True)->SvgElement:
        element = etree.fromstring('<rect id="{}" width="{}" height="{}"/>'.format(self.__create_ref('rect'), width, heigth))
        self.__append_element(element, visible)
        return SvgElement(element)

    def draw_circle(self, radius:float, center:Tuple[float, float], visible:bool = True):
        element = etree.fromstring(
            '<circle id="{}" r="{}" cx="{}" cy="{}"/>'.format(self.__create_ref('circle'), radius, *center))
        self.__append_element(element, visible)
        return SvgElement(element)

    def draw_ellipse(self, radius:Tuple[float, float], center:Tuple[float, float], visible:bool = True):
        element = etree.fromstring(
            '<ellipse id="{}" rx="{}" ry="{}" cx="{}" cy="{}"/>'.format(self.__create_ref('ellipse'), *radius, *center))
        self.__append_element(element, visible)
        return SvgElement(element)

    def draw_line(self, pt1:Tuple[float, float], pt2:Tuple[float, float], visible:bool = True):
        element = etree.fromstring(
            '<line id="{}" x1="{}" y1="{}" x2="{}" y2="{}"/>'.format(self.__create_ref('line'), *pt1, *pt2))
        self.__append_element(element, visible)
        return SvgElement(element)

    def draw_polygon(self, vertex:List[Tuple[float, float]], visible:bool = True):
        element = etree.fromstring(
            '<polygon id="{}" points="{}"/>'.format(self.__create_ref('polygon'), ' '.join(['{},{}'.format(*x) for x in vertex])))
        self.__append_element(element, visible)
        return SvgElement(element)

    def draw_text(self, text:str, offset:Tuple[float, float] = None, visible:bool = True):
        if not offset:
            element = etree.fromstring('<text id="{}">{}</text>'.format(self.__create_ref('text'), text))
        else:
            element = etree.fromstring('<text id="{}" dx="{}" dy="{}">{}</text>'.format(self.__create_ref('text'), *offset, text))
        self.__append_element(element, visible)
        return SvgElement(element)

    def draw_polyline(self, points:List[Tuple[float, float]], visible:bool = True):
        element = etree.fromstring(
            '<polyline id="{}" points="{}"/>'.format(self.__create_ref('polyline'),
                                                    ' '.join(['{},{}'.format(*x) for x in points])))
        self.__append_element(element, visible)
        return SvgElement(element)

    def __repr__(self):
        svg_bytes = etree.tostring(self.__context, pretty_print=True, encoding='utf-8') # type: bytes
        return svg_bytes.decode('utf-8').replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"')

if __name__ == '__main__':
    # path = SvgPath()
    # pts = []
    # path.clear()
    # path.move_to(0, 200)
    # pts.append((0, 200))
    # pts.append(pts[0])
    # path.curve_to((50, 200),(100, 200))
    # offset = (100, 200)
    # pts.append(offset)
    # import random
    # for n in range(10):
    #     point = random.randint(10, 50) + offset[0], random.randint(-50, 50) + offset[1]
    #     pts.append(point)
    #     offset = point
    #     path.append_curve_to(point)
    # print(path)
    # pts.append(pts[-1])
    #
    # path.clear()
    # path.move_to(0, 200)
    # path.catmull_rom(pts, interpolate_density=20)
    # print(path)
    graphics = SvgGraphics()
    graphics.draw_rect(10, 100).stroke(1.5, 'red')\
        .rotate(30, (5, 50))\
        .translate(-15, 35)\
        .scale(1.2, 1.2)\
        .fill('green')\
        .rotate(20)\
        .translate(100,100).skewX(10).skewY(10).matrix(1,2,3,4,5,6)
    graphics.new_group()
    graphics.draw_circle(100, (0,0))
    graphics.new_group()
    graphics.draw_ellipse((10,20), (40, 50))
    print(graphics.__repr__())
