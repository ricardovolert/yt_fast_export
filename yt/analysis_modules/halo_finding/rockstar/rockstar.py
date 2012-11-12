"""
Operations to get Rockstar loaded up

Author: Matthew Turk <matthewturk@gmail.com>
Affiliation: Columbia University
Homepage: http://yt.enzotools.org/
License:
  Copyright (C) 2011 Matthew Turk.  All Rights Reserved.

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

from yt.mods import *
from os import environ
from os import mkdir
from os import path
from yt.utilities.parallel_tools.parallel_analysis_interface import \
    ParallelAnalysisInterface, ProcessorPool, Communicator

from yt.analysis_modules.halo_finding.halo_objects import * #Halos & HaloLists
import rockstar_interface
import socket
import time

class DomainDecomposer(ParallelAnalysisInterface):
    def __init__(self, pf, comm):
        ParallelAnalysisInterface.__init__(self, comm=comm)
        self.pf = pf
        self.hierarchy = pf.h
        self.center = (pf.domain_left_edge + pf.domain_right_edge)/2.0

    def decompose(self):
        dd = self.pf.h.all_data()
        check, LE, RE, data_source = self.partition_hierarchy_3d(dd)
        return data_source

class RockstarHaloFinder(ParallelAnalysisInterface):
    def __init__(self, ts, num_readers = 1, num_writers = None, 
            outbase=None,particle_mass=-1.0,dm_type=1,force_res=None):
        r"""Spawns the Rockstar Halo finder, distributes dark matter
        particles and finds halos.

        The halo finder requires dark matter particles of a fixed size.
        Rockstar has three main processes: reader, writer, and the 
        server which coordinates reader/writer processes.

        Parameters
        ----------
        ts   : TimeSeriesData, StaticOutput
            This is the data source containing the DM particles. Because 
            halo IDs may change from one snapshot to the next, the only
            way to keep a consistent halo ID across time is to feed 
            Rockstar a set of snapshots, ie, via TimeSeriesData.
        num_readers: int
            The number of reader can be increased from the default
            of 1 in the event that a single snapshot is split among
            many files. This can help in cases where performance is
            IO-limited. Default is 1.
        num_writers: int
            The number of writers determines the number of processing threads
            as well as the number of threads writing output data.
            The default is set comm.size-num_readers-1.
        outbase: str
            This is where the out*list files that Rockstar makes should be
            placed. Default is 'rockstar_halos'.
        particle_mass: float
            This sets the DM particle mass used in Rockstar.
        dm_type: 1
            In order to exclude stars and other particle types, define
            the dm_type. Default is 1, as Enzo has the DM particle type=1.
        force_res: float
            This parameter specifies the force resolution that Rockstar uses
            in units of Mpc/h.
            If no value is provided, this parameter is automatically set to
            the width of the smallest grid element in the simulation from the
            last data snapshot (i.e. the one where time has evolved the
            longest) in the time series:
            ``pf_last.h.get_smallest_dx() * pf_last['mpch']``.
            
        Returns
        -------
        None

        Examples
        --------
        To use the script below you must run it using MPI:
        mpirun -np 3 python test_rockstar.py --parallel

        test_rockstar.py:

        from mpi4py import MPI
        from yt.analysis_modules.halo_finding.rockstar.api import RockstarHaloFinder
        from yt.mods import *
        import sys

        files = glob.glob('/u/cmoody3/data/a*')
        files.sort()
        ts = TimeSeriesData.from_filenames(files)
        pm = 7.81769027e+11
        rh = RockstarHaloFinder(ts, particle_mass=pm)
        rh.run()
        """
        ParallelAnalysisInterface.__init__(self)
        # No subvolume support
        #we assume that all of the snapshots in the time series
        #use the same domain info as the first snapshots
        if not isinstance(ts,TimeSeriesData):
            ts = TimeSeriesData([ts])
        self.ts = ts
        self.dm_type = dm_type
        tpf = ts.__iter__().next()
        def _particle_count(field, data):
            try:
                return (data["particle_type"]==dm_type).sum()
            except KeyError:
                return np.prod(data["particle_position_x"].shape)
        add_field("particle_count",function=_particle_count, not_in_all=True,
            particle_type=True)
        # Get total_particles in parallel.
        dd = tpf.h.all_data()
        self.total_particles = int(dd.quantities['TotalQuantity']('particle_count')[0])
        self.hierarchy = tpf.h
        self.particle_mass = particle_mass 
        self.center = (tpf.domain_right_edge + tpf.domain_left_edge)/2.0
        data_source = tpf.h.all_data()
        if outbase is None:
            outbase = 'rockstar_halos'
        self.outbase = outbase
        if num_writers is None:
            num_writers = self.comm.size - num_readers -1
        self.num_readers = num_readers
        self.num_writers = num_writers
        self.particle_mass = particle_mass
        if force_res is None:
            self.force_res = ts[-1].h.get_smallest_dx() * pf['mpch']
        else:
            self.force_res = force_res
        self.le = tpf.domain_left_edge
        self.re = tpf.domain_right_edge
        if self.num_readers + self.num_writers + 1 != self.comm.size:
            print '%i reader + %i writers != %i mpi'%\
                    (self.num_readers, self.num_writers, self.comm.size)
            raise RuntimeError
        self.center = (tpf.domain_right_edge + tpf.domain_left_edge)/2.0
        data_source = tpf.h.all_data()
        self.handler = rockstar_interface.RockstarInterface(
                self.ts, data_source)

    def __del__(self):
        self.pool.free_all()

    def _get_hosts(self):
        if self.comm.size == 1 or self.workgroup.name == "server":
            server_address = socket.gethostname()
            sock = socket.socket()
            sock.bind(('', 0))
            port = sock.getsockname()[-1]
            del sock
        else:
            server_address, port = None, None
        self.server_address, self.port = self.comm.mpi_bcast(
            (server_address, port))
        self.port = str(self.port)

    def run(self, block_ratio = 1,**kwargs):
        """
        
        """
        if self.comm.size > 1:
            self.pool = ProcessorPool()
            mylog.debug("Num Writers = %s Num Readers = %s",
                        self.num_writers, self.num_readers)
            self.pool.add_workgroup(1, name = "server")
            self.pool.add_workgroup(self.num_readers, name = "readers")
            self.pool.add_workgroup(self.num_writers, name = "writers")
            for wg in self.pool.workgroups:
                if self.comm.rank in wg.ranks: self.workgroup = wg
        if block_ratio != 1:
            raise NotImplementedError
        self._get_hosts()
        self.handler.setup_rockstar(self.server_address, self.port,
                    len(self.ts), self.total_particles, 
                    self.dm_type,
                    parallel = self.comm.size > 1,
                    num_readers = self.num_readers,
                    num_writers = self.num_writers,
                    writing_port = -1,
                    block_ratio = block_ratio,
                    outbase = self.outbase,
                    force_res=self.force_res,
                    particle_mass = float(self.particle_mass),
                    **kwargs)
        #because rockstar *always* write to exactly the same
        #out_0.list filename we make a directory for it
        #to sit inside so it doesn't get accidentally
        #overwritten 
        if self.workgroup.name == "server":
            if not os.path.exists(self.outbase):
                os.mkdir(self.outbase)
            # Make a record of which dataset corresponds to which set of
            # output files because it will be easy to lose this connection.
            fp = open(self.outbase + '/pfs.txt', 'w')
            fp.write("# pfname\tindex\n")
            for i, pf in enumerate(self.ts):
                pfloc = path.join(path.relpath(pf.fullpath), pf.basename)
                line = "%s\t%d\n" % (pfloc, i)
                fp.write(line)
            fp.close()
        if self.comm.size == 1:
            self.handler.call_rockstar()
        else:
            self.comm.barrier()
            if self.workgroup.name == "server":
                self.handler.start_server()
            elif self.workgroup.name == "readers":
                time.sleep(0.1 + self.workgroup.comm.rank/10.0)
                self.handler.start_client()
            elif self.workgroup.name == "writers":
                time.sleep(0.2 + self.workgroup.comm.rank/10.0)
                self.handler.start_client()
            self.pool.free_all()
        self.comm.barrier()
        self.pool.free_all()
    
    def halo_list(self,file_name='out_0.list'):
        """
        Reads in the out_0.list file and generates RockstarHaloList
        and RockstarHalo objects.
        """
        return RockstarHaloList(self.pf,self.outbase+'/%s'%file_name)
