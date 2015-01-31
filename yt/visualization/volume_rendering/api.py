"""
API for yt.visualization.volume_rendering



"""

#-----------------------------------------------------------------------------
# Copyright (c) 2013, yt Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from .transfer_functions import TransferFunction, ColorTransferFunction, \
                             PlanckTransferFunction, \
                             MultiVariateTransferFunction, \
                             ProjectionTransferFunction
from .image_handling import export_rgba, import_rgba, \
                           plot_channel, plot_rgb

# Need to re-implement (Stereo)SphericalCamera
#from .camera import Camera, PerspectiveCamera, StereoPairCamera, \
#    off_axis_projection, FisheyeCamera, MosaicFisheyeCamera, \
#    HEALpixCamera, InteractiveCamera, ProjectionCamera, \
#    SphericalCamera, StereoSphericalCamera
from .camera import Camera
from .transfer_function_helper import TransferFunctionHelper
from .volume_rendering import volume_render
from .off_axis_projection import off_axis_projection
from .scene import Scene
from .render_source import VolumeSource, OpaqueSource, LineSource, BoxSource
from .zbuffer_array import ZBuffer
