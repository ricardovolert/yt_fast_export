"""

"""
cimport cython
import numpy as np
cimport numpy as np
import sys 

from yt.geometry.selection_routines cimport SelectorObject
from libc.stdint cimport int32_t, int64_t
from libc.stdlib cimport malloc, free
import  data_structures  

cdef extern from "stdlib.h":
    void *alloca(int)

cdef extern from "artio.h":
    ctypedef struct artio_fileset_handle "artio_fileset" :
        pass
    ctypedef struct artio_selection "artio_selection" :
        pass
    ctypedef struct artio_context :
        pass
    cdef extern artio_context *artio_context_global 

    # open modes
    cdef int ARTIO_OPEN_HEADER "ARTIO_OPEN_HEADER"
    cdef int ARTIO_OPEN_GRID "ARTIO_OPEN_GRID"
    cdef int ARTIO_OPEN_PARTICLES "ARTIO_OPEN_PARTICLES" 

    # parameter constants
    cdef int ARTIO_TYPE_STRING "ARTIO_TYPE_STRING"
    cdef int ARTIO_TYPE_CHAR "ARTIO_TYPE_CHAR"
    cdef int ARTIO_TYPE_INT "ARTIO_TYPE_INT"
    cdef int ARTIO_TYPE_FLOAT "ARTIO_TYPE_FLOAT"
    cdef int ARTIO_TYPE_DOUBLE "ARTIO_TYPE_DOUBLE"
    cdef int ARTIO_TYPE_LONG "ARTIO_TYPE_LONG"

    cdef int ARTIO_MAX_STRING_LENGTH "ARTIO_MAX_STRING_LENGTH"

    cdef int ARTIO_PARAMETER_EXHAUSTED "ARTIO_PARAMETER_EXHAUSTED"

    # grid read options
    cdef int ARTIO_READ_LEAFS "ARTIO_READ_LEAFS"
    cdef int ARTIO_READ_REFINED "ARTIO_READ_REFINED"
    cdef int ARTIO_READ_ALL "ARTIO_READ_ALL"
    cdef int ARTIO_READ_REFINED_NOT_ROOT "ARTIO_READ_REFINED_NOT_ROOT"
    cdef int ARTIO_RETURN_CELLS "ARTIO_RETURN_CELLS"
    cdef int ARTIO_RETURN_OCTS "ARTIO_RETURN_OCTS"

    # errors
    cdef int ARTIO_SUCCESS "ARTIO_SUCCESS"
    cdef int ARTIO_ERR_MEMORY_ALLOCATION "ARTIO_ERR_MEMORY_ALLOCATION"

    artio_fileset_handle *artio_fileset_open(char *file_prefix, int type, artio_context *context )
    int artio_fileset_close( artio_fileset_handle *handle )
    int artio_fileset_open_particle( artio_fileset_handle *handle )
    int artio_fileset_open_grid(artio_fileset_handle *handle) 
    int artio_fileset_close_grid(artio_fileset_handle *handle) 

    # selection functions
    artio_selection *artio_selection_allocate( artio_fileset *handle )
    int artio_selection_add_root_cell( artio_selection *selection, int coords[3] )
    int artio_selection_destroy( artio_selection *selection )
    int artio_selection_iterator( artio_selection *selection,
            int64_t max_range_size, int64_t *start, int64_t *end )
    int64_t artio_selection_size( artio_selection *selection )

    # parameter functions
    int artio_parameter_iterate( artio_fileset_handle *handle, char *key, int *type, int *length )
    int artio_parameter_get_int_array(artio_fileset_handle *handle, char * key, int length, int32_t *values)
    int artio_parameter_get_float_array(artio_fileset_handle *handle, char * key, int length, float *values)
    int artio_parameter_get_long_array(artio_fileset_handle *handle, char * key, int length, int64_t *values)
    int artio_parameter_get_double_array(artio_fileset_handle *handle, char * key, int length, double *values)
    int artio_parameter_get_string_array(artio_fileset_handle *handle, char * key, int length, char **values )

    # grid functions
    int artio_grid_cache_sfc_range(artio_fileset_handle *handle, int64_t start, int64_t end)
    int artio_grid_clear_sfc_cache( artio_fileset_handle *handle ) 

    int artio_grid_read_root_cell_begin(artio_fileset_handle *handle, int64_t sfc, 
        double *pos, float *variables,
        int *num_tree_levels, int *num_octs_per_level)
    int artio_grid_read_root_cell_end(artio_fileset_handle *handle)

    int artio_grid_read_level_begin(artio_fileset_handle *handle, int level )
    int artio_grid_read_level_end(artio_fileset_handle *handle)

    int artio_grid_read_oct(artio_fileset_handle *handle, double *pos, 
            float *variables, int *refined)

    int artio_grid_count_octs_in_sfc_range(artio_fileset_handle *handle,
            int64_t start, int64_t end, int64_t *num_octs)

    #particle functions
    int artio_fileset_open_particles(artio_fileset_handle *handle)
    int artio_particle_read_root_cell_begin(artio_fileset_handle *handle, int64_t sfc,
                        int * num_particle_per_species)
    int artio_particle_read_root_cell_end(artio_fileset_handle *handle)
    int artio_particle_read_particle(artio_fileset_handle *handle, int64_t *pid, int *subspecies,
                        double *primary_variables, float *secondary_variables)
    int artio_particle_cache_sfc_range(artio_fileset_handle *handle, int64_t sfc_start, int64_t sfc_end)
    int artio_particle_read_species_begin(artio_fileset_handle *handle, int species)
    int artio_particle_read_species_end(artio_fileset_handle *handle) 
   

