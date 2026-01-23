# C/C++ API Examples

This directory contains examples for using GuideLLM's C/C++ API.

## Building the C Extension

First, build and install the Python package with C extensions:

```bash
cd /path/to/guidellm
pip install -e .
```

This will compile the `guidellm_c_api` Python C extension module.

## C++ Example

The `cpp_example.cpp` file demonstrates how to use the C API from C++ to run a benchmark that matches the command:

```bash
guidellm benchmark run --target http://192.168.2.34:8000 \
  --request-type text_completions --profile poisson \
  --rate 1 --rate 2 --rate 3 --rate 4 --rate 5 --rate 6 --rate 7 \
  --rate 8 --rate 9 --rate 12 --rate 16 --rate 24 --rate 32 \
  --data "dist://prompt_tokens=[32,128,512,2040];prompt_probs=[0.35,0.35,0.20,0.10];output_tokens=[32,128,512];output_probs=[0.50,0.35,0.15]" \
  --processor microsoft/phi-4 --random-seed 42 --max-seconds 60
```

### Building the C++ Example

**Note:** The C wrapper (`guidellm_c_wrapper.c`) needs to be compiled as a shared library first. For now, you can use Python's C API directly:

```bash
cd examples
g++ -std=c++11 -I../include $(python3-config --includes) \
    -o cpp_example cpp_example.cpp \
    $(python3-config --ldflags) -lpython3.12
```

Or use the provided Makefile:

```bash
cd examples
make
```

### Running the Example

```bash
./cpp_example
```

## Using the C API Directly

The C API header (`include/guidellm_c_api.h`) provides a complete interface. The main functions are:

- `guidellm_init()` - Initialize the library
- `guidellm_run_benchmark()` - Run a benchmark with the given configuration
- `guidellm_reimport_report()` - Re-import and export a saved benchmark report
- `guidellm_get_last_error()` - Get the last error message
- `guidellm_cleanup()` - Cleanup resources

## Important Notes

1. **Python Environment**: The C API requires Python to be initialized. Make sure Python and the `guidellm` package are installed in your environment.

2. **Memory Management**: Always call `guidellm_free()` on any memory returned by the API functions.

3. **Error Handling**: Check return codes and use `guidellm_get_last_error()` to get detailed error messages.

4. **Thread Safety**: The current implementation is not thread-safe. Use appropriate synchronization if calling from multiple threads.

