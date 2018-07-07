#!/usr/bin/env python3
import io
from typing import Tuple, List

class SvgPath(object):
    def __init__(self):
        self.__data = io.StringIO()

    def clear(self):
        self.__data.truncate(0)

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

    def draw_catmull_rom_splines(self, points:List[Tuple[float, float]], interpolate_density:int = 10):
        points = points.copy()
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

if __name__ == '__main__':
    path = SvgPath()
    path.move_to(0, 0)
    path.line_to(-1, -1)
    path.line_xto(1)
    path.line_yto(1)
    path.cubic_curve_to(c1=(1,1), c2=(2,2), e=(3,3))
    path.append_cubic_curve_to(c=(4, 4), e=(5, 5))
    path.arc((10,15),(100,100))
    print(path)

    pts = []

    path.clear()
    path.move_to(0, 200)
    pts.append((0, 200))
    pts.append(pts[0])
    path.curve_to((50, 200),(100, 200))
    offset = (100, 200)
    pts.append(offset)
    import random
    for n in range(10):
        point = random.randint(10, 50) + offset[0], random.randint(-50, 50) + offset[1]
        pts.append(point)
        offset = point
        path.append_curve_to(point)
    print(path)
    pts.append(pts[-1])

    path.clear()
    path.move_to(0, 200)
    path.draw_catmull_rom_splines(pts, interpolate_density=20)
    print(path)
