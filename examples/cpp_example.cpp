#include "../include/guidellm_c_api.h"
#include <iostream>
#include <vector>
#include <cstring>

int main() {
    // Initialize GuideLLM
    if (guidellm_init() != GUIDELLM_SUCCESS) {
        std::cerr << "Error initializing GuideLLM: " << guidellm_get_last_error() << std::endl;
        return 1;
    }
    
    // Setup configuration matching your command:
    // guidellm benchmark run --target http://192.168.2.34:8000 
    //   --request-type text_completions --profile poisson 
    //   --rate 1 --rate 2 --rate 3 --rate 4 --rate 5 --rate 6 --rate 7 
    //   --rate 8 --rate 9 --rate 12 --rate 16 --rate 24 --rate 32 
    //   --data "dist://prompt_tokens=[32,128,512,2040];prompt_probs=[0.35,0.35,0.20,0.10];output_tokens=[32,128,512];output_probs=[0.50,0.35,0.15]" 
    //   --processor microsoft/phi-4 --random-seed 42 --max-seconds 60
    
    guidellm_benchmark_config_t config = {0};
    
    // Required fields
    config.target = "http://192.168.2.34:8000";
    
    // Data with distribution URI
    const char* data_source = "dist://prompt_tokens=[32,128,512,2040];prompt_probs=[0.35,0.35,0.20,0.10];output_tokens=[32,128,512];output_probs=[0.50,0.35,0.15]";
    config.data = &data_source;
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
    
    // Set defaults for optional fields that need explicit values
    config.data_samples = -1;  // Use all samples
    config.sample_requests = 10;  // Default sample requests
    config.prefer_response_metrics = 1;  // True
    config.max_requests = -1;  // No limit
    config.max_errors = -1;  // No limit
    config.max_error_rate = -1.0;  // No limit
    config.max_global_error_rate = -1.0;  // No limit
    config.data_num_workers = 1;  // Default workers
    
    // Run benchmark
    char* output_json = nullptr;
    size_t output_json_len = 0;
    
    std::cout << "Running benchmark..." << std::endl;
    std::cout << "Target: " << config.target << std::endl;
    std::cout << "Profile: " << config.profile << std::endl;
    std::cout << "Rates: ";
    for (size_t i = 0; i < config.rate_count; i++) {
        std::cout << config.rate[i];
        if (i < config.rate_count - 1) std::cout << ", ";
    }
    std::cout << std::endl;
    
    guidellm_error_t result = guidellm_run_benchmark(&config, &output_json, &output_json_len);
    
    if (result == GUIDELLM_SUCCESS) {
        std::cout << "\nBenchmark completed successfully!" << std::endl;
        std::cout << "Output results (JSON):" << std::endl;
        std::cout << output_json << std::endl;
        guidellm_free(output_json);
    } else {
        std::cerr << "Error running benchmark: " << guidellm_get_last_error() << std::endl;
        guidellm_cleanup();
        return 1;
    }
    
    // Cleanup
    guidellm_cleanup();
    std::cout << "\nDone!" << std::endl;
    return 0;
}

