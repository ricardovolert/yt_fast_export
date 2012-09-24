"""Provides utility and helper functions for testing in yt.

Author: Anthony Scpatz <scopatz@gmail.com>
Affiliation: The University of Chicago
Homepage: http://yt-project.org/
License:
  Copyright (C) 2012 Anthony Scopatz.  All Rights Reserved.

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

import numpy as np


def amrspace(extent, levels=7, cells=8):
    """Creates two numpy arrays representing the left and right bounds of 
    an AMR grid as well as an array for the AMR level of each cell.

    Parameters
    ----------
    extent : array-like
        This a sequence of length 2*ndims that is the bounds of each dimension.
        For example, the 2D unit square would be given by [0.0, 1.0, 0.0, 1.0].
        A 3D cylindrical grid may look like [0.0, 2.0, -1.0, 1.0, 0.0, 2*np.pi].
    levels : int or sequence of ints, optional
        This is the number of AMR refinement levels.  If given as a sequence (of
        length ndims), then each dimension will be refined down to this level.
        All values in this array must be the same or zero.  A zero valued dimension
        indicates that this dim should not be refined.  Taking the 3D cylindrical
        example above if we don't want refine theta but want r and z at 5 we would 
        set levels=(5, 5, 0).
    cells : int, optional
        This is the number of cells per refinement level.

    Returns
    -------
    left : float ndarray, shape=(npoints, ndims)
        The left AMR grid points.
    right : float ndarray, shape=(npoints, ndims)
        The right AMR grid points.
    level : int ndarray, shape=(npoints,)
        The AMR level for each point.

    Examples
    --------
    >>> l, r, lvl = amrspace([0.0, 2.0, 1.0, 2.0, 0.0, 3.14], levels=(3,3,0), cells=2)
    >>> print l
    [[ 0.     1.     0.   ]
     [ 0.25   1.     0.   ]
     [ 0.     1.125  0.   ]
     [ 0.25   1.125  0.   ]
     [ 0.5    1.     0.   ]
     [ 0.     1.25   0.   ]
     [ 0.5    1.25   0.   ]
     [ 1.     1.     0.   ]
     [ 0.     1.5    0.   ]
     [ 1.     1.5    0.   ]]

    """
    extent = np.asarray(extent, dtype='f8')
    dextent = extent[1::2] - extent[::2]
    ndims = len(dextent)

    if isinstance(levels, int):
        minlvl = maxlvl = levels
        levels = np.array([levels]*ndims, dtype='int32')
    else:
        levels = np.asarray(levels, dtype='int32')
        minlvl = levels.min()
        maxlvl = levels.max()
        if minlvl != maxlvl and (minlvl != 0 or set([minlvl, maxlvl]) != set(levels)):
            raise ValueError("all levels must have the same value or zero.")
    dims_zero = (levels == 0)
    dims_nonzero = ~dims_zero
    ndims_nonzero = dims_nonzero.sum()

    npoints = (cells**ndims_nonzero - 1)*maxlvl + 1
    left = np.empty((npoints, ndims), dtype='float64')
    right = np.empty((npoints, ndims), dtype='float64')
    level = np.empty(npoints, dtype='int32')

    # fill zero dims
    left[:,dims_zero] = extent[::2][dims_zero]
    right[:,dims_zero] = extent[1::2][dims_zero]

    # fill non-zero dims
    dcell = 1.0 / cells
    left_slice =  tuple([slice(extent[2*n], extent[2*n+1], extent[2*n+1]) if \
        dims_zero[n] else slice(0.0,1.0,dcell) for n in range(ndims)])
    right_slice = tuple([slice(extent[2*n+1], extent[2*n], -extent[2*n+1]) if \
        dims_zero[n] else slice(dcell,1.0+dcell,dcell) for n in range(ndims)])
    left_norm_grid = np.reshape(np.mgrid[left_slice].T.flat[ndims:], (-1, ndims))
    lng_zero = left_norm_grid[:,dims_zero]
    lng_nonzero = left_norm_grid[:,dims_nonzero]

    right_norm_grid = np.reshape(np.mgrid[right_slice].T.flat[ndims:], (-1, ndims))
    rng_zero = right_norm_grid[:,dims_zero]
    rng_nonzero = right_norm_grid[:,dims_nonzero]

    level[0] = maxlvl
    left[0,:] = extent[::2]
    right[0,dims_zero] = extent[1::2][dims_zero]
    right[0,dims_nonzero] = (dcell**maxlvl)*dextent[dims_nonzero] + extent[::2][dims_nonzero]
    for i, lvl in enumerate(range(maxlvl, 0, -1)):
        start = (cells**ndims_nonzero - 1)*i + 1
        stop = (cells**ndims_nonzero - 1)*(i+1) + 1
        dsize = dcell**(lvl-1) * dextent[dims_nonzero]
        level[start:stop] = lvl
        left[start:stop,dims_zero] = lng_zero
        left[start:stop,dims_nonzero] = lng_nonzero*dsize + extent[::2][dims_nonzero]
        right[start:stop,dims_zero] = rng_zero
        right[start:stop,dims_nonzero] = rng_nonzero*dsize + extent[::2][dims_nonzero]

    return left, right, level
