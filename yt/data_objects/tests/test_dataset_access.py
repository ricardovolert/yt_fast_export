from yt.testing import fake_amr_ds, assert_equal

# This will test the "dataset access" method.

def test_region_from_d():
    ds = fake_amr_ds(fields=["density"])
    # We'll do a couple here

    # First, no string units
    reg1 = ds.d[0.2:0.3,0.4:0.6,:]
    reg2 = ds.region([0.25, 0.5, 0.5], [0.2, 0.4, 0.0], [0.3, 0.6, 1.0])
    yield assert_equal, reg1["density"], reg2["density"]

    # Now, string units in some -- 1.0 == cm
    reg1 = ds.d[(0.1, 'cm'):(0.5, 'cm'), :, (0.25, 'cm'): (0.35, 'cm')]
    reg2 = ds.region([0.3, 0.5, 0.3], [0.1, 0.0, 0.25], [0.5, 1.0, 0.35])
    yield assert_equal, reg1["density"], reg2["density"]

    # And, lots of : usage!
    reg1 = ds.d[:, :, :]
    reg2 = ds.all_data()
    yield assert_equal, reg1["density"], reg2["density"]

def test_accessing_all_data():
    # This will test first that we can access all_data, and next that we can
    # access it multiple times and get the *same object*.
    ds = fake_amr_ds(fields=["density"])
    dd = ds.all_data()
    yield assert_equal, ds.d["density"], dd["density"]
    # Now let's assert that it's the same object
    rho = ds.d["density"]
    rho *= 2.0
    yield assert_equal, dd["density"]*2.0, ds.d["density"]
    yield assert_equal, dd["gas", "density"]*2.0, ds.d["gas", "density"]
