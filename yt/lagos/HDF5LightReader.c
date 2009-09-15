/************************************************************************
* Copyright (C) 2007-2009 Matthew Turk.  All Rights Reserved.
*
* This file is part of yt.
*
* yt is free software; you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation; either version 3 of the License, or
* (at your option) any later version.
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with this program.  If not, see <http://www.gnu.org/licenses/>.
*
************************************************************************/


//
// HDF5_LightReader
//   A module for light-weight reading of HDF5 files
//

#include "Python.h"

#include <stdio.h>
#include <math.h>
#include <signal.h>
#include <ctype.h>
#include "hdf5.h"

#include "numpy/ndarrayobject.h"

static PyObject *_hdf5ReadError;
herr_t iterate_dataset(hid_t loc_id, const char *name, void *nodelist);

/* Structures for particle reading */

typedef struct particle_validation_ {
    int count;
    int npart;
    int stride_size;
    int *mask;
    char **field_names;
    int (*count_func)(struct particle_validation_ *data);
    int (*count_func_float)(struct particle_validation_ *data);
    int (*count_func_double)(struct particle_validation_ *data);
    int (*count_func_longdouble)(struct particle_validation_ *data);
    void *validation_reqs;
    void *particle_position[3];
} particle_validation;

typedef struct region_validation_ {
    npy_float64 left_edge[3];
    npy_float64 right_edge[3];
    int periodic;
} region_validation;

/* Forward declarations */
int setup_validator_region(particle_validation *data, PyObject *InputData);
int run_validators(particle_validation *pv, char *filename, 
                   int grid_id);

/* Different data type validators */

int count_particles_region_FLOAT(particle_validation *data);
int count_particles_region_DOUBLE(particle_validation *data);

int get_my_desc_type(hid_t native_type_id){

   /*
   http://terra.rice.edu/comp.res/apps/h/hdf5/docs/RM_H5T.html#Datatype-GetNativeType

   hid_t H5Tget_native_type(hid_t type_id, H5T_direction_t direction  ) returns
   from the following list:
        H5T_NATIVE_CHAR         NPY_??
        H5T_NATIVE_SHORT        NPY_SHORT
        H5T_NATIVE_INT          NPY_INT
        H5T_NATIVE_LONG         NPY_LONG
        H5T_NATIVE_LLONG        NPY_LONGLONG

        H5T_NATIVE_UCHAR        NPY_??
        H5T_NATIVE_USHORT       NPY_USHORT
        H5T_NATIVE_UINT         NPY_UINT
        H5T_NATIVE_ULONG        NPY_ULONG
        H5T_NATIVE_ULLONG       NPY_ULONGLONG

        H5T_NATIVE_FLOAT        NPY_FLOAT
        H5T_NATIVE_DOUBLE       NPY_DOUBLE
        H5T_NATIVE_LDOUBLE      NPY_LONGDOUBLE
    */

       if(H5Tequal(native_type_id, H5T_NATIVE_SHORT   ) > 0){return NPY_SHORT;}
  else if(H5Tequal(native_type_id, H5T_NATIVE_INT     ) > 0){return NPY_INT;}
  else if(H5Tequal(native_type_id, H5T_NATIVE_LONG    ) > 0){return NPY_LONG;}
  else if(H5Tequal(native_type_id, H5T_NATIVE_LLONG   ) > 0){return NPY_LONGLONG;}
  else if(H5Tequal(native_type_id, H5T_NATIVE_USHORT  ) > 0){return NPY_USHORT;}
  else if(H5Tequal(native_type_id, H5T_NATIVE_UINT    ) > 0){return NPY_UINT;}
  else if(H5Tequal(native_type_id, H5T_NATIVE_ULONG   ) > 0){return NPY_ULONG;}
  else if(H5Tequal(native_type_id, H5T_NATIVE_ULLONG  ) > 0){return NPY_ULONGLONG;}
  else if(H5Tequal(native_type_id, H5T_NATIVE_FLOAT   ) > 0){return NPY_FLOAT;}
  else if(H5Tequal(native_type_id, H5T_NATIVE_DOUBLE  ) > 0){return NPY_DOUBLE;}
  else if(H5Tequal(native_type_id, H5T_NATIVE_LDOUBLE ) > 0){return NPY_LONGDOUBLE;}
  else {return -1;}

}

