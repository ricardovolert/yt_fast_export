"""
OWLS-specific fields




"""

#-----------------------------------------------------------------------------
# Copyright (c) 2013, yt Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import numpy as np

from yt.funcs import *
from yt.fields.field_info_container import \
    FieldInfoContainer
from .definitions import \
    gadget_ptypes, \
    ghdf5_ptypes

# Here are helper functions for things like vector fields and so on.

def _get_conv(cf):
    def _convert(data):
        return data.convert(cf)
    return _convert

class SPHFieldInfo(FieldInfoContainer):
    known_other_fields = ()

    known_particle_fields = (
        ("Mass", ("code_mass", ["particle_mass"], None)),
        ("Masses", ("code_mass", ["particle_mass"], None)),
        ("Coordinates", ("code_length", [], None)),
        ("Velocity", ("code_velocity", ["velocity"], None)),
        ("Velocities", ("code_velocity", ["velocity"], None)),
        ("ParticleIDs", ("", ["particle_index"], None)),
        ("InternalEnergy", ("", ["thermal_energy"], None)),
        ("SmoothingLength", ("code_length", ["smoothing_length"], None)),
        ("Density", ("code_mass / code_length**3", ["density"], None)),
        ("Temperature", ("K", ["temperature"], None)),
        ("Epsilon", ("", [], None)),
        ("Metals", ("code_metallicity", ["metallicity"], None)),
        ("Phi", ("", [], None)),
        ("FormationTime", ("code_time", ["creation_time"], None)),
    )
