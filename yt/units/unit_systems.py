"""
Unit system class.

"""

#-----------------------------------------------------------------------------
# Copyright (c) 2013, yt Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from yt.extern.six import string_types
from yt.units import dimensions
from yt.units.unit_object import Unit

unit_system_registry = {}

class UnitSystem(object):
    def __init__(self, name, length_unit, mass_unit, time_unit,
                 temperature_unit, angle_unit, current_mks_unit=None,
                 unit_registry=None):
        self.units_map = {dimensions.length: length_unit,
                          dimensions.mass: mass_unit,
                          dimensions.time: time_unit,
                          dimensions.temperature: temperature_unit,
                          dimensions.angle: angle_unit}
        if current_mks_unit is not None:
            self.units_map[dimensions.current_mks] = current_mks_unit
        self.unit_registry = unit_registry
        self.base_units = self.units_map.copy()
        unit_system_registry[name] = self

    def __getitem__(self, key):
        if isinstance(key, string_types):
            key = getattr(dimensions, key)
        if key not in self.units_map:
            dims = key.expand()
            units = Unit("")
            for factor in dims.as_ordered_factors():
                dim = list(factor.free_symbols)[0]
                u = self.units_map[dim]
                if factor.is_Pow:
                    u = u ** factor.as_base_exp()[1]
                units *= u
            self.units_map[key] = units
        return self.units_map[key]

    def __setitem__(self, key, value):
        if isinstance(key, string_types):
            key = getattr(dimensions, key)
        self.units_map[key] = Unit(value, unit_registry=self.unit_registry)

def create_code_unit_system(ds):
    code_unit_system = UnitSystem(str(ds), "code_length", "code_mass", "code_time",
                                  "code_temperature", "radian")
    code_unit_system[dimensions.velocity] = "code_velocity"

cgs_unit_system = UnitSystem("cgs", "cm", "g", "s", "K", "radian")
cgs_unit_system[dimensions.energy] = "erg"
cgs_unit_system[dimensions.specific_energy] = "erg/g"
cgs_unit_system[dimensions.pressure] = "dyne/cm**2"
cgs_unit_system[dimensions.force] = "dyne"
cgs_unit_system[dimensions.magnetic_field_cgs] = "gauss"

mks_unit_system = UnitSystem("mks", "m", "kg", "s", "K", "radian",
                             current_mks_unit="A")
mks_unit_system[dimensions.energy] = "J"
mks_unit_system[dimensions.specific_energy] = "J/kg"
mks_unit_system[dimensions.pressure] = "Pa"
mks_unit_system[dimensions.force] = "N"
mks_unit_system[dimensions.magnetic_field_mks] = "T"

imperial_unit_system = UnitSystem("imperial", "ft", "lbm", "s", "R", "radian")
imperial_unit_system[dimensions.force] = "lbf"
imperial_unit_system[dimensions.energy] = "ft*lbf"

galactic_unit_system = UnitSystem("galactic", "kpc", "Msun", "Myr", "K", "radian")
galactic_unit_system[dimensions.energy] = "keV"
galactic_unit_system[dimensions.magnetic_field_cgs] = "uG"

geographic_unit_system = UnitSystem("geographic", "mile", "lbm", "s", "K", "deg")
geographic_unit_system[dimensions.pressure] = "atm"
