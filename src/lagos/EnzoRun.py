#
# raven:
#   A module for dealing with Enzo data
#   Currently isolated fromall HippoDraw classes
#
# Written by: Matthew Turk (mturk@stanford.edu) Nov 2006
# Modified:
#

from yt.lagos import *
from EnzoHierarchy import *

class EnzoRun:
    """
    A class that is used to hold the information about an entire Enzo
    Simulation.  This includes all of the datadumps, the parameter file,
    and possibly even the initial conditions.
    """
    def __init__(self, metaData, outputs=[]):
        """
        Returns an instance of EnzoRun.

        Arguments:
            metaData -- string, describing the run as a whole.

        We're going to try to avoid setting too many of the parameters here,
        as many will be changed on and off.  However, we can definitely set all
        of the parameters that are fixed from the initial conditions -- things
        like root grid conditions, problem type, and so on.  While these *may*
        change during the run (for instance, changing to SN problem type) they
        won't do so without quite a bit of effort on the part of the user, and
        we thus don't quite have to care about them too much.

        This is primarily a storage container.  If we open it up, and add to
        it all of our datadumps, we can snag lots of fun information from them
        all.
        """
        self.metaData = metaData
        self.outputs = obj.array(outputs)       # Object array of EnzoHierarchies
        self.timesteps = array(shape=self.outputs.shape, type=Float64) # Timesteps

    def sortOutputs(self):
        """
        Sorts outputs, solely by the time at which they were created.

        Note that this may not be what we want -- we may actually want the time
        in the simulation at which they were dumped.
        """
        order = argsort(self.timesteps)
        self.outputs = self.outputs[order]
        self.timesteps = self.timesteps[order]

    def addOutput(self, hierarchy):
        """
        Add an output.  Also, sorts.

        Arguments:
            hierarchy -- either a single hierarchy or a list of hierarchies
                         (EnzoHierarchy objects)
        """
        if not isinstance(hierarchy, types.ListType):
            hierarchy = [hierarchy]
        # Our arrays are both one-d, so we'll just extend them
        t = []
        for h in hierarchy:
            t.append(h["InitialTime"])
        self.outputs = obj.array(self.outputs.tolist() + hierarchy)
        self.timesteps=array(self.timesteps.tolist() + t,type=Float64)
        self.sortOutputs()

    def addOutputByFilename(self, filename, hdf_version=4):
        """
        Feed it a list of parameter files, andi t will add 'em all

        Arguments:
            filename -- either a single filename or a list of filenames
        """
        if not isinstance(filename, types.ListType):
            filename = [filename]
        k = []
        for fn in filename:
            mylog.info("Adding %s to EnzoRun", fn)
            k.append(EnzoHierarchy(fn, hdf_version=hdf_version))
        self.addOutput(k)

    def getCommandLine(self):
        return "./enzo_red_i9_r16"

    def runFunction(self, func, args, fmt_string = None):
        """
        Here we can call runFunction, feeding it a function and some arguments.

        The function will be called with every EnzoHierarchy as the first
        argument, and the *args as the rest of the arguments.

        Arguments:
            func -- function handler to be called for every EnzoHierarchy
                    note that it will be called as such:
                    func(EnzoHierarchy, [fmt_string % index], *args)
            args -- a list of arguments to pass in
            fmt_string -- this is an optional argument, which will be %'d
                          against the index of the parameter file.  Note that
                          it is only %'d against the *index*, so even if the
                          thing is called DataDump1042, if it's the first one, it'll get 0.
        """
        if not isinstance(args, types.ListType):
            args = [args]
        for i in range(self.outputs.shape[0]):
            a = [self.outputs[i]]
            if fmt_string != None:
                s = fmt_string % i
                a += [s]
            a += args
            mylog.info("Calling %s on %s", func.func_name, a[0].parameterFilename)
            func(*a)
