"""
Field Interpolation Tables


Authors:
 * Matthew Turk 


"""

#-----------------------------------------------------------------------------
# Copyright (c) 2013, yt Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

cimport cython
cimport numpy as np
from fp_utils cimport imax, fmax, imin, fmin, iclip, fclip, fabs

DEF Nch = 4

cdef struct FieldInterpolationTable:
    # Note that we make an assumption about retaining a reference to values
    # externally.
    np.float64_t *values 
    np.float64_t bounds[2]
    np.float64_t dbin
    np.float64_t idbin
    int field_id
    int weight_field_id
    int weight_table_id
    int nbins

cdef extern from "math.h": 
    double expf(double x) nogil 

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
cdef inline void FIT_initialize_table(FieldInterpolationTable *fit, int nbins,
              np.float64_t *values, np.float64_t bounds1, np.float64_t bounds2,
              int field_id, int weight_field_id, int weight_table_id) nogil:
    fit.bounds[0] = bounds1; fit.bounds[1] = bounds2
    fit.nbins = nbins
    fit.dbin = (fit.bounds[1] - fit.bounds[0])/(fit.nbins-1)
    fit.idbin = 1.0/fit.dbin
    # Better not pull this out from under us, yo
    fit.values = values
    fit.field_id = field_id
    fit.weight_field_id = weight_field_id
    fit.weight_table_id = weight_table_id

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
cdef inline np.float64_t FIT_get_value(FieldInterpolationTable *fit,
                                       np.float64_t dvs[6]) nogil:
    cdef np.float64_t bv, dy, dd, tf, rv
    cdef int bin_id
    if dvs[fit.field_id] >= fit.bounds[1] or dvs[fit.field_id] <= fit.bounds[0]: return 0.0
    bin_id = <int> ((dvs[fit.field_id] - fit.bounds[0]) * fit.idbin)
    bin_id = iclip(bin_id, 0, fit.nbins-2)
    dd = dvs[fit.field_id] - (fit.bounds[0] + bin_id * fit.dbin) # x - x0
    bv = fit.values[bin_id]
    dy = fit.values[bin_id + 1] - bv
    if fit.weight_field_id != -1:
        return dvs[fit.weight_field_id] * (bv + dd*dy*fit.idbin)
    return (bv + dd*dy*fit.idbin)

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
cdef inline void FIT_eval_transfer(np.float64_t dt, np.float64_t *dvs,
                            np.float64_t *rgba, int n_fits,
                            FieldInterpolationTable fits[6],
                            int field_table_ids[6], int grey_opacity) nogil:
    cdef int i, fid, use
    cdef np.float64_t ta, tf, ttot, istorage[6], trgba[6], dot_prod
    for i in range(6): istorage[i] = 0.0
    for i in range(n_fits):
        istorage[i] = FIT_get_value(&fits[i], dvs)
    for i in range(n_fits):
        fid = fits[i].weight_table_id
        if fid != -1: istorage[i] *= istorage[fid]
    for i in range(6):
        trgba[i] = istorage[field_table_ids[i]]

    if grey_opacity == 1:
        ta = fmax(1.0 - dt*trgba[3],0.0)
        for i in range(4):
            rgba[i] = dt*trgba[i] + ta*rgba[i]
    else:
        for i in range(3):
            ta = fmax(1.0-dt*trgba[i], 0.0)
            rgba[i] = dt*trgba[i] + ta*rgba[i]

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
cdef inline void FIT_eval_transfer_with_light(np.float64_t dt, np.float64_t *dvs, 
        np.float64_t *grad, np.float64_t *l_dir, np.float64_t *l_rgba,
        np.float64_t *rgba, int n_fits,
        FieldInterpolationTable fits[6],
        int field_table_ids[6], int grey_opacity) nogil:
    cdef int i, fid, use
    cdef np.float64_t ta, tf, istorage[6], trgba[6], dot_prod
    dot_prod = 0.0
    for i in range(3):
        dot_prod += l_dir[i]*grad[i]
    #dot_prod = fmax(0.0, dot_prod)
    for i in range(6): istorage[i] = 0.0
    for i in range(n_fits):
        istorage[i] = FIT_get_value(&fits[i], dvs)
    for i in range(n_fits):
        fid = fits[i].weight_table_id
        if fid != -1: istorage[i] *= istorage[fid]
    for i in range(6):
        trgba[i] = istorage[field_table_ids[i]]
    if grey_opacity == 1:
        ta = fmax(1.0-dt*(trgba[0] + trgba[1] + trgba[2]), 0.0)
        for i in range(3):
            rgba[i] = (1.-ta)*trgba[i]*(1. + dot_prod*l_rgba[i]) + ta * rgba[i]
    else:
        for i in range(3):
            ta = fmax(1.0-dt*trgba[i], 0.0)
            rgba[i] = (1.-ta)*trgba[i]*(1. + dot_prod*l_rgba[i]) + ta * rgba[i]

