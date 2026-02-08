"""
Benchmark execution orchestration and lifecycle management.

Provides the core benchmarking engine that coordinates request scheduling,
data aggregation, and result compilation across execution strategies and
environments. The Benchmarker manages the complete benchmark lifecycle from
request submission through result compilation while implementing thread-safe
singleton operations for consistent state management across concurrent workflows.
"""

from __future__ import annotations

import asyncio
import uuid
from abc import ABC
from collections.abc import AsyncIterator, Iterable
from typing import Generic

from guidellm.benchmark.profiles import Profile
from guidellm.benchmark.progress import BenchmarkerProgress
from guidellm.benchmark.schemas import (
    BenchmarkAccumulatorT,
    BenchmarkConfig,
    BenchmarkT,
)
from guidellm.benchmark.schemas.base import TransientPhaseConfig
from guidellm.logger import logger
from guidellm.scheduler import (
    BackendInterface,
    Constraint,
    Environment,
    MultiTurnRequestT,
    RequestT,
    ResponseT,
    Scheduler,
    SchedulingStrategy,
)
from guidellm.utils import ThreadSafeSingletonMixin
from guidellm.utils.mixins import InfoMixin

__all__ = ["Benchmarker"]


class Benchmarker(
    Generic[BenchmarkT, RequestT, ResponseT],
    ABC,
    ThreadSafeSingletonMixin,
):
    """
    Orchestrates benchmark execution across scheduling strategies.

    Coordinates benchmarking runs by managing request scheduling, metric aggregation,
    and result compilation. Implements a thread-safe singleton pattern to ensure
    consistent state management across concurrent operations while supporting multiple
    scheduling strategies and execution environments.
    """

    async def run(
        self,
        accumulator_class: type[BenchmarkAccumulatorT],
        benchmark_class: type[BenchmarkT],
        requests: Iterable[RequestT | MultiTurnRequestT[RequestT]],
        backend: BackendInterface[RequestT, ResponseT],
        profile: Profile,
        environment: Environment,
        warmup: TransientPhaseConfig,
        cooldown: TransientPhaseConfig,
        sample_requests: int | None = 20,
        prefer_response_metrics: bool = True,
        progress: (
            BenchmarkerProgress[BenchmarkAccumulatorT, BenchmarkT] | None
        ) = None,
        delay: list[float] | None = None,
        restart_backend_between_runs: bool = False,
        pause_for_enter: bool = False,
    ) -> AsyncIterator[BenchmarkT]:
        """
        Execute benchmark runs across scheduling strategies in the profile.

        :param accumulator_class: Class for accumulating metrics during execution
        :param benchmark_class: Class for constructing final benchmark results
        :param requests: Request datasets to process across strategies
        :param backend: Backend interface for executing requests
        :param profile: Profile defining scheduling strategies and constraints
        :param environment: Environment for execution coordination
        :param warmup: Warmup phase configuration before benchmarking
        :param cooldown: Cooldown phase configuration after benchmarking
        :param sample_requests: Number of requests to sample for estimation,
            defaults to 20
        :param prefer_response_metrics: Whether to prefer response metrics over
            request metrics, defaults to True
        :param progress: Optional tracker for benchmark lifecycle events
        :param delay: List of delays in seconds before executing each benchmark run.
            If list has fewer elements than benchmark runs, remaining delays are 0.
            If None or empty, no delays are applied. Defaults to None.
        :param restart_backend_between_runs: If True, restarts the backend (closes
            and reopens connections) between each benchmark run. Ensures fresh
            connections for each rate benchmark. Defaults to False.
        :param pause_for_enter: If True, pauses and waits for Enter key press before
            each benchmark run. Useful for manual inspection or coordination. Defaults
            to False.
        :yield: Compiled benchmark result for each strategy execution
        :raises Exception: If benchmark execution or compilation fails
        """
        with self.thread_lock:
            if progress:
                await progress.on_initialize(profile)

            run_id = str(uuid.uuid4())
            strategies_generator = profile.strategies_generator()
            strategy: SchedulingStrategy | None
            constraints: dict[str, Constraint] | None
            strategy, constraints = next(strategies_generator)
            benchmark_count = 0

            while strategy is not None:
                # Apply delay before each benchmark run based on the delay list
                # Get delay for current benchmark (default to 0 if not specified)
                if delay is not None and len(delay) > 0:
                    current_delay = delay[benchmark_count] if benchmark_count < len(delay) else 0.0
                    if current_delay > 0.0:
                        logger.info(
                            f"Delaying for {current_delay} seconds before benchmark run "
                            f"{benchmark_count + 1}..."
                        )
                        await asyncio.sleep(current_delay)
                
                # Pause for Enter key press if requested
                if pause_for_enter:
                    rate_info = f" (run {benchmark_count + 1})"
                    logger.info(
                        f"Paused before benchmark{rate_info}. "
                        "Press Enter to continue..."
                    )
                    # Use asyncio to run input() in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, input)
                    logger.info("Continuing with benchmark...")
                
                # Restart backend between runs if requested (except for first run)
                if restart_backend_between_runs and benchmark_count > 0:
                    logger.info(
                        f"Restarting backend between benchmark runs "
                        f"(closing and reopening connections)..."
                    )
                    await backend.process_shutdown()
                    await backend.process_startup()
                    await backend.validate()
                    logger.info("Backend restarted successfully")

                if progress:
                    await progress.on_benchmark_start(strategy)

                config = BenchmarkConfig(
                    run_id=run_id,
                    run_index=len(profile.completed_strategies),
                    strategy=strategy,
                    constraints=(
                        {
                            key: InfoMixin.extract_from_obj(val)
                            for key, val in constraints.items()
                        }
                        if isinstance(constraints, dict)
                        else {"constraint": InfoMixin.extract_from_obj(constraints)}
                        if constraints
                        else {}
                    ),
                    sample_requests=sample_requests,
                    warmup=warmup,
                    cooldown=cooldown,
                    prefer_response_metrics=prefer_response_metrics,
                    profile=profile,
                    requests=InfoMixin.extract_from_obj(requests),
                    backend=InfoMixin.extract_from_obj(backend),
                    environment=InfoMixin.extract_from_obj(environment),
                )
                accumulator = accumulator_class(config=config)
                scheduler_state = None
                scheduler: Scheduler[RequestT, ResponseT] = Scheduler()

                async for (
                    response,
                    request,
                    request_info,
                    scheduler_state,
                ) in scheduler.run(
                    requests=requests,
                    backend=backend,
                    strategy=strategy,
                    env=environment,
                    **constraints or {},
                ):
                    try:
                        accumulator.update_estimate(
                            response,
                            request,
                            request_info,
                            scheduler_state,
                        )
                        if progress:
                            await progress.on_benchmark_update(
                                accumulator, scheduler_state
                            )
                    except Exception as err:  # noqa: BLE001
                        logger.error(
                            f"Error updating benchmark estimate/progress: {err}"
                        )

                benchmark = benchmark_class.compile(
                    accumulator=accumulator,
                    scheduler_state=scheduler_state,
                )

                if progress:
                    await progress.on_benchmark_complete(benchmark)

                yield benchmark
                benchmark_count += 1

                try:
                    strategy, constraints = strategies_generator.send(benchmark)
                except StopIteration:
                    strategy = None
                    constraints = None

            if progress:
                await progress.on_finalize()
