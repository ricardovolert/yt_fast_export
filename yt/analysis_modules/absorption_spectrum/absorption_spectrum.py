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

import h5py
import numpy as np

from .absorption_line import tau_profile

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
        self.spectrum_line_list = None
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

    def make_spectrum(self, input_file, output_file="spectrum.h5",
                      line_list_file="lines.txt",
                      use_peculiar_velocity=True, njobs="auto"):
        """
        Make spectrum from ray data using the line list.

        Parameters
        ----------

        input_file : string
           path to input ray data.
        output_file : optional, string
           path for output file.  File formats are chosen based on the
           filename extension.  ``.h5`` for hdf5, ``.fits`` for fits,
           and everything else is ASCII.
           Default: "spectrum.h5"
        line_list_file : optional, string
           path to file in which the list of all deposited lines
           will be saved.  If set to None, the line list will not
           be saved.  Note, when running in parallel, combining the
           line lists can be quite slow, so it is recommended to set
           this to None when running in parallel unless you really
           want them.
           Default: "lines.txt"
        use_peculiar_velocity : optional, bool
           if True, include line of sight velocity for shifting lines.
           Default: True
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

        input_fields = ['dl', 'redshift', 'temperature']
        field_units = {"dl": "cm", "redshift": "", "temperature": "K"}
        field_data = {}
        if use_peculiar_velocity:
            input_fields.append('velocity_los')
            field_units["velocity_los"] = "cm/s"
        for feature in self.line_list + self.continuum_list:
            if not feature['field_name'] in input_fields:
                input_fields.append(feature['field_name'])
                field_units[feature["field_name"]] = "cm**-3"

        input = h5py.File(input_file, 'r')
        for field in input_fields:
            field_data[field] = YTArray(input[field].value, field_units[field])
        input.close()

        self.tau_field = np.zeros(self.lambda_bins.size)
        self.spectrum_line_list = []

        if njobs == "auto":
            comm = _get_comm(())
            njobs = min(comm.size, len(self.line_list))

        self._add_lines_to_spectrum(field_data, use_peculiar_velocity,
                                    line_list_file is not None, njobs=njobs)
        self._add_continua_to_spectrum(field_data, use_peculiar_velocity)

        self.flux_field = np.exp(-self.tau_field)

        if output_file.endswith('.h5'):
            self._write_spectrum_hdf5(output_file)
        elif output_file.endswith('.fits'):
            self._write_spectrum_fits(output_file)
        else:
            self._write_spectrum_ascii(output_file)
        if line_list_file is not None:
            self._write_spectrum_line_list(line_list_file)

        del field_data
        return (self.lambda_bins, self.flux_field)

    def _add_continua_to_spectrum(self, field_data, use_peculiar_velocity):
        """
        Add continuum features to the spectrum.
        """
        # Only add continuum features down to tau of 1.e-4.
        tau_min = 1.e-4

        for continuum in self.continuum_list:
            column_density = field_data[continuum['field_name']] * field_data['dl']
            delta_lambda = continuum['wavelength'] * field_data['redshift']
            if use_peculiar_velocity:
                # include factor of (1 + z) because our velocity is in proper frame.
                delta_lambda += continuum['wavelength'] * (1 + field_data['redshift']) * \
                    field_data['velocity_los'] / speed_of_light_cgs
            this_wavelength = delta_lambda + continuum['wavelength']
            right_index = np.digitize(this_wavelength, self.lambda_bins).clip(0, self.n_lambda)
            left_index = np.digitize((this_wavelength *
                                     np.power((tau_min * continuum['normalization'] /
                                               column_density), (1. / continuum['index']))),
                                    self.lambda_bins).clip(0, self.n_lambda)

            valid_continuua = np.where(((column_density /
                                         continuum['normalization']) > tau_min) &
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
                               save_line_list, njobs=-1):
        """
        Add the absorption lines to the spectrum.
        """
        # Only make voigt profile for slice of spectrum that is 10 times the line width.
        spectrum_bin_ratio = 5
        # Widen wavelength window until optical depth reaches a max value at the ends.
        max_tau = 0.001

        for line in parallel_objects(self.line_list, njobs=njobs):
            column_density = field_data[line['field_name']] * field_data['dl']
            delta_lambda = line['wavelength'] * field_data['redshift']
            if use_peculiar_velocity:
                # include factor of (1 + z) because our velocity is in proper frame.
                delta_lambda += line['wavelength'] * (1 + field_data['redshift']) * \
                    field_data['velocity_los'] / speed_of_light_cgs
            thermal_b =  np.sqrt((2 * boltzmann_constant_cgs *
                                  field_data['temperature']) /
                                  line['atomic_mass'])
            center_bins = np.digitize((delta_lambda + line['wavelength']),
                                      self.lambda_bins)

            # ratio of line width to bin width
            width_ratio = ((line['wavelength'] + delta_lambda) * \
                           thermal_b / speed_of_light_cgs / self.bin_width).in_units("").d

            if (width_ratio < 1.0).any():
                mylog.warn(("%d out of %d line components are unresolved, " +
                            "consider increasing spectral resolution.") %
                           ((width_ratio < 1.0).sum(), width_ratio.size))

            # do voigt profiles for a subset of the full spectrum
            left_index  = (center_bins -
                           spectrum_bin_ratio * width_ratio).astype(int).clip(0, self.n_lambda)
            right_index = (center_bins +
                           spectrum_bin_ratio * width_ratio).astype(int).clip(0, self.n_lambda)

            # loop over all lines wider than the bin width
            valid_lines = np.where((width_ratio >= 1.0) &
                                   (right_index - left_index > 1))[0]
            pbar = get_pbar("Adding line - %s [%f A]: " % (line['label'], line['wavelength']),
                            valid_lines.size)

            # Sanitize units here
            column_density.convert_to_units("cm ** -2")
            lbins = self.lambda_bins.d  # Angstroms
            lambda_0 = line['wavelength'].d  # Angstroms
            v_doppler = thermal_b.in_cgs().d  # cm / s
            cdens = column_density.d
            dlambda = delta_lambda.d  # Angstroms
            vlos = field_data['velocity_los'].in_units("km/s").d

            for i, lixel in parallel_objects(enumerate(valid_lines), njobs=-1):
                my_bin_ratio = spectrum_bin_ratio

                while True:
                    lambda_bins, line_tau = \
                        tau_profile(
                            lambda_0, line['f_value'], line['gamma'], v_doppler[lixel],
                            cdens[lixel], delta_lambda=dlambda[lixel],
                            lambda_bins=lbins[left_index[lixel]:right_index[lixel]])

                    # Widen wavelength window until optical depth reaches a max value at the ends.
                    if (line_tau[0] < max_tau and line_tau[-1] < max_tau) or \
                      (left_index[lixel] <= 0 and right_index[lixel] >= self.n_lambda):
                        break
                    my_bin_ratio *= 2
                    left_index[lixel]  = (center_bins[lixel] -
                                          my_bin_ratio *
                                          width_ratio[lixel]).astype(int).clip(0, self.n_lambda)
                    right_index[lixel] = (center_bins[lixel] +
                                          my_bin_ratio *
                                          width_ratio[lixel]).astype(int).clip(0, self.n_lambda)

                self.tau_field[left_index[lixel]:right_index[lixel]] += line_tau
                if save_line_list and line['label_threshold'] is not None and \
                        cdens[lixel] >= line['label_threshold']:
                    if use_peculiar_velocity:
                        peculiar_velocity = vlos[lixel]
                    else:
                        peculiar_velocity = 0.0
                    self.spectrum_line_list.append({'label': line['label'],
                                                    'wavelength': (lambda_0 + dlambda[lixel]),
                                                    'column_density': column_density[lixel],
                                                    'b_thermal': thermal_b[lixel],
                                                    'redshift': field_data['redshift'][lixel],
                                                    'v_pec': peculiar_velocity})
                pbar.update(i)
            pbar.finish()

            del column_density, delta_lambda, thermal_b, \
                center_bins, width_ratio, left_index, right_index

        comm = _get_comm(())
        self.tau_field = comm.mpi_allreduce(self.tau_field, op="sum")
        if save_line_list:
            self.spectrum_line_list = comm.par_combine_object(
                self.spectrum_line_list, "cat", datatype="list")

    @parallel_root_only
    def _write_spectrum_line_list(self, filename):
        """
        Write out list of spectral lines.
        """
        mylog.info("Writing spectral line list: %s." % filename)
        self.spectrum_line_list.sort(key=lambda obj: obj['wavelength'])
        f = open(filename, 'w')
        f.write('#%-14s %-14s %-12s %-12s %-12s %-12s\n' %
                ('Wavelength', 'Line', 'N [cm^-2]', 'b [km/s]', 'z', 'v_pec [km/s]'))
        for line in self.spectrum_line_list:
            f.write('%-14.6f %-14ls %e %e %e %e.\n' % (line['wavelength'], line['label'],
                                                line['column_density'], line['b_thermal'],
                                                line['redshift'], line['v_pec']))
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
