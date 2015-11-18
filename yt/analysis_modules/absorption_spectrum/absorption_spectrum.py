"""
AbsorptionSpectrum class and member functions.



"""

from __future__ import absolute_import

#-----------------------------------------------------------------------------
# Copyright (c) 2013, yt Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from yt.utilities.on_demand_imports import _h5py as h5py
import numpy as np

from .absorption_line import tau_profile

from yt.extern.six import string_types
from yt.convenience import load
from yt.funcs import get_pbar, mylog
from yt.units.yt_array import YTArray, YTQuantity
from yt.utilities.physical_constants import \
    boltzmann_constant_cgs, \
    speed_of_light_cgs
from yt.utilities.on_demand_imports import _astropy
from yt.utilities.parallel_tools.parallel_analysis_interface import \
    _get_comm, \
    parallel_objects, \
    parallel_root_only

pyfits = _astropy.pyfits

class AbsorptionSpectrum(object):
    r"""Create an absorption spectrum object.

    Parameters
    ----------

    lambda_min : float
       lower wavelength bound in angstroms.
    lambda_max : float
       upper wavelength bound in angstroms.
    n_lambda : float
       number of wavelength bins.
    """

    def __init__(self, lambda_min, lambda_max, n_lambda):
        self.n_lambda = n_lambda
        self.tau_field = None
        self.flux_field = None
        self.absorbers_list = None
        self.lambda_bins = YTArray(np.linspace(lambda_min, lambda_max, n_lambda),
                                   "angstrom")
        self.bin_width = YTQuantity((lambda_max - lambda_min) /
                                    float(n_lambda - 1), "angstrom")
        self.line_list = []
        self.continuum_list = []

    def add_line(self, label, field_name, wavelength,
                 f_value, gamma, atomic_mass,
                 label_threshold=None):
        r"""Add an absorption line to the list of lines included in the spectrum.

        Parameters
        ----------

        label : string
           label for the line.
        field_name : string
           field name from ray data for column densities.
        wavelength : float
           line rest wavelength in angstroms.
        f_value  : float
           line f-value.
        gamma : float
           line gamme value.
        atomic_mass : float
           mass of atom in amu.
        """
        self.line_list.append({'label': label, 'field_name': field_name,
                               'wavelength': YTQuantity(wavelength, "angstrom"),
                               'f_value': f_value,
                               'gamma': gamma,
                               'atomic_mass': YTQuantity(atomic_mass, "amu"),
                               'label_threshold': label_threshold})

    def add_continuum(self, label, field_name, wavelength,
                      normalization, index):
        """
        Add a continuum feature that follows a power-law.

        Parameters
        ----------

        label : string
           label for the feature.
        field_name : string
           field name from ray data for column densities.
        wavelength : float
           line rest wavelength in angstroms.
        normalization : float
           the column density normalization.
        index : float
           the power-law index for the wavelength dependence.
        """

        self.continuum_list.append({'label': label, 'field_name': field_name,
                                    'wavelength': wavelength,
                                    'normalization': normalization,
                                    'index': index})

    def make_spectrum(self, input_file, output_file=None,
                      line_list_file=None, output_absorbers_file=None,
                      use_peculiar_velocity=True, 
                      subgrid_resolution=10, njobs="auto"):
        """
        Make spectrum from ray data using the line list.

        Parameters
        ----------

        input_file : string or dataset
           path to input ray data or a loaded ray dataset
        output_file : optional, string
           Option to save a file containing the wavelength, flux, and optical 
           depth fields.  File formats are chosen based on the filename extension.  
           ``.h5`` for hdf5, ``.fits`` for fits, and everything else is ASCII.
           Default: None
        output_absorbers_file : optional, string
           Option to save a text file containing all of the absorbers and 
           corresponding wavelength and redshift information.
           For parallel jobs, combining the lines lists can be slow so it
           is recommended to set to None in such circumstances.
           Default: None
        use_peculiar_velocity : optional, bool
           if True, include line of sight velocity for shifting lines.
           Default: True
        subgrid_resolution : optional, int
           When a line is being added that is unresolved (ie its thermal
           width is less than the spectral bin width), the voigt profile of
           the line is deposited into an array of virtual bins at higher
           resolution.  The optical depth from these virtual bins is integrated
           and then added to the coarser spectral bin.  The subgrid_resolution
           value determines the ratio between the thermal width and the 
           bin width of the virtual bins.  Increasing this value yields smaller
           virtual bins, which increases accuracy, but is more expensive.
           A value of 10 yields accuracy to the 4th significant digit.
           Default: 10
        njobs : optional, int or "auto"
           the number of process groups into which the loop over
           absorption lines will be divided.  If set to -1, each
           absorption line will be deposited by exactly one processor.
           If njobs is set to a value less than the total number of
           available processors (N), then the deposition of an
           individual line will be parallelized over (N / njobs)
           processors.  If set to "auto", it will first try to
           parallelize over the list of lines and only parallelize
           the line deposition if there are more processors than
           lines.  This is the optimal strategy for parallelizing
           spectrum generation.
           Default: "auto"
        """
        if line_list_file is not None:
            mylog.info("'line_list_file' keyword is deprecated. Please use " \
                       "'output_absorbers_file'.")
            output_absorbers_file = line_list_file

        input_fields = ['dl', 'redshift', 'temperature']
        field_units = {"dl": "cm", "redshift": "", "temperature": "K"}
        if use_peculiar_velocity:
            input_fields.append('velocity_los')
            input_fields.append('redshift_eff')
            field_units["velocity_los"] = "cm/s"
            field_units["redshift_eff"] = ""
        for feature in self.line_list + self.continuum_list:
            if not feature['field_name'] in input_fields:
                input_fields.append(feature['field_name'])
                field_units[feature["field_name"]] = "cm**-3"

        if isinstance(input_file, string_types):
            input_ds = load(input_file)
        else:
            input_ds = input_file
        field_data = input_ds.all_data()

        self.tau_field = np.zeros(self.lambda_bins.size)
        self.absorbers_list = []

        if njobs == "auto":
            comm = _get_comm(())
            njobs = min(comm.size, len(self.line_list))

        self._add_lines_to_spectrum(field_data, use_peculiar_velocity,
                                    output_absorbers_file,
                                    subgrid_resolution=subgrid_resolution,
                                    njobs=njobs)
        self._add_continua_to_spectrum(field_data, use_peculiar_velocity)

        self.flux_field = np.exp(-self.tau_field)

        if output_file is None:
            pass
        elif output_file.endswith('.h5'):
            self._write_spectrum_hdf5(output_file)
        elif output_file.endswith('.fits'):
            self._write_spectrum_fits(output_file)
        else:
            self._write_spectrum_ascii(output_file)
        if output_absorbers_file is not None:
            self._write_absorbers_file(output_absorbers_file)

        del field_data
        return (self.lambda_bins, self.flux_field)

    def _add_continua_to_spectrum(self, field_data, use_peculiar_velocity):
        """
        Add continuum features to the spectrum.
        """
        # Only add continuum features down to tau of 1.e-4.
        min_tau = 1.e-3

        for continuum in self.continuum_list:
            column_density = field_data[continuum['field_name']] * field_data['dl']
            # redshift_eff field combines cosmological and velocity redshifts
            if use_peculiar_velocity:
                delta_lambda = continuum['wavelength'] * field_data['redshift_eff']
            else:
                delta_lambda = continuum['wavelength'] * field_data['redshift']
            this_wavelength = delta_lambda + continuum['wavelength']
            right_index = np.digitize(this_wavelength, self.lambda_bins).clip(0, self.n_lambda)
            left_index = np.digitize((this_wavelength *
                                     np.power((min_tau * continuum['normalization'] /
                                               column_density), (1. / continuum['index']))),
                                    self.lambda_bins).clip(0, self.n_lambda)

            valid_continuua = np.where(((column_density /
                                         continuum['normalization']) > min_tau) &
                                       (right_index - left_index > 1))[0]
            pbar = get_pbar("Adding continuum feature - %s [%f A]: " % \
                                (continuum['label'], continuum['wavelength']),
                            valid_continuua.size)
            for i, lixel in enumerate(valid_continuua):
                line_tau = np.power((self.lambda_bins[left_index[lixel]:right_index[lixel]] /
                                     this_wavelength[lixel]), continuum['index']) * \
                                     column_density[lixel] / continuum['normalization']
                self.tau_field[left_index[lixel]:right_index[lixel]] += line_tau
                pbar.update(i)
            pbar.finish()

    def _add_lines_to_spectrum(self, field_data, use_peculiar_velocity,
                               output_absorbers_file, subgrid_resolution=10, 
                               njobs=-1):
        """
        Add the absorption lines to the spectrum.
        """
        # Widen wavelength window until optical depth falls below this tau 
        # value at the ends to assure that the wings of a line have been 
        # fully resolved.
        min_tau = 1e-3

        # step through each ionic transition (e.g. HI, HII, MgII) specified
        # and deposit the lines into the spectrum
        for line in parallel_objects(self.line_list, njobs=njobs):
            column_density = field_data[line['field_name']] * field_data['dl']

            # redshift_eff field combines cosmological and velocity redshifts
            # so delta_lambda gives the offset in angstroms from the rest frame
            # wavelength to the observed wavelength of the transition 
            if use_peculiar_velocity:
                delta_lambda = line['wavelength'] * field_data['redshift_eff']
            else:
                delta_lambda = line['wavelength'] * field_data['redshift']
            # lambda_obs is central wavelength of line after redshift
            lambda_obs = line['wavelength'] + delta_lambda
            # bin index in lambda_bins of central wavelength of line after z
            center_index = np.digitize(lambda_obs, self.lambda_bins)

            # thermal broadening b parameter
            thermal_b =  np.sqrt((2 * boltzmann_constant_cgs *
                                  field_data['temperature']) /
                                  line['atomic_mass'])

            # the actual thermal width of the lines
            thermal_width = (lambda_obs * thermal_b / 
                             speed_of_light_cgs).convert_to_units("angstrom")

            # Sanitize units for faster runtime of the tau_profile machinery.
            lambda_0 = line['wavelength'].d  # line's rest frame; angstroms
            lambda_1 = lambda_obs.d # line's observed frame; angstroms
            cdens = column_density.in_units("cm**-2").d # cm**-2
            thermb = thermal_b.in_cgs().d  # thermal b coefficient; cm / s
            dlambda = delta_lambda.d  # lambda offset; angstroms
            vlos = field_data['velocity_los'].in_units("km/s").d # km/s

            # When we actually deposit the voigt profile, sometimes we will
            # have underresolved lines (ie lines with smaller widths than
            # the spectral bin size).  Here, we create virtual bins small
            # enough in width to well resolve each line, deposit the voigt 
            # profile into them, then numerically integrate their tau values
            # and sum them to redeposit them into the actual spectral bins.

            # virtual bins (vbins) will be:
            # 1) <= the bin_width; assures at least as good as spectral bins
            # 2) <= 1/10th the thermal width; assures resolving voigt profiles
            #   (actually 1/subgrid_resolution value, default is 1/10)
            # 3) a bin width will be divisible by vbin_width times a power of 
            #    10; this will assure we don't get spikes in the deposited
            #    spectra from uneven numbers of vbins per bin
            resolution = thermal_width / self.bin_width 
            vbin_width = self.bin_width / \
                         10**(np.ceil(np.log10(subgrid_resolution/resolution)).clip(0, np.inf))
            vbin_width = vbin_width.in_units('angstrom').d

            # the virtual window into which the line is deposited initially 
            # spans a region of 5 thermal_widths, but this may expand
            n_vbins = np.ceil(5*thermal_width.d/vbin_width)
            vbin_window_width = n_vbins*vbin_width

            if (thermal_width < self.bin_width).any():
                mylog.info(("%d out of %d line components will be " + \
                            "deposited as unresolved lines.") %
                           ((thermal_width < self.bin_width).sum(), 
                            thermal_width.size))

            valid_lines = np.arange(len(thermal_width))
            pbar = get_pbar("Adding line - %s [%f A]: " % \
                            (line['label'], line['wavelength']),
                            thermal_width.size)

            # for a given transition, step through each location in the 
            # observed spectrum where it occurs and deposit a voigt profile
            for i in parallel_objects(valid_lines, njobs=-1):
                my_vbin_window_width = vbin_window_width[i]
                my_n_vbins = n_vbins[i]
                my_vbin_width = vbin_width[i]

                while True:
                    vbins = \
                        np.linspace(lambda_1[i]-my_vbin_window_width/2.,
                                    lambda_1[i]+my_vbin_window_width/2., 
                                    my_n_vbins, endpoint=False)

                    vbins, vtau = \
                        tau_profile(
                            lambda_0, line['f_value'], line['gamma'], thermb[i],
                            cdens[i], delta_lambda=dlambda[i],
                            lambda_bins=vbins)

                    # If tau has not dropped below min tau threshold by the
                    # edges (ie the wings), then widen the wavelength 
                    # window and repeat process. 
                    if (vtau[0] < min_tau and vtau[-1] < min_tau):
                        break
                    my_vbin_window_width *= 2
                    my_n_vbins *= 2

                # identify the extrema of the vbin_window so as to speed
                # up searching over the entire lambda_bins array
                bins_from_center = np.ceil((my_vbin_window_width/2.) / \
                                           self.bin_width.d) + 1
                left_index = (center_index[i] - bins_from_center).clip(0, self.n_lambda)
                right_index = (center_index[i] + bins_from_center).clip(0, self.n_lambda)
                window_width = right_index - left_index

                # run digitize to identify which vbins are deposited into which
                # global lambda bins.
                # shift global lambda bins over by half a bin width; 
                # this has the effect of assuring np.digitize will place 
                # the vbins in the closest bin center.
                binned = np.digitize(vbins, 
                                     self.lambda_bins[left_index:right_index] \
                                     + (0.5 * self.bin_width))

                # numerically integrate the virtual bins to calculate a
                # virtual equivalent width; then sum the virtual equivalent
                # widths and deposit into each spectral bin
                vEW = vtau * my_vbin_width
                EW = [vEW[binned == j].sum() for j in np.arange(window_width)]
                EW = np.array(EW)/self.bin_width.d
                self.tau_field[left_index:right_index] += EW

                # write out absorbers to file if the column density of
                # an absorber is greater than the specified "label_threshold" 
                # of that absorption line
                if output_absorbers_file and \
                   line['label_threshold'] is not None and \
                   cdens[i] >= line['label_threshold']:

                    if use_peculiar_velocity:
                        peculiar_velocity = vlos[i]
                    else:
                        peculiar_velocity = 0.0
                    self.absorbers_list.append({'label': line['label'],
                                                'wavelength': (lambda_0 + dlambda[i]),
                                                'column_density': column_density[i],
                                                'b_thermal': thermal_b[i],
                                                'redshift': field_data['redshift'][i],
                                                'redshift_eff': field_data['redshift_eff'][i],
                                                'v_pec': peculiar_velocity})
                pbar.update(i)
            pbar.finish()

            del column_density, delta_lambda, lambda_obs, center_index, \
                thermal_b, thermal_width, lambda_1, cdens, thermb, dlambda, \
                vlos, resolution, vbin_width, n_vbins, vbin_window_width, \
                valid_lines, vbins, vtau, vEW

        comm = _get_comm(())
        self.tau_field = comm.mpi_allreduce(self.tau_field, op="sum")
        if output_absorbers_file:
            self.absorbers_list = comm.par_combine_object(
                self.absorbers_list, "cat", datatype="list")

    @parallel_root_only
    def _write_absorbers_file(self, filename):
        """
        Write out ASCII list of all substantial absorbers found in spectrum
        """
        if filename is None:
            return
        mylog.info("Writing absorber list: %s." % filename)
        self.absorbers_list.sort(key=lambda obj: obj['wavelength'])
        f = open(filename, 'w')
        f.write('#%-14s %-14s %-12s %-14s %-15s %-9s %-10s\n' %
                ('Wavelength', 'Line', 'N [cm^-2]', 'b [km/s]', 'z_cosmo', \
                 'z_eff', 'v_pec [km/s]'))
        for line in self.absorbers_list:
            f.write('%-14.6f %-14ls %e %e % e % e % e\n' % (line['wavelength'], \
                line['label'], line['column_density'], line['b_thermal'], \
                line['redshift'], line['redshift_eff'], line['v_pec']))
        f.close()

    @parallel_root_only
    def _write_spectrum_ascii(self, filename):
        """
        Write spectrum to an ascii file.
        """
        mylog.info("Writing spectrum to ascii file: %s." % filename)
        f = open(filename, 'w')
        f.write("# wavelength[A] tau flux\n")
        for i in range(self.lambda_bins.size):
            f.write("%e %e %e\n" % (self.lambda_bins[i],
                                    self.tau_field[i], self.flux_field[i]))
        f.close()

    @parallel_root_only
    def _write_spectrum_fits(self, filename):
        """
        Write spectrum to a fits file.
        """
        mylog.info("Writing spectrum to fits file: %s." % filename)
        col1 = pyfits.Column(name='wavelength', format='E', array=self.lambda_bins)
        col2 = pyfits.Column(name='flux', format='E', array=self.flux_field)
        cols = pyfits.ColDefs([col1, col2])
        tbhdu = pyfits.BinTableHDU.from_columns(cols)
        tbhdu.writeto(filename, clobber=True)

    @parallel_root_only
    def _write_spectrum_hdf5(self, filename):
        """
        Write spectrum to an hdf5 file.

        """
        mylog.info("Writing spectrum to hdf5 file: %s." % filename)
        output = h5py.File(filename, 'w')
        output.create_dataset('wavelength', data=self.lambda_bins)
        output.create_dataset('tau', data=self.tau_field)
        output.create_dataset('flux', data=self.flux_field)
        output.close()
