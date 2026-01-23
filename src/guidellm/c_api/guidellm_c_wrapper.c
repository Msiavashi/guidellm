#include <Python.h>
#include <stdlib.h>
#include <string.h>

// Include the header - when compiling, use -I flag to point to include directory
// For example: -I../../include or -I/path/to/guidellm/include
// We'll define the structure inline here to avoid path issues
// In production, you'd compile with: gcc -I../../include ...

#ifndef GUIDELLM_C_API_H
// Define the structures and functions inline if header not available
// This allows the file to compile standalone, but ideally you'd use the header

typedef enum {
    GUIDELLM_SUCCESS = 0,
    GUIDELLM_ERROR_INVALID_ARG = -1,
    GUIDELLM_ERROR_RUNTIME = -2,
    GUIDELLM_ERROR_MEMORY = -3,
    GUIDELLM_ERROR_UNKNOWN = -4
} guidellm_error_t;

typedef struct {
    const char* target;
    const char** data;
    size_t data_count;
    const char* profile;
    double* rate;
    size_t rate_count;
    const char* phases;
    int repeat;
    const char* backend;
    const char* model;
    const char* backend_kwargs_json;
    const char* processor;
    const char* processor_args_json;
    const char* request_type;
    int data_samples;
    const char** data_args_json;
    size_t data_args_count;
    const char* data_column_mapper_json;
    const char* data_collator;
    const char* data_sampler;
    int data_num_workers;
    const char* dataloader_kwargs_json;
    const char* output_dir;
    const char** outputs;
    size_t outputs_count;
    int sample_requests;
    const char* warmup_json;
    const char* cooldown_json;
    double rampup;
    int prefer_response_metrics;
    double max_seconds;
    int max_requests;
    int max_errors;
    double max_error_rate;
    double max_global_error_rate;
    const char* over_saturation_json;
    int random_seed;
} guidellm_benchmark_config_t;

typedef struct {
    const char* file_path;
    const char* output_path;
    const char** output_formats;
    size_t output_formats_count;
} guidellm_reimport_config_t;

guidellm_error_t guidellm_init(void);
void guidellm_cleanup(void);
const char* guidellm_get_last_error(void);
guidellm_error_t guidellm_run_benchmark(
    const guidellm_benchmark_config_t* config,
    char** output_json,
    size_t* output_json_len
);
guidellm_error_t guidellm_reimport_report(
    const guidellm_reimport_config_t* config,
    char** output_json,
    size_t* output_json_len
);
void guidellm_free(void* ptr);

#else
#include "guidellm_c_api.h"
#endif

static char* last_error = NULL;
static int python_initialized = 0;

static void set_error(const char* error_msg) {
    if (last_error) {
        free(last_error);
    }
    if (error_msg) {
        last_error = strdup(error_msg);
    } else {
        last_error = NULL;
    }
}

guidellm_error_t guidellm_init(void) {
    if (!python_initialized) {
        Py_Initialize();
        if (!Py_IsInitialized()) {
            set_error("Failed to initialize Python");
            return GUIDELLM_ERROR_RUNTIME;
        }
        python_initialized = 1;
    }
    return GUIDELLM_SUCCESS;
}

void guidellm_cleanup(void) {
    if (last_error) {
        free(last_error);
        last_error = NULL;
    }
    if (python_initialized) {
        Py_Finalize();
        python_initialized = 0;
    }
}

const char* guidellm_get_last_error(void) {
    return last_error ? last_error : "No error";
}

void guidellm_free(void* ptr) {
    if (ptr) {
        free(ptr);
    }
}

// Helper to add JSON string to dict
static void add_json_to_dict(PyObject* dict, const char* key, const char* json_str) {
    if (!json_str) return;
    
    PyObject* json_module = PyImport_ImportModule("json");
    if (!json_module) return;
    
    PyObject* loads = PyObject_GetAttrString(json_module, "loads");
    Py_DECREF(json_module);
    
    if (!loads) return;
    
    PyObject* json_obj = PyObject_CallFunction(loads, "s", json_str);
    Py_DECREF(loads);
    
    if (json_obj) {
        PyDict_SetItemString(dict, key, json_obj);
        Py_DECREF(json_obj);
    }
}