static PyObject *
Py_ReadHDF5DataSet(PyObject *obj, PyObject *args)
{
    char *filename, *nodename;

    char *dspacename = NULL;
    hsize_t *my_dims = NULL;
    hsize_t *my_max_dims = NULL;
    npy_intp *dims = NULL;
    hid_t file_id, datatype_id, native_type_id, dataset, dataspace, dsetr,
          memspace;
    herr_t my_error;
    htri_t file_exists;
    size_t type_size;
    int my_rank, i;
    H5E_auto_t err_func;
    void *err_datastream;
    PyArrayObject *my_array = NULL;
    file_id = datatype_id = native_type_id = dataset = 0;
    dataspace = 0;

    if (!PyArg_ParseTuple(args, "ss|s",
            &filename, &nodename, &dspacename))
        return PyErr_Format(_hdf5ReadError,
               "ReadHDF5DataSet: Invalid parameters.");

    /* How portable is this? */
    if (access(filename, R_OK) < 0) {
        PyErr_Format(_hdf5ReadError,
                 "ReadHDF5DataSet: %s does not exist, or no read permissions\n",
                     filename);
        goto _fail;
    }

    file_exists = H5Fis_hdf5(filename);
    if (file_exists == 0) {
        PyErr_Format(_hdf5ReadError,
                 "ReadHDF5DataSet: %s is not an HDF5 file", filename);
        goto _fail;
    }

    file_id = H5Fopen (filename, H5F_ACC_RDONLY, H5P_DEFAULT); 

    if (file_id < 0) {
        PyErr_Format(_hdf5ReadError,
                 "ReadHDF5DataSet: Unable to open %s", filename);
        goto _fail;
    }
    
    dsetr = -1;
    if(dspacename != NULL){
      /*fprintf(stderr, "Getting dspace %s\n", dspacename);*/
      dsetr = H5Dopen(file_id, dspacename);
    }

    /* We turn off error reporting briefly, because it turns out that
       reading datasets with group names is more forgiving than finding
       datasets with group names using the high-level interface. */

    H5Eget_auto(&err_func, &err_datastream);
    H5Eset_auto(NULL, NULL);
    dataset = H5Dopen(file_id, nodename);
    H5Eset_auto(err_func, err_datastream);

    if(dataset < 0) {
        PyErr_Format(_hdf5ReadError,
                 "ReadHDF5DataSet: Unable to open dataset (%s, %s).",
                                    filename, nodename);
        goto _fail;
    }

    if(dsetr >= 0) {
      hdset_reg_ref_t reference[1];
      my_error = H5Dread(dsetr, H5T_STD_REF_DSETREG, H5S_ALL, H5S_ALL, 
          H5P_DEFAULT, reference);
      if(my_error < 0) {
        PyErr_Format(_hdf5ReadError,
            "ReadHDF5DataSet: Unable to read particle reference (%s, %s, %s).",
            filename, nodename, dspacename);
        goto _fail;
      }
      H5Dclose(dsetr);
      dataspace = H5Rget_region(file_id, H5R_DATASET_REGION, reference);
      if(dataspace < 0) {
        PyErr_Format(_hdf5ReadError,
            "ReadHDF5DataSet: Unable to dereference particle dataspace (%s, %s).",
            filename, nodename);
        goto _fail;
      }
      my_rank = 1;
      /* How do we keep this from leaking in failures? */
      my_dims = malloc(sizeof(hsize_t) * my_rank);
      my_max_dims = malloc(sizeof(hsize_t) * my_rank);
      my_dims[0] = my_max_dims[0] = H5Sget_select_npoints(dataspace);
    } else {
      dataspace = H5Dget_space(dataset);
      if(dataspace < 0) {
        PyErr_Format(_hdf5ReadError,
            "ReadHDF5DataSet: Unable to open dataspace (%s, %s).",
            filename, nodename);
        goto _fail;
      }
      my_rank = H5Sget_simple_extent_ndims( dataspace );
      if(my_rank < 0) {
        PyErr_Format(_hdf5ReadError,
            "ReadHDF5DataSet: Problem getting dataset rank (%s, %s).",
            filename, nodename);
        goto _fail;
      }

      /* How do we keep this from leaking in failures? */
      my_dims = malloc(sizeof(hsize_t) * my_rank);
      my_max_dims = malloc(sizeof(hsize_t) * my_rank);
      my_error = H5Sget_simple_extent_dims( dataspace, my_dims, my_max_dims );
      if(my_error < 0) {
        PyErr_Format(_hdf5ReadError,
            "ReadHDF5DataSet: Problem getting dataset dimensions (%s, %s).",
            filename, nodename);
        goto _fail;
      }
    }
    dims = malloc(my_rank * sizeof(npy_intp));
    for (i = 0; i < my_rank; i++) dims[i] = (npy_intp) my_dims[i];

    datatype_id = H5Dget_type(dataset);
    native_type_id = H5Tget_native_type(datatype_id, H5T_DIR_ASCEND);
    type_size = H5Tget_size(native_type_id);

    /* Behavior here is intentionally undefined for non-native types */

    int my_desc_type = get_my_desc_type(native_type_id);
    if (my_desc_type == -1) {
          PyErr_Format(_hdf5ReadError,
                       "ReadHDF5DataSet: Unrecognized datatype.  Use a more advanced reader.");
          goto _fail;
    }

    my_array = (PyArrayObject *) PyArray_SimpleNewFromDescr(my_rank, dims,
                PyArray_DescrFromType(my_desc_type));
    if (!my_array) {
        PyErr_Format(_hdf5ReadError,
                 "ReadHDF5DataSet: Unable to create NumPy array.");
      
        goto _fail;
    }
    memspace = H5Screate_simple(my_rank, my_dims, NULL); 
    /*fprintf(stderr, "Total Selected: %s %d %d %d\n",
            dspacename,
            (int) H5Sget_select_npoints(memspace),
            (int) H5Sget_select_npoints(dataspace),
            (int) my_rank);*/

    H5Dread(dataset, native_type_id, memspace, dataspace, H5P_DEFAULT, my_array->data);

    PyArray_UpdateFlags(my_array, NPY_OWNDATA | my_array->flags);
    PyObject *return_value = Py_BuildValue("N", my_array);

    H5Sclose(dataspace);
    H5Sclose(memspace);
    H5Dclose(dataset);
    H5Tclose(native_type_id);
    H5Tclose(datatype_id);
    H5Fclose(file_id);
    free(my_dims);
    free(my_max_dims);
    free(dims);

    return return_value;

    _fail:
      Py_XDECREF(my_array);
      if(!(file_id <= 0)&&(H5Iget_ref(file_id))) H5Fclose(file_id);
      if(!(dataset <= 0)&&(H5Iget_ref(dataset))) H5Dclose(dataset);
      if(!(dataspace <= 0)&&(H5Iget_ref(dataspace))) H5Sclose(dataspace);
      if(!(native_type_id <= 0)&&(H5Iget_ref(native_type_id))) H5Tclose(native_type_id);
      if(!(datatype_id <= 0)&&(H5Iget_ref(datatype_id))) H5Tclose(datatype_id);
      if(my_dims != NULL) free(my_dims);
      if(my_max_dims != NULL) free(my_max_dims);
      if(dims != NULL) free(dims);
      return NULL;
}

