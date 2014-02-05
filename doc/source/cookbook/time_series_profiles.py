from yt.mods import *

# Create a time-series object.
es = simulation("enzo_tiny_cosmology/32Mpc_32.enzo", "Enzo")
es.get_time_series(redshifts=[5, 4, 3, 2, 1, 0])

# Lists to hold profiles, labels, and plot specifications.
profiles = []
labels = []
plot_specs = []

# Loop over each dataset in the time-series.
for pf in es:
    # Create a data container to hold the whole dataset.
    ad = pf.h.all_data()
    # Create a 1d profile of density vs. temperature.
    profiles.append(create_profile(ad, ["Density"], 
                                   fields=["Temperature"]))
    # Add labels and linestyles.
    labels.append("z = %.2f" % pf.current_redshift)
    plot_specs.append(dict(linewidth=2, alpha=0.7))

# Create the profile plot from the list of profiles.
plot = ProfilePlot.from_profiles(profiles, labels=labels,
                                 plot_specs=plot_specs)
# Save the image.
plot.save()