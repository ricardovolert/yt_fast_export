"""
Miscellaneous FITS routines
"""

#-----------------------------------------------------------------------------
# Copyright (c) 2013, yt Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import numpy as np
from yt.fields.api import add_field
from yt.fields.derived_field import ValidateSpatial
from yt.funcs import mylog, get_image_suffix
from yt.visualization._mpl_imports import FigureCanvasAgg
import os

def _make_counts(emin, emax):
    def _counts(field, data):
        e = data["event_energy"].in_units("keV")
        mask = np.logical_and(e >= emin, e < emax)
        x = data["event_x"][mask]
        y = data["event_y"][mask]
        z = np.ones(x.shape)
        pos = np.array([x,y,z]).transpose()
        img = data.deposit(pos, method="count")
        return data.pf.arr(img, "counts/pixel")
    return _counts

def setup_counts_fields(ebounds):
    for (emin, emax) in ebounds:
        cfunc = _make_counts(emin, emax)
        fname = "counts_%s-%s" % (emin, emax)
        mylog.info("Creating counts field %s." % fname)
        add_field(("gas",fname), function=cfunc,
                  units="counts/pixel",
                  validators = [ValidateSpatial()],
                  display_name="Counts (%s-%s keV)" % (emin, emax))

def ds9_region(ds, reg, obj=None):
    import pyregion
    r = pyregion.open(reg)
    reg_name = reg.split(".")[0]
    nx = ds.domain_dimensions[ds.lon_axis]
    ny = ds.domain_dimensions[ds.lat_axis]
    mask = r.get_mask(header=ds.wcs_2d.to_header(),
                      shape=[nx,ny])
    def _reg_field(field, data):
        i = data["x"].ndarray_view().astype("int")-1
        j = data["y"].ndarray_view().astype("int")-1
        new_mask = mask[i,j]
        ret = data["zeros"].copy()
        ret[new_mask] = 1.
        return ret
    ds.index
    ds.field_info.add_field(("gas",reg_name), function=_reg_field)
    if obj is None:
        obj = ds.all_data()
    return obj.cut_region(["obj['%s'] > 0" % (reg_name)])

class PlotWindowWCS(object):
    r"""
    Use the wcsaxes library to plot celestial coordinates on the axes.
    See http://wcsaxes.readthedocs.org for details.

    Parameters
    ----------
    pw : on-axis PlotWindow instance
        The PlotWindow instance to add celestial axes to.
    """
    def __init__(self, pw):
        from wcsaxes import WCSAxes
        if pw.oblique:
            raise NotImplementedError("WCS axes are not implemented for oblique plots.")
        if not hasattr(pw.pf, "wcs_2d"):
            raise NotImplementedError("WCS axes are not implemented for this dataset.")
        if pw.data_source.axis != pw.pf.vel_axis:
            raise NotImplementedError("WCS axes are not implemented for this axis.")
        self.pf = pw.pf
        self.pw = pw
        self.plots = {}
        self.wcs_axes = []
        for f in pw.plots:
            rect = pw.plots[f]._get_best_layout()[1]
            fig = pw.plots[f].figure
            ax = WCSAxes(fig, rect, wcs=pw.pf.wcs_2d, frameon=False)
            fig.add_axes(ax)
            self.wcs_axes.append(ax)
        self._setup_plots()

    def _setup_plots(self):
        pw = self.pw
        for f, ax in zip(pw.plots, self.wcs_axes):
            wcs = ax.wcs.wcs
            pw.plots[f].axes.get_xaxis().set_visible(False)
            pw.plots[f].axes.get_yaxis().set_visible(False)
            xax = pw.pf.coordinates.x_axis[pw.data_source.axis]
            yax = pw.pf.coordinates.y_axis[pw.data_source.axis]
            xlabel = "%s (%s)" % (wcs.ctype[xax].split("-")[0],
                                  wcs.cunit[xax])
            ylabel = "%s (%s)" % (wcs.ctype[yax].split("-")[0],
                                  wcs.cunit[yax])
            fp = pw._font_properties
            ax.coords[0].set_axislabel(xlabel, fontproperties=fp)
            ax.coords[1].set_axislabel(ylabel, fontproperties=fp)
            ax.set_xlim(pw.xlim[0].value, pw.xlim[1].value)
            ax.set_ylim(pw.ylim[0].value, pw.ylim[1].value)
            ax.coords[0].ticklabels.set_fontproperties(fp)
            ax.coords[1].ticklabels.set_fontproperties(fp)
            self.plots[f] = pw.plots[f]
        self.pw = pw
        self.pf = self.pw.pf

    def refresh(self):
        self._setup_plots(self)

    def keys(self):
        return self.plots.keys()

    def values(self):
        return self.plots.values()

    def items(self):
        return self.plots.items()

    def __getitem__(self, key):
        for k in self.keys():
            if k[1] == key:
                return self.plots[k]

    def show(self):
        from IPython.core.display import display
        for k, v in sorted(self.plots.iteritems()):
            canvas = FigureCanvasAgg(v.figure)
            display(v.figure)

    def save(self, name=None, mpl_kwargs=None):
        if mpl_kwargs is None:
            mpl_kwargs = {}
        mpl_kwargs["bbox_inches"] = "tight"
        self.pw.save(name=name, mpl_kwargs=mpl_kwargs)
