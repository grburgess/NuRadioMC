import numpy as np
cimport numpy as np

# Numpy must be initialized. When using numpy from C or Cython you must
# _always_ do that, or you will have segfaults
np.import_array()

cdef extern from "numpy/arrayobject.h":
    void PyArray_ENABLEFLAGS(np.ndarray arr, int flags)

cdef extern from "createAsk.h":
    void getTimeTrace2(double *& , double *& , double *& , double *& , int & ,
                       double, double, double, double, double, int)
    void getFrequencySpectrum2(double *& , double *& , int & ,
                               double, double, double * , int, int)

cpdef get_time_trace(energy, theta, fmin, fmax, df, is_em_shower):
    cdef:
        double * times
        double * ex
        double * ey
        double * ez
        int size
        np.npy_intp shape[1]

    getTimeTrace2(times, ex, ey, ez, size, energy,
                  theta, fmin, fmax, df, is_em_shower)

    # 1. Make sure that you have called np.import_array()
    # http://gael-varoquaux.info/programming/
    # cython-example-of-exposing-c-computed-arrays-in-python-without-data-copies.html
    # 2. OWNDATA flag is important. It tells the NumPy to free data when the python object is deleted.
    # https://stackoverflow.com/questions/23872946/force-numpy-ndarray-to-take-ownership-of-its-memory-in-cython/
    # You can verify that the memory gets freed when Python object is deleted by using tools such as pmap.
    shape[0] = < np.npy_intp > size
    cdef np.ndarray[double, ndim = 1] p_t = np.PyArray_SimpleNewFromData(1, shape, np.NPY_DOUBLE, times)
    PyArray_ENABLEFLAGS(p_t, np.NPY_OWNDATA)
    cdef np.ndarray[double, ndim = 1] p_ex = np.PyArray_SimpleNewFromData(1, shape, np.NPY_DOUBLE, ex)
    PyArray_ENABLEFLAGS(p_ex, np.NPY_OWNDATA)
    cdef np.ndarray[double, ndim = 1] p_ey = np.PyArray_SimpleNewFromData(1, shape, np.NPY_DOUBLE, ey)
    PyArray_ENABLEFLAGS(p_ey, np.NPY_OWNDATA)
    cdef np.ndarray[double, ndim = 1] p_ez = np.PyArray_SimpleNewFromData(1, shape, np.NPY_DOUBLE, ez)
    PyArray_ENABLEFLAGS(p_ez, np.NPY_OWNDATA)
    return p_t, p_ex, p_ey, p_ez

cpdef get_frequency_spectrum(energy, theta, freqs, is_em_shower):
    cdef:
        double * spectrumReal
        double * spectrumImag
        int size
        np.npy_intp shape[1]
        np.ndarray[double, mode = "c"] freqs2 = freqs

    getFrequencySpectrum2(spectrumReal, spectrumImag, size,
                          energy, theta, & freqs2[0], len(freqs2), is_em_shower)

    # 1. Make sure that you have called np.import_array()
    # http://gael-varoquaux.info/programming/
    # cython-example-of-exposing-c-computed-arrays-in-python-without-data-copies.html
    # 2. OWNDATA flag is important. It tells the NumPy to free data when the python object is deleted.
    # https://stackoverflow.com/questions/23872946/force-numpy-ndarray-to-take-ownership-of-its-memory-in-cython/
    # You can verify that the memory gets freed when Python object is deleted by using tools such as pmap.
    shape[0] = < np.npy_intp > size
    cdef np.ndarray[double, ndim = 1] spec_real = np.PyArray_SimpleNewFromData(1, shape, np.NPY_DOUBLE, spectrumReal)
    PyArray_ENABLEFLAGS(spec_real, np.NPY_OWNDATA)
    cdef np.ndarray[double, ndim = 1] spec_imag = np.PyArray_SimpleNewFromData(1, shape, np.NPY_DOUBLE, spectrumImag)
    PyArray_ENABLEFLAGS(spec_imag, np.NPY_OWNDATA)
    return spec_real + 1j * spec_imag
