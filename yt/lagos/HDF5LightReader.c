/************************************************************************
* Copyright (C) 2007 Matthew Turk.  All Rights Reserved.
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
#include "H5LT.h"
#include "hdf5.h"

#include "numpy/ndarrayobject.h"


static PyObject *_hdf5ReadError;

static PyObject *
Py_ReadHDF5DataSet(PyObject *obj, PyObject *args)
{
    char *filename, *nodename;

    hsize_t *my_dims = NULL;
    npy_intp *dims = NULL;
    hid_t file_id, datatype_id, native_type_id, dataset;
    herr_t my_error;
    htri_t file_exists;
    H5T_class_t class_id;
    size_t type_size;
    int my_typenum, my_rank, i;
    H5E_auto_t err_func;
    void *err_datastream;
    PyArrayObject *my_array = NULL;
    file_id = datatype_id = native_type_id = dataset = 0;

    if (!PyArg_ParseTuple(args, "ss",
            &filename, &nodename))
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
                 "ReadHDF5DataSet: Unable to open %s", nodename);
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
                 "ReadHDF5DataSet: Unable to open dataset (%s, %s).",
                                    filename, nodename);
        goto _fail;
    }

    my_error = H5LTget_dataset_ndims ( file_id, nodename, &my_rank );
    if(my_error) {
        PyErr_Format(_hdf5ReadError,
                 "ReadHDF5DataSet: Problem getting dataset rank (%s, %s).",
                                    filename, nodename);
        goto _fail;
    }

    /* How do we keep this from leaking in failures? */
    my_dims = malloc(sizeof(hsize_t) * my_rank);
    my_error = H5LTget_dataset_info ( file_id, nodename,
                my_dims, &class_id, &type_size );

    if(my_error < 0) {
        PyErr_Format(_hdf5ReadError,
                 "ReadHDF5DataSet: Problem getting dataset info (%s, %s).",
                                    filename, nodename);
        goto _fail;
    }

    dims = malloc(my_rank * sizeof(npy_intp));
    for (i = 0; i < my_rank; i++) dims[i] = (npy_intp) my_dims[i];

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

    datatype_id = H5Dget_type(dataset);
    native_type_id = H5Tget_native_type(datatype_id, H5T_DIR_ASCEND);

    /* Behavior here is intentionally undefined for non-native types */
    int my_desc_type;
         if(H5Tequal(native_type_id, H5T_NATIVE_SHORT   ) > 0){my_desc_type = NPY_SHORT;}
    else if(H5Tequal(native_type_id, H5T_NATIVE_INT     ) > 0){my_desc_type = NPY_INT;}
    else if(H5Tequal(native_type_id, H5T_NATIVE_LONG    ) > 0){my_desc_type = NPY_LONG;}
    else if(H5Tequal(native_type_id, H5T_NATIVE_LLONG   ) > 0){my_desc_type = NPY_LONGLONG;}
    else if(H5Tequal(native_type_id, H5T_NATIVE_USHORT  ) > 0){my_desc_type = NPY_USHORT;}
    else if(H5Tequal(native_type_id, H5T_NATIVE_UINT    ) > 0){my_desc_type = NPY_UINT;}
    else if(H5Tequal(native_type_id, H5T_NATIVE_ULONG   ) > 0){my_desc_type = NPY_ULONG;}
    else if(H5Tequal(native_type_id, H5T_NATIVE_ULLONG  ) > 0){my_desc_type = NPY_ULONGLONG;}
    else if(H5Tequal(native_type_id, H5T_NATIVE_FLOAT   ) > 0){my_desc_type = NPY_FLOAT;}
    else if(H5Tequal(native_type_id, H5T_NATIVE_DOUBLE  ) > 0){my_desc_type = NPY_DOUBLE;}
    else if(H5Tequal(native_type_id, H5T_NATIVE_LDOUBLE ) > 0){my_desc_type = NPY_LONGDOUBLE;}
    else {
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

    H5LTread_dataset(file_id, nodename, native_type_id, (void *) my_array->data);

    PyArray_UpdateFlags(my_array, NPY_OWNDATA | my_array->flags);
    PyObject *return_value = Py_BuildValue("N", my_array);

    H5Fclose(file_id);
    H5Dclose(dataset);
    H5Tclose(native_type_id);
    H5Tclose(datatype_id);
    free(my_dims);
    free(dims);

    return return_value;

    _fail:
      Py_XDECREF(my_array);
      if(!(file_id <= 0)&&(H5Iget_ref(file_id))) H5Fclose(file_id);
      if(!(dataset <= 0)&&(H5Iget_ref(dataset))) H5Dclose(dataset);
      if(!(native_type_id <= 0)&&(H5Iget_ref(native_type_id))) H5Tclose(native_type_id);
      if(!(datatype_id <= 0)&&(H5Iget_ref(datatype_id))) H5Tclose(datatype_id);
      if(my_dims != NULL) free(my_dims);
      if(dims != NULL) free(dims);
      return NULL;
}

static PyMethodDef _hdf5LightReaderMethods[] = {
    {"ReadData", Py_ReadHDF5DataSet, METH_VARARGS},
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