static PyObject *
Py_ReadHDF5DataSetSlice(PyObject *obj, PyObject *args)
{
    char *filename, *nodename;

    hsize_t *my_dims = NULL;
    hsize_t *my_max_dims = NULL;
    npy_intp *dims = NULL;
    hid_t file_id, datatype_id, native_type_id, dataset, dataspace, memspace;
    herr_t my_error;
    htri_t file_exists;
    int my_rank, i, axis, coord;
    H5E_auto_t err_func;
    void *err_datastream;
    PyArrayObject *my_array = NULL;
    file_id = datatype_id = native_type_id = dataset = dataspace = memspace = 0;

    if (!PyArg_ParseTuple(args, "ssII",
            &filename, &nodename, &axis, &coord))
        return PyErr_Format(_hdf5ReadError,
               "ReadHDF5DataSetSlice: Invalid parameters.");

    /* How portable is this? */
    if (access(filename, R_OK) < 0) {
        PyErr_Format(_hdf5ReadError,
                 "ReadHDF5DataSetSlice: %s does not exist, or no read permissions\n",
                     filename);
        goto _fail;
    }

    file_exists = H5Fis_hdf5(filename);
    if (file_exists == 0) {
        PyErr_Format(_hdf5ReadError,
                 "ReadHDF5DataSetSlice: %s is not an HDF5 file", filename);
        goto _fail;
    }

    file_id = H5Fopen (filename, H5F_ACC_RDONLY, H5P_DEFAULT); 

    if (file_id < 0) {
        PyErr_Format(_hdf5ReadError,
                 "ReadHDF5DataSetSlice: Unable to open %s", filename);
        goto _fail;
    }

    /* We turn off error reporting briefly, because it turns out that
       reading datasets with group names is more forgiving than finding
       datasets with group names using the high-level interface. */

    H5Eget_auto(&err_func, &err_datastream);
    H5Eset_auto(NULL, NULL);
    dataset = H5Dopen(file_id, nodename);
    H5Eset_auto(err_func, err_datastream);

    if(dataset < 0) {
        PyErr_Format(_hdf5ReadError,
                 "ReadHDF5DataSetSlice: Unable to open dataset (%s, %s).",
                                    filename, nodename);
        goto _fail;
    }
    dataspace = H5Dget_space(dataset);
    if(dataspace < 0) {
        PyErr_Format(_hdf5ReadError,
                 "ReadHDF5DataSetSlice: Unable to open dataspace (%s, %s).",
                                    filename, nodename);
        goto _fail;
    }

    my_rank = H5Sget_simple_extent_ndims( dataspace );
    if(my_rank!=3) {
        PyErr_Format(_hdf5ReadError,
                 "ReadHDF5DataSetSlice: Sorry, I only know how to slice 3D into 2D.");
        goto _fail;
    }

    /* How do we keep this from leaking in failures? */
    my_dims = malloc(sizeof(hsize_t) * my_rank);
    my_max_dims = malloc(sizeof(hsize_t) * my_rank);
    my_error = H5Sget_simple_extent_dims( dataspace, my_dims, my_max_dims );
    if(my_error < 0) {
        PyErr_Format(_hdf5ReadError,
                 "ReadHDF5DataSetSlice: Problem getting dataset info (%s, %s).",
                                    filename, nodename);
        goto _fail;
    }

    dims = malloc(my_rank * sizeof(npy_intp));
    for (i = 0; i < my_rank; i++) dims[i] = (npy_intp) my_dims[i];

    datatype_id = H5Dget_type(dataset);
    native_type_id = H5Tget_native_type(datatype_id, H5T_DIR_ASCEND);

    /* Behavior here is intentionally undefined for non-native types */

    int my_desc_type = get_my_desc_type(native_type_id);
    if (my_desc_type == -1) {
          PyErr_Format(_hdf5ReadError,
                       "ReadHDF5DataSetSlice: Unrecognized datatype.  Use a more advanced reader.");
          goto _fail;
    }

    /* Okay, now let's figure out what the dataspaces will look like */

    hsize_t slice_coords[3] = {0, 0, 0};
    slice_coords[axis] = coord;
    hsize_t slice_blocks[3] = {dims[0], dims[1], dims[2]};
    slice_blocks[axis] = 1;

    my_error = H5Sselect_hyperslab(dataspace, H5S_SELECT_SET, slice_coords, NULL, 
     slice_blocks, NULL);
    if(my_error) {
        PyErr_Format(_hdf5ReadError,
                 "ReadHDF5DataSetSlice: Problem selecting hyperslab.");
        goto _fail;
    }

    hsize_t slice_dims[2];
    int j = 0;
    for (i=0;i<3;i++)if(i!=axis)slice_dims[j++]=dims[i];
    memspace = H5Screate_simple(2,slice_dims,NULL); 

    npy_intp slice_dims_i[2] = {slice_dims[0], slice_dims[1]};
    my_array = (PyArrayObject *) PyArray_SimpleNewFromDescr(2, slice_dims_i,
                PyArray_DescrFromType(my_desc_type));
    if (!my_array) {
        PyErr_Format(_hdf5ReadError,
                 "ReadHDF5DataSetSlice: Unable to create NumPy array.");
        goto _fail;
    }

    my_error = H5Dread(dataset, native_type_id, memspace, dataspace, H5P_DEFAULT,    
                       my_array->data);

    PyArray_UpdateFlags(my_array, NPY_OWNDATA | my_array->flags);
    PyObject *return_value = Py_BuildValue("N", my_array);

    H5Fclose(file_id);
    H5Dclose(dataset);
    H5Sclose(dataspace);
    H5Sclose(memspace);
    H5Tclose(native_type_id);
    H5Tclose(datatype_id);
    free(my_dims);
    free(my_max_dims);
    free(dims);

    return return_value;

    _fail:
      Py_XDECREF(my_array);
      if(!(file_id <= 0)&&(H5Iget_ref(file_id))) H5Fclose(file_id);
      if(!(dataset <= 0)&&(H5Iget_ref(dataset))) H5Dclose(dataset);
      if(!(dataspace <= 0)&&(H5Iget_ref(dataspace))) H5Sclose(dataspace);
      if(!(memspace <= 0)&&(H5Iget_ref(memspace))) H5Sclose(memspace);
      if(!(native_type_id <= 0)&&(H5Iget_ref(native_type_id))) H5Tclose(native_type_id);
      if(!(datatype_id <= 0)&&(H5Iget_ref(datatype_id))) H5Tclose(datatype_id);
      if(my_dims != NULL) free(my_dims);
      if(my_max_dims != NULL) free(my_max_dims);
      if(dims != NULL) free(dims);
      return NULL;

}

