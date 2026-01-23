# GuideLLM C/C++ API

This module provides C/C++ bindings for GuideLLM, allowing you to use GuideLLM functionality from C or C++ applications without HTTP requests.

## Architecture

The C/C++ API consists of three main components:

1. **`guidellm_c_api.c`** - Python C extension module that wraps the async Python functions
2. **`guidellm_c_wrapper.c`** - C wrapper library that provides a clean C API interface
3. **`include/guidellm_c_api.h`** - C header file with the public API

## Building

### Building the Python C Extension

The Python C extension (`guidellm_c_api`) is built automatically when you install the package:

```bash
pip install -e .
```

This compiles `src/guidellm/c_api/guidellm_c_api.c` into a Python extension module.

### Building the C Wrapper Library

The C wrapper (`guidellm_c_wrapper.c`) needs to be compiled as a shared library. You can do this manually:

```bash
# Get Python configuration
PYTHON_CONFIG=$(python3-config)

# Compile the wrapper as a shared library
gcc -shared -fPIC \
    -I$(python3-config --includes) \
    -I../include \
    -o libguidellm_c_wrapper.so \
    guidellm_c_wrapper.c \
    $(python3-config --ldflags) \
    -lpython3.12
```

Or create a proper build system using CMake or similar.

## Usage

### From C++

```cpp
#include "guidellm_c_api.h"

int main() {
    // Initialize
    guidellm_init();
    
    // Configure benchmark
    guidellm_benchmark_config_t config = {0};
    config.target = "http://localhost:8000";
    const char* data = "prompt_tokens=256,output_tokens=128";
    config.data = &data;
    config.data_count = 1;
    config.profile = "poisson";
    config.max_seconds = 60.0;
    
    // Run benchmark
    char* output_json = nullptr;
    size_t output_json_len = 0;
    guidellm_error_t result = guidellm_run_benchmark(&config, &output_json, &output_json_len);
    
    if (result == GUIDELLM_SUCCESS) {
        // Use output_json
        guidellm_free(output_json);
    }
    
    // Cleanup
    guidellm_cleanup();
    return 0;
}
```

### From C

The API is C-compatible, so you can use it directly from C code.

## API Reference

### Error Codes

- `GUIDELLM_SUCCESS` - Operation succeeded
- `GUIDELLM_ERROR_INVALID_ARG` - Invalid argument provided
- `GUIDELLM_ERROR_RUNTIME` - Runtime error occurred
- `GUIDELLM_ERROR_MEMORY` - Memory allocation failed
- `GUIDELLM_ERROR_UNKNOWN` - Unknown error

### Functions

#### `guidellm_init()`
Initialize the GuideLLM library. Must be called before any other functions.

#### `guidellm_cleanup()`
Cleanup resources and finalize the library.

#### `guidellm_run_benchmark(config, output_json, output_json_len)`
Run a benchmark with the given configuration.

**Parameters:**
- `config` - Pointer to `guidellm_benchmark_config_t` structure
- `output_json` - Pointer to output buffer (allocated by function)
- `output_json_len` - Pointer to output length

**Returns:** Error code

#### `guidellm_reimport_report(config, output_json, output_json_len)`
Re-import a saved benchmark report and export to other formats.

#### `guidellm_get_last_error()`
Get the last error message as a C string.

#### `guidellm_free(ptr)`
Free memory allocated by the library.

## Configuration Structure

The `guidellm_benchmark_config_t` structure contains all configuration options:

- **Required fields:** `target`, `data`, `data_count`
- **Profile:** `profile`, `rate`, `rate_count`, `phases`, `repeat`
- **Backend:** `backend`, `model`, `backend_kwargs_json`
- **Data:** `processor`, `request_type`, `data_samples`, etc.
- **Output:** `output_dir`, `outputs`, `outputs_count`
- **Constraints:** `max_seconds`, `max_requests`, `max_errors`, etc.

See `include/guidellm_c_api.h` for the complete structure definition.

## Notes

1. The C API requires Python to be initialized. Make sure Python and the `guidellm` package are installed.

2. All string parameters are expected to be UTF-8 encoded.

3. JSON parameters (like `backend_kwargs_json`) should be valid JSON strings.

4. Memory returned by the API must be freed using `guidellm_free()`.

5. The API is not thread-safe. Use appropriate synchronization for multi-threaded applications.

