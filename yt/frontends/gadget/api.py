"""
API for Gadget frontend




"""

#-----------------------------------------------------------------------------
# Copyright (c) 2014, yt Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from .data_structures import \
    GadgetDataset, \
    GadgetHDF5Dataset, \
    GadgetFieldInfo

from .io import \
    IOHandlerGadgetBinary, \
    IOHandlerGadgetHDF5

from . import tests