static PyObject *
Py_ReadListOfDatasets(PyObject *obj, PyObject *args)
{
    char *filename, *nodename;

    hid_t file_id;
    herr_t my_error;
    htri_t file_exists;
    file_id = 0;

    if (!PyArg_ParseTuple(args, "ss",
            &filename, &nodename))
        return PyErr_Format(_hdf5ReadError,
               "ReadListOfDatasets: Invalid parameters.");

    /* How portable is this? */
    if (access(filename, R_OK) < 0) {
        PyErr_Format(_hdf5ReadError,
                 "ReadListOfDatasets: %s does not exist, or no read permissions\n",
                     filename);
        goto _fail;
    }

    file_exists = H5Fis_hdf5(filename);
    if (file_exists == 0) {
        PyErr_Format(_hdf5ReadError,
                 "ReadListOfDatasets: %s is not an HDF5 file", filename);
        goto _fail;
    }

    file_id = H5Fopen (filename, H5F_ACC_RDONLY, H5P_DEFAULT); 
    PyObject *nodelist = PyList_New(0);
    if (nodelist == NULL) {
        PyErr_Format(_hdf5ReadError,
                 "ReadListOfDatasets: List couldn't be made!");
        goto _fail;
    }

    my_error = H5Giterate(file_id, nodename, NULL, iterate_dataset, (void *) nodelist);
    H5Fclose(file_id);
    if (my_error) {
        PyErr_Format(_hdf5ReadError,
                 "ReadListOfDatasets: Problem iterating over HDF5 set.");
        goto _fail;
    }
    
    PyObject *return_value = Py_BuildValue("N", nodelist);
    return return_value;

    _fail:
      Py_XDECREF(nodelist);
      if(!(file_id <= 0)&&(H5Iget_ref(file_id))) H5Fclose(file_id);
      return NULL;
    
}

