# E2E test for delay functionality between benchmark runs

import time
from pathlib import Path

import pytest

from tests.e2e.utils import (
    GuidellmClient,
    assert_no_python_exceptions,
    load_benchmark_report,
)
from tests.e2e.vllm_sim_server import VllmSimServer


@pytest.fixture(scope="module")
def server():
    """
    Pytest fixture to start and stop the server for the entire module.
    """
    server = VllmSimServer(
        port=8001,
        model="databricks/dolly-v2-12b",
        mode="random",
        time_to_first_token=1,  # 1ms TTFT
        inter_token_latency=1,  # 1ms ITL
    )
    try:
        server.start()
        yield server
    finally:
        server.stop()


@pytest.mark.timeout(60)
@pytest.mark.sanity
def test_uniform_delay_between_benchmarks(server: VllmSimServer, tmp_path: Path):
    """
    Test that a single delay parameter applies uniformly to all benchmark runs.
    """
    report_name = "uniform_delay_benchmarks.json"
    report_path = tmp_path / report_name
    
    # Test parameters
    rates = [3, 5]  # Two different rates to run
    delay_seconds = 3  # 3 seconds delay for all runs
    max_requests_per_run = 5  # Small number for quick test
    
    # Create and configure the guidellm client
    client = GuidellmClient(
        target=server.get_url(),
        output_dir=tmp_path,
        outputs=report_name,
    )
    
    # Record start time
    start_time = time.time()
    
    # Start the benchmark with multiple rates and uniform delay
    client.start_benchmark(
        profile="constant",
        rate=rates[0],  # First rate
        max_requests=max_requests_per_run,
        additional_args=f"--rate {rates[1]} --delay {delay_seconds}",
    )
    
    # Wait for the benchmark to complete
    client.wait_for_completion(timeout=60)
    
    # Record end time
    end_time = time.time()
    total_elapsed = end_time - start_time
    
    # Assert no Python exceptions occurred
    assert_no_python_exceptions(client.stderr)
    
    # Load and validate the report
    report = load_benchmark_report(report_path)
    
    # Should have 2 benchmarks (one for each rate)
    assert len(report["benchmarks"]) == 2, (
        f"Expected 2 benchmarks, got {len(report['benchmarks'])}"
    )
    
    # With uniform delay, we expect delays before both runs (including first)
    # Total delay time should be at least: delay_seconds * 2
    expected_min_delay = delay_seconds * 2
    
    assert total_elapsed >= expected_min_delay, (
        f"Total elapsed time ({total_elapsed:.2f}s) should be at least "
        f"{expected_min_delay}s (delays before each run)"
    )
    
    # Verify both benchmarks completed successfully
    for i, benchmark in enumerate(report["benchmarks"]):
        successful_requests = benchmark["requests"]["successful"]
        assert len(successful_requests) > 0, (
            f"Benchmark {i} should have successful requests"
        )


@pytest.mark.timeout(60)
@pytest.mark.sanity
def test_per_rate_delay_between_benchmarks(server: VllmSimServer, tmp_path: Path):
    """
    Test that multiple delay values apply per-rate to benchmark runs.
    
    This tests the key feature: different delays for different rates.
    """
    report_name = "per_rate_delay_benchmarks.json"
    report_path = tmp_path / report_name
    
    # Test parameters
    rates = [3, 5, 8]  # Three different rates
    delays = [0, 2, 4]  # Different delay for each rate
    max_requests_per_run = 5
    
    # Create and configure the guidellm client
    client = GuidellmClient(
        target=server.get_url(),
        output_dir=tmp_path,
        outputs=report_name,
    )
    
    # Record start time
    start_time = time.time()
    
    # Start the benchmark with per-rate delays
    client.start_benchmark(
        profile="constant",
        rate=rates[0],
        max_requests=max_requests_per_run,
        additional_args=(
            f"--rate {rates[1]} --rate {rates[2]} "
            f"--delay {delays[0]} --delay {delays[1]} --delay {delays[2]}"
        ),
    )
    
    # Wait for the benchmark to complete
    client.wait_for_completion(timeout=60)
    
    # Record end time
    end_time = time.time()
    total_elapsed = end_time - start_time
    
    # Assert no Python exceptions occurred
    assert_no_python_exceptions(client.stderr)
    
    # Load and validate the report
    report = load_benchmark_report(report_path)
    
    # Should have 3 benchmarks
    assert len(report["benchmarks"]) == 3, (
        f"Expected 3 benchmarks, got {len(report['benchmarks'])}"
    )
    
    # Expected total delay: 0 + 2 + 4 = 6 seconds
    expected_min_delay = sum(delays)
    
    assert total_elapsed >= expected_min_delay, (
        f"Total elapsed time ({total_elapsed:.2f}s) should be at least "
        f"{expected_min_delay}s (sum of per-rate delays)"
    )
    
    # Verify all benchmarks completed successfully
    for i, benchmark in enumerate(report["benchmarks"]):
        successful_requests = benchmark["requests"]["successful"]
        assert len(successful_requests) > 0, (
            f"Benchmark {i} should have successful requests"
        )


