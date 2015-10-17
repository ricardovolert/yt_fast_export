"""
Volume rendering

"""

# ----------------------------------------------------------------------------
# Copyright (c) 2014, yt Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
# ----------------------------------------------------------------------------


from .scene import Scene
from .camera import Camera
from .render_source import VolumeSource
from .utils import data_source_or_all
from yt.funcs import mylog
from yt.utilities.exceptions import YTSceneFieldNotFound


def create_scene(data_source, field=None):
    r""" Set up a scene object with sensible defaults for use in volume 
    rendering.

    A helper function that creates a default camera view, transfer
    function, and image size. Using these, it returns an instance 
    of the Scene class, allowing one to further modify their rendering.

    This function is the same as volume_render() except it doesn't render
    the image.

    Parameters
    ----------
    data_source : :class:`yt.data_objects.data_containers.AMR3DData`
        This is the source to be rendered, which can be any arbitrary yt
        3D object
    field: string, tuple, optional
        The field to be rendered. If unspecified, this will use the 
        default_field for your dataset's frontend--usually ('gas', 'density').
        A default transfer function will be built that spans the range of 
        values for that given field, and the field will be logarithmically 
        scaled if the field_info object specifies as such.

    Returns
    -------
    sc: Scene
        A :class:`yt.visualization.volume_rendering.scene.Scene` object
        that was constructed during the rendering. Useful for further
        modifications, rotations, etc.

    Example:
    >>> import yt
    >>> ds = yt.load("Enzo_64/DD0046/DD0046")
    >>> sc = yt.create_scene(ds)
    """
    data_source = data_source_or_all(data_source)
    sc = Scene()
    if field is None:
        field = data_source.ds.default_field
        if field not in data_source.ds.derived_field_list:
            raise YTSceneFieldNotFound("""Could not find field '%s' in %s. 
                  Please specify a field in create_scene()""" % \
                  (field, data_source.ds))
        mylog.info('Setting default field to %s' % field.__repr__())

    vol = VolumeSource(data_source, field=field)
    sc.add_source(vol)
    sc.camera = Camera(data_source)
    return sc

def volume_render(data_source, field=None, fname=None, sigma_clip=None):
    r""" Create a simple volume rendering of a data source.

    A helper function that creates a default camera view, transfer
    function, and image size. Using these, it returns an image and
    an instance of the Scene class, allowing one to further modify
    their rendering.

    Parameters
    ----------
    data_source : :class:`yt.data_objects.data_containers.AMR3DData`
        This is the source to be rendered, which can be any arbitrary yt
        3D object
    field: string, tuple, optional
        The field to be rendered. If unspecified, this will use the 
        default_field for your dataset's frontend--usually ('gas', 'density').
        A default transfer function will be built that spans the range of 
        values for that given field, and the field will be logarithmically 
        scaled if the field_info object specifies as such.
    fname: string, optional
        If specified, the resulting rendering will be saved to this filename
        in png format.
    sigma_clip: float, optional
        If specified, the resulting image will be clipped before saving,
        using a threshold based on sigma_clip multiplied by the standard
        deviation of the pixel values. Recommended values are between 2 and 6.
        Default: None

    Returns
    -------
    im: ImageArray
        The resulting image, stored as an ImageArray object.
    sc: Scene
        A :class:`yt.visualization.volume_rendering.scene.Scene` object
        that was constructed during the rendering. Useful for further
        modifications, rotations, etc.

    Example:
    >>> import yt
    >>> ds = yt.load("Enzo_64/DD0046/DD0046")
    >>> im, sc = yt.volume_render(ds, fname='test.png', sigma_clip=4.0)
    """
    sc = create_scene(data_source, field=field)
    im = sc.render()
    sc.save(fname=fname, sigma_clip=sigma_clip)
    return im, sc