herr_t iterate_dataset(hid_t loc_id, const char *name, void *nodelist)
{
    H5G_stat_t statbuf;
    PyObject* node_name;

    H5Gget_objinfo(loc_id, name, 0, &statbuf);
    if (statbuf.type == H5G_DATASET) {
        node_name = PyString_FromString(name);
        if (node_name == NULL) {return -1;}
        if (PyList_Append((PyObject *)nodelist, node_name)) {return -1;}
    }
    return 0;
};

PyArrayObject* get_array_from_nodename(char *nodename, hid_t rootnode);

static PyObject *
Py_ReadMultipleGrids(PyObject *obj, PyObject *args)
{
    // Process:
    //      - Create dict to hold data
    //      - Open each top-level node in order
    //      - For each top-level node create a dictionary
    //      - Insert new dict in top-level dict
    //      - Read each dataset, insert into dict

    // Format arguments

    char *filename = NULL;
    PyObject *grid_ids = NULL;
    PyObject *set_names = NULL;
    Py_ssize_t num_sets = 0;
    Py_ssize_t num_grids = 0;

    if (!PyArg_ParseTuple(args, "sOO",
            &filename, &grid_ids, &set_names))
        return PyErr_Format(_hdf5ReadError,
               "ReadMultipleGrids: Invalid parameters.");

    num_grids = PyList_Size(grid_ids);
    num_sets = PyList_Size(set_names);
    PyObject *grids_dict = PyDict_New(); // New reference
    PyObject *grid_key = NULL;
    PyObject *grid_data = NULL;
    PyObject *oset_name = NULL;
    PyArrayObject *cur_data = NULL;
    char *set_name;
    hid_t file_id, grid_node;
    file_id = grid_node = 0;
    int i, n;
    long id;
    char grid_node_name[13]; // Grid + 8 + \0

    file_id = H5Fopen (filename, H5F_ACC_RDONLY, H5P_DEFAULT); 

    if (file_id < 0) {
        PyErr_Format(_hdf5ReadError,
                 "ReadMultipleGrids: Unable to open %s", filename);
        goto _fail;
    }

    for(i = 0; i < num_grids; i++) {
        grid_key = PyList_GetItem(grid_ids, i);
        id = PyInt_AsLong(grid_key);
        sprintf(grid_node_name, "Grid%08li", id);
        grid_data = PyDict_New(); // New reference
        PyDict_SetItem(grids_dict, grid_key, grid_data);
        grid_node = H5Gopen(file_id, grid_node_name);
        if (grid_node < 0) {
              PyErr_Format(_hdf5ReadError,
                  "ReadHDF5DataSet: Error opening (%s, %s)",
                  filename, grid_node_name);
              goto _fail;
        }
        for(n = 0; n < num_sets; n++) {
            // This points to the in-place internal char*
            oset_name = PyList_GetItem(set_names, n);
            set_name = PyString_AsString(oset_name);
            cur_data = get_array_from_nodename(set_name, grid_node);
            if (cur_data != NULL) {
                PyDict_SetItem(grid_data, oset_name, (PyObject *) cur_data);
            }
            Py_XDECREF(cur_data); // still one left
        }
        // We just want the one reference from the grids_dict value set
        Py_DECREF(grid_data); 
        H5Gclose(grid_node);
    }

    H5Fclose(file_id);
    PyObject *return_value = Py_BuildValue("N", grids_dict);
    return return_value;

    _fail:

      if(!(file_id <= 0)&&(H5Iget_ref(file_id))) H5Fclose(file_id);
      if(!(grid_node <= 0)&&(H5Iget_ref(grid_node))) H5Gclose(grid_node);
      Py_XDECREF(grid_data);
      PyDict_Clear(grids_dict); // Should catch the sub-dictionaries
      return NULL;

}

