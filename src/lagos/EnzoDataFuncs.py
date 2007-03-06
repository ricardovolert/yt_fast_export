"""
The data-file handling functions

@author: U{Matthew Turk<http://www.stanford.edu/~mturk/>}
@organization: U{KIPAC<http://www-group.slac.stanford.edu/KIPAC/>}
@contact: U{mturk@slac.stanford.edu<mailto:mturk@slac.stanford.edu>}
"""
from yt.lagos import *

def getFieldsHDF4(self):
    """
    Returns a list of fields associated with the filename
    Should *only* be called as EnzoGridInstance.getFields, never as getFields(object)
    """
    return SD.SD(self.filename).datasets().keys()

def getFieldsHDF5(self):
    """
    Returns a list of fields associated with the filename
    Should *only* be called as EnzoGridInstance.getFields, never as getFields(object)
    """
    fls = []
    for fl in tables.openFile(self.filename).listNodes("/"):
        fls.append(fl.name)
    return fls

def readDataHDF4(self, field):
    """
    Returns after having obtained or generated a field.  Should throw an
    exception.  Should only be called as EnzoGridInstance.readData()
    
    @param field: field to read
    @type field: string
    """
    if self.data.has_key(field):
        return 1
    try:
        self[field] = SD.SD(self.filename).select(field).get()
        self[field].swapaxes(0,2)
    except:
        self.generateField(field)
    return 2

def readAllDataHDF4(self):
    """
    Reads all fields inside an HDF4 file.  Should only be called as
    EnzoGridInstance.readAllData() .
    """
    sets = SD.SD(self.filename).datasets()
    for set in sets:
        self.readDataFast(set)

def readDataHDF5(self, field):
    """
    Reads a field from an HDF5 file.  Should only be called as
    EnzoGridInstance.realData()

    @param field: field to read
    @type field: string
    """
    if self.has_key(field):
        return 1
    f = tables.openFile(self.filename)
    try:
        self[field] = f.getNode("/", field).read()
        self[field].swapaxes(0,2)
    except:
        self.generateField(field)
    #self[field] = ones(self.data[field].shape)
    f.close()
    return 2

def readAllDataHDF5(self):
    """
    Not implemented.  Fix me!
    """
    pass

def readDataSliceHDF5(self, grid, field, sl):
    """
    Reads a slice through the HDF5 data

    @param grid: Grid to slice
    @type grid: L{EnzoGrid<EnzoGrid>}
    @param field: field to get
    @type field: string
    @param sl: region to get
    @type sl: SliceType
    """
    f = tables.openFile(grid.filename)
    ss = f.getNode("/", field)[sl]
    f.close()
    return ss

def readDataSliceHDF4(self, grid, field, sl):
    """
    Reads a slice through the HDF4 data

    @param grid: Grid to slice
    @type grid: L{EnzoGrid<EnzoGrid>}
    @param field: field to get
    @type field: string
    @param sl: region to get
    @type sl: SliceType
    """
    return SD.SD(grid.filename).select(field)[sl]
