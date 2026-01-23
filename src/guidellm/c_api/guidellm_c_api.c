#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <structmember.h>
#include <string.h>

// Forward declarations
static PyObject* guidellm_run_benchmark(PyObject* self, PyObject* args, PyObject* kwargs);
static PyObject* guidellm_reimport_report(PyObject* self, PyObject* args, PyObject* kwargs);
static PyObject* guidellm_get_error_message(PyObject* self, PyObject* args);

// Module methods
static PyMethodDef GuidellmMethods[] = {
    {
        "run_benchmark",
        (PyCFunction)guidellm_run_benchmark,
        METH_VARARGS | METH_KEYWORDS,
        "Run a benchmark and generate reports. Returns JSON string of output results."
    },
    {
        "reimport_report",
        (PyCFunction)guidellm_reimport_report,
        METH_VARARGS | METH_KEYWORDS,
        "Re-import a benchmark report and export to other formats."
    },
    {
        "get_error_message",
        guidellm_get_error_message,
        METH_VARARGS,
        "Get the last error message."
    },
    {NULL, NULL, 0, NULL}
};

// Module definition
static struct PyModuleDef guidellm_c_api_module = {
    PyModuleDef_HEAD_INIT,
    "guidellm_c_api",
    "C API wrapper for GuideLLM benchmarking",
    -1,
    GuidellmMethods
};

// Initialize module
PyMODINIT_FUNC PyInit_guidellm_c_api(void) {
    return PyModule_Create(&guidellm_c_api_module);
}

// Helper to run async function
static PyObject* run_async_function(PyObject* async_func, PyObject* args, PyObject* kwargs) {
    PyObject* result = NULL;
    PyObject* event_loop = NULL;
    PyObject* run_until_complete = NULL;
    
    // Import asyncio
    PyObject* asyncio = PyImport_ImportModule("asyncio");
    if (!asyncio) {
        return NULL;
    }
    
    // Get or create event loop
    PyObject* get_event_loop = PyObject_GetAttrString(asyncio, "get_event_loop");
    if (!get_event_loop) {
        Py_DECREF(asyncio);
        return NULL;
    }
    
    event_loop = PyObject_CallObject(get_event_loop, NULL);
    Py_DECREF(get_event_loop);
    
    if (!event_loop) {
        // Try new_event_loop if get_event_loop fails
        PyObject* new_event_loop = PyObject_GetAttrString(asyncio, "new_event_loop");
        if (new_event_loop) {
            event_loop = PyObject_CallObject(new_event_loop, NULL);
            Py_DECREF(new_event_loop);
            PyObject* set_event_loop = PyObject_GetAttrString(asyncio, "set_event_loop");
            if (set_event_loop && event_loop) {
                PyObject_CallObject(set_event_loop, PyTuple_Pack(1, event_loop));
                Py_DECREF(set_event_loop);
            }
        }
    }
    
    Py_DECREF(asyncio);
    
    if (!event_loop) {
        return NULL;
    }
    
    // Call the async function
    PyObject* coro = PyObject_Call(async_func, args, kwargs);
    if (!coro) {
        Py_DECREF(event_loop);
        return NULL;
    }
    
    // Run until complete
    run_until_complete = PyObject_GetAttrString(event_loop, "run_until_complete");
    if (!run_until_complete) {
        Py_DECREF(coro);
        Py_DECREF(event_loop);
        return NULL;
    }
    
    result = PyObject_CallFunction(run_until_complete, "O", coro);
    
    Py_DECREF(run_until_complete);
    Py_DECREF(coro);
    Py_DECREF(event_loop);
    
    return result;
}

