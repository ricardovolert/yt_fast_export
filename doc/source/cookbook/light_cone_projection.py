### THIS RECIPE IS CURRENTLY BROKEN IN YT-3.0
### DO NOT TRUST THIS RECIPE UNTIL THIS LINE IS REMOVED

import yt
from yt.analysis_modules.cosmological_observation.light_cone.light_cone import LightCone

# Create a LightCone object extending from z = 0 to z = 0.1
# with a 600 arcminute field of view and a resolution of
# 60 arcseconds.

# We have already set up the redshift dumps to be
# used for this, so we will not use any of the time
# data dumps.
lc = LightCone('enzo_tiny_cosmology/32Mpc_32.enzo',
               'Enzo', 0., 0.1,
               observer_redshift=0.0,
               field_of_view_in_arcminutes=600.0,
               image_resolution_in_arcseconds=60.0,
               time_data=False)

# Calculate a randomization of the solution.
lc.calculate_light_cone_solution(seed=123456789)

# Choose the field to be projected.
field = 'SZY'

# Set njobs to -1 to have one core work on each projection
# in parallel.  Set save_slice_images to True to see an
# image for each individual slice.
lc.project_light_cone(field, save_stack=False,
                      save_final_image=True,
                      save_slice_images=False,
                      njobs=-1)
