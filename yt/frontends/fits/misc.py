"""
FITS-specific miscellaneous functions
"""

#-----------------------------------------------------------------------------
# Copyright (c) 2013, yt Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import numpy as np
from yt.funcs import fix_axis, ensure_list, iterable
from yt.visualization.plot_window import AxisAlignedSlicePlot, \
    OffAxisSlicePlot, ProjectionPlot, OffAxisProjectionPlot

def force_aspect(ax,aspect=1):
    im = ax.get_images()
    extent = im[0].get_extent()
    ax.set_aspect(abs((extent[1]-extent[0])/(extent[3]-extent[2]))/aspect)

def convert_ticks(ticks, to_hours=False):
    deg_ticks = ticks.astype("int")
    min_ticks = ((ticks - deg_ticks)*60.).astype("int")
    sec_ticks = ((((ticks - deg_ticks)*60.)-min_ticks)*60.).astype("int")
    deg_string = "d"
    if to_hours:
        deg_ticks = (deg_ticks*24./360.).astype("int")
        deg_string = "h"
    return ["%02d%s%02dm%02ds" % (dt, deg_string, mt, st)
            for dt, mt, st in zip(deg_ticks, min_ticks, sec_ticks)]

def set_onaxis_wcs(pw):

    ax = pw.plots.values()[0].axes
    xpix = ax.get_xticks()
    ypix = ax.get_xticks()
    ra_ticks, dummy = pw.ds.wcs_2d.wcs_pix2world(xpix, ypix[0]*np.ones((len(xpix))), 1)
    dummy, dec_ticks = pw.ds.wcs_2d.wcs_pix2world(xpix[0]*np.ones((len(ypix))), ypix, 1)
    if pw.ds.dimensionality == 3:
        vlim = pw.ds.wcs_1d.wcs_pix2world([pw.xlim[0], pw.xlim[1]], 1)[0]

    if pw.axis == pw.ds.ra_axis:
        xname = "Dec"
        yname = pw.ds.vel_name
        xunit = str(pw.ds.wcs_2d.wcs.cunit[1])
        yunit = str(pw.ds.wcs_1d.wcs.cunit[0])
    elif pw.axis == pw.ds.dec_axis:
        xname = "RA"
        yname = pw.ds.vel_name
        xunit = str(pw.ds.wcs_2d.wcs.cunit[0])
        yunit = str(pw.ds.wcs_1d.wcs.cunit[0])
    elif pw.axis == pw.ds.vel_axis:
        xname = "RA"
        yname = "Dec"
        xunit = str(pw.ds.wcs_2d.wcs.cunit[0])
        yunit = str(pw.ds.wcs_2d.wcs.cunit[1])

    for k,v in pw.plots.iteritems():
        v.axes.set_xlabel(r"%s (%s)" % (xname, xunit))
        v.axes.set_ylabel(r"%s (%s)" % (yname, yunit))
        if xname == "Dec":
            v.axes.xaxis.set_ticklabels(convert_ticks(dec_ticks), size=14)
        if yname == "Dec":
            v.axes.yaxis.set_ticklabels(convert_ticks(dec_ticks), size=14)
        if xname == "RA":
            v.axes.xaxis.set_ticklabels(convert_ticks(ra_ticks, to_hours=True), size=14)
        if yname == pw.ds.vel_name:
            extent = (pw.xlim[0].value, pw.xlim[1].value, vlim[0], vlim[1])
            v.image.set_extent(extent)

class FITSSlicePlot(AxisAlignedSlicePlot):

    def __init__(self, ds, axis, fields, set_wcs=False, **kwargs):

        if isinstance(axis, basestring):
            if axis in ds.axis_names:
                axis = ds.axis_names[axis]
        self.axis = fix_axis(axis)
        self.ds = ds
        self.set_wcs = set_wcs
        super(FITSSlicePlot, self).__init__(ds, axis, fields, origin="native", **kwargs)
        self.set_axes_unit("pixel")

    def _set_wcs(self):
        if self.set_wcs:
            set_onaxis_wcs(self)

    def show(self):
        self._set_wcs()
        super(FITSSlicePlot, self).show()

    def save_wcs(self, *args, **kwargs):
        self._set_wcs()
        super(FITSSlicePlot, self).save(*args, **kwargs)

class FITSOffAxisSlicePlot(OffAxisSlicePlot):

    def __init__(self, ds, normal, fields, set_wcs=False, **kwargs):

        self.ds = ds
        self.set_wcs = set_wcs
        
        super(FITSOffAxisSlicePlot, self).__init__(ds, normal, fields, **kwargs)
        self.set_axes_unit("pixel")

class FITSProjectionPlot(ProjectionPlot):

    def __init__(self, ds, axis, fields, set_wcs=False, **kwargs):

        self.ds = ds
        if isinstance(axis, basestring):
            if axis in ds.axis_names:
                axis = ds.axis_names[axis]
        self.axis = fix_axis(axis)
        self.set_wcs = set_wcs

        super(FITSProjectionPlot, self).__init__(ds, axis, fields, origin="native", **kwargs)
        self.set_axes_unit("pixel")

    def _set_wcs(self):
        if self.set_wcs:
            set_onaxis_wcs(self)

    def show(self):
        self._set_wcs()
        super(FITSProjectionPlot, self).show()

    def save(self, *args, **kwargs):
        self._set_wcs()
        super(FITSProjectionPlot, self).save(*args, **kwargs)

class FITSOffAxisProjectionPlot(OffAxisProjectionPlot):

    def __init__(self, ds, normal, fields, set_wcs=False, **kwargs):

        self.ds = ds
        self.set_wcs = set_wcs
        super(FITSOffAxisProjectionPlot, self).__init__(ds, normal, fields, axes_unit="pixel", **kwargs)