PyArrayObject* get_array_from_nodename(char *nodename, hid_t rootnode)
{
    
    H5E_auto_t err_func;
    void *err_datastream;
    herr_t my_error;
    hsize_t *my_dims = NULL;
    hsize_t *my_max_dims = NULL;
    npy_intp *dims = NULL;
    int my_rank, i;
    size_t type_size;
    PyArrayObject *my_array = NULL;
    hid_t datatype_id, native_type_id, dataset, dataspace;
    datatype_id = native_type_id = dataset = dataspace = 0;

    H5Eget_auto(&err_func, &err_datastream);
    H5Eset_auto(NULL, NULL);
    dataset = H5Dopen(rootnode, nodename);
    H5Eset_auto(err_func, err_datastream);

    if(dataset < 0) goto _fail;

    dataspace = H5Dget_space(dataset);
    if(dataspace < 0) goto _fail;

    my_rank = H5Sget_simple_extent_ndims( dataspace );
    if(my_rank < 0) goto _fail;

    my_dims = malloc(sizeof(hsize_t) * my_rank);
    my_max_dims = malloc(sizeof(hsize_t) * my_rank);
    my_error = H5Sget_simple_extent_dims( dataspace, my_dims, my_max_dims );
    if(my_error < 0) goto _fail;

    dims = malloc(my_rank * sizeof(npy_intp));
    for (i = 0; i < my_rank; i++) dims[i] = (npy_intp) my_dims[i];

    datatype_id = H5Dget_type(dataset);
    native_type_id = H5Tget_native_type(datatype_id, H5T_DIR_ASCEND);
    type_size = H5Tget_size(native_type_id);

    /* Behavior here is intentionally undefined for non-native types */

    int my_desc_type = get_my_desc_type(native_type_id);
    if (my_desc_type == -1) {
          PyErr_Format(_hdf5ReadError,
                       "ReadHDF5DataSet: Unrecognized datatype.  Use a more advanced reader.");
          goto _fail;
    }

    // Increments the refcount
    my_array = (PyArrayObject *) PyArray_SimpleNewFromDescr(my_rank, dims,
                PyArray_DescrFromType(my_desc_type));
    if (!my_array) goto _fail;

    H5Dread(dataset, native_type_id, H5S_ALL, H5S_ALL, H5P_DEFAULT, my_array->data);
    H5Sclose(dataspace);
    H5Dclose(dataset);
    H5Tclose(native_type_id);
    H5Tclose(datatype_id);
    free(my_dims);
    free(my_max_dims);
    free(dims);

    PyArray_UpdateFlags(my_array, NPY_OWNDATA | my_array->flags);
    return my_array;

    _fail:
      if(!(dataset <= 0)&&(H5Iget_ref(dataset))) H5Dclose(dataset);
      if(!(dataspace <= 0)&&(H5Iget_ref(dataspace))) H5Sclose(dataspace);
      if(!(native_type_id <= 0)&&(H5Iget_ref(native_type_id))) H5Tclose(native_type_id);
      if(!(datatype_id <= 0)&&(H5Iget_ref(datatype_id))) H5Tclose(datatype_id);
      if(my_dims != NULL) free(my_dims);
      if(my_max_dims != NULL) free(my_max_dims);
      if(dims != NULL) free(dims);
      return NULL;
}

static PyObject *
Py_ReadParticles(PyObject *obj, PyObject *args)
{
    // Process:
    //      - Interpret arguments:
    //          - List of filenames
    //          - List of grid ids (this is Enzo HDF5-specific)
    //          - Validation arguments
    //          - List of true/false for validation
    //      - Set up validation scheme
    //      - Iterate over grids, counting
    //      - Allocate array
    //      - Iterate over grids, turning on and off dataspace

    int source_type, ig, id, i;
    Py_ssize_t ngrids;

    PyObject *field_list, *filename_list, *grid_ids, *fully_enclosed, *vargs;
    vargs = field_list = filename_list = grid_ids = fully_enclosed = NULL;
    int stride_size = 100000;

    if (!PyArg_ParseTuple(args, "iOOOOO",
            &source_type, /* This is a non-public API, so we just take ints */
            &filename_list, &grid_ids, &vargs, &fully_enclosed))
        return PyErr_Format(_hdf5ReadError,
               "ReadParticles: Invalid parameters.");

    if (!PyList_Check(filename_list)) {
        PyErr_Format(_hdf5ReadError,
                 "ReadParticles: filename_list is not a list!\n");
        goto _fail;
    }
    ngrids = PyList_Size(filename_list);

    if (!PyList_Check(grid_ids)
        || (PyList_Size(grid_ids) != ngrids)) {
        PyErr_Format(_hdf5ReadError,
                 "ReadParticles: grid_ids is not a list of correct length!\n");
        goto _fail;
    }

    if (!PyTuple_Check(vargs)) {
        PyErr_Format(_hdf5ReadError,
                 "ReadParticles: vargs is not a tuple!\n");
        goto _fail;
    }

    if (!PyList_Check(fully_enclosed)
        || (PyList_Size(fully_enclosed) != ngrids)) {
        PyErr_Format(_hdf5ReadError,
                 "ReadParticles: fully_enclosed is not a list of correct length!\n");
        goto _fail;
    }

    /* We've now parsed all our arguments and it is time to set up the
       validator */

    /* First initialize our particle_validation structure */
    particle_validation pv;
    pv.mask = (int*) malloc(sizeof(int) * stride_size);
    pv.stride_size = stride_size;

    switch(source_type) {
        case 0:
            /* Region type */
            setup_validator_region(&pv, vargs);
            break;
        default:
            PyErr_Format(_hdf5ReadError,
                    "Unrecognized data source.\n");
            goto _fail;
            break;
    }

    /* Okay, now we open our files and stride over each grid in the files. */

    PyObject *temp = NULL;
    char *filename = NULL;
    int num_cells = 0;

    for (ig = 0; ig < ngrids ; ig++) {
        /* Read the data into our buffer here */
        /* Borrowed reference to the fully-enclosed calculation */
        temp = PyList_GetItem(fully_enclosed, ig);
        num_cells = PyInt_AsLong(temp);
        if (num_cells == 0){
            /* We need a filename and a grid id */
            temp = PyList_GetItem(filename_list, ig);
            filename = PyString_AsString(temp);
            temp = PyList_GetItem(grid_ids, ig);
            id = PyInt_AsLong(temp);
            if(run_validators(&pv, filename, id) < 0) {
                goto _fail;
            }
        } else {
            pv.count += num_cells;
        }
    }

    /* Now we know how many particles we want. */

    for (ig = 0; ig < ngrids ; ig++) {

    }

    /* Now we do some finalization */
    for (i = 0; i<3; i++) {
        free(pv.particle_position[i]);
    }

    free(pv.validation_reqs);
    /* We don't need to free pv */

    _fail:
#warning "_fail needs to be implemented"

        return NULL;
}

