// This program enables to call libfuzzers functions from python.
// Copyright (c) 2019 Robert Bosch GmbH
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <fcntl.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <dlfcn.h>
#include <sys/random.h>
#include <stdlib.h>

#define MAX_NUM_MUTATIONS 4

// From libFuzzer. This function applies one mutation to a string.
uint32_t (*LLVMFuzzerMutate)(uint8_t*, size_t, size_t) = NULL;

char *mutated_input = NULL;
size_t max_input_length = 0;

// LibFuzzer has an option to use a callback, which we do not use.
int callback(const uint8_t *Data, size_t Size) {
    return 0;
}

static PyObject* _initialize(PyObject *self, PyObject *args) {
	if (LLVMFuzzerMutate) {
        // Only initialize the mutator once.
        // Already initialized, return 1
        PyObject *ret = Py_BuildValue("i", 1);
        return ret;
	}

    // maximum input length for generated inputs.
    Py_ssize_t py_max_input_length;

    if (!PyArg_ParseTuple(args, "n", &py_max_input_length)) {
        return NULL;
    }
    max_input_length = (size_t)py_max_input_length;

    void *dh = dlopen(getenv("libfuzzer_mutator_so_path"), RTLD_NOW);
    if (!dh) {
      fprintf(stderr, "Failed to open custom mutator shared library: %s\n",
              dlerror());
      exit(1);
    }

	void (*LLVMFuzzerMyInit)(void*, unsigned int) = dlsym(dh, "LLVMFuzzerMyInit");
    if (!LLVMFuzzerMyInit) {
      fprintf(stderr, "ERROR: Symbol LLVMFuzzerMyInit not found in "
                      "libfuzzer-mutator.so\n");
      exit(4);
    }

    // Initialize libFuzzer's mutator with a random seed.
    unsigned int seed;
    ssize_t getr = getrandom(&seed, sizeof(seed), 0);
    if (getr != sizeof(seed)) {
        fprintf(stderr, "getrandom failed. getr=%zd\n", getr);
        exit(3);
    }
    LLVMFuzzerMyInit(callback, seed);

	LLVMFuzzerMutate =  dlsym(dh, "LLVMFuzzerMutate");
	if (!LLVMFuzzerMutate) {
      fprintf(stderr, "ERROR: Symbol LLVMFuzzerMutate not found in "
                      "libfuzzer-mutator.so\n");
        exit(2);
    }

    // Allocate buffer for generated inputs.
    mutated_input = malloc(sizeof(char) * max_input_length);
    if (mutated_input == NULL) {
        perror("Malloc for mutated_input failed:");
        exit(3);
    }

    // Return 0
    PyObject *ret = Py_BuildValue("i", 0);
    return ret;
}

static PyObject* _mutate(PyObject *self, PyObject *args) {

    const char *base_input;
    Py_ssize_t base_input_length;

    if (!PyArg_ParseTuple(args, "y#", &base_input, &base_input_length)) {
        return NULL;
    }

	if (!LLVMFuzzerMutate) {
        fprintf(stderr, "ERROR: Not initialized. "
                        "Must call _pylibfuzzer.initialize() "
                        "before _pylibfuzzer.mutate() can be called\n");
        exit(4);
	}

    if ((size_t)base_input_length > max_input_length) {
        fprintf(stderr, "ERROR: passed input is larger than max_input_length\n");
        exit(5);

    }

    // Copy immutable baseline input to buffer.
    memcpy(mutated_input, base_input, (size_t)base_input_length);

    size_t input_len = (size_t)base_input_length;

    //Choose number of mutations between 1 and MAX_NUM_MUTATIONS
    int num_mutations = (rand() % MAX_NUM_MUTATIONS) + 1;
    // Apply NUM_MUTATIONS mutations to the input.
    for (int i = 0; i < num_mutations; i++) {
        input_len = LLVMFuzzerMutate((uint8_t *)mutated_input, input_len, max_input_length);
    }

    // Create a Python 'bytes' object, and initialize it with the content of
    // the buffer. Return this bytes object.
    PyObject *ret = PyBytes_FromStringAndSize(mutated_input, (Py_ssize_t)input_len);
    return ret;
}

// The rest of this file is setup for the Python/C API.
static struct PyMethodDef methods[] = {
    {"initialize", (PyCFunction)_initialize, METH_VARARGS},
    {"mutate", (PyCFunction)_mutate, METH_VARARGS},
    {NULL, NULL}
};

static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT,
    "_pylibfuzzer",
    NULL,
    -1,
    methods
};

PyMODINIT_FUNC PyInit__pylibfuzzer(void) {
	return PyModule_Create(&module);
}
