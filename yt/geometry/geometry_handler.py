"""
AMR hierarchy container class

Author: Matthew Turk <matthewturk@gmail.com>
Affiliation: KIPAC/SLAC/Stanford
Homepage: http://yt-project.org/
License:
  Copyright (C) 2007-2011 Matthew Turk.  All Rights Reserved.

  This file is part of yt.

  yt is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import cPickle
import weakref
import h5py
from exceptions import IOError, TypeError
from types import ClassType

from yt.funcs import *
from yt.config import ytcfg
from yt.data_objects.data_containers import \
    data_object_registry
from yt.data_objects.field_info_container import \
    NullFunc
from yt.utilities.io_handler import io_registry
from yt.utilities.logger import ytLogger as mylog
from yt.utilities.parallel_tools.parallel_analysis_interface import \
    ParallelAnalysisInterface, parallel_splitter

class GeometryHandler(ParallelAnalysisInterface):

    def __init__(self, pf, data_style):
        ParallelAnalysisInterface.__init__(self)
        self.parameter_file = weakref.proxy(pf)
        self.pf = self.parameter_file

        self._initialize_state_variables()

        mylog.debug("Initializing data storage.")
        self._initialize_data_storage()

        # Must be defined in subclass
        mylog.debug("Setting up classes.")
        self._setup_classes()

        mylog.debug("Setting up domain geometry.")
        self._setup_geometry()

        mylog.debug("Initializing data grid data IO")
        self._setup_data_io()

        mylog.debug("Detecting fields.")
        self._detect_fields()

        mylog.debug("Adding unknown detected fields")
        self._setup_unknown_fields()

        mylog.debug("Setting up derived fields")
        self._setup_derived_fields()

    def __del__(self):
        if self._data_file is not None:
            self._data_file.close()

    def _initialize_state_variables(self):
        self._parallel_locking = False
        self._data_file = None
        self._data_mode = None
        self._max_locations = {}
        self.num_grids = None

    def _setup_classes(self, dd):
        # Called by subclass
        self.object_types = []
        self.objects = []
        self.plots = []
        for name, cls in sorted(data_object_registry.items()):
            cname = cls.__name__
            if cname.endswith("Base"): cname = cname[:-4]
            self._add_object_class(name, cname, cls, dd)
        if self.pf.refine_by != 2 and hasattr(self, 'proj') and \
            hasattr(self, 'overlap_proj'):
            mylog.warning("Refine by something other than two: reverting to"
                        + " overlap_proj")
            self.proj = self.overlap_proj
        self.object_types.sort()

    def _setup_unknown_fields(self):
        known_fields = self.parameter_file._fieldinfo_known
        for field in self.field_list:
            # By allowing a backup, we don't mandate that it's found in our
            # current field info.  This means we'll instead simply override
            # it.
            ff = self.parameter_file.field_info.pop(field, None)
            if field not in known_fields:
                rootloginfo("Adding unknown field %s to list of fields", field)
                cf = None
                if self.parameter_file.has_key(field):
                    def external_wrapper(f):
                        def _convert_function(data):
                            return data.convert(f)
                        return _convert_function
                    cf = external_wrapper(field)
                # Note that we call add_field on the field_info directly.  This
                # will allow the same field detection mechanism to work for 1D, 2D
                # and 3D fields.
                self.pf.field_info.add_field(
                        field, NullFunc,
                        convert_function=cf, take_log=False, units=r"Unknown")
            else:
                mylog.debug("Adding known field %s to list of fields", field)
                self.parameter_file.field_info[field] = known_fields[field]

    # Now all the object related stuff
    def all_data(self, find_max=False):
        pf = self.parameter_file
        if find_max: c = self.find_max("Density")[1]
        else: c = (pf.domain_right_edge + pf.domain_left_edge)/2.0
        return self.region(c,
            pf.domain_left_edge, pf.domain_right_edge)

    def _initialize_data_storage(self):
        if not ytcfg.getboolean('yt','serialize'): return
        fn = self.pf.storage_filename
        if fn is None:
            if os.path.isfile(os.path.join(self.directory,
                                "%s.yt" % self.pf.unique_identifier)):
                fn = os.path.join(self.directory,"%s.yt" % self.pf.unique_identifier)
            else:
                fn = os.path.join(self.directory,
                        "%s.yt" % self.parameter_file.basename)
        dir_to_check = os.path.dirname(fn)
        # We have four options:
        #    Writeable, does not exist      : create, open as append
        #    Writeable, does exist          : open as append
        #    Not writeable, does not exist  : do not attempt to open
        #    Not writeable, does exist      : open as read-only
        exists = os.path.isfile(fn)
        if not exists:
            writeable = os.access(dir_to_check, os.W_OK)
        else:
            writeable = os.access(fn, os.W_OK)
        writeable = writeable and not ytcfg.getboolean('yt','onlydeserialize')
        # We now have our conditional stuff
        self.comm.barrier()
        if not writeable and not exists: return
        if writeable:
            try:
                if not exists: self.__create_data_file(fn)
                self._data_mode = 'a'
            except IOError:
                self._data_mode = None
                return
        else:
            self._data_mode = 'r'

        self.__data_filename = fn
        self._data_file = h5py.File(fn, self._data_mode)

    def __create_data_file(self, fn):
        # Note that this used to be parallel_root_only; it no longer is,
        # because we have better logic to decide who owns the file.
        f = h5py.File(fn, 'a')
        f.close()

    def _setup_data_io(self):
        self.io = io_registry[self.data_style]()

    def _save_data(self, array, node, name, set_attr=None, force=False, passthrough = False):
        """
        Arbitrary numpy data will be saved to the region in the datafile
        described by *node* and *name*.  If data file does not exist, it throws
        no error and simply does not save.
        """

        if self._data_mode != 'a': return
        try:
            node_loc = self._data_file[node]
            if name in node_loc and force:
                mylog.info("Overwriting node %s/%s", node, name)
                del self._data_file[node][name]
            elif name in node_loc and passthrough:
                return
        except:
            pass
        myGroup = self._data_file['/']
        for q in node.split('/'):
            if q: myGroup = myGroup.require_group(q)
        arr = myGroup.create_dataset(name,data=array)
        if set_attr is not None:
            for i, j in set_attr.items(): arr.attrs[i] = j
        self._data_file.flush()

    def _reload_data_file(self, *args, **kwargs):
        if self._data_file is None: return
        self._data_file.close()
        del self._data_file
        self._data_file = h5py.File(self.__data_filename, self._data_mode)

    save_data = parallel_splitter(_save_data, _reload_data_file)

    def _get_data_reader_dict(self):
        dd = { 'pf' : self.parameter_file, # Already weak
               'hierarchy': weakref.proxy(self) }
        return dd

    def _reset_save_data(self,round_robin=False):
        if round_robin:
            self.save_data = self._save_data
        else:
            self.save_data = parallel_splitter(self._save_data, self._reload_data_file)

    def save_object(self, obj, name):
        """
        Save an object (*obj*) to the data_file using the Pickle protocol,
        under the name *name* on the node /Objects.
        """
        s = cPickle.dumps(obj, protocol=-1)
        self.save_data(s, "/Objects", name, force = True)

    def load_object(self, name):
        """
        Load and return and object from the data_file using the Pickle protocol,
        under the name *name* on the node /Objects.
        """
        obj = self.get_data("/Objects", name)
        if obj is None:
            return
        obj = cPickle.loads(obj.value)
        if iterable(obj) and len(obj) == 2:
            obj = obj[1] # Just the object, not the pf
        if hasattr(obj, '_fix_pickle'): obj._fix_pickle()
        return obj

    def get_data(self, node, name):
        """
        Return the dataset with a given *name* located at *node* in the
        datafile.
        """
        if self._data_file == None:
            return None
        if node[0] != "/": node = "/%s" % node

        myGroup = self._data_file['/']
        for group in node.split('/'):
            if group:
                if group not in myGroup:
                    return None
                myGroup = myGroup[group]
        if name not in myGroup:
            return None

        full_name = "%s/%s" % (node, name)
        try:
            return self._data_file[full_name][:]
        except TypeError:
            return self._data_file[full_name]

    def _close_data_file(self):
        if self._data_file:
            self._data_file.close()
            del self._data_file
            self._data_file = None

    def _add_object_class(self, name, class_name, base, dd):
        self.object_types.append(name)
        obj = type(class_name, (base,), dd)
        setattr(self, name, obj)