cdef check_artio_status(int status, char *fname="[unknown]"):
    if status!=ARTIO_SUCCESS :
        callername = sys._getframe().f_code.co_name
        nline = sys._getframe().f_lineno
        print 'failure with status', status, 'in function',fname,'from caller', callername, nline 
        sys.exit(1)


cdef class artio_fileset :
    cdef public object parameters 
    cdef artio_fileset_handle *handle
    cdef int64_t num_root_cells
    cdef int64_t sfc_min, sfc_max
    cdef public int num_grid

    # grid attributes
    cdef int min_level, max_level
    cdef int num_grid_variables

    def __init__(self, char *file_prefix) :
        cdef int artio_type = ARTIO_OPEN_HEADER
        cdef int64_t num_root

        self.handle = artio_fileset_open( file_prefix, artio_type, artio_context_global ) 
        self.read_parameters()
        print 'print parameters in caller.pyx',self.parameters
        print 'done reading header parameters'

        self.num_root_cells = self.parameters['num_root_cells'][0]
        self.num_grid = 1
        num_root = self.num_root_cells
        while num_root > 1 :
            self.num_grid <<= 1
            num_root >>= 3

        #kln - add particle detection code
        status = artio_fileset_open_particles( self.handle )
        check_artio_status(status)
 
        # dhr - add grid detection code 
        status = artio_fileset_open_grid( self.handle )
        check_artio_status(status)

        self.min_level = 0
        self.max_level = self.parameters['grid_max_level'][0]

        # note the root level method may force chunking to be done on 0-level ytocts 
        self.sfc_min = 0
        self.sfc_max = self.parameters['grid_file_sfc_index'][1]-1
        self.num_grid_variables = self.parameters['num_grid_variables'][0]

    def read_parameters(self) :
        cdef char key[64]
        cdef int type
        cdef int length
        cdef char ** char_values
        cdef int32_t *int_values
        cdef int64_t *long_values
        cdef float *float_values
        cdef double *double_values

        self.parameters = {}

        while artio_parameter_iterate( self.handle, key, &type, &length ) == ARTIO_SUCCESS :
            if type == ARTIO_TYPE_STRING :
                char_values = <char **>malloc(length*sizeof(char *))
                for i in range(length) :
                    char_values[i] = <char *>malloc( ARTIO_MAX_STRING_LENGTH*sizeof(char) )
                artio_parameter_get_string_array( self.handle, key, length, char_values ) 
                parameter = [ char_values[i] for i in range(length) ]
                for i in range(length) :
                    free(char_values[i])
                free(char_values)
            elif type == ARTIO_TYPE_INT :
                int_values = <int32_t *>malloc(length*sizeof(int32_t))
                artio_parameter_get_int_array( self.handle, key, length, int_values )
                parameter = [ int_values[i] for i in range(length) ]
                free(int_values)
            elif type == ARTIO_TYPE_LONG :
                long_values = <int64_t *>malloc(length*sizeof(int64_t))
                artio_parameter_get_long_array( self.handle, key, length, long_values )
                parameter = [ long_values[i] for i in range(length) ]
                free(long_values)
            elif type == ARTIO_TYPE_FLOAT :
                float_values = <float *>malloc(length*sizeof(float))
                artio_parameter_get_float_array( self.handle, key, length, float_values )
                parameter = [ float_values[i] for i in range(length) ]
                free(float_values)
            elif type == ARTIO_TYPE_DOUBLE :
                double_values = <double *>malloc(length*sizeof(double))
                artio_parameter_get_double_array( self.handle, key, length, double_values )
                parameter = [ double_values[i] for i in range(length) ]
                free(double_values)
            else :
                print "ERROR: invalid type!"

            self.parameters[key] = parameter