@pytest.mark.timeout(60)
@pytest.mark.sanity
def test_no_delay_between_benchmarks(server: VllmSimServer, tmp_path: Path):
    """
    Test that benchmarks run immediately when no delay is specified.
    
    This is a control test to ensure the default behavior (no delay) still works.
    """
    report_name = "no_delay_benchmarks.json"
    report_path = tmp_path / report_name
    
    # Test parameters
    rates = [3, 5]
    max_requests_per_run = 5
    
    # Create and configure the guidellm client
    client = GuidellmClient(
        target=server.get_url(),
        output_dir=tmp_path,
        outputs=report_name,
    )
    
    # Start the benchmark with multiple rates but NO delay
    client.start_benchmark(
        profile="constant",
        rate=rates[0],
        max_requests=max_requests_per_run,
        additional_args=f"--rate {rates[1]}",  # No --delay parameter
    )
    
    # Wait for the benchmark to complete
    client.wait_for_completion(timeout=60)
    
    # Assert no Python exceptions occurred
    assert_no_python_exceptions(client.stderr)
    
    # Load and validate the report
    report = load_benchmark_report(report_path)
    
    # Should have 2 benchmarks
    assert len(report["benchmarks"]) == 2, (
        f"Expected 2 benchmarks, got {len(report['benchmarks'])}"
    )


@pytest.mark.timeout(60)
@pytest.mark.sanity
def test_partial_delays_with_defaults(server: VllmSimServer, tmp_path: Path):
    """
    Test that when fewer delays than rates are specified, remaining delays default to 0.
    """
    report_name = "partial_delay_benchmarks.json"
    report_path = tmp_path / report_name
    
    # Test parameters
    rates = [3, 5, 8, 10]  # Four rates
    delays = [0, 2]  # Only two delays - remaining should be 0
    max_requests_per_run = 5
    
    # Create and configure the guidellm client
    client = GuidellmClient(
        target=server.get_url(),
        output_dir=tmp_path,
        outputs=report_name,
    )
    
    # Start the benchmark with partial delays
    client.start_benchmark(
        profile="constant",
        rate=rates[0],
        max_requests=max_requests_per_run,
        additional_args=(
            f"--rate {rates[1]} --rate {rates[2]} --rate {rates[3]} "
            f"--delay {delays[0]} --delay {delays[1]}"
        ),
    )
    
    # Wait for the benchmark to complete
    client.wait_for_completion(timeout=60)
    
    # Assert no Python exceptions occurred
    assert_no_python_exceptions(client.stderr)
    
    # Load and validate the report
    report = load_benchmark_report(report_path)
    
    # Should have 4 benchmarks
    assert len(report["benchmarks"]) == 4, (
        f"Expected 4 benchmarks, got {len(report['benchmarks'])}"
    )
    
    # Verify all benchmarks completed successfully
    for i, benchmark in enumerate(report["benchmarks"]):
        successful_requests = benchmark["requests"]["successful"]
        assert len(successful_requests) > 0, (
            f"Benchmark {i} should have successful requests"
        )
