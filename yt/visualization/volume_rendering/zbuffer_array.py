"""


"""

#-----------------------------------------------------------------------------
# Copyright (c) 2013, yt Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from yt.funcs import mylog
from yt.data_objects.api import ImageArray
import numpy as np


class ZBuffer(object):
    """docstring for ZBuffer"""
    def __init__(self, rgba, z):
        super(ZBuffer, self).__init__()
        assert(rgba.shape[:len(z.shape)] == z.shape)
        self.rgba = rgba
        self.z = z
        self.shape = z.shape

    def __add__(self, other):
        assert(self.shape == other.shape)
        f = self.z < other.z
        use_self = np.dstack((f, f, f, f))
        b = self.z > other.z
        use_other = np.dstack((b, b, b, b))
        if self.z.shape[1] == 1:
            # Non-rectangular
            rgba = (self.rgba * f[:,None,:])
            rgba += (other.rgba * (1.0 - f)[:,None,:])
        else:
            rgba = self.rgba*use_self + other.rgba*use_other
        z = np.min([self.z, other.z], axis=0)
        return ZBuffer(rgba, z)

    def __eq__(self, other):
        equal = True
        equal *= np.all(self.rgba == other.rgba)
        equal *= np.all(self.z == other.z)
        return equal

    def paint(self, ind, value, z):
        if z < self.z[ind]:
            self.rgba[ind] = value
            self.z[ind] = z

if __name__ == "__main__":
    shape = (64, 64)
    for shape in [(64, 64), (16, 16, 4), (128), (16, 32)]:
        b1 = ZBuffer(np.random.random(shape), np.ones(shape))
        b2 = ZBuffer(np.random.random(shape), np.zeros(shape))
        c = b1 + b2
        assert(np.all(c.rgba == b2.rgba))
        assert(np.all(c.z == b2.z))
        assert(np.all(c == b2))