guidellm_error_t guidellm_run_benchmark(
    const guidellm_benchmark_config_t* config,
    char** output_json,
    size_t* output_json_len
) {
    if (!config || !output_json || !output_json_len) {
        set_error("Invalid arguments");
        return GUIDELLM_ERROR_INVALID_ARG;
    }
    
    if (!config->target || !config->data || config->data_count == 0) {
        set_error("Required fields missing: target and data");
        return GUIDELLM_ERROR_INVALID_ARG;
    }
    
    if (!python_initialized) {
        guidellm_error_t err = guidellm_init();
        if (err != GUIDELLM_SUCCESS) {
            return err;
        }
    }
    
    // Import the C API module
    PyObject* module = PyImport_ImportModule("guidellm_c_api");
    if (!module) {
        PyObject* error = PyErr_Occurred();
        if (error) {
            PyObject* error_str = PyObject_Str(error);
            const char* error_msg = PyUnicode_AsUTF8(error_str);
            set_error(error_msg);
            Py_DECREF(error_str);
        } else {
            set_error("Failed to import guidellm_c_api module");
        }
        return GUIDELLM_ERROR_RUNTIME;
    }
    
    PyObject* func = PyObject_GetAttrString(module, "run_benchmark");
    Py_DECREF(module);
    
    if (!func) {
        set_error("Failed to get run_benchmark function");
        return GUIDELLM_ERROR_RUNTIME;
    }
    
    // Build keyword arguments dictionary
    PyObject* kwargs = PyDict_New();
    
    // Required fields
    PyDict_SetItemString(kwargs, "target", PyUnicode_FromString(config->target));
    
    // Data array
    PyObject* data_list = PyList_New(config->data_count);
    for (size_t i = 0; i < config->data_count; i++) {
        PyList_SetItem(data_list, i, PyUnicode_FromString(config->data[i]));
    }
    PyDict_SetItemString(kwargs, "data", data_list);
    
    // Profile configuration
    if (config->profile) {
        PyDict_SetItemString(kwargs, "profile", PyUnicode_FromString(config->profile));
    }
    
    if (config->rate && config->rate_count > 0) {
        PyObject* rate_list = PyList_New(config->rate_count);
        for (size_t i = 0; i < config->rate_count; i++) {
            PyList_SetItem(rate_list, i, PyFloat_FromDouble(config->rate[i]));
        }
        PyDict_SetItemString(kwargs, "rate", rate_list);
    }
    
    if (config->phases) {
        PyDict_SetItemString(kwargs, "phases", PyUnicode_FromString(config->phases));
    }
    
    if (config->repeat > 0) {
        PyDict_SetItemString(kwargs, "repeat", PyLong_FromLong(config->repeat));
    }
    
    // Backend configuration
    if (config->backend) {
        PyDict_SetItemString(kwargs, "backend", PyUnicode_FromString(config->backend));
    }
    
    if (config->model) {
        PyDict_SetItemString(kwargs, "model", PyUnicode_FromString(config->model));
    }
    
    if (config->backend_kwargs_json) {
        add_json_to_dict(kwargs, "backend_kwargs", config->backend_kwargs_json);
    }
    
    // Data configuration
    if (config->processor) {
        PyDict_SetItemString(kwargs, "processor", PyUnicode_FromString(config->processor));
    }
    
    if (config->processor_args_json) {
        add_json_to_dict(kwargs, "processor_args", config->processor_args_json);
    }
    
    if (config->request_type) {
        PyDict_SetItemString(kwargs, "request_type", PyUnicode_FromString(config->request_type));
    }
    
    if (config->data_samples != -1) {
        PyDict_SetItemString(kwargs, "data_samples", PyLong_FromLong(config->data_samples));
    }
    
    if (config->data_args_json && config->data_args_count > 0) {
        PyObject* data_args_list = PyList_New(config->data_args_count);
        for (size_t i = 0; i < config->data_args_count; i++) {
            if (config->data_args_json[i]) {
                PyObject* json_module = PyImport_ImportModule("json");
                if (json_module) {
                    PyObject* loads = PyObject_GetAttrString(json_module, "loads");
                    Py_DECREF(json_module);
                    if (loads) {
                        PyObject* json_obj = PyObject_CallFunction(loads, "s", config->data_args_json[i]);
                        PyList_SetItem(data_args_list, i, json_obj);
                        Py_DECREF(loads);
                    }
                }
            }
        }
        PyDict_SetItemString(kwargs, "data_args", data_args_list);
    }
    
    if (config->data_column_mapper_json) {
        add_json_to_dict(kwargs, "data_column_mapper", config->data_column_mapper_json);
    }
    
    if (config->data_collator) {
        PyDict_SetItemString(kwargs, "data_collator", PyUnicode_FromString(config->data_collator));
    }
    
    if (config->data_sampler) {
        PyDict_SetItemString(kwargs, "data_sampler", PyUnicode_FromString(config->data_sampler));
    }
    
    if (config->data_num_workers > 0) {
        PyDict_SetItemString(kwargs, "data_num_workers", PyLong_FromLong(config->data_num_workers));
    }
    
    if (config->dataloader_kwargs_json) {
        add_json_to_dict(kwargs, "dataloader_kwargs", config->dataloader_kwargs_json);
    }
    
    // Output configuration
    if (config->output_dir) {
        PyDict_SetItemString(kwargs, "output_dir", PyUnicode_FromString(config->output_dir));
    }
    
    if (config->outputs && config->outputs_count > 0) {
        PyObject* outputs_list = PyList_New(config->outputs_count);
        for (size_t i = 0; i < config->outputs_count; i++) {
            PyList_SetItem(outputs_list, i, PyUnicode_FromString(config->outputs[i]));
        }
        PyDict_SetItemString(kwargs, "outputs", outputs_list);
    }
    
    // Benchmarker configuration
    if (config->sample_requests >= 0) {
        PyObject* sample_val = (config->sample_requests > 0) 
            ? PyLong_FromLong(config->sample_requests) 
            : Py_None;
        Py_INCREF(sample_val);
        PyDict_SetItemString(kwargs, "sample_requests", sample_val);
    }
    
    if (config->warmup_json) {
        add_json_to_dict(kwargs, "warmup", config->warmup_json);
    }
    
    if (config->cooldown_json) {
        add_json_to_dict(kwargs, "cooldown", config->cooldown_json);
    }
    
    if (config->rampup > 0.0) {
        PyDict_SetItemString(kwargs, "rampup", PyFloat_FromDouble(config->rampup));
    }
    
    if (config->prefer_response_metrics >= 0) {
        PyDict_SetItemString(kwargs, "prefer_response_metrics", 
            PyBool_FromLong(config->prefer_response_metrics));
    }
    
    // Constraints configuration
    if (config->max_seconds >= 0.0) {
        PyObject* max_sec_val = (config->max_seconds > 0) 
            ? PyFloat_FromDouble(config->max_seconds) 
            : Py_None;
        Py_INCREF(max_sec_val);
        PyDict_SetItemString(kwargs, "max_seconds", max_sec_val);
    }
    
    if (config->max_requests >= 0) {
        PyObject* max_req_val = (config->max_requests > 0) 
            ? PyLong_FromLong(config->max_requests) 
            : Py_None;
        Py_INCREF(max_req_val);
        PyDict_SetItemString(kwargs, "max_requests", max_req_val);
    }
    
    if (config->max_errors >= 0) {
        PyObject* max_err_val = (config->max_errors > 0) 
            ? PyLong_FromLong(config->max_errors) 
            : Py_None;
        Py_INCREF(max_err_val);
        PyDict_SetItemString(kwargs, "max_errors", max_err_val);
    }
    
    if (config->max_error_rate >= 0.0) {
        PyObject* max_err_rate_val = (config->max_error_rate > 0) 
            ? PyFloat_FromDouble(config->max_error_rate) 
            : Py_None;
        Py_INCREF(max_err_rate_val);
        PyDict_SetItemString(kwargs, "max_error_rate", max_err_rate_val);
    }
    
    if (config->max_global_error_rate >= 0.0) {
        PyObject* max_global_err_rate_val = (config->max_global_error_rate > 0) 
            ? PyFloat_FromDouble(config->max_global_error_rate) 
            : Py_None;
        Py_INCREF(max_global_err_rate_val);
        PyDict_SetItemString(kwargs, "max_global_error_rate", max_global_err_rate_val);
    }
    
    if (config->over_saturation_json) {
        add_json_to_dict(kwargs, "over_saturation", config->over_saturation_json);
    }
    
    // Other configuration
    if (config->random_seed >= 0) {
        PyDict_SetItemString(kwargs, "random_seed", PyLong_FromLong(config->random_seed));
    }
    
    // Call the Python function
    PyObject* result = PyObject_Call(func, PyTuple_New(0), kwargs);
    Py_DECREF(kwargs);
    Py_DECREF(func);
    
    if (!result) {
        PyObject* error = PyErr_Occurred();
        if (error) {
            PyObject* error_str = PyObject_Str(error);
            const char* error_msg = PyUnicode_AsUTF8(error_str);
            set_error(error_msg);
            Py_DECREF(error_str);
        } else {
            set_error("Failed to run benchmark");
        }
        return GUIDELLM_ERROR_RUNTIME;
    }
    
    // Convert result to JSON string
    const char* json_str = PyUnicode_AsUTF8(result);
    if (!json_str) {
        Py_DECREF(result);
        set_error("Failed to convert result to string");
        return GUIDELLM_ERROR_RUNTIME;
    }
    
    *output_json_len = strlen(json_str);
    *output_json = (char*)malloc(*output_json_len + 1);
    if (!*output_json) {
        Py_DECREF(result);
        set_error("Memory allocation failed");
        return GUIDELLM_ERROR_MEMORY;
    }
    
    strcpy(*output_json, json_str);
    Py_DECREF(result);
    
    return GUIDELLM_SUCCESS;
}

