"""
ART frontend tests using D9p a=0.500




"""

#-----------------------------------------------------------------------------
# Copyright (c) 2013, yt Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from yt.testing import \
    requires_file, \
    assert_equal, \
    units_override_check
from yt.utilities.answer_testing.framework import \
    requires_ds, \
    big_patch_amr, \
    PixelizedProjectionValuesTest, \
    data_dir_load
from yt.frontends.art.api import ARTDataset

_fields = ("density", "temperature", "particle_mass", ("all", "particle_position_x"))

d9p = "D9p_500/10MpcBox_HartGal_csf_a0.500.d"

@requires_ds(d9p, big_data=True)
def test_d9p():
    ds = data_dir_load(d9p)
    yield assert_equal, str(ds), "10MpcBox_HartGal_csf_a0.500.d"
    for test in big_patch_amr(d9p, _fields):
        test_d9p.__name__ = test.description
        yield test
    dso = [None, ("sphere", ("max", (0.1, 'unitary')))]
    for field in _fields:
        for axis in [0, 1, 2]:
            for dobj_name in dso:
                for weight_field in [None, "density"]:
                    yield PixelizedProjectionValuesTest(
                        d9p, axis, field, weight_field,
                        dobj_name)


    ad = ds.all_data()
    ANANStars = 6255
    yield assert_equal, ad[('stars','particle_type')].size, ANANStars
    yield assert_equal, ad[('specie4', 'particle_type')].size, ANANStars
    ANANDM = 2833405
    yield assert_equal, ad[('darkmatter','particle_type')].size, ANANDM
    yield assert_equal, ad[('darkmatter','particle_type')].size, ANANDM
    yield assert_equal, ad[('specie0', 'particle_type')].size + \
        ad[('specie1', 'particle_type')].size + \
        ad[('specie2', 'particle_type')].size + \
        ad[('specie3', 'particle_type')].size, ANANDM

    ANABoxSize = yt.units.yt_array.YTQuantity(7.1442196564,'Mpc')
    ANAVolume = yt.units.yt_array.YTQuantity(364.640074656,'Mpc**3')
    Volume = 1
    for i in ds.domain_width.in_units('Mpc'):
        yield assert_almost_equal, i, ANABoxSize
        Volume *= i
    yield assert_almost_equal, Volume, ANAVolume

    ANANCells = 4087490
    yield assert_equal, ds.ncell, ANANCells

    ANATotDMMass = yt.units.yt_array.YTQuantity(1.01191786811e+14,'Msun')
    ANATotStarMass = yt.units.yt_array.YTQuantity(1.776251e+6,'Msun')
    ANATotGasMass = yt.units.yt_array.YTQuantity(1.781994e+13,'Msun')
    yield assert_almost_equal, ad[('darkmatter','particle_mass')].sum()\
        .in_units('Msun'), ANATotDMMass
    yield assert_almost_equal, ad[('stars','particle_mass')].sum()\
        .in_units('Msun'), ANATotStarMass
    yield assert_almost_equal, ad[('gas','cell_mass')].sum()\
        .in_units('Msun'), ANATotGasMass



@requires_file(d9p)
def test_ARTDataset():
    assert isinstance(data_dir_load(d9p), ARTDataset)

@requires_file(d9p)
def test_units_override():
    for test in units_override_check(d9p):
        yield test

