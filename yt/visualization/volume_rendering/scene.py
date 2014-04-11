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
from camera import Camera
from render_source import VolumeSource, OpaqueSource
from yt.data_objects.api import ImageArray
from zbuffer_array import ZBuffer
from .utils import data_source_or_all
import numpy as np


class SceneHandle(object):
    """docstring for SceneHandle"""
    def __init__(self, scene, camera, source, lens):
        mylog.debug("Entering %s" % str(self))
        self.scene = scene
        self.camera = camera
        self.source = source
        self.lens = lens

    def __repr__(self):
        desc = super(SceneHandle, self).__repr__()
        desc += str(self)
        return desc

    def __str__(self):
        desc = "Scene Handler\n"
        desc += ".scene: " + self.scene.__repr__() + "\n"
        desc += ".camera: " + self.camera.__repr__() + "\n"
        desc += ".source: " + self.source.__repr__() + "\n"
        desc += ".lens: " + self.lens.__repr__() + "\n"
        return desc


class Scene(object):

    """Skeleton Class for 3D Scenes"""

    _current = None

    def __init__(self):
        mylog.debug("Entering %s" % str(self))
        super(Scene, self).__init__()
        self.sources = {}
        self.default_camera = None

    def get_source(self, source_num):
        return self.sources.values()[source_num]

    def iter_opaque_sources(self):
        """
        Iterate over opaque RenderSource objects,
        returning a tuple of (key, source)
        """
        for k, source in self.sources.iteritems():
            if isinstance(source, OpaqueSource):
                yield k, source

    def iter_transparent_sources(self):
        """
        Iterate over opaque RenderSource objects,
        returning a tuple of (key, source)
        """
        for k, source in self.sources.iteritems():
            if not isinstance(source, OpaqueSource):
                yield k, source

    def get_default_camera(self):
        """
        Use exisiting sources and their data sources to
        build a default camera. If no useful source is
        available, create a default Camera at 1,1,1 in the
        1,0,0 direction"""
        for k, source in self.sources.iteritems():
            cam = source.get_default_camera()
            if cam is not None:
                break
        if cam is None:
            cam = Camera()
        self.default_camera = cam
        return cam

    def add_source(self, render_source, keyname=None):
        """
        Add a render source to the scene.  This will autodetect the
        type of source.
        """
        if keyname is None:
            keyname = 'source_%02i' % len(self.sources)

        self.sources[keyname] = render_source

        return self

    def render(self, fname=None, clip_ratio=None, camera=None):
        if camera is None:
            camera = self.default_camera
        assert(camera is not None)
        self.validate()
        ims = {}
        for k, v in self.sources.iteritems():
            v.validate()
            print 'Running', k, v
            ims[k] = v.render(camera)

        bmp = np.zeros_like(ims.values()[0])
        for k, v in ims.iteritems():
            bmp += v
        bmp = ImageArray(bmp.d)
        assert(isinstance(bmp, ImageArray))

        if fname is not None:
            bmp.write_png(fname, clip_ratio=clip_ratio)
        return bmp

    def validate(self):
        for k, source in self.sources.iteritems():
            source.validate()
        return

    def composite(self):
        cam = self.default_camera
        opaque = ZBuffer(
            np.zeros([cam.resolution[0],
                     cam.resolution[1],
                     4]),
            np.ones(cam.resolution) * np.inf)

        for k, source in self.iter_opaque_sources():
            print "Adding opaque source:", source
            if source.zbuffer is not None:
                opaque = opaque + source.zbuffer

        for k, source in self.iter_transparent_sources():
            print "Adding transparent source:", source
            print opaque.z.min(), opaque.z.max()
            print opaque.rgba[:,:,:3].max()
            im = source.render(cam, zbuffer=opaque)
            #opaque = opaque + source.zbuffer
        return im

    def set_default_camera(self, camera):
        self.default_camera = camera

    def get_handle(self, key=None):
        """docstring for get_handle"""

        if key is None:
            key = self.sources.keys()[0]
        handle = SceneHandle(self, self.camera, self.sources[key],
                             self.sources[key].lens)
        return handle


def volume_render(data_source, field=None, fname=None):
    data_source = data_source_or_all(data_source)
    sc = Scene()
    if field is None:
        data_source.pf.index
        field = data_source.pf.field_list[0]
        mylog.info('Setting default field to %s' % field.__repr__())

    vol = VolumeSource(data_source, field=field)
    cam = Camera(data_source)
    sc.set_default_camera(cam)
    sc.add_source(vol)
    return sc.render(fname=fname), sc