// Run benchmark function
static PyObject* guidellm_run_benchmark(PyObject* self, PyObject* args, PyObject* kwargs) {
    PyObject* benchmark_func = NULL;
    PyObject* args_obj = NULL;
    PyObject* result = NULL;
    PyObject* report = NULL;
    PyObject* output_results = NULL;
    PyObject* json_str = NULL;
    
    // Import the benchmark function
    PyObject* entrypoints = PyImport_ImportModule("guidellm.benchmark.entrypoints");
    if (!entrypoints) {
        return NULL;
    }
    
    benchmark_func = PyObject_GetAttrString(entrypoints, "benchmark_generative_text");
    Py_DECREF(entrypoints);
    
    if (!benchmark_func) {
        return NULL;
    }
    
    // Import BenchmarkGenerativeTextArgs
    PyObject* schemas = PyImport_ImportModule("guidellm.benchmark.schemas.generative.entrypoints");
    if (!schemas) {
        Py_DECREF(benchmark_func);
        return NULL;
    }
    
    PyObject* args_class = PyObject_GetAttrString(schemas, "BenchmarkGenerativeTextArgs");
    Py_DECREF(schemas);
    
    if (!args_class) {
        Py_DECREF(benchmark_func);
        return NULL;
    }
    
    // Create args object from kwargs
    PyObject* create_method = PyObject_GetAttrString(args_class, "create");
    Py_DECREF(args_class);
    
    if (!create_method) {
        Py_DECREF(benchmark_func);
        return NULL;
    }
    
    // Build args tuple (scenario=None)
    PyObject* create_args = PyTuple_New(1);
    Py_INCREF(Py_None);
    PyTuple_SET_ITEM(create_args, 0, Py_None);
    
    // Create BenchmarkGenerativeTextArgs from kwargs
    args_obj = PyObject_Call(create_method, create_args, kwargs);
    Py_DECREF(create_method);
    Py_DECREF(create_args);
    
    if (!args_obj) {
        Py_DECREF(benchmark_func);
        return NULL;
    }
    
    // Call the async benchmark function
    PyObject* call_args = PyTuple_New(1);
    PyTuple_SET_ITEM(call_args, 0, args_obj);
    
    result = run_async_function(benchmark_func, call_args, NULL);
    Py_DECREF(call_args);
    Py_DECREF(benchmark_func);
    
    if (!result || !PyTuple_Check(result) || PyTuple_Size(result) != 2) {
        if (result) Py_DECREF(result);
        return NULL;
    }
    
    // Extract report and output_results
    report = PyTuple_GetItem(result, 0);
    output_results = PyTuple_GetItem(result, 1);
    Py_INCREF(report);
    Py_INCREF(output_results);
    
    // Convert output_results to JSON string
    PyObject* json_module = PyImport_ImportModule("json");
    if (!json_module) {
        Py_DECREF(report);
        Py_DECREF(output_results);
        Py_DECREF(result);
        return NULL;
    }
    
    PyObject* dumps = PyObject_GetAttrString(json_module, "dumps");
    Py_DECREF(json_module);
    
    if (!dumps) {
        Py_DECREF(report);
        Py_DECREF(output_results);
        Py_DECREF(result);
        return NULL;
    }
    
    json_str = PyObject_CallFunction(dumps, "O", output_results);
    Py_DECREF(dumps);
    Py_DECREF(report);
    Py_DECREF(output_results);
    Py_DECREF(result);
    
    return json_str;
}

// Reimport report function
static PyObject* guidellm_reimport_report(PyObject* self, PyObject* args, PyObject* kwargs) {
    PyObject* reimport_func = NULL;
    PyObject* result = NULL;
    PyObject* json_str = NULL;
    
    // Import the reimport function
    PyObject* entrypoints = PyImport_ImportModule("guidellm.benchmark.entrypoints");
    if (!entrypoints) {
        return NULL;
    }
    
    reimport_func = PyObject_GetAttrString(entrypoints, "reimport_benchmarks_report");
    Py_DECREF(entrypoints);
    
    if (!reimport_func) {
        return NULL;
    }
    
    // Call the async reimport function
    result = run_async_function(reimport_func, args, kwargs);
    Py_DECREF(reimport_func);
    
    if (!result || !PyTuple_Check(result) || PyTuple_Size(result) != 2) {
        if (result) Py_DECREF(result);
        return NULL;
    }
    
    // Extract output_results and convert to JSON
    PyObject* output_results = PyTuple_GetItem(result, 1);
    Py_INCREF(output_results);
    Py_DECREF(result);
    
    PyObject* json_module = PyImport_ImportModule("json");
    if (!json_module) {
        Py_DECREF(output_results);
        return NULL;
    }
    
    PyObject* dumps = PyObject_GetAttrString(json_module, "dumps");
    Py_DECREF(json_module);
    
    if (!dumps) {
        Py_DECREF(output_results);
        return NULL;
    }
    
    json_str = PyObject_CallFunction(dumps, "O", output_results);
    Py_DECREF(dumps);
    Py_DECREF(output_results);
    
    return json_str;
}

// Get error message (helper)
static PyObject* guidellm_get_error_message(PyObject* self, PyObject* args) {
    PyObject* exc_type = NULL;
    PyObject* exc_value = NULL;
    PyObject* exc_traceback = NULL;
    PyObject* error_str = NULL;
    
    PyErr_Fetch(&exc_type, &exc_value, &exc_traceback);
    
    if (exc_value) {
        error_str = PyObject_Str(exc_value);
        Py_DECREF(exc_value);
    } else {
        error_str = PyUnicode_FromString("Unknown error");
    }
    
    if (exc_type) Py_DECREF(exc_type);
    if (exc_traceback) Py_DECREF(exc_traceback);
    
    return error_str;
}

