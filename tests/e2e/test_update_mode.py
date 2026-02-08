# E2E test for update mode functionality

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
        port=8003,
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


@pytest.mark.timeout(120)
@pytest.mark.sanity
def test_update_replaces_matching_rate(server: VllmSimServer, tmp_path: Path):
    """
    Test that update mode replaces matching rate benchmark while preserving others.
    
    This is the core update functionality - re-running a specific rate updates
    only that benchmark while keeping others intact.
    """
    report_name = "benchmarks.json"
    report_path = tmp_path / report_name
    
    # Step 1: Run initial sweep with 3 rates
    client1 = GuidellmClient(
        target=server.get_url(),
        output_dir=tmp_path,
        outputs=report_name,
    )
    
    client1.start_benchmark(
        profile="constant",
        rate=3,
        max_requests=5,
        additional_args="--rate 5 --rate 8",
    )
    client1.wait_for_completion(timeout=60)
    assert_no_python_exceptions(client1.stderr)
    
    # Verify initial report
    report1 = load_benchmark_report(report_path)
    assert len(report1["benchmarks"]) == 3, "Should have 3 benchmarks initially"
    
    # Extract request counts from initial benchmarks
    initial_counts = {
        i: len(bm["requests"]["successful"])
        for i, bm in enumerate(report1["benchmarks"])
    }
    
    # Step 2: Re-run only rate 5 with update mode
    client2 = GuidellmClient(
        target=server.get_url(),
        output_dir=tmp_path,
        outputs=report_name,
    )
    
    client2.start_benchmark(
        profile="constant",
        rate=5,
        max_requests=8,  # Different from initial (5 requests)
        additional_args="--update",
    )
    client2.wait_for_completion(timeout=60)
    assert_no_python_exceptions(client2.stderr)
    
    # Verify updated report
    report2 = load_benchmark_report(report_path)
    
    # Should still have 3 benchmarks
    assert len(report2["benchmarks"]) == 3, "Should still have 3 benchmarks after update"
    
    # Find the benchmark for rate 5 (middle one, index 1)
    rate_5_benchmark = None
    rate_3_benchmark = None
    rate_8_benchmark = None
    
    for bm in report2["benchmarks"]:
        strategy = bm["config"]["strategy"]
        if "rate" in strategy:
            rate = strategy["rate"]
            if abs(rate - 5.0) < 0.01:
                rate_5_benchmark = bm
            elif abs(rate - 3.0) < 0.01:
                rate_3_benchmark = bm
            elif abs(rate - 8.0) < 0.01:
                rate_8_benchmark = bm
    
    assert rate_5_benchmark is not None, "Rate 5 benchmark should exist"
    assert rate_3_benchmark is not None, "Rate 3 benchmark should be preserved"
    assert rate_8_benchmark is not None, "Rate 8 benchmark should be preserved"
    
    # Rate 5 should have new data (8 requests instead of 5)
    rate_5_successful = len(rate_5_benchmark["requests"]["successful"])
    assert rate_5_successful == 8, (
        f"Rate 5 should have 8 requests (updated), got {rate_5_successful}"
    )
    
    # Rates 3 and 8 should have original data (5 requests)
    rate_3_successful = len(rate_3_benchmark["requests"]["successful"])
    rate_8_successful = len(rate_8_benchmark["requests"]["successful"])
    assert rate_3_successful == 5, (
        f"Rate 3 should have 5 requests (preserved), got {rate_3_successful}"
    )
    assert rate_8_successful == 5, (
        f"Rate 8 should have 5 requests (preserved), got {rate_8_successful}"
    )


@pytest.mark.timeout(120)
@pytest.mark.sanity
def test_update_adds_new_rates(server: VllmSimServer, tmp_path: Path):
    """
    Test that update mode adds new rates to existing report.
    """
    report_name = "benchmarks.json"
    report_path = tmp_path / report_name
    
    # Step 1: Run initial sweep with 2 rates
    client1 = GuidellmClient(
        target=server.get_url(),
        output_dir=tmp_path,
        outputs=report_name,
    )
    
    client1.start_benchmark(
        profile="constant",
        rate=3,
        max_requests=5,
        additional_args="--rate 5",
    )
    client1.wait_for_completion(timeout=60)
    assert_no_python_exceptions(client1.stderr)
    
    # Verify initial report has 2 benchmarks
    report1 = load_benchmark_report(report_path)
    assert len(report1["benchmarks"]) == 2, "Should have 2 benchmarks initially"
    
    # Step 2: Add new rate with update mode
    client2 = GuidellmClient(
        target=server.get_url(),
        output_dir=tmp_path,
        outputs=report_name,
    )
    
    client2.start_benchmark(
        profile="constant",
        rate=10,
        max_requests=5,
        additional_args="--update",
    )
    client2.wait_for_completion(timeout=60)
    assert_no_python_exceptions(client2.stderr)
    
    # Verify report now has 3 benchmarks
    report2 = load_benchmark_report(report_path)
    assert len(report2["benchmarks"]) == 3, (
        f"Should have 3 benchmarks after adding new rate, got {len(report2['benchmarks'])}"
    )
    
    # Verify all three rates are present
    rates_found = []
    for bm in report2["benchmarks"]:
        strategy = bm["config"]["strategy"]
        if "rate" in strategy:
            rates_found.append(strategy["rate"])
    
    rates_found.sort()
    expected_rates = [3.0, 5.0, 10.0]
    
    assert len(rates_found) == 3, f"Should find 3 rates, found {len(rates_found)}"
    for expected, found in zip(expected_rates, rates_found):
        assert abs(expected - found) < 0.01, (
            f"Expected rate {expected}, found {found}"
        )