#    @cython.boundscheck(False)
    @cython.wraparound(False)
    @cython.cdivision(True)
    def particle_var_fill(self, accessed_species, masked_particles,SelectorObject selector, fields) :
        # major issues:
        # 1) cannot choose which subspecies to access
        # 2) but what if a species doesnt have a field? make it zeroes
        # 3) mask size should be calculated and not just num_acc_species   
        # e.g.   
        # accessed species = nbody, stars, bh
        # secondary speces[nbody] = []
        # secondary speces[stars] = [birth, mass, blah]
        # secondary speces[bh] = [accretionrate, mass, spin]
        #
        cdef double **primary_variables
        cdef float **secondary_variables
        cdef int **fieldtoindex
        cdef int *iacctoispec 
        cdef int status
        cdef np.ndarray[np.float32_t, ndim=1] arr
        cdef int **mask
        cdef int *num_particles_per_species 
        cdef int **pos_index

        cdef int *subspecies
        subspecies = <int*>malloc(sizeof(int))
        cdef int64_t *pid
        pid = <int64_t *>malloc(sizeof(int64_t))

        cdef int nf = len(fields)
        cdef int i, j, level
        cdef np.float64_t dds[3], pos[3]
        cdef int eterm[3]


        if len(accessed_species) != 1 : 
            print 'multiple particle species access needs serious thought'
            sys.exit(1)
 
        print 'fields in var_fill:', fields
        # setup the range for all reads:
        status = artio_particle_cache_sfc_range( self.handle, 
                                                 self.sfc_min, self.sfc_max )
        check_artio_status(status)
	
        # particle species ##########        
        num_acc_species = len(accessed_species)
        num_species = self.parameters['num_particle_species'][0]
        labels_species = self.parameters['particle_species_labels']

        fieldtoindex = <int**>malloc(sizeof(int*)*num_species)
        if not fieldtoindex: raise MemoryError
        pos_index = <int**>malloc(sizeof(int*)*num_species)
        if not pos_index: raise MemoryError
        num_particles_per_species =  <int *>malloc(
            sizeof(int)*num_species) 
        if not num_particles_per_species : raise MemoryError
        iacctoispec = <int*>malloc(sizeof(int)*num_acc_species)
        if not iacctoispec: raise MemoryError
        for i, spec in enumerate(accessed_species):
            j = labels_species.index(spec)
            iacctoispec[i] = j
            # species of the same type (e.g. N-BODY) MUST be sequential in the label array
            if i > 0 and iacctoispec[i] == iacctoispec[i-1] :
                iacctoispec[i] = j+1
        # check that iacctoispec points to uniq indices
        for i in range(num_acc_species): 
            for j in range(i+1,num_acc_species):  
                if iacctoispec[i]==iacctoispec[j]:
                    print iacctoispec[i]
                    print 'some accessed species indices point to the same ispec; exitting'
                    sys.exit(1)

        # mask ####################
        # mask[spec][particle] fields are irrelevant for masking 
        # -- masking only cares abount position
        mask = <int**>malloc(sizeof(int*)*num_acc_species)
        if not mask :
            raise MemoryError
        for aspec in range(num_acc_species) :
            ispec=iacctoispec[aspec]
            mask[aspec] = <int*>malloc(
                 self.parameters['particle_species_num'][ispec] 
                 * sizeof(int))
            if not mask[aspec] :
                 raise MemoryError
 
            
        # particle field labels and order ##########        
        labels_primary={}
        labels_secondary={}
        labels_static={}
        howtoread = {}
        for ispec in range(num_species) : 
            fieldtoindex[ispec] = <int*>malloc(nf*sizeof(int))
            if not fieldtoindex[ispec] : raise MemoryError

        countnbody = 0 
        for ispec in range(num_species) : 
            # data_structures converted fields into ART labels
            # now attribute ART fields to each species primary/secondary/static/empty
            # so that we know how to read them
            param_name = "species_%02d_primary_variable_labels" % ispec
            labels_primary[ispec] = self.parameters[param_name]
            if self.parameters["num_secondary_variables"][ispec] > 0 :
                param_name = "species_%02d_secondary_variable_labels" % ispec
                labels_secondary[ispec] = self.parameters[param_name]
            else : 
                labels_secondary[ispec] = []

            if labels_species[ispec] == 'N-BODY' :
                labels_static[ispec] = ["MASS"]
            else : 
                labels_static[ispec] = [] 
            labels_static[ispec].append("particle_index") 

            for i, f in enumerate(fields):
                if   f in labels_primary[ispec]:
                    howtoread[ispec,i]= 'primary'
                    fieldtoindex[ispec][i] = labels_primary[ispec].index(f)
                elif f in labels_secondary[ispec]:
                    howtoread[ispec,i]= 'secondary'
                    fieldtoindex[ispec][i] = labels_secondary[ispec].index(f)
                        
                elif f in labels_static[ispec]:
                    #each new N-BODY spec adds one to the static mass location
                    if labels_species[ispec] == 'N-BODY' and f == 'MASS' :
                        howtoread[ispec,i]= 'staticNBODY'
                        fieldtoindex[ispec][i] = countnbody
                        countnbody += 1 #MASS happens once per N-BODY species
                        print 'count the nbody species',countnbody
                    else :
                        howtoread[ispec,i]= 'staticINDEX'
                else : 
                    howtoread[ispec,i]= 'empty'
                    fieldtoindex[ispec][i] = 9999999
                    
                print 'ispec', ispec,'field',f, 'howtoread', howtoread[ispec,i] 
            #fix pos_index
            pos_index[ispec] = <int*>malloc(3*sizeof(int))
            pos_index[ispec][0] = labels_primary[ispec].index('POSITION_X')
            pos_index[ispec][1] = labels_primary[ispec].index('POSITION_Y')
            pos_index[ispec][2] = labels_primary[ispec].index('POSITION_Z')
                                
                                

        # allocate io pointers ############
        primary_variables = <double **>malloc(sizeof(double**)*num_acc_species)  
        secondary_variables = <float **>malloc(sizeof(float**)*num_acc_species)  
        if (not primary_variables) or (not secondary_variables) : raise MemoryError
            
        for aspec in range(num_acc_species) : 
            primary_variables[aspec]   = <double *>malloc(self.parameters['num_primary_variables'][aspec]*sizeof(double))
            secondary_variables[aspec] = <float *>malloc(self.parameters['num_secondary_variables'][aspec]*sizeof(float))
            if (not primary_variables[aspec]) or (not secondary_variables[aspec]) : raise MemoryError

        count_mask = []
        ipspec = []
        # counts=0 ##########
        for aspec in range(num_acc_species) :
             count_mask.append(0)
             ipspec.append(0)
        # mask begin ##########
        print "generating mask for particles"
        for sfc in range( self.sfc_min, self.sfc_max+1 ) :
            status = artio_particle_read_root_cell_begin( 
                self.handle, sfc,
                num_particles_per_species )
            check_artio_status(status)
            # ispec is index out of all specs and aspecs is index out of accessed
            # ispec only needed for num_particles_per_species and 
            #    artio_particle_read_species_begin
            for aspec in range(num_acc_species ) :
                ispec = iacctoispec[aspec]
                status = artio_particle_read_species_begin(
                    self.handle, ispec)
                check_artio_status(status)