int setup_validator_region(particle_validation *data, PyObject *InputData)
{
    int i;
    /* These are borrowed references */
    PyArrayObject *left_edge = (PyArrayObject *) PyTuple_GetItem(InputData, 0);
    PyArrayObject *right_edge = (PyArrayObject *) PyTuple_GetItem(InputData, 1);
    PyObject *operiodic = PyTuple_GetItem(InputData, 2);
    
    region_validation *rv = (region_validation *)
                malloc(sizeof(region_validation));
    data->validation_reqs = (void *) rv;

    for (i = 0; i < 3; i++){
        rv->left_edge[i] = *(npy_float64*) PyArray_GETPTR1(left_edge, i);
        rv->right_edge[i] = *(npy_float64*) PyArray_GETPTR1(right_edge, i);
    }

    rv->periodic = PyInt_AsLong(operiodic);

    data->count_func = NULL;
    data->count_func_float = count_particles_region_FLOAT;
    data->count_func_double = count_particles_region_DOUBLE;

    /* We need to insert more periodic logic here */

    return 1;
}

int run_validators(particle_validation *pv, char *filename, 
                   int grid_id)
{
    int i;
    hid_t file_id;
    hid_t dataset_x, dataset_y, dataset_z;
    hid_t dataspace, memspace;
    hid_t datatype_id, native_type_id;
    hid_t my_error;
    char name_x[255], name_y[255], name_z[255];
    hsize_t num_part;
    hsize_t current_pos = 0;
    hsize_t count = 0;

    snprintf(name_x, 255, "/Grid%08i/particle_position_x", grid_id);
    snprintf(name_y, 255, "/Grid%08i/particle_position_y", grid_id);
    snprintf(name_z, 255, "/Grid%08i/particle_position_z", grid_id);

    /* First we open the file */

    file_id = H5Fopen(filename, H5F_ACC_RDONLY, H5P_DEFAULT);
    if (file_id < 0) {
        PyErr_Format(_hdf5ReadError,
                 "ReadHDF5DataSet: Unable to open %s", filename);
        goto _fail;
    }

    /* Figure out the size of our array */

    /* Note that we are using one dimension, not multiple.  If you're using
       Enzo data with multiple particle dimensions, well, I'm afraid I can't help you.
       Just now, at least.  */

    dataset_x = H5Dopen(file_id, name_x);
    dataset_y = H5Dopen(file_id, name_y);
    dataset_z = H5Dopen(file_id, name_z);

    dataspace = H5Dget_space(dataset_x);
    my_error = H5Sget_simple_extent_dims( dataspace, &num_part, NULL );

    /* Let's get the information about the datatype now */
    datatype_id = H5Dget_type(dataset_x);
    native_type_id = H5Tget_native_type(datatype_id, H5T_DIR_ASCEND);

    /* If the count function is not set, set it and allocate arrays */
    if(pv->count_func == NULL){
      int typesize = 0;
      if(H5Tequal(native_type_id, H5T_NATIVE_FLOAT) > 0) {
        pv->count_func = pv->count_func_float;
        typesize = sizeof(float);
      } else if (H5Tequal(native_type_id, H5T_NATIVE_DOUBLE) > 0 ) {
        pv->count_func = pv->count_func_double;
        typesize = sizeof(double);
      } else if (H5Tequal(native_type_id, H5T_NATIVE_LDOUBLE) > 0 ) {
        pv->count_func = pv->count_func_longdouble;
        typesize = sizeof(long double);
      } else {
        H5Tclose(datatype_id); H5Tclose(native_type_id);
        PyErr_Format(_hdf5ReadError,
            "ReadHDF5DataSet: Unrecognized particle position array type");
        goto _fail;
      }
      /* We allocate arrays here */
      for(i = 0; i < 3; i++)
        pv->particle_position[i] = malloc(pv->stride_size * typesize);
    }
    
    /* Now we create an in-memory dataspace */

    memspace = H5Screate(H5S_SIMPLE);

    /* We begin our iteration over the strides here */

    while(current_pos < num_part) {
        count = ((current_pos + count > num_part) ? 
                    num_part-current_pos : pv->stride_size );

        H5Sselect_hyperslab(dataspace, H5S_SELECT_SET, &current_pos, NULL,
                            &count, NULL);
        H5Dread(dataset_x, native_type_id, memspace, dataspace, H5P_DEFAULT,
                pv->particle_position[0]);
        H5Dread(dataset_y, native_type_id, memspace, dataspace, H5P_DEFAULT,
                pv->particle_position[1]);
        H5Dread(dataset_z, native_type_id, memspace, dataspace, H5P_DEFAULT,
                pv->particle_position[2]);

        pv->count_func(pv);

        current_pos += pv->stride_size;
    }

    H5Dclose(dataset_x);
    H5Dclose(dataset_y);
    H5Dclose(dataset_z);
    H5Sclose(dataspace);
    H5Sclose(memspace);
    H5Tclose(datatype_id);
    H5Tclose(native_type_id);

    _fail:
#warning "_fail needs to be implemented"

        return -1;
}

