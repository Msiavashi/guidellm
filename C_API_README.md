# GuideLLM C/C++ API

This document describes how to use GuideLLM's C/C++ API to generate workloads and create reports from C or C++ applications, without using HTTP requests.

## Overview

The C/C++ API provides a complete interface to all GuideLLM functionality, allowing you to:

- Run benchmarks with full configuration support
- Generate reports in multiple formats (JSON, CSV, HTML)
- Re-import and re-export existing benchmark reports
- Use all features available in the CLI

## Architecture

The API consists of:

1. **Python C Extension** (`guidellm_c_api`) - Wraps Python async functions
2. **C Wrapper Library** (`libguidellm_c_wrapper.so`) - Provides clean C API
3. **C Header** (`include/guidellm_c_api.h`) - Public API definition

## Building

### Step 1: Install GuideLLM with C Extensions

```bash
cd /path/to/guidellm
pip install -e .
```

This builds the Python C extension module automatically.

### Step 2: Build the C Wrapper Library

```bash
./build_c_api.sh
```

This creates `build/libguidellm_c_wrapper.so` that you can link against.

## Usage Example

Here's a complete C++ example that matches your command:

```cpp
#include "include/guidellm_c_api.h"
#include <iostream>
#include <vector>

int main() {
    // Initialize
    if (guidellm_init() != GUIDELLM_SUCCESS) {
        std::cerr << "Error: " << guidellm_get_last_error() << std::endl;
        return 1;
    }
    
    // Configure benchmark
    guidellm_benchmark_config_t config = {0};
    
    // Required fields
    config.target = "http://192.168.2.34:8000";
    const char* data = "dist://prompt_tokens=[32,128,512,2040];prompt_probs=[0.35,0.35,0.20,0.10];output_tokens=[32,128,512];output_probs=[0.50,0.35,0.15]";
    config.data = &data;
    config.data_count = 1;
    
    // Profile and rates
    config.profile = "poisson";
    std::vector<double> rates = {1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 16, 24, 32};
    config.rate = rates.data();
    config.rate_count = rates.size();
    
    // Request type
    config.request_type = "text_completions";
    
    // Processor
    config.processor = "microsoft/phi-4";
    
    // Constraints
    config.max_seconds = 60.0;
    config.random_seed = 42;
    
    // Run benchmark
    char* output_json = nullptr;
    size_t output_json_len = 0;
    
    guidellm_error_t result = guidellm_run_benchmark(&config, &output_json, &output_json_len);
    
    if (result == GUIDELLM_SUCCESS) {
        std::cout << "Benchmark completed!" << std::endl;
        std::cout << "Results: " << output_json << std::endl;
        guidellm_free(output_json);
    } else {
        std::cerr << "Error: " << guidellm_get_last_error() << std::endl;
    }
    
    guidellm_cleanup();
    return 0;
}
```

### Compiling the Example

```bash
g++ -std=c++11 -I. -L./build \
    -o example examples/cpp_example.cpp \
    -lguidellm_c_wrapper \
    $(python3-config --ldflags) -lpython3.12
```

## API Reference

### Initialization

```c
guidellm_error_t guidellm_init(void);
void guidellm_cleanup(void);
const char* guidellm_get_last_error(void);
```

### Running Benchmarks

```c
guidellm_error_t guidellm_run_benchmark(
    const guidellm_benchmark_config_t* config,
    char** output_json,
    size_t* output_json_len
);
```

### Re-importing Reports

```c
guidellm_error_t guidellm_reimport_report(
    const guidellm_reimport_config_t* config,
    char** output_json,
    size_t* output_json_len
);
```

### Memory Management

```c
void guidellm_free(void* ptr);
```

## Configuration Structure

The `guidellm_benchmark_config_t` structure supports all CLI options:

- **Target & Data:** `target`, `data[]`, `data_count`
- **Profile:** `profile`, `rate[]`, `rate_count`, `phases`, `repeat`
- **Backend:** `backend`, `model`, `backend_kwargs_json`
- **Data Processing:** `processor`, `request_type`, `data_samples`, etc.
- **Output:** `output_dir`, `outputs[]`, `outputs_count`
- **Constraints:** `max_seconds`, `max_requests`, `max_errors`, etc.
- **Other:** `random_seed`, `warmup_json`, `cooldown_json`, etc.

See `include/guidellm_c_api.h` for complete documentation.

## Feature Parity

✅ **All CLI features are supported**, including:

- All profile types (sweep, poisson, constant, concurrent, etc.)
- Multiple rate values
- Distribution URIs for data (`dist://...`)
- All request types (text_completions, chat_completions, etc.)
- All processors and tokenizers
- All output formats (json, csv, html)
- All constraints (max_seconds, max_requests, etc.)
- Warmup/cooldown configuration
- Over-saturation detection
- And more...

## Requirements

- Python 3.10+ with development headers
- GCC or compatible C compiler
- GuideLLM package installed
- Python C API libraries

## Troubleshooting

### "Failed to import guidellm_c_api module"

Make sure you've installed the package: `pip install -e .`

### "Failed to initialize Python"

Ensure Python development headers are installed:
- Ubuntu/Debian: `sudo apt-get install python3-dev`
- Fedora: `sudo dnf install python3-devel`
- macOS: Usually included with Xcode

### Linking errors

Make sure you're linking against:
- `libguidellm_c_wrapper.so` (from build/)
- Python library (`-lpython3.12` or similar)
- Python C API flags from `python3-config --ldflags`

## Examples

See `examples/` directory for complete working examples.