guidellm_error_t guidellm_reimport_report(
    const guidellm_reimport_config_t* config,
    char** output_json,
    size_t* output_json_len
) {
    if (!config || !output_json || !output_json_len) {
        set_error("Invalid arguments");
        return GUIDELLM_ERROR_INVALID_ARG;
    }
    
    if (!config->file_path) {
        set_error("Required field missing: file_path");
        return GUIDELLM_ERROR_INVALID_ARG;
    }
    
    if (!python_initialized) {
        guidellm_error_t err = guidellm_init();
        if (err != GUIDELLM_SUCCESS) {
            return err;
        }
    }
    
    // Import the C API module
    PyObject* module = PyImport_ImportModule("guidellm_c_api");
    if (!module) {
        PyObject* error = PyErr_Occurred();
        if (error) {
            PyObject* error_str = PyObject_Str(error);
            const char* error_msg = PyUnicode_AsUTF8(error_str);
            set_error(error_msg);
            Py_DECREF(error_str);
        } else {
            set_error("Failed to import guidellm_c_api module");
        }
        return GUIDELLM_ERROR_RUNTIME;
    }
    
    PyObject* func = PyObject_GetAttrString(module, "reimport_report");
    Py_DECREF(module);
    
    if (!func) {
        set_error("Failed to get reimport_report function");
        return GUIDELLM_ERROR_RUNTIME;
    }
    
    // Build arguments
    PyObject* args = PyTuple_New(3);
    PyTuple_SET_ITEM(args, 0, PyUnicode_FromString(config->file_path));
    PyTuple_SET_ITEM(args, 1, config->output_path ? PyUnicode_FromString(config->output_path) : Py_None);
    
    // Build output_formats tuple
    PyObject* output_formats = Py_None;
    if (config->output_formats && config->output_formats_count > 0) {
        output_formats = PyTuple_New(config->output_formats_count);
        for (size_t i = 0; i < config->output_formats_count; i++) {
            PyTuple_SET_ITEM(output_formats, i, PyUnicode_FromString(config->output_formats[i]));
        }
    } else {
        Py_INCREF(Py_None);
    }
    PyTuple_SET_ITEM(args, 2, output_formats);
    
    // Call the Python function
    PyObject* result = PyObject_CallObject(func, args);
    Py_DECREF(args);
    Py_DECREF(func);
    
    if (!result) {
        PyObject* error = PyErr_Occurred();
        if (error) {
            PyObject* error_str = PyObject_Str(error);
            const char* error_msg = PyUnicode_AsUTF8(error_str);
            set_error(error_msg);
            Py_DECREF(error_str);
        } else {
            set_error("Failed to reimport report");
        }
        return GUIDELLM_ERROR_RUNTIME;
    }
    
    // Convert result to JSON string
    const char* json_str = PyUnicode_AsUTF8(result);
    if (!json_str) {
        Py_DECREF(result);
        set_error("Failed to convert result to string");
        return GUIDELLM_ERROR_RUNTIME;
    }
    
    *output_json_len = strlen(json_str);
    *output_json = (char*)malloc(*output_json_len + 1);
    if (!*output_json) {
        Py_DECREF(result);
        set_error("Memory allocation failed");
        return GUIDELLM_ERROR_MEMORY;
    }
    
    strcpy(*output_json, json_str);
    Py_DECREF(result);
    
    return GUIDELLM_SUCCESS;
}

