#ifndef GUIDELLM_C_API_H
#define GUIDELLM_C_API_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stddef.h>
#include <stdint.h>

// Error codes
typedef enum {
    GUIDELLM_SUCCESS = 0,
    GUIDELLM_ERROR_INVALID_ARG = -1,
    GUIDELLM_ERROR_RUNTIME = -2,
    GUIDELLM_ERROR_MEMORY = -3,
    GUIDELLM_ERROR_UNKNOWN = -4
} guidellm_error_t;

// Benchmark configuration structure with all features
typedef struct {
    // Required fields
    const char* target;              // Target endpoint URL (required)
    const char** data;               // Array of data sources (required)
    size_t data_count;               // Number of data sources
    
    // Benchmark profile configuration
    const char* profile;              // Profile type (default: "sweep")
    double* rate;                     // Request rates array (optional)
    size_t rate_count;                // Number of rates
    const char* phases;               // Phase specification for bursty profile
    int repeat;                       // Number of times to repeat phases (default: 1)
    
    // Backend configuration
    const char* backend;              // Backend type (default: "openai_http")
    const char* model;                // Model identifier (optional)
    const char* backend_kwargs_json;  // Backend kwargs as JSON string (optional)
    
    // Data configuration
    const char* processor;            // Processor/tokenizer path or name (optional)
    const char* processor_args_json;  // Processor args as JSON string (optional)
    const char* request_type;         // Request type/formatter (e.g., "text_completions", "chat_completions")
    int data_samples;                 // Number of samples (-1 for all, default: -1)
    const char** data_args_json;      // Per-dataset args as JSON strings (optional)
    size_t data_args_count;           // Number of data args
    const char* data_column_mapper_json; // Column mapper as JSON string (optional)
    const char* data_collator;        // Data collator type (optional)
    const char* data_sampler;         // Data sampler type (optional)
    int data_num_workers;             // Number of data loading workers (default: 1)
    const char* dataloader_kwargs_json; // Dataloader kwargs as JSON string (optional)
    
    // Output configuration
    const char* output_dir;           // Output directory (optional)
    const char** outputs;             // Output formats array (optional)
    size_t outputs_count;             // Number of output formats
    
    // Benchmarker configuration
    int sample_requests;              // Number of sample requests (default: 10, -1 for all)
    const char* warmup_json;          // Warmup config as JSON string (optional)
    const char* cooldown_json;        // Cooldown config as JSON string (optional)
    double rampup;                    // Rampup duration in seconds (default: 0.0)
    int prefer_response_metrics;      // Prefer response metrics (default: 1/true)
    
    // Constraints configuration
    double max_seconds;               // Max seconds (-1.0 for none)
    int max_requests;                 // Max requests (-1 for none)
    int max_errors;                   // Max errors (-1 for none)
    double max_error_rate;            // Max error rate (-1.0 for none)
    double max_global_error_rate;     // Max global error rate (-1.0 for none)
    const char* over_saturation_json; // Over-saturation config as JSON string (optional)
    
    // Other configuration
    int random_seed;                  // Random seed (default: 42)
} guidellm_benchmark_config_t;

// Report reimport configuration
typedef struct {
    const char* file_path;            // Path to report file (required)
    const char* output_path;          // Output path (optional)
    const char** output_formats;      // Output formats array (optional)
    size_t output_formats_count;      // Number of output formats
} guidellm_reimport_config_t;

// Initialize GuideLLM library
guidellm_error_t guidellm_init(void);

// Cleanup GuideLLM library
void guidellm_cleanup(void);

// Get last error message
const char* guidellm_get_last_error(void);

// Run a benchmark
guidellm_error_t guidellm_run_benchmark(
    const guidellm_benchmark_config_t* config,
    char** output_json,
    size_t* output_json_len
);

// Reimport a benchmark report
guidellm_error_t guidellm_reimport_report(
    const guidellm_reimport_config_t* config,
    char** output_json,
    size_t* output_json_len
);

// Free memory allocated by the library
void guidellm_free(void* ptr);

#ifdef __cplusplus
}
#endif

#endif // GUIDELLM_C_API_H