#                if num_particles_per_species[ispec]  >0 :
#                    print "masking root cell of np=",num_particles_per_species[ispec] 

                for particle in range( num_particles_per_species[ispec] ) :
#                    print 'snl in caller: aspec count_mask count',aspec,ispec, count_mask[aspec], ipspec[aspec] #, sizeof(primary_variables[aspec]), sizeof(secondary_variables[aspec])
                    status = artio_particle_read_particle(
                        self.handle,
                        pid, subspecies, primary_variables[aspec],
                        secondary_variables[aspec])
                    check_artio_status(status)
#                    print 'snl in caller2: aspec count_mask count',aspec,ispec, count_mask[aspec], ipspec[aspec]
                    pos[0] = primary_variables[aspec][pos_index[aspec][0]]
                    pos[1] = primary_variables[aspec][pos_index[aspec][1]]
                    pos[2] = primary_variables[aspec][pos_index[aspec][2]]
                    mask[aspec][ipspec[aspec]] = selector.select_cell(pos, dds, eterm)
                    count_mask[aspec] += mask[aspec][count_mask[aspec]]
                    ipspec[aspec] += 1
#                    print 'ipspec',ipspec[aspec], pos[1], pos[0], pos[2], \
#                        secondary_variables[aspec][0]
                status = artio_particle_read_species_end( self.handle )
                check_artio_status(status)
            status = artio_particle_read_root_cell_end( self.handle )
            check_artio_status(status)
        print 'done masking'
	##########################################################

        cdef np.float32_t **fpoint
        fpoint = <np.float32_t**>malloc(sizeof(np.float32_t*)*nf)
        num_masked_particles = sum(count_mask)
        if not fpoint : raise MemoryError
        for i, f in enumerate(fields):
            masked_particles[f] = np.empty(num_masked_particles,dtype="float32")    
            arr = masked_particles[f]
            fpoint[i] = <np.float32_t *>arr.data

	##########################################################
        #variable begin ##########
        print "reading in particle variables"
        for aspec in range(num_acc_species) :
             count_mask[aspec] = 0
             ipspec[aspec] = 0
        ipall = 0
        for sfc in range( self.sfc_min, self.sfc_max+1 ) :
                status = artio_particle_read_root_cell_begin( self.handle, sfc,
                    num_particles_per_species )
                check_artio_status(status)	
                
                for aspec in range(num_acc_species) :
                    ispec = iacctoispec[aspec]
                    status = artio_particle_read_species_begin(self.handle, ispec);
                    check_artio_status(status)
                    for particle in range( num_particles_per_species[ispec] ) :
                        
                        status = artio_particle_read_particle(self.handle,
                                        pid, subspecies, primary_variables[aspec],
                                        secondary_variables[aspec])
                        check_artio_status(status)
                        
                        if mask[aspec][ipspec[aspec]] == 1 :
                             for i in range(nf):
                                 
                                 if not (howtoread[ispec,i] == 'empty') : 
                                     assert(fieldtoindex[ispec][i]<100)
                                 if   howtoread[ispec,i] == 'primary' : 
                                     fpoint[i][ipall] = primary_variables[aspec][fieldtoindex[ispec][i]]
                                 elif howtoread[ispec,i] == 'secondary' :
                                     fpoint[i][ipall] = secondary_variables[aspec][fieldtoindex[ispec][i]]
                                 elif howtoread[ispec,i] == 'staticNBODY' : 
                                     fpoint[i][ipall] = self.parameters["particle_species_mass"][fieldtoindex[ispec][i]]
                                 elif howtoread[ispec,i] == 'staticINDEX' : 
                                     fpoint[i][ipall] = ipall
                                 elif howtoread[ispec,i] == 'empty' : 
                                     fpoint[i][ipall] = 0
                                 else : 
                                     print 'undefined how to read in caller', howtoread[ispec,i]
                                     print 'this should be impossible.'
                                     sys.exit(1)
                                 # print 'reading into fpoint', ipall,fpoint[i][ipall], fields[i]
                             ipall += 1
                        ipspec[aspec] += 1
                        
                    status = artio_particle_read_species_end( self.handle )
                    check_artio_status(status)
                    
                status = artio_particle_read_root_cell_end( self.handle )
                check_artio_status(status)
 

        free(subspecies)
        free(pid)
        free(num_particles_per_species)
        free(iacctoispec)
        free(mask)
        free(fieldtoindex)
        free(pos_index)
        free(primary_variables)
        free(secondary_variables)
        free(fpoint)

        print 'done filling particle variables', ipall



    #@cython.boundscheck(False)
    @cython.wraparound(False)
    @cython.cdivision(True)
    def read_grid_chunk(self, int64_t sfc_start, int64_t sfc_end, fields):
        cdef int i
        cdef int level
        cdef int num_oct_levels
        cdef int *num_octs_per_level
        cdef float *variables
        cdef int refined[8]
        cdef int status
        cdef int64_t max_octs
        cdef double dpos[3]
        cdef np.float64_t pos[3]
        cdef np.float64_t dds[3]
        cdef int eterm[3]
        cdef int num_fields  = len(fields)
        field_order = <int*>malloc(sizeof(int)*num_fields)

        # translate fields from ARTIO names to indices
        var_labels = self.parameters['grid_variable_labels']
        for i, f in enumerate(fields):
            if f not in var_labels:
                print "This field is not known to ARTIO:", f
                raise RuntimeError
            field_order[i] = var_labels.index(f)

        # dhr - can push these mallocs to the object to save malloc/free
        num_octs_per_level = <int *>malloc(self.max_level*sizeof(int))
        variables = <float *>malloc(8*self.num_grid_variables*sizeof(float))

        # dhr - cache the entire domain (replace later)
        status = artio_grid_cache_sfc_range( self.handle, self.sfc_min, self.sfc_max )
        check_artio_status(status) 

        # determine max number of cells we could hit (optimize later)
        status = artio_grid_count_octs_in_sfc_range(artio_fileset *handle, 
                sfc_start, sfc_end, &max_octs )
        check_artio_status(status)
        max_cells = sfc_end-sfc_start+1 + max_octs*8

        # allocate space for _fcoords, _icoords, _fwidth, _ires
        fcoords = np.empty((max_cells, 3), dtype="float64")
        ires = np.empty(max_cells, dtype="int64")

        data = {}
        for f in fields :
            data[f] = np.empty(max_cells, dtype="float32")

        cells_selected = 0
        for sfc in range( sfc_min, sfc_max+1 ) :
            status = artio_grid_read_root_cell_begin( self.handle, sfc, 
                    dpos, variables, &num_oct_levels, num_octs_per_level )
            check_artio_status(status) 

            for level in range(1,num_oct_levels+1) :
                status = artio_grid_read_level_begin( self.handle, level )
                check_artio_status(status) 

                for i in range(3) :
                    dds[i] = 2.**-level

                for oct in range(num_octs_per_level[level-1]) :
                    status = artio_grid_read_oct( self.handle, dpos, variables, refined )
                    check_artio_status(status) 

                    for child in range(8) :
                        if not refined[child] :
                            for i in range(3) :
                                pos[i] = dpos[i] + dds[i]*(-0.5 if (child & (1<<i)) else 0.5)

                            if selector.check_cell( pos, dds, eterm ) :
                                for i in range(3) :
                                    fcoords[count][i] = dpos[i]
                                ires[count] = level
                                for i, f in enumerate(fields) :
                                    data[f][count] = variables[self.num_grid_variables*child+field_order[i]]
                                count += 1 
                status = artio_grid_read_level_end( self.handle )
                check_artio_status(status) 
            else : # root cell is unrefined, add it to the list
                for i, f in enumerate(fields) :
                    data[f][count] = variables[field_order[i]]
                for i in range(3) :
                    fcoords[count][i] = dpos[i]
                ires[count] = 0
                count += 1

            status = artio_grid_read_root_cell_end( self.handle )
            check_artio_status(status) 
        
        status = artio_grid_clear_sfc_cache( self.handle )
        check_artio_status(status)

        free(num_octs_per_level) 
        free(variables)
        free(refined)
        free(field_order)

        fcoords.resize((count,3))
        ires.resize(count)

        return (fcoords, ires, data)

    def root_sfc_ranges(self, SelectorObject selector)
       cdef int max_range_size = 1024
       cdef int coords[3], sfc_start, sfc_end
       cdef float pos[3]
       cdef np.float64 dds[3]
       cdef artio_selection *selection

       dds[0] = 1.0
       dds[1] = 1.0
       dds[2] = 1.0

       sfc_ranges=[]
       selection = artio_selection_allocate(self.handle)
       for coords[0] in range(self.num_grid) :
           for coords[1] in range(self.num_grid) :
               for coords[2] in range(self.num_grid) :
                   pos[0] = coords[0]
                   pos[1] = coords[1]
                   pos[2] = coords[2]
                   if(selector.select_cell(pos, dds, eterm)):
                       artio_selection_add_root_cell(selection, coords)
       while( artio_selection_iterator(selection, max_range_size, sfc_start, sfc_end) ):
           sfc_ranges.append([sfc_start, sfc_end])
       artio_selection_destroy(selection)
       return sfc_ranges

###################################################
def artio_is_valid( char *file_prefix ) :
    cdef artio_fileset_handle *handle = artio_fileset_open( file_prefix, 
            ARTIO_OPEN_HEADER, artio_context_global )
    if handle == NULL :
        return False
    else :
        artio_fileset_close(handle) 
    return True