/* Hate to do copy-pasta here, but I think it is necessary */

int count_particles_region_FLOAT(particle_validation *data)
{
    /* Our data comes packed in a struct, off which our pointers all hang */

    /* First is our validation requirements, which are a set of three items: */

    int ind;
    region_validation *vdata;

    vdata = (region_validation*) data->validation_reqs;
    
    float **particle_data = (float **) data->particle_position;

    float *particle_position_x = particle_data[0];
    float *particle_position_y = particle_data[1];
    float *particle_position_z = particle_data[2];

    if (vdata->periodic == 0) {
      for (ind = 0; ind < data->npart; ind++) {
        if ((particle_position_x[ind] > vdata->left_edge[0])
            && (particle_position_x[ind] < vdata->right_edge[0])
            && (particle_position_y[ind] > vdata->left_edge[1])
            && (particle_position_y[ind] < vdata->right_edge[1])
            && (particle_position_z[ind] > vdata->left_edge[2])
            && (particle_position_z[ind] < vdata->right_edge[2])) {
          data->count++;
          data->mask[ind] = 1;
        } else {
          data->mask[ind] = 0;
        }
      }
    } else {
        /* We need periodic logic here */
    }
    return 1;
}

int count_particles_region_DOUBLE(particle_validation *data)
{
    /* Our data comes packed in a struct, off which our pointers all hang */

    /* First is our validation requirements, which are a set of three items: */

    int ind;
    region_validation *vdata;

    vdata = (region_validation*) data->validation_reqs;
    
    double **particle_data = (double **) data->particle_position;

    double *particle_position_x = particle_data[0];
    double *particle_position_y = particle_data[1];
    double *particle_position_z = particle_data[2];

    if (vdata->periodic == 0) {
      for (ind = 0; ind < data->npart; ind++) {
        if ((particle_position_x[ind] > vdata->left_edge[0])
            && (particle_position_x[ind] < vdata->right_edge[0])
            && (particle_position_y[ind] > vdata->left_edge[1])
            && (particle_position_y[ind] < vdata->right_edge[1])
            && (particle_position_z[ind] > vdata->left_edge[2])
            && (particle_position_z[ind] < vdata->right_edge[2])) {
          data->count++;
          data->mask[ind] = 1;
        } else {
          data->mask[ind] = 0;
        }
      }
    } else {
        /* We need periodic logic here */
    }
    return 1;
}

static PyMethodDef _hdf5LightReaderMethods[] = {
    {"ReadData", Py_ReadHDF5DataSet, METH_VARARGS},
    {"ReadDataSlice", Py_ReadHDF5DataSetSlice, METH_VARARGS},
    {"ReadListOfDatasets", Py_ReadListOfDatasets, METH_VARARGS},
    {"ReadMultipleGrids", Py_ReadMultipleGrids, METH_VARARGS},
    {NULL, NULL} 
};

#ifdef MS_WIN32
__declspec(dllexport)
#endif

void initHDF5LightReader(void)
{
    PyObject *m, *d;
    m = Py_InitModule("HDF5LightReader", _hdf5LightReaderMethods);
    d = PyModule_GetDict(m);
    _hdf5ReadError = PyErr_NewException("HDF5LightReader.ReadingError", NULL, NULL);
    PyDict_SetItemString(d, "ReadingError", _hdf5ReadError);
    import_array();
}
