"""
Unit test the kD trees in yt.


Authors:
 * Stephen Skory 


"""

#-----------------------------------------------------------------------------
# Copyright (c) 2013, yt Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from yt.testing import *

try:
    from yt.utilities.kdtree.api import *
except ImportError:
    mylog.debug("The Fortran kD-Tree did not import correctly.")

from yt.utilities.spatial import cKDTree

def setup():
    pass

def test_fortran_tree():
    r"""This test makes sure that the fortran kdtree is finding the correct
    nearest neighbors.
    """
    # Four points.
    try:
        fKD.pos = np.empty((3, 4), dtype='float64', order='F')
    except NameError:
        return
    # Make four points by hand that, in particular, will allow us to test
    # the periodicity of the kdtree.
    points = np.array([0.01, 0.5, 0.98, 0.99])
    fKD.pos[0, :] = points
    fKD.pos[1, :] = points
    fKD.pos[2, :] = points
    fKD.qv = np.empty(3, dtype='float64')
    fKD.dist = np.empty(4, dtype='float64')
    fKD.tags = np.empty(4, dtype='int64')
    fKD.nn = 4
    fKD.sort = True
    create_tree(0)
    # Now we check to make sure that we find the correct nearest neighbors,
    # which get stored in dist and tags.
    fKD.qv[:] = 0.999
    find_nn_nearest_neighbors()
    # Fix fortran counting.
    fKD.tags -= 1
    # Clean up before the tests.
    free_tree(0)
    # What the answers should be.
    dist = np.array([2.43e-04, 3.63e-04, 1.083e-03, 7.47003e-01])
    tags = np.array([3, 0, 2, 1], dtype='int64')
    assert_array_almost_equal(fKD.dist, dist)
    assert_array_equal(fKD.tags, tags)

def test_cython_tree():
    r"""This test makes sure that the cython kdtree is finding the correct
    nearest neighbors.
    """
    # Four points.
    pos = np.empty((4, 3), dtype='float64')
    # Make four points by hand that, in particular, will allow us to test
    # the periodicity of the kdtree.
    points = np.array([0.01, 0.5, 0.98, 0.99])
    pos[:, 0] = points
    pos[:, 1] = points
    pos[:, 2] = points
    kdtree = cKDTree(pos, leafsize = 2)
    qv = np.array([0.999]*3)
    res = kdtree.query(qv, 4, period=[1.,1.,1])
    # What the answers should be.
    dist = np.array([2.43e-04, 3.63e-04, 1.083e-03, 7.47003e-01])
    tags = np.array([3, 0, 2, 1], dtype='int64')
    assert_array_almost_equal(res[0], dist)
    assert_array_equal(res[1], tags)