@pytest.mark.timeout(120)
@pytest.mark.sanity
def test_update_with_multiple_replacements(server: VllmSimServer, tmp_path: Path):
    """
    Test that update mode can replace multiple matching rates at once.
    """
    report_name = "benchmarks.json"
    report_path = tmp_path / report_name
    
    # Step 1: Run initial sweep with 4 rates
    client1 = GuidellmClient(
        target=server.get_url(),
        output_dir=tmp_path,
        outputs=report_name,
    )
    
    client1.start_benchmark(
        profile="constant",
        rate=2,
        max_requests=5,
        additional_args="--rate 4 --rate 6 --rate 8",
    )
    client1.wait_for_completion(timeout=60)
    assert_no_python_exceptions(client1.stderr)
    
    # Verify initial report
    report1 = load_benchmark_report(report_path)
    assert len(report1["benchmarks"]) == 4, "Should have 4 benchmarks initially"
    
    # Step 2: Re-run rates 4 and 8 with update mode
    client2 = GuidellmClient(
        target=server.get_url(),
        output_dir=tmp_path,
        outputs=report_name,
    )
    
    client2.start_benchmark(
        profile="constant",
        rate=4,
        max_requests=10,  # Different count to verify update
        additional_args="--rate 8 --update",
    )
    client2.wait_for_completion(timeout=60)
    assert_no_python_exceptions(client2.stderr)
    
    # Verify report still has 4 benchmarks
    report2 = load_benchmark_report(report_path)
    assert len(report2["benchmarks"]) == 4, (
        f"Should still have 4 benchmarks after update, got {len(report2['benchmarks'])}"
    )
    
    # Verify rates 4 and 8 were updated (10 requests) and rates 2,6 preserved (5 requests)
    results = {}
    for bm in report2["benchmarks"]:
        strategy = bm["config"]["strategy"]
        if "rate" in strategy:
            rate = strategy["rate"]
            successful_count = len(bm["requests"]["successful"])
            results[rate] = successful_count
    
    # Rates 4 and 8 should have 10 requests (updated)
    assert results.get(4.0) == 10, f"Rate 4 should have 10 requests (updated), got {results.get(4.0)}"
    assert results.get(8.0) == 10, f"Rate 8 should have 10 requests (updated), got {results.get(8.0)}"
    
    # Rates 2 and 6 should have 5 requests (preserved)
    assert results.get(2.0) == 5, f"Rate 2 should have 5 requests (preserved), got {results.get(2.0)}"
    assert results.get(6.0) == 5, f"Rate 6 should have 5 requests (preserved), got {results.get(6.0)}"


@pytest.mark.timeout(60)
@pytest.mark.sanity
def test_update_without_existing_file(server: VllmSimServer, tmp_path: Path):
    """
    Test that update mode works gracefully when no existing file is present.
    
    Should behave like normal mode (create new file).
    """
    report_name = "benchmarks.json"
    report_path = tmp_path / report_name
    
    # Ensure no existing file
    if report_path.exists():
        report_path.unlink()
    
    # Run with update mode but no existing file
    client = GuidellmClient(
        target=server.get_url(),
        output_dir=tmp_path,
        outputs=report_name,
    )
    
    client.start_benchmark(
        profile="constant",
        rate=5,
        max_requests=5,
        additional_args="--update",
    )
    client.wait_for_completion(timeout=60)
    assert_no_python_exceptions(client.stderr)
    
    # Should see warning about missing file in stderr
    assert client.stderr is not None
    assert "Could not load existing report" in client.stderr or "Creating new report" in client.stderr
    
    # Report should be created normally
    report = load_benchmark_report(report_path)
    assert len(report["benchmarks"]) == 1, "Should have 1 benchmark"
