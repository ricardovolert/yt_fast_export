"""
All of the base-level stuff for plotting.

Author: Matthew Turk <matthewturk@gmail.com>
Affiliation: KIPAC/SLAC/Stanford
Homepage: http://yt.enzotools.org/
License:
  Copyright (C) 2007-2009 Matthew Turk.  All Rights Reserved.

  This file is part of yt.

  yt is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from yt.raven import *

# No better place to put this
def concatenate_pdfs(output_fn, input_fns):
    from pyPdf import PdfFileWriter, PdfFileReader
    outfile = PdfFileWriter()
    for fn in input_fns:
        infile = PdfFileReader(open(fn, 'rb'))
        outfile.addPage(infile.getPage(0))
    outfile.write(open(output_fn, "wb"))

class PlotCollection(object):
    __id_counter = 0
    def __init__(self, pf, center=None):
        r"""The primary interface for creating plots.

        The PlotCollection object was created to ease the creation of multiple
        slices, projections and so forth made from a single parameter file.
        The concept is that when the width on one image changes, it should
        change on all the others.  The PlotCollection can create all plot types
        available in yt.

        Parameters
        ----------
        pf : `StaticOutput`
            The parameter file from which all the plots will be created.
        center : array_like, optional
            The 'center' supplied to plots like sphere plots, slices, and so
            on.  Should be 3 elements.  Defaults to the point of maximum
            density.
        Long_variable_name : {'hi', 'ho'}, optional
            Choices in brackets, default first when optional.

        Notes
        -----
        This class is the primary entry point to creating plots, but it is not
        the only entry point.  Additionally, creating a PlotCollection should
        be a "cheap" operation.

        You may iterate over the plots in the PlotCollection, via something
        like:

        >>> pc = PlotCollection(pf)
        >>> for p in pc: print p

        Examples
        --------

        >>> pc = PlotCollection(pf, center=[0.5, 0.5, 0.5])
        >>> pc.add_slice("Density", 0)
        >>> pc.save()

        """
        PlotTypes.Initialize()
        self.plots = []
        self.pf = pf
        if center == None:
            v,self.c = pf.h.find_max("Density") # @todo: ensure no caching
        elif center == "center" or center == "c":
            self.c = (pf["DomainRightEdge"] + pf["DomainLeftEdge"])/2.0
        else:
            self.c = na.array(center, dtype='float64')
        mylog.info("Created plot collection with default plot-center = %s",
                    list(self.c))

    def __iter__(self):
        for p in self.plots:
            yield p

    def save(self, basename=None, format="png", override=False, force_save=False):
        r"""Save out all the plots hanging off this plot collection, using
        generated names.

        This function will create names for every plot that belongs to the
        PlotCollection and save them out.  The names will, by default, be
        prefixed with the name of the affiliate parameter file, and the file
        names should indicate clearly what each plot represents.

        Parameters
        ----------
        basename : string, optional
            The prefix for all of the plot filenames.
        format : string, optional
            The plot file format.  Can be 'png', 'pdf', 'eps', 'jpg', or
            anything else that matplotlib understands.
        override : boolean
            If this is true, then no generated filenames will be appended to
            the base name.  You probably don't want this.
        force_save : boolean
            In parallel, only the root task (proc 0) saves an image, unless
            this is set to True.

        Returns
        -------
        items : string
            This function returns a list of the filenames created.

        Examples
        --------

        >>> fns = pc.save()
        >>> for fn in fns: print "Saved", fn
        """
        if basename is None: basename = str(self.pf)
        fn = []
        for plot in self.plots:
            fn.append(plot.save_image(basename, format=format, 
                      override=override, force_save=force_save))
            mylog.info("Saved %s", fn[-1])
        return fn

    def set_xlim(self, xmin, xmax):
        r"""Set the x-limits of all plots.

        set_xlim on all plots is called with the parameters passed to this
        function.

        Parameters
        ----------
        xmin : float
            The left boundary for the x axis.
        xmax : float
            The right boundary for the x axis.
        """
        for plot in self.plots:
            plot.set_xlim(xmin, xmax)

    def set_ylim(self, ymin, ymax):
        r"""Set the y-limits of all plots.

        set_ylim on all plots is called with the parameters passed to this
        function.

        Parameters
        ----------
        ymin : float
            The left boundary for the x axis.
        ymax : float
            The right boundary for the x axis.
        """
        for plot in self.plots:
            plot.set_ylim(ymin, ymax)

    def set_zlim(self, zmin, zmax, *args, **kwargs):
        """
        Set the limits of the colorbar. 'min' or 'max' are possible inputs 
        when combined with dex=value, where value gives the maximum number of 
        dex to go above/below the min/max.  If value is larger than the true
        range of values, min/max are limited to true range.

        Only ONE of the following options can be specified. If all 3 are
        specified, they will be used in the following precedence order:
            ticks - a list of floating point numbers at which to put ticks
            minmaxtick - display DEFAULT ticks with min & max also displayed
            nticks - if ticks not specified, can automatically determine a
               number of ticks to be evenly spaced in log space
        """
        for plot in self.plots:
            plot.set_autoscale(False)
            plot.set_zlim(zmin, zmax, *args, **kwargs)

    def set_lim(self, lim):
        r"""Set the x- and y-limits of all plots.

        set_xlim on all plots is called with the parameters passed to this
        function, and then set_ylim is called.

        Parameters
        ----------
        lim : tuple of floats
            (xmin, xmax, ymin, ymax)
        """
        for plot in self.plots:
            plot.set_xlim(*lim[:2])
            plot.set_ylim(*lim[2:])

    def autoscale(self):
        r"""Turn on autoscaling on all plots.

        This has the same effect as:

        >>> for p in pc: p.set_autoscale(True)

        By default, all plots are autoscaled until the colorbar is set
        manually.  This turns autoscaling back on.  The colors may not be
        updated unless _redraw_image is called on the plots, which should occur
        with a change in the width or saving of images.
        """
        for plot in self.plots:
            plot.set_autoscale(True)

    def set_width(self, width, unit):
        r"""Change the width of all image plots.

        This function changes all the widths of the image plots (but notably
        not any phase plots or profile plots) to be a given physical extent.

        Parameters
        ----------
        width : float
            The numeric value of the new width.
        unit : string
            The unit in which the given width is expressed.
        """
        for plot in self.plots:
            plot.set_width(width, unit)

    def set_cmap(self, cmap):
        r"""Change the colormap of all plots.

        This function will update the colormap on all plots for which a
        colormap makes sense.  The colors may not be updated unless
        _redraw_image is called on the plots, which should occur with a change
        in the width or saving of images.

        Parameters
        ----------
        cmap : string
            An acceptable colormap.  See either raven.color_maps or
            http://www.scipy.org/Cookbook/Matplotlib/Show_colormaps .
        """
        for plot in self.plots:
            plot.set_cmap(cmap)

    def switch_field(self, field):
        r"""Change the displayed of all image plots.

        All images that display a field -- slices, cutting planes, projections
        -- will be switched to display the specified field.  For projections,
        this will re-generate the projection, if it is unable to load the
        projected field off-disk.

        Parameters
        ----------
        field : string
            Any field that can be generated or read from disk.
        """
        for plot in self.plots:
            plot.switch_z(field)
    switch_z = switch_field

    def _add_plot(self, plot):
        r"""This function adds a plot to the plot collection.

        This function is typically used internally to add a plot on to the
        current list of plots.  However, if you choose to manually create a
        plot, this can be used to add it to a collection for convenient
        modification.

        Parameters
        ----------
        plot : `yt.raven.RavenPlot`
            A plot, which will be appended to the list of plots handled by this
            plot collection.

        Returns
        -------
        plot : `yt.raven.RavenPlot`
            The plot handed to the function is passed back through.  This is
            unnecessary, but is done for historical reasons.
        """
        self.plots.append(plot)
        return plot

    def add_slice(self, field, axis, coord=None, center=None,
                 use_colorbar=True, figure = None, axes = None, fig_size=None,
                 periodic = True, obj = None, field_parameters = None):
        r"""Create a slice, from that a slice plot, and add it to the current
        collection.

        This function will generate a `yt.lagos.AMRSliceBase` from the given
        parameters.  This slice then gets passed to a `yt.raven.SlicePlot`, and
        the resultant plot is added to the current collection.  Various
        parameters allow control of the way the slice is displayed, as well as
        how the slice is generated.

        Parameters
        ----------
        field : string
            The initial field to slice and display.
        axis : int
            The axis along which to slice.  Can be 0, 1, or 2 for x, y, z.
        coord : float, optional
            The coordinate to place the slice at, along the slicing axis.
        center : array_like, optional
            The center to be used for things like radius and radial velocity.
            Defaults to the center of the plot collection.
        use_colorbar : bool, optional
            Whether we should leave room for and create a colorbar.
        figure : `matplotlib.figure.Figure`, optional
            The figure onto which the axes will be placed.  Typically not used
            unless *axes* is also specified.
        axes : `matplotlib.axes.Axes`, optional
            The axes object which will be used to create the image plot.
            Typically used for things like multiplots and the like.
        fig_size : tuple of floats
            This parameter can act as a proxy for the manual creation of a
            figure.  By specifying it, you can create plots with an arbitrarily
            large or small size.  It is in inches, defaulting to 100 dpi.
        periodic : boolean, optional
            By default, the slices are assumed to be periodic, and they will
            wrap around the edges.
        obj : `yt.lagos.AMRSliceBase`, optional
            If you would like to use an existing slice, you may specify it
            here, in which case a new slice will not be created.
        field_parameters : dict, optional
            This set of parameters will be passed to the slice upon creation,
            which can be used for passing variables to derived fields.

        Returns
        -------
        plot : `yt.raven.SlicePlot`
            The plot that has been added to the PlotCollection.

        See Also
        --------
        yt.lagos.AMRSliceBase : This is the type created by this function and 
                                passed to the plot created here.

        Notes
        -----
        This is the primary mechanism for creating slice plots, and generating
        slice plots along multiple axes was the original purpose of the
        PlotCollection.

        Note that all plots can be modified.  See `callback_list` for more
        information.

        Examples
        --------

        >>> pf = load("RD0005-mine/RedshiftOutput0005")
        >>> pc = PlotCollection(pf, [0.5, 0.5, 0.5])
        >>> p = pc.add_slice("Density", 0)
        """
        if center == None:
            center = self.c
        if coord == None:
            coord = center[axis]
        if obj is None:
            if field_parameters == None: field_parameters = {}
            obj = self.pf.hierarchy.slice(axis, coord, field,
                            center=center, **field_parameters)
        p = self._add_plot(PlotTypes.SlicePlot(
                         obj, field, use_colorbar=use_colorbar,
                         axes=axes, figure=figure,
                         size=fig_size, periodic=periodic))
        mylog.info("Added slice of %s at %s = %s with 'center' = %s", field,
                    axis_names[axis], coord, list(center))
        p["Axis"] = lagos.axis_names[axis]
        return p

    def add_particles(self, axis, width, p_size=1.0, col='k', stride=1.0,
                      data_source=None, figure=None, axes=None):
        r"""Create a plot of a thick slab of particles.

        This function will generate a `yt.lagos.AMRRegionBase` from the given
        parameters, and all particles which are within that region will be
        plotted.

        Parameters
        ----------
        axis : int
            The axis along which to create the thick slab.  Can be 0, 1, or 2
            for x, y, z.
        width : float
            The width of the thick slab, in code units, from which particles
            will be plotted.
        p_size : float, optional
            The size of the points to be used to represent the particles, in
            pixels.
        col : color, optional
            Specified in matplotlib color specifications, the color that
            particles should be.
        stride : float, optional
            The stride through the particles to plot.  Used to plot every
            fifth, every tenth, etc.  Note that the sorted order of particles
            may result in a biased selection of particles.
        data_source : `yt.lagos.AMRData`, optional
            If specified, this will be the data source used for obtaining
            particles.
        figure : `matplotlib.figure.Figure`, optional
            The figure onto which the axes will be placed.  Typically not used
            unless *axes* is also specified.
        axes : `matplotlib.axes.Axes`, optional
            The axes object which will be used to create the image plot.
            Typically used for things like multiplots and the like.

        Returns
        -------
        plot : `yt.raven.ParticlePlot`
            The plot that has been added to the PlotCollection.

        Notes
        -----
        This plot type can be very expensive, and does not necessarily produce
        the best visual results.  Plotting a large number of particles can be
        very tricky, and often it's much better to instead use a slice or a
        (thin) projection of deposited density, like particle_density_pyx.

        Examples
        --------

        >>> pf = load("RD0005-mine/RedshiftOutput0005")
        >>> pc = PlotCollection(pf, [0.5, 0.5, 0.5])
        >>> p = pc.add_particles(0, 1.0)
        """
        LE = self.pf["DomainLeftEdge"].copy()
        RE = self.pf["DomainRightEdge"].copy()
        LE[axis] = self.c[axis] - width/2.0
        RE[axis] = self.c[axis] + width/2.0
        if data_source is None: data_source = self.pf.h.region(self.c, LE, RE)
        data_source.axis = axis
        p = self._add_plot(PlotTypes.ParticlePlot(data_source, axis,
                                        width, p_size, col, stride, figure,
                                        axes))
        p["Axis"] = lagos.axis_names[axis]
        return p

    def add_cutting_plane(self, field, normal,
                          center=None, use_colorbar=True,
                          figure = None, axes = None, fig_size=None, obj=None,
                           field_parameters = None):
        r"""Create a cutting plane, from that a plot, and add it to the current
        collection.

        A cutting plane is an oblique slice through the simulation volume,
        oriented by a specified normal vector that is perpendicular to the
        image plane.  This function will generate a
        `yt.lagos.AMRCuttingPlaneBase` from the given parameters.  This cutting
        plane then gets passed to a `yt.raven.CuttingPlanePlot`, and the
        resultant plot is added to the current collection.  Various parameters
        allow control of the way the slice is displayed, as well as how the
        plane is generated.

        Parameters
        ----------
        field : string
            The initial field to slice and display.
        normal : array_like
            The vector that defines the desired plane.  For instance, the
            angular momentum of a sphere.
        center : array_like, optional
            The center to be used for things like radius and radial velocity.
            Defaults to the center of the plot collection.
        use_colorbar : bool, optional
            Whether we should leave room for and create a colorbar.
        figure : `matplotlib.figure.Figure`, optional
            The figure onto which the axes will be placed.  Typically not used
            unless *axes* is also specified.
        axes : `matplotlib.axes.Axes`, optional
            The axes object which will be used to create the image plot.
            Typically used for things like multiplots and the like.
        fig_size : tuple of floats
            This parameter can act as a proxy for the manual creation of a
            figure.  By specifying it, you can create plots with an arbitrarily
            large or small size.  It is in inches, defaulting to 100 dpi.
        obj : `AMRCuttingPlaneBase`, optional
            If you would like to use an existing cutting plane, you may specify
            it here, in which case a new cutting plane will not be created.
        field_parameters : dict, optional
            This set of parameters will be passed to the cutting plane upon
            creation, which can be used for passing variables to derived
            fields.

        Returns
        -------
        plot : `yt.raven.CuttingPlanePlot`
            The plot that has been added to the PlotCollection.

        See Also
        --------
        yt.lagos.AMRCuttingPlaneBase : This is the type created by this function.

        Notes
        -----
        This is the primary mechanism for creating cutting plane plots.  Note
        that they are somewhat slow, but useful to orient the image in an
        arbitrary direction.

        Note that all plots can be modified.  See `callback_list` for more
        information.

        Examples
        --------

        Here's a simple mechanism for getting the angular momentum of a
        collapsing cloud and generating a cutting plane aligned with the
        angular momentum vector.

        >>> pf = load("RD0005-mine/RedshiftOutput0005")
        >>> v, c = pf.h.find_max("Density")
        >>> sp = pf.h.sphere(c, 1000.0/pf['au'])
        >>> L = sp.quantities["AngularMomentumVector"]()
        >>> pc = PlotCollection(pf)
        >>> p = pc.add_cutting_plane("Density", L)
        """
        if center == None:
            center = self.c
        if not obj:
            cp = self.pf.hierarchy.cutting(normal, center, field, **kwargs)
        else:
            cp = obj
        p = self._add_plot(PlotTypes.CuttingPlanePlot(cp, field,
                         use_colorbar=use_colorbar, axes=axes, figure=figure,
                         size=fig_size))
        mylog.info("Added plane of %s with 'center' = %s and normal = %s", field,
                    list(center), list(normal))
        p["Axis"] = "CuttingPlane"
        return p

    def add_fixed_res_cutting_plane(self, field, normal, width, res=512,
             center=None, use_colorbar=True, figure = None, axes = None,
             fig_size=None, obj=None, field_parameters = None):
        r"""Create a fixed resolution cutting plane, from that a plot, and add
        it to the current collection.

        A cutting plane is an oblique slice through the simulation volume,
        oriented by a specified normal vector that is perpendicular to the
        image plane.  This function will slice through, but instead of
        retaining all the data necessary to rescale the cutting plane at any
        width, it only retains the pixels for a single width.  This function
        will generate a `yt.lagos.AMRFixedResCuttingPlaneBase` from the given
        parameters.  This image buffer then gets passed to a
        `yt.raven.FixedResolutionPlot`, and the resultant plot is added to the
        current collection.  Various parameters allow control of the way the
        slice is displayed, as well as how the plane is generated.

        Parameters
        ----------
        field : string
            The initial field to slice and display.
        normal : array_like
            The vector that defines the desired plane.  For instance, the
            angular momentum of a sphere.
        width : float
            The width, in code units, of the image plane.
        res : int
            The returned image buffer must be square; this number is how many
            pixels on a side it will have.
        center : array_like, optional
            The center to be used for things like radius and radial velocity.
            Defaults to the center of the plot collection.
        use_colorbar : bool, optional
            Whether we should leave room for and create a colorbar.
        figure : `matplotlib.figure.Figure`, optional
            The figure onto which the axes will be placed.  Typically not used
            unless *axes* is also specified.
        axes : `matplotlib.axes.Axes`, optional
            The axes object which will be used to create the image plot.
            Typically used for things like multiplots and the like.
        fig_size : tuple of floats
            This parameter can act as a proxy for the manual creation of a
            figure.  By specifying it, you can create plots with an arbitrarily
            large or small size.  It is in inches, defaulting to 100 dpi.
        obj : `AMRCuttingPlaneBase`, optional
            If you would like to use an existing cutting plane, you may specify
            it here, in which case a new cutting plane will not be created.
        field_parameters : dict, optional
            This set of parameters will be passed to the cutting plane upon
            creation, which can be used for passing variables to derived
            fields.

        Returns
        -------
        plot : `yt.raven.FixedResolutionPlot`
            The plot that has been added to the PlotCollection.

        See Also
        --------
        yt.lagos.AMRFixedResCuttingPlaneBase : This is the type created by this
                                               function.

        Examples
        --------

        Here's a simple mechanism for getting the angular momentum of a
        collapsing cloud and generating a cutting plane aligned with the
        angular momentum vector.

        >>> pf = load("RD0005-mine/RedshiftOutput0005")
        >>> v, c = pf.h.find_max("Density")
        >>> sp = pf.h.sphere(c, 1000.0/pf['au'])
        >>> L = sp.quantities["AngularMomentumVector"]()
        >>> pc = PlotCollection(pf)
        >>> p = pc.add_fixed_res_cutting_plane("Density", L, 1000.0/pf['au'])
        """
        if center == None:
            center = self.c
        if not obj:
            if field_parameters is None: field_parameters = {}
            data = self.pf.hierarchy.fixed_res_cutting \
                 (normal, center, width, res, **field_parameters)
            #data = frc[field]
        else:
            data = obj
        p = self._add_plot(PlotTypes.FixedResolutionPlot(data, field,
                         use_colorbar=use_colorbar, axes=axes, figure=figure,
                         size=fig_size))
        mylog.info("Added fixed-res plane of %s with 'center' = %s and "
                   "normal = %s", field, list(center), list(normal))
        p["Axis"] = "CuttingPlane"
        return p

    def add_projection(self, field, axis,  weight_field=None,
                       data_source = None,
                       center=None, use_colorbar=True,
                       figure = None, axes = None, fig_size=None,
                       periodic = True, obj = None, field_parameters = None):
        r"""Create a projection, from that a projection plot, and add it to the
        current collection.

        This function will generate a `yt.lagos.AMRProjBase` from the given
        parameters.  This projection then gets passed to a
        `yt.raven.ProjectionPlot`, and the resultant plot is added to the
        current collection.  Various parameters allow control of the way the
        slice is displayed, as well as how the slice is generated.

        Parameters
        ----------
        field : string
            The initial field to slice and display.
        axis : int
            The axis along which to slice.  Can be 0, 1, or 2 for x, y, z.
        data_source : `yt.lagos.AMRData`
            This is a data source respecting the `AMRData` protocol (i.e., it
            has grids and so forth) that will be used as input to the
            projection.
        weight_field : string
            If specified, this will be the weighting field and the resultant
            projection will be a line-of-sight average, defined as sum( f_i *
            w_i * dl ) / sum( w_i * dl )
        center : array_like, optional
            The center to be used for things like radius and radial velocity.
            Defaults to the center of the plot collection.
        use_colorbar : bool, optional
            Whether we should leave room for and create a colorbar.
        figure : `matplotlib.figure.Figure`, optional
            The figure onto which the axes will be placed.  Typically not used
            unless *axes* is also specified.
        axes : `matplotlib.axes.Axes`, optional
            The axes object which will be used to create the image plot.
            Typically used for things like multiplots and the like.
        fig_size : tuple of floats
            This parameter can act as a proxy for the manual creation of a
            figure.  By specifying it, you can create plots with an arbitrarily
            large or small size.  It is in inches, defaulting to 100 dpi.
        periodic : boolean, optional
            By default, the slices are assumed to be periodic, and they will
            wrap around the edges.
        obj : `yt.lagos.AMRProjBase`, optional
            If you would like to use an existing projection, you may specify it
            here, in which case a new projection will not be created.  If this
            option is specified the options data_source, weight_field and
            field_parameters will be ignored.
        field_parameters : dict, optional
            This set of parameters will be passed to the slice upon creation,
            which can be used for passing variables to derived fields.

        Returns
        -------
        plot : `yt.raven.ProjectionPlot`
            The plot that has been added to the PlotCollection.

        See Also
        --------
        yt.lagos.AMRProjBase : This is the type created by this function and 
                               passed to the plot created here.

        Notes
        -----
        This is the primary mechanism for creating projection plots, and
        generating projection plots along multiple axes was the original
        purpose of the PlotCollection.

        Note that all plots can be modified.  See `callback_list` for more
        information.

        Examples
        --------

        >>> pf = load("RD0005-mine/RedshiftOutput0005")
        >>> pc = PlotCollection(pf, [0.5, 0.5, 0.5])
        >>> p = pc.add_projection("Density", 0, "Density")
        """
        if field_parameters is None: field_parameters = {}
        if center == None:
            center = self.c
        if obj is None:
            obj = self.pf.hierarchy.proj(axis, field, weight_field,
                                         source = data_source, center=center,
                                         **field_parameters)
        p = self._add_plot(PlotTypes.ProjectionPlot(obj, field,
                         use_colorbar=use_colorbar, axes=axes, figure=figure,
                         size=fig_size, periodic=periodic))
        p["Axis"] = lagos.axis_names[axis]
        return p

    def add_profile_object(self, data_source, fields,
                           weight="CellMassMsun", accumulation=False,
                           x_bins=64, x_log=True, x_bounds=None,
                           lazy_reader=True, id=None,
                           figure=None, axes=None):
        r"""From an existing object, create a 1D, binned profile.

        This function will accept an existing `AMRData` source and from that,
        it will generate a `Binned1DProfile`, based on the specified options.
        This is useful if you have extracted a region, or if you wish to bin
        some set of massages data -- or even if you wish to bin anything other
        than a sphere.  The profile will be 1D, which means while it can have
        an arbitrary number of fields, those fields will all be binned based on
        a single field.

        Parameters
        ----------
        data_source : `yt.lagos.AMRData`
            This is a data source respecting the `AMRData` protocol (i.e., it
            has grids and so forth) that will be used as input to the profile
            generation.
        fields : list of strings
            The first element of this list is the field by which we will bin;
            all subsequent fields will be binned and their profiles added to
            the underlying `BinnedProfile1D`.
        weight : string, default "CellMassMsun"
            The weighting field for an average.  This defaults to mass-weighted
            averaging.
        accumulation : boolean, optional
            If true, from the low-value to the high-value the values in all
            binned fields will be accumulated.  This is useful for instance
            when adding an unweighted CellMassMsun to a radial plot, as it will
            show mass interior to that radius.
        x_bins : int, optional
            How many bins should there be in the independent variable?
        x_log : boolean, optional
            Should the bin edges be log-spaced?
        x_bounds : tuple of floats, optional
            If specified, the boundary values for the binning.  If unspecified,
            the min/max from the data_source will be used.  (Non-zero min/max
            in case of log-spacing.)
        lazy_reader : boolean, optional
            If this is false, all of the data will be read into memory before
            any processing occurs.  It defaults to true, and grids are binned
            on a one-by-one basis.  Note that parallel computation requires
            this to be true.
        id : int, optional
            If specified, this will be the "semi-unique id" of the resultant
            plot.  This should not be set.
        figure : `matplotlib.figure.Figure`, optional
            The figure onto which the axes will be placed.  Typically not used
            unless *axes* is also specified.
        axes : `matplotlib.axes.Axes`, optional
            The axes object which will be used to create the image plot.
            Typically used for things like multiplots and the like.

        Returns
        -------
        plot : `yt.raven.ProfilePlot`
            The plot that has been added to the PlotCollection.

        See Also
        --------
        yt.lagos.BinnedProfile1D : This is the object that does the
                                   transformation of raw data into a 1D
                                   profile.

        Examples
        --------

        >>> reg = pf.h.region([0.1, 0.2, 0.3], [0.0, 0.1, 0.2],
                              [0.2, 0.3, 0.4])
        >>> pc.add_profile_object(reg, ["Density", "Temperature"])
        """
        if x_bounds is None:
            x_min, x_max = data_source.quantities["Extrema"](
                            fields[0], non_zero = x_log,
                            lazy_reader=lazy_reader)[0]
        else:
            x_min, x_max = x_bounds
        profile = lagos.BinnedProfile1D(data_source,
                                     x_bins, fields[0], x_min, x_max, x_log,
                                     lazy_reader)
        if len(fields) > 1:
            profile.add_fields(fields[1], weight=weight, accumulation=accumulation)
        if id is None: id = self._get_new_id()
        p = self._add_plot(PlotTypes.Profile1DPlot(profile, fields, id,
                                                   axes=axes, figure=figure))
        return p

    def add_profile_sphere(self, radius, unit, fields, center = None,
                           weight="CellMassMsun", accumulation=False,
                           x_bins=64, x_log=True, x_bounds=None,
                           lazy_reader=True, id=None,
                           figure=None, axes=None):
        r"""From a description of a sphere, create a 1D, binned profile.

        This function will accept the radius of a sphere, and from that it will
        generate a `Binned1DProfile`, based on the specified options.  The
        profile will be 1D, which means while it can have an arbitrary number
        of fields, those fields will all be binned based on a single field.

        All subsequent parameters beyond "unit" will be passed verbatim to
        add_profile_object.

        Parameters
        ----------
        radius : float
            The radius of the sphere to generate.
        unit : string
            The unit in which the given radius is expressed.
        fields : list of strings
            The first element of this list is the field by which we will bin;
            all subsequent fields will be binned and their profiles added to
            the underlying `BinnedProfile1D`.
        center : array_like, optional
            The center to be used for things like radius and radial velocity.
            Defaults to the center of the plot collection.
        weight : string, default "CellMassMsun"
            The weighting field for an average.  This defaults to mass-weighted
            averaging.
        accumulation : boolean, optional
            If true, from the low-value to the high-value the values in all
            binned fields will be accumulated.  This is useful for instance
            when adding an unweighted CellMassMsun to a radial plot, as it will
            show mass interior to that radius.
        x_bins : int, optional
            How many bins should there be in the independent variable?
        x_log : boolean, optional
            Should the bin edges be log-spaced?
        x_bounds : tuple of floats, optional
            If specified, the boundary values for the binning.  If unspecified,
            the min/max from the data_source will be used.  (Non-zero min/max
            in case of log-spacing.)
        lazy_reader : boolean, optional
            If this is false, all of the data will be read into memory before
            any processing occurs.  It defaults to true, and grids are binned
            on a one-by-one basis.  Note that parallel computation requires
            this to be true.
        id : int, optional
            If specified, this will be the "semi-unique id" of the resultant
            plot.  This should not be set.
        figure : `matplotlib.figure.Figure`, optional
            The figure onto which the axes will be placed.  Typically not used
            unless *axes* is also specified.
        axes : `matplotlib.axes.Axes`, optional
            The axes object which will be used to create the image plot.
            Typically used for things like multiplots and the like.

        Returns
        -------
        plot : `yt.raven.ProfilePlot`
            The plot that has been added to the PlotCollection.  Note that the
            underlying sphere may be accessed as .data.data_source

        See Also
        --------
        yt.lagos.BinnedProfile1D : This is the object that does the
                                   transformation of raw data into a 1D
                                   profile.
        yt.lagos.AMRSphereBase : This is the object auto-generated by this
                                 function.

        Examples
        --------

        >>> pc.add_profile_sphere(1.0, 'kpc', ["Density", "Electron_Fraction"])
        """
        if center is None:
            center = self.c
        r = radius/self.pf[unit]
        sphere = self.pf.hierarchy.sphere(center, r)
        p = self.add_profile_object(sphere, fields, weight, accumulation,
                           x_bins, x_log, x_bounds, lazy_reader, id,
                           figure, axes)
        p["Width"] = radius
        p["Unit"] = unit
        p["Axis"] = None
        return p

    def add_phase_object(self, data_source, fields, cmap=None,
                               weight="CellMassMsun", accumulation=False,
                               x_bins=64, x_log=True, x_bounds=None,
                               y_bins=64, y_log=True, y_bounds=None,
                               lazy_reader=True, id=None,
                               axes = None, figure = None,
                               fractional=False):
        r"""From an existing object, create a 2D, binned profile.

        This function will accept an existing `AMRData` source and from that,
        it will generate a `Binned2DProfile`, based on the specified options.
        This is useful if you have extracted a region, or if you wish to bin
        some set of massages data -- or even if you wish to bin anything other
        than a sphere.  The profile will be 2D, which means while it can have
        an arbitrary number of fields, those fields will all be binned based on
        two fields.

        Parameters
        ----------
        data_source : `yt.lagos.AMRData`
            This is a data source respecting the `AMRData` protocol (i.e., it
            has grids and so forth) that will be used as input to the profile
            generation.
        fields : list of strings
            The first element of this list is the field by which we will bin
            into the y-axis, the second is the field by which we will bin onto
            the y-axis.  All subsequent fields will be binned and their
            profiles added to the underlying `BinnedProfile2D`.
        cmap : string, optional
            An acceptable colormap.  See either raven.color_maps or
            http://www.scipy.org/Cookbook/Matplotlib/Show_colormaps .
        weight : string, default "CellMassMsun"
            The weighting field for an average.  This defaults to mass-weighted
            averaging.
        accumulation : list of booleans, optional
            If true, from the low-value to the high-value the values in all
            binned fields will be accumulated.  This is useful for instance
            when adding an unweighted CellMassMsun to a radial plot, as it will
            show mass interior to that radius.  The first value is for the
            x-axis, the second value for the y-axis.  Note that accumulation
            will only be along each row or column.
        x_bins : int, optional
            How many bins should there be in the x-axis variable?
        x_log : boolean, optional
            Should the bin edges be log-spaced?
        x_bounds : tuple of floats, optional
            If specified, the boundary values for the binning.  If unspecified,
            the min/max from the data_source will be used.  (Non-zero min/max
            in case of log-spacing.)
        y_bins : int, optional
            How many bins should there be in the y-axis variable?
        y_log : boolean, optional
            Should the bin edges be log-spaced?
        y_bounds : tuple of floats, optional
            If specified, the boundary values for the binning.  If unspecified,
            the min/max from the data_source will be used.  (Non-zero min/max
            in case of log-spacing.)
        lazy_reader : boolean, optional
            If this is false, all of the data will be read into memory before
            any processing occurs.  It defaults to true, and grids are binned
            on a one-by-one basis.  Note that parallel computation requires
            this to be true.
        id : int, optional
            If specified, this will be the "semi-unique id" of the resultant
            plot.  This should not be set.
        figure : `matplotlib.figure.Figure`, optional
            The figure onto which the axes will be placed.  Typically not used
            unless *axes* is also specified.
        axes : `matplotlib.axes.Axes`, optional
            The axes object which will be used to create the image plot.
            Typically used for things like multiplots and the like.
        fractional : boolean
            If true, the plot will be normalized to the sum of all the binned
            values.

        Returns
        -------
        plot : `yt.raven.PlotTypes.PhasePlot`
            The plot that has been added to the PlotCollection.

        See Also
        --------
        yt.lagos.BinnedProfile2D : This is the object that does the
                                   transformation of raw data into a 1D
                                   profile.
        
        Examples
        --------
        This will show the mass-distribution in the Density-Temperature plane.
        
        >>> pf = load("RD0005-mine/RedshiftOutput0005")
        >>> reg = pf.h.region([0.1, 0.2, 0.3], [0.0, 0.1, 0.2],
        ...                   [0.2, 0.3, 0.4])
        >>> pc.add_phase_object(reg, ["Density", "Temperature", "CellMassMsun"],
        ...                     weight = None)
        """
        if x_bounds is None:
            x_min, x_max = data_source.quantities["Extrema"](
                                    fields[0], non_zero = x_log,
                                    lazy_reader=lazy_reader)[0]
        else:
            x_min, x_max = x_bounds
        if y_bounds is None:
            y_min, y_max = data_source.quantities["Extrema"](
                                    fields[1], non_zero = y_log,
                                    lazy_reader=lazy_reader)[0]
        else:
            y_min, y_max = y_bounds
        profile = lagos.BinnedProfile2D(data_source,
                                     x_bins, fields[0], x_min, x_max, x_log,
                                     y_bins, fields[1], y_min, y_max, y_log,
                                     lazy_reader)
        if id is None: id = self._get_new_id()
        p = self._add_plot(PlotTypes.PhasePlot(profile, fields, 
                                               id, cmap=cmap,
                                               figure=figure, axes=axes))
        if len(fields) > 2:
            # This will add all the fields to the profile object
            p.switch_z(fields[2], weight=weight, accumulation=accumulation, fractional=fractional)
        return p

    def add_phase_sphere(self, radius, unit, fields, center = None, cmap=None,
                         weight="CellMassMsun", accumulation=False,
                         x_bins=64, x_log=True, x_bounds=None,
                         y_bins=64, y_log=True, y_bounds=None,
                         lazy_reader=True, id=None,
                         axes = None, figure = None,
                         fractional=False):
        r"""From a description of a sphere, create a 2D, binned profile.

        This function will accept the radius of a sphere, and from that it will
        generate a `Binned1DProfile`, based on the specified options.  The
        profile will be 2D, which means while it can have an arbitrary number
        of fields, those fields will all be binned based on two fields.

        All subsequent parameters beyond "unit" will be passed verbatim to
        add_profile_object.

        Parameters
        ----------
        radius : float
            The radius of the sphere to generate.
        unit : string
            The unit in which the given radius is expressed.
        fields : list of strings
            The first element of this list is the field by which we will bin
            into the y-axis, the second is the field by which we will bin onto
            the y-axis.  All subsequent fields will be binned and their
            profiles added to the underlying `BinnedProfile2D`.
        center : array_like, optional
            The center to be used for things like radius and radial velocity.
            Defaults to the center of the plot collection.
        cmap : string, optional
            An acceptable colormap.  See either raven.color_maps or
            http://www.scipy.org/Cookbook/Matplotlib/Show_colormaps .
        weight : string, default "CellMassMsun"
            The weighting field for an average.  This defaults to mass-weighted
            averaging.
        accumulation : list of booleans, optional
            If true, from the low-value to the high-value the values in all
            binned fields will be accumulated.  This is useful for instance
            when adding an unweighted CellMassMsun to a radial plot, as it will
            show mass interior to that radius.  The first value is for the
            x-axis, the second value for the y-axis.  Note that accumulation
            will only be along each row or column.
        x_bins : int, optional
            How many bins should there be in the x-axis variable?
        x_log : boolean, optional
            Should the bin edges be log-spaced?
        x_bounds : tuple of floats, optional
            If specified, the boundary values for the binning.  If unspecified,
            the min/max from the data_source will be used.  (Non-zero min/max
            in case of log-spacing.)
        y_bins : int, optional
            How many bins should there be in the y-axis variable?
        y_log : boolean, optional
            Should the bin edges be log-spaced?
        y_bounds : tuple of floats, optional
            If specified, the boundary values for the binning.  If unspecified,
            the min/max from the data_source will be used.  (Non-zero min/max
            in case of log-spacing.)
        lazy_reader : boolean, optional
            If this is false, all of the data will be read into memory before
            any processing occurs.  It defaults to true, and grids are binned
            on a one-by-one basis.  Note that parallel computation requires
            this to be true.
        id : int, optional
            If specified, this will be the "semi-unique id" of the resultant
            plot.  This should not be set.
        figure : `matplotlib.figure.Figure`, optional
            The figure onto which the axes will be placed.  Typically not used
            unless *axes* is also specified.
        axes : `matplotlib.axes.Axes`, optional
            The axes object which will be used to create the image plot.
            Typically used for things like multiplots and the like.
        fractional : boolean
            If true, the plot will be normalized to the sum of all the binned
            values.

        Returns
        -------
        plot : `yt.raven.PhasePlot`
            The plot that has been added to the PlotCollection.

        See Also
        --------
        yt.lagos.BinnedProfile2D : This is the object that does the
                                   transformation of raw data into a 1D
                                   profile.

        Examples
        --------

        This will show the mass-distribution in the Density-Temperature plane.

        >>> pc.add_phase_sphere(1.0, 'kpc',
                ["Density", "Temperature", "CellMassMsun"], weight = None)
        """

        if center is None: center = self.c
        r = radius/self.pf[unit]
        data_source = self.pf.hierarchy.sphere(center, r)
        p = add_phase_object(self, data_source, fields, cmap,
                             weight, accumulation,
                             x_bins, x_log, x_bounds,
                             y_bins, y_log, y_bounds,
                             lazy_reader, id, axes, figure, fractional)
        p["Width"] = radius
        p["Unit"] = unit
        p["Axis"] = None
        return p

    def add_scatter_source(self, data_source, fields, id=None,
                     figure = None, axes = None, plot_options = None):
        r"""Given a data source, make a scatter plot from that data source.

        This is a very simple plot: you give it an instance of `AMRData`, two
        field names, and it will plot them on an axis

        Parameters
        ----------
        data_source : `yt.lagos.AMRData`
            This will be the data source from which field values will be
            obtained.
        fields : tuple of strings
            The first of these will be the x-field, and the second the y-field.
        id : int, optional
            If specified, this will be the "semi-unique id" of the resultant
            plot.  This should not be set.
        figure : `matplotlib.figure.Figure`, optional
            The figure onto which the axes will be placed.  Typically not used
            unless *axes* is also specified.
        axes : `matplotlib.axes.Axes`, optional
            The axes object which will be used to create the image plot.
            Typically used for things like multiplots and the like.
        plot_options : dict
            These options will be given to `matplotlib.axes.Axes.scatter`
        
        Returns
        -------
        plot : `yt.raven.ScatterPlot`
            The plot that has been added to the PlotCollection.

        Notes
        -----
        This is a simpler way of making a phase plot, but note that because
        pixels are deposited in order, the color may be a biased sample.

        Examples
        --------

        >>> reg = pf.h.region([0.1, 0.2, 0.3], [0.0, 0.1, 0.2],
                              [0.2, 0.3, 0.4])
        >>> pc.add_scatter_plot(reg, ["Density", "Temperature"],
        >>>                     plot_options = {'color':'b'})
        """
        if id is None: id = self._get_new_id()
        if plot_options is None: plot_options = {}
        sp = PlotTypes.ScatterPlot(data_source, fields, id,
                                   plot_options = plot_options,
                                   figure=figure, axes=axes)
        p = self._add_plot(sp)
        return p

    def add_fixed_resolution_plot(self, frb, field, use_colorbar=True,
                      figure = None, axes = None, fig_size=None):
        r"""Create a fixed resolution image from an existing buffer.

        This accepts a `FixedResolutionBuffer` and will make a plot from that
        buffer.

        Parameters
        ----------
        frb : `yt.raven.FixedResolutionBuffer`
            The buffer from which fields will be pulled.
        field : string
            The initial field to display.
        use_colorbar : bool, optional
            Whether we should leave room for and create a colorbar.
        figure : `matplotlib.figure.Figure`, optional
            The figure onto which the axes will be placed.  Typically not used
            unless *axes* is also specified.
        axes : `matplotlib.axes.Axes`, optional
            The axes object which will be used to create the image plot.
            Typically used for things like multiplots and the like.
        fig_size : tuple of floats
            This parameter can act as a proxy for the manual creation of a
            figure.  By specifying it, you can create plots with an arbitrarily
            large or small size.  It is in inches, defaulting to 100 dpi.

        Returns
        -------
        plot : `yt.raven.FixedResolutionPlot`
            The plot that has been added to the PlotCollection.

        See Also
        --------
        yt.extensions.image_writer.write_image : A faster, colorbarless way to
                                                 write out FRBs.

        Examples
        --------

        Here's a simple mechanism for getting the angular momentum of a
        collapsing cloud and generating a cutting plane aligned with the
        angular momentum vector.

        >>> pf = load("RD0005-mine/RedshiftOutput0005")
        >>> proj = pf.h.proj(0, "Density")
        >>> frb = FixedResolutionBuffer(proj, (0.2, 0.3, 0.4, 0.5), (512, 512))
        >>> p = pc.add_fixed_resolution_plot(frb, "Density")
        """
        p = self._add_plot(PlotTypes.FixedResolutionPlot(frb, field,
                         use_colorbar=use_colorbar, axes=axes, figure=figure,
                         size=fig_size))
        p["Axis"] = "na"
        return p

    def add_ortho_ray(self, axis, coords, field, figure = None,
                      axes = None, field_parameters = None,
                      plot_options = None):
        r"""Create a ray parallel to some axis, from that a line plot, and add
        it to the current collection.

        This function will generate a `yt.lagos.AMROrthoRayBase` from the given
        parameters.  This ray then gets passed to a `yt.raven.LineQueryPLot`, and
        the resultant plot is added to the current collection.  Various
        parameters allow control of the way the line plot is displayed, as well as
        how the ray is generated.

        Parameters
        ----------
        axis : int
            The axis along which to cast the ray.  Can be 0, 1, or 2 for x, y,
            z.
        coords : tuple of floats
            The coordinates to place the ray at.  Note that the axes are in the
            form of x_dict[axis] and y_dict[axis] for some axis.
        field : string
            The initial field to slice and display.
        figure : `matplotlib.figure.Figure`, optional
            The figure onto which the axes will be placed.  Typically not used
            unless *axes* is also specified.
        axes : `matplotlib.axes.Axes`, optional
            The axes object which will be used to create the image plot.
            Typically used for things like multiplots and the like.
        field_parameters : dict, optional
            This set of parameters will be passed to the slice upon creation,
            which can be used for passing variables to derived fields.
        plot_options : dict
            These options will be given to `matplotlib.axes.Axes.plot`

        Returns
        -------
        plot : `yt.raven.LineQueryPlot`
            The plot that has been added to the PlotCollection.

        See Also
        --------
        yt.lagos.AMROrthoRayBase : This is the type created by this function and 
                                   passed to the plot created here.

        Examples
        --------

        This will cast a ray from (0.0, 0.5, 0.5) to (1.0, 0.5, 0.5) and plot
        it.

        >>> pf = load("RD0005-mine/RedshiftOutput0005")
        >>> pc = PlotCollection(pf, [0.5, 0.5, 0.5])
        >>> p = pc.add_ortho_ray(0, (0.5, 0.5), "Density")
        """

        if field_parameters is None: field_parameters = {}
        if plot_options is None: plot_options = {}
        data_source = self.pf.h.ortho_ray(axis, coords, field,
                        **field_parameters)
        p = self._add_plot(PlotTypes.LineQueryPlot(data_source,
                [axis_names[axis], field], self._get_new_id(),
                figure=figure, axes=axes, plot_options=plot_options))
        return p

    def add_ray(self, start_point, end_point, field, figure = None,
                axes = None, field_parameters = None, plot_options = None):
        r"""Create a ray between two points, from that a line plot, and add
        it to the current collection.

        This function will generate a `yt.lagos.AMRRayBase` from the given
        parameters.  This ray then gets passed to a `yt.raven.LineQueryPLot`, and
        the resultant plot is added to the current collection.  Various
        parameters allow control of the way the line plot is displayed, as well as
        how the ray is generated.

        Parameters
        ----------
        start_point : array_like
            The starting point of the ray.
        end_point : array_like
            The ending point of the ray.
        field : string
            The initial field to slice and display.
        figure : `matplotlib.figure.Figure`, optional
            The figure onto which the axes will be placed.  Typically not used
            unless *axes* is also specified.
        axes : `matplotlib.axes.Axes`, optional
            The axes object which will be used to create the image plot.
            Typically used for things like multiplots and the like.
        field_parameters : dict, optional
            This set of parameters will be passed to the slice upon creation,
            which can be used for passing variables to derived fields.
        plot_options : dict
            These options will be given to `matplotlib.axes.Axes.plot`

        Returns
        -------
        plot : `yt.raven.LineQueryPlot`
            The plot that has been added to the PlotCollection.

        See Also
        --------
        yt.lagos.AMRRayBase : This is the type created by this function and 
                              passed to the plot created here.

        Examples
        --------

        This will cast a ray from (0.1, 0.2, 0.3) to (0.9, 0.7, 0.4) and plot
        it.

        >>> pf = load("RD0005-mine/RedshiftOutput0005")
        >>> pc = PlotCollection(pf, [0.5, 0.5, 0.5])
        >>> p = pc.add_ray((0.1, 0.2, 0.3), (0.9, 0.7, 0.4), "Density")
        """
        if field_parameters is None: field_parameters = {}
        if plot_options is None: plot_options = {}
        data_source = self.pf.h.ray(start_point, end_point, field,
                                    **field_parameters)
        p = self._add_plot(PlotTypes.LineQueryPlot(data_source,
                ['t', field], self._get_new_id(),
                figure=figure, axes=axes, plot_options=plot_options))
        return p

    def _get_new_id(self):
        self.__id_counter += 1
        return self.__id_counter-1

    @rootonly
    def save_book(self, filename, author = None, title = None, keywords = None,
                  subject = None, creator = None, producer = None,
                  creation_data = None):
        r"""Save a multipage PDF of all the current plots, rather than
        individual image files.

        This function will utilize the matplotlib PDF backend to create a new
        PDF, and for every plot that the PlotCollection currently has, it will
        render a new page into that PDF.  The pages will be in the order of the
        current plots.

        Parameters
        ----------
        filename : string
            The name of the PDF file to generate.  Note that it will be
            overwritten, and '.pdf' will not be appended.
        author : string, optional
            The string to place in the metadata value of the PDF for 'author'.
        title : string, optional
            The string to place in the metadata value of the PDF for 'title'.
        keywords : string, optional
            The string to place in the metadata value of the PDF for 'keywords'.
        subject : string, optional
            The string to place in the metadata value of the PDF for 'subject'.
        creator : string, optional
            The string to place in the metadata value of the PDF for 'creator'.
        producer : string, optional
            The string to place in the metadata value of the PDF for 'producer'.
        creation_date : string, optional
            The string to place in the metadata value of the PDF for
            'creation_date'.

        Returns
        -------
        Nothing

        Examples
        --------
        This will set up a new PlotCollection, add some plots, and then save it
        as a PDF.

        >>> pc = PlotCollection(pf, [0.5, 0.5, 0.5])
        >>> pc.add_projection("Density", 0)
        >>> pc.add_projection("Density", 1)
        >>> pc.add_projection("Density", 2)
        >>> pc.set_width(0.5, 'pc')
        >>> dd = pf.h.all_data()
        >>> pc.add_phase_object(dd, ["Density", "Temperature", "CellMassMsun"],
        ...                     weight = None)
        >>> pc.save_book("my_plots.pdf", author="Matthew Turk", 
        ...              title="Fun plots")
        """
        from matplotlib.backends.backend_pdf import PdfPages
        outfile = PdfPages(filename)
        for plot in self.plots:
            plot.save_to_pdf(outfile)
        if info is not None:
            outfile._file.writeObject(outfile._file.infoObject, info)
        outfile.close()

def wrap_pylab_newplot(func):
    @wraps(func)
    def pylabify(self, *args, **kwargs):
        # Let's assume that axes and figure are not in the positional
        # arguments -- probably safe!
        new_fig = self.pylab.figure()
        try:
            new_fig.canvas.set_window_title("%s" % (self.pf))
        except AttributeError:
            pass
        kwargs['axes'] = self.pylab.gca()
        kwargs['figure'] = self.pylab.gcf()
        retval = func(self, *args, **kwargs)
        retval._redraw_image()
        retval._fig_num = new_fig.number
        self.pylab.show()
        self.pylab.draw()
        return retval
    return pylabify

def wrap_pylab_show(func):
    @wraps(func)
    def pylabify(self, *args, **kwargs):
        retval = func(self, *args, **kwargs)
        fig_num = self.pylab.gcf().number
        for p in self.plots:
            self.pylab.figure(p._fig_num)
            self.pylab.draw()
        self.pylab.figure(fig_num)
        return retval
    return pylabify

class _Interactify(type):
    # All inherited methods get wrapped if they start with add_ or set_
    # So anything inheriting this automatically gets set up; additional
    # wrappings can be done manually.  Note that this does NOT modify
    # methods that are only in the subclasses.
    def __init__(cls, name, bases, d):
        super(_Interactify, cls).__init__(name, bases, d)
        for base in bases:
            for attrname in dir(base):
                if attrname in d: continue # If overridden, don't reset
                attr = getattr(cls, attrname)
                if type(attr) == types.MethodType:
                    if attrname.startswith("add_"):
                        setattr(cls, attrname, wrap_pylab_newplot(attr))
                    elif attrname.startswith("set_"):
                        setattr(cls, attrname, wrap_pylab_show(attr))

class PlotCollectionInteractive(PlotCollection):
    __metaclass__ = _Interactify

    autoscale = wrap_pylab_show(PlotCollection.autoscale)
    switch_field = wrap_pylab_show(PlotCollection.switch_field)

    def __init__(self, *args, **kwargs):
        import pylab
        self.pylab = pylab
        super(PlotCollectionInteractive, self).__init__(*args, **kwargs)

    def redraw(self):
        r"""Redraw all affiliated plots.

        To ensure that any interactive windows are up to date, this function
        can be called to redraw all images into them.
        """
        for plot in self.plots:
            plot._redraw_image()
        self.pylab.show()

    def clear_figures(self):
        r"""Clear all interactive figures affiliated with this collection.

        Because reusing figures between plot collections can be tricky,
        occasionally they must be manually cleared to re-obtain empty figures
        for future plotting.  This will clear all figures.
        """
        for plot in self.plots:
            self.pylab.figure(plot._fig_num)
            self.pylab.clf()

def get_multi_plot(nx, ny, colorbar = 'vertical', bw = 4, dpi=300):
    r"""Construct a multiple axes plot object, with or without a colorbar, into
    which multiple plots may be inserted.

    This will create a set of `matplotlib.axes.Axes`, all lined up into a grid,
    which are then returned to the user and which can be used to plot multiple
    plots on a single figure.

    Parameters
    ----------
    nx : int
        Number of axes to create along the x-direction
    ny : int
        Number of axes to create along the y-direction
    colorbar : {'vertical', 'horizontal', None}, optional
        Should Axes objects for colorbars be allocated, and if so, should they
        correspond to the horizontal or vertical set of axes?

    Returns
    -------
    fig : `matplotlib.figure.Figure
        The figure created inside which the axes reside
    tr : list of list of `matplotlib.axes.Axes` objects
        This is a list, where the inner list is along the x-axis and the outer
        is along the y-axis
    cbars : list of `matplotlib.axes.Axes` objects
        Each of these is an axes onto which a colorbar can be placed.

    Notes
    -----
    This is a simple implementation for a common use case.  Viewing the source
    can be instructure, and is encouraged to see how to generate more
    complicated or more specific sets of multiplots for your own purposes.
    """
    PlotTypes.Initialize()
    hf, wf = 1.0/ny, 1.0/nx
    fudge_x = fudge_y = 1.0
    if colorbar is None:
        fudge_x = fudge_y = 1.0
    elif colorbar.lower() == 'vertical':
        fudge_x = nx/(0.25+nx)
        fudge_y = 1.0
    elif colorbar.lower() == 'horizontal':
        fudge_x = 1.0
        fudge_y = ny/(0.40+ny)
    fig = matplotlib.figure.Figure((bw*nx/fudge_x, bw*ny/fudge_y), dpi=dpi)
    fig.set_canvas(be.engineVals["canvas"](fig))
    fig.subplots_adjust(wspace=0.0, hspace=0.0,
                        top=1.0, bottom=0.0,
                        left=0.0, right=1.0)
    tr = []
    print fudge_x, fudge_y
    for j in range(ny):
        tr.append([])
        for i in range(nx):
            left = i*wf*fudge_x
            bottom = fudge_y*(1.0-(j+1)*hf) + (1.0-fudge_y)
            ax = fig.add_axes([left, bottom, wf*fudge_x, hf*fudge_y])
            tr[-1].append(ax)
    cbars = []
    if colorbar is None:
        pass
    elif colorbar.lower() == 'horizontal':
        for i in range(nx):
            # left, bottom, width, height
            # Here we want 0.10 on each side of the colorbar
            # We want it to be 0.05 tall
            # And we want a buffer of 0.15
            ax = fig.add_axes([wf*(i+0.10)*fudge_x, hf*fudge_y*0.20,
                               wf*(1-0.20)*fudge_x, hf*fudge_y*0.05])
            cbars.append(ax)
    elif colorbar.lower() == 'vertical':
        for j in range(ny):
            ax = fig.add_axes([wf*(nx+0.05)*fudge_x, hf*fudge_y*(ny-(j+0.95)),
                               wf*fudge_x*0.05, hf*fudge_y*0.90])
            ax.clear()
            cbars.append(ax)
    return fig, tr, cbars
