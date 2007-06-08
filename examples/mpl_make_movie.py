# Simple example of how to use matplotlib for plotting.
# A lot of this will become automated, but here's some lower level stuff
# to give an idea of what it's all about.

# Note that this just plots three linked AMR plots.  (They can be projections,
# too!)  We could just as easily make a fourth plot that is of any type.
# Color bar support will be added soon.  For now it is not clear to me the best
# way to proceed.

# NOTE THAT YOUR ~/.matplotlib/matplotlibrc must have "Agg" set as the engine.
# matplotlibrc will show up automatically after you import pylab the very first
# time.

# Set the parameters of our movie
maxwidth = (1,'1')
minwidth = (0.5,"au")
numframes = 100
filename_template = "frame%04i.png"
fieldName = "NumberDensity"
hierarchy_filename = "DataDump0022.dir/DataDump0022"

# Import the modules we need
import yt.lagos as lagos
from yt.arraytypes import *
import yt.raven as raven
import pylab
from math import log10

# Standard data loading
a=lagos.EnzoHierarchy(hierarchy_filename)
v,c=a.findMax("Density")
centers = [(c[1],c[2]),(c[0],c[2]),(c[0],c[1])]

# We want a square figure
fig = pylab.figure(figsize=(8,8))

# This makes them all adjacent
fig.subplots_adjust(hspace=0,wspace=0,bottom=0.0, top=1.0, left=0.0, right=1.0)

# This sets the color map
pylab.prism()

# These are the inital bounds
absmin = 1e+30
absmax = 1e-30

# Set up lists...
slices = []
axes=[]
ims = []

# Now, for each axis, do the thingie
for i in range(3):
    slices.append(lagos.EnzoSlice(a, i, c[i], fieldName))
    # Subplots are 1-indexed, so we do i+1
    axes.append(fig.add_subplot(2,2,i+1, aspect='equal'))
    ims.append(axes[-1].amrshow(slices[-1].x, slices[-1].y, slices[-1].dx, \
                          slices[-1].dy, na.log10(slices[-1][fieldName])))
    # If you know the bounds in advance, feel free to drop these next two lines
    absmin = min(na.log10(slices[-1][fieldName]).min(), absmin)
    absmax = max(na.log10(slices[-1][fieldName]).max(), absmax)
    axes[-1].set_xticks(()) # we don't want any of these things
    axes[-1].set_yticks(())
    axes[-1].set_xlabel("")
    axes[-1].set_ylabel("")

# For easier access
ac = zip(axes, centers, ims)
i=0

# We want to do this log-spaced.
# Note that we make numframes complex, so that it is regarded by mgrid
# as a number of steps to take, rather than a step-size interval.
for w in na.mgrid[log10(maxwidth[0]/a[maxwidth[1]])\
                 :log10(minwidth[0]/a[minwidth[1]])\
                 :numframes*1j]:
    width = 10**w
    # Zoom in...
    for ax, cc, im in ac:
        ax.set_xlim(cc[0]-0.5*width, cc[0]+0.5*width)
        ax.set_ylim(cc[1]-0.5*width, cc[1]+0.5*width)
    for im in ims: 
        # For now, we need to do this to keep the scale the same on
        # the next call to draw, which happens on .savefig().
        # I'm working on a "linked" AMR plot, which will automate all of these
        # processes.
        im.set_next_clim(absmin, absmax)
    s = filename_template % (i)
    fig.savefig(s)
    print "Saved %s" % (s)
    i+=1
