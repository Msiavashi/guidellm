"""
Primary interface for executing and re-importing generative text benchmarks.

This module orchestrates comprehensive benchmarking workflows by coordinating backend
initialization, data loading, profile configuration, and output generation. It provides
two main entry points: `benchmark_generative_text` for executing new benchmarks and
`reimport_benchmarks_report` for re-exporting existing results. The resolution functions
convert user-provided arguments into fully configured components, handling backend
validation, data preprocessing, profile constraints, and output format specifications.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, MutableMapping
from pathlib import Path
from typing import Any, Literal

from torch.utils.data import Sampler
from datasets import Dataset, IterableDataset
from transformers import PreTrainedTokenizerBase
from typing_extensions import TypeAliasType

from guidellm.backends import Backend, BackendType
from guidellm.benchmark.benchmarker import Benchmarker
from guidellm.benchmark.outputs import (
    GenerativeBenchmarkerConsole,
    GenerativeBenchmarkerOutput,
)
from guidellm.benchmark.profiles import Profile, ProfileType
from guidellm.benchmark.progress import GenerativeConsoleBenchmarkerProgress
from guidellm.benchmark.schemas import (
    BenchmarkGenerativeTextArgs,
    GenerativeBenchmark,
    GenerativeBenchmarkAccumulator,
    GenerativeBenchmarksReport,
)
from guidellm.benchmark.schemas.base import TransientPhaseConfig
from guidellm.data import (
    DataLoader,
    DatasetPreprocessor,
    GenerativeRequestCollator,
    PreprocessorRegistry,
    ProcessorFactory,
    RequestFormatter,
)
from guidellm.data.loaders import DatasetsIterator
from guidellm.data.preprocessors.preprocessor import DataDependentPreprocessor
from guidellm.data.preprocessors import GenerativeColumnMapper
from guidellm.data.deserializers import DatasetDeserializerFactory
from guidellm.data.preprocessors.token_budget import (
    compute_input_tokens,
    compute_output_tokens,
)
from guidellm.data.cache import DatasetFilterCache
from guidellm.scheduler import (
    ConstraintInitializer,
    NonDistributedEnvironment,
    StrategyType,
)
from guidellm.schemas import GenerationRequest, GenerationResponse
from guidellm.schemas.statistics import DistributionSummary
from guidellm.settings import settings
from guidellm.utils import Console, InfoMixin

__all__ = [
    "benchmark_generative_text",
    "reimport_benchmarks_report",
]


# Type Aliases

OutputFormatT = TypeAliasType(
    "OutputFormatT",
    tuple[str, ...]
    | list[str]
    | Mapping[str, str | dict[str, Any] | GenerativeBenchmarkerOutput]
    | None,
)
"""Output format specification as strings, mappings, or configured output instances"""

ProcessorInputT = TypeAliasType("ProcessorInputT", str | Path | PreTrainedTokenizerBase)
"""Processor input as model identifier, path to tokenizer, or tokenizer instance"""


# Helper Functions


async def resolve_backend(
    backend: BackendType | Backend,
    target: str,
    model: str | None,
    console: Console | None = None,
    **backend_kwargs: dict[str, Any],
) -> tuple[Backend, str]:
    """
    Initialize and validate a backend instance for benchmarking execution.

    Handles backend creation from type identifiers or pre-configured instances,
    performs startup validation, and resolves the default model if not specified.
    The backend is shut down after validation to ensure clean state for subsequent
    benchmark execution.

    :param backend: Backend type identifier or pre-configured Backend instance
    :param target: Target endpoint URL or connection string for the backend
    :param model: Model identifier to use with the backend, or None to use default
    :param console: Console instance for progress reporting, or None
    :param backend_kwargs: Additional keyword arguments passed to backend initialization
    :return: Tuple of initialized Backend instance and resolved model identifier
    """
    console_step = (
        console.print_update_step(title=f"Initializing backend {backend}")
        if console
        else None
    )
    backend_instance = (
        Backend.create(backend, target=target, model=model, **(backend_kwargs or {}))
        if not isinstance(backend, Backend)
        else backend
    )

    if console_step:
        console_step.update(
            f"{backend_instance.__class__.__name__} backend initialized"
        )

    await backend_instance.process_startup()
    await backend_instance.validate()

    if model is None:
        if console_step:
            console_step.update(
                title="Resolving default model from backend.default_model",
                status_level="info",
            )
        model = await backend_instance.default_model()

    await backend_instance.process_shutdown()

    if console_step:
        console_step.finish(
            title=(
                f"{backend_instance.__class__.__name__} backend validated "
                f"with model {model}"
            ),
            details=backend_instance.info,
            status_level="success",
        )

    return backend_instance, model


async def resolve_processor(
    processor: ProcessorInputT | None,
    model: str | None,
    console: Console | None = None,
) -> ProcessorInputT | None:
    """
    Resolve the tokenization processor, defaulting to model if not provided.

    :param processor: Processor identifier, path, tokenizer instance, or None
    :param model: Model identifier to use as fallback processor
    :param console: Console instance for progress reporting, or None
    :return: Resolved processor or None if neither processor nor model provided
    """
    console_step = (
        console.print_update_step(title=f"Resolving processor {processor}")
        if console
        else None
    )

    if processor is not None:
        if console_step:
            console_step.finish(
                title="Processor resolved",
                details=f"Using processor '{processor}'",
                status_level="success",
            )
    else:
        processor = model
        if console_step:
            console_step.finish(
                title="Processor resolved",
                details=f"Using model '{processor}' as processor",
                status_level="success",
            )

    return processor


async def resolve_request_loader(
    data: list[Any],
    model: str,
    data_args: list[dict[str, Any]] | None,
    data_samples: int,
    processor: ProcessorInputT | None,
    processor_args: dict[str, Any] | None,
    data_column_mapper: (
        DatasetPreprocessor
        | dict[str, str | list[str]]
        | Literal["generative_column_mapper"]
    ),
    data_request_formatter: (RequestFormatter | dict[str, str] | str),
    data_collator: Callable | Literal["generative"] | None,
    data_sampler: Sampler[int] | Literal["shuffle"] | None,
    data_num_workers: int | None,
    random_seed: int,
    sharegpt_preprocessor: dict[str, Any] | None = None,
    token_budget_total: int | None = None,
    max_input_length: int | None = None,
    max_output_length: int | None = None,
    use_filter_cache: bool = True,
    input_length_stats: bool = False,
    console: Console | None = None,
    **dataloader_kwargs: dict[str, Any] | None,
) -> DataLoader[GenerationRequest]:
    """
    Construct a DataLoader for GenerationRequest objects from raw data inputs.

    Initializes and configures the data pipeline including column mapping, request
    formatting, collation, and sampling. Resolves string-based preprocessor identifiers
    from the PreprocessorRegistry and creates appropriate instances with provided
    configurations.

    :param data: List of data sources to load requests from
    :param model: Model identifier for request formatting
    :param data_args: Arguments for each data source in the data list
    :param data_samples: Number of samples to draw from the dataset
    :param processor: Processor for tokenization operations
    :param processor_args: Arguments for processor initialization
    :param data_column_mapper: Preprocessor or mapping for standardizing column names
    :param data_request_formatter: Preprocessor or config for formatting requests
    :param data_collator: Collation function or type for batching requests
    :param data_sampler: Sampler instance or type for data sampling
    :param data_num_workers: Number of worker processes for data loading
    :param random_seed: Seed for reproducible random operations
    :param console: Console instance for progress reporting, or None
    :param dataloader_kwargs: Additional arguments passed to DataLoader initialization
    :return: Configured DataLoader instance for GenerationRequest objects
    :raises ValueError: If request formatter type is not registered in
        PreprocessorRegistry
    :raises TypeError: If registered request formatter is not a RequestFormatter
        subclass
    """
    console_step = (
        console.print_update_step(title=f"Initializing request loader from {data}")
        if console
        else None
    )

    data_column_mapper_instance: DatasetPreprocessor
    if isinstance(data_column_mapper, DatasetPreprocessor):
        data_column_mapper_instance = data_column_mapper
    else:
        column_mappings = (
            data_column_mapper if isinstance(data_column_mapper, dict) else None
        )
        data_column_mapper_instance = GenerativeColumnMapper(
            column_mappings=column_mappings  # type: ignore[arg-type]
        )

    processor_factory = None
    data_request_formatter_instance: RequestFormatter
    if isinstance(data_request_formatter, RequestFormatter):
        data_request_formatter_instance = data_request_formatter
    else:
        if isinstance(data_request_formatter, str):
            request_type = data_request_formatter
            formatter_kwargs: dict[str, Any] = {}
        else:
            # Extract request_type from formatter dictionary
            formatter_dict = dict(data_request_formatter)
            request_type = formatter_dict.pop("request_type", settings.preferred_route)
            formatter_kwargs = formatter_dict

        if (
            formatter_class := PreprocessorRegistry.get_registered_object(request_type)
        ) is None:
            raise ValueError(
                f"Request formatter '{request_type}' is not registered in the "
                f"PreprocessorRegistry."
            )
        if not issubclass(formatter_class, RequestFormatter):
            raise TypeError(
                f"Request formatter '{request_type}' is not a subclass of "
                f"RequestFormatter."
            )

        # Create processor factory for the formatter
        processor_factory = ProcessorFactory(
            processor=processor if processor is not None else model,
            processor_args=processor_args,
        )

        data_request_formatter_instance = formatter_class(
            model=model,
            processor_factory=processor_factory,
            **formatter_kwargs,
        )

    if processor_factory is None:
        processor_factory = ProcessorFactory(
            processor=processor if processor is not None else model,
            processor_args=processor_args,
        )

    # Build preprocessors list
    preprocessors_list: list[DatasetPreprocessor] = []

    # Add ShareGPT preprocessor if configured (must come first to transform conversational data)
    sharegpt_instance: DatasetPreprocessor | None = None
    if sharegpt_preprocessor:
        preprocessor_type = sharegpt_preprocessor.get("type", "conversational")

        if preprocessor_type == "conversational":
            from guidellm.data.preprocessors.sharegpt import ShareGPTPreprocessor

            sharegpt_config = {
                k: v for k, v in sharegpt_preprocessor.items() if k != "type"
            }
            sharegpt_instance = ShareGPTPreprocessor(**sharegpt_config)
            preprocessors_list.append(sharegpt_instance)
        elif preprocessor_type == "tokenized":
            from guidellm.data.preprocessors.tokenized_sharegpt import (
                TokenizedShareGPTPreprocessor,
            )

            sharegpt_config = {
                k: v for k, v in sharegpt_preprocessor.items() if k != "type"
            }
            sharegpt_instance = TokenizedShareGPTPreprocessor(
                processor_factory=processor_factory,
                **sharegpt_config,
            )
            preprocessors_list.append(sharegpt_instance)

    # Optional token budget/length prefilter BEFORE workload generation
    prefiltered_lengths: list[int] | None = None
    has_filtering = (
        token_budget_total is not None
        or max_input_length is not None
        or max_output_length is not None
    )
    
    if has_filtering:
        # Initialize cache if requested (supports all filtering methods)
        cache: DatasetFilterCache | None = None
        cached_data: list[list[dict[str, Any]]] | None = None
        
        # Normalize data_args early to ensure consistent cache keys
        if not data_args:
            data_args = [{} for _ in data]
        
        filter_params = {
            "max_input_length": max_input_length,
            "max_output_length": max_output_length,
            "token_budget_total": token_budget_total,
            "random_seed": random_seed,
            "data_samples": data_samples,
        }
        processor_name = str(processor) if processor is not None else model
        
        if use_filter_cache:
            cache = DatasetFilterCache()
            
            # Try to load from cache
            try:
                cached_data = cache.get(
                    data_sources=data,
                    filter_params=filter_params,
                    data_args=data_args,
                    processor_name=processor_name,
                )
                if console and cached_data is not None:
                    console.print_update(
                        title="Loaded filtered dataset from cache",
                        status="success",
                    )
            except Exception as e:
                if console:
                    console.print_update(
                        title=f"Cache load failed: {e}",
                        status="warning",
                    )
                cached_data = None
        
        # If we don't have cached data, perform filtering
        if cache is None or cached_data is None:
            datasets = []
            for datum, data_kwargs in zip(data, data_args, strict=False):
                datasets.append(
                    DatasetDeserializerFactory.deserialize(
                        data=datum,
                        processor_factory=processor_factory,
                        random_seed=random_seed,
                        **data_kwargs,
                    )
                )

            if any(isinstance(dataset, IterableDataset) for dataset in datasets) and (
                data_samples is None or data_samples <= 0
            ):
                raise ValueError(
                    "Token length filtering on iterable datasets requires a finite "
                    "`data_samples` value to avoid infinite prefiltering."
                )

            if isinstance(data_column_mapper_instance, DataDependentPreprocessor):
                data_column_mapper_instance.setup_data(
                    datasets=datasets,
                    data_args=data_args,
                )

            if console:
                console.print_update(
                    title=f"Filtering dataset with constraints: "
                          f"max_input={max_input_length or 'none'}, "
                          f"max_output={max_output_length or 'none'}, "
                          f"total_budget={token_budget_total or 'none'}",
                    status="info",
                )

            filtered_data: list[list[dict[str, Any]]] = [
                [] for _ in range(len(datasets))
            ]
            prefiltered_lengths = []
            dataset_iters = [iter(dataset) for dataset in datasets]
            filtered_count = 0
            max_filtered = data_samples if data_samples and data_samples > 0 else None

            while True:
                try:
                    items = [next(dataset_iter) for dataset_iter in dataset_iters]
                except StopIteration:
                    break

                if max_filtered is not None and filtered_count >= max_filtered:
                    break

                mapping_items = []
                for item in items:
                    if not isinstance(item, dict):
                        raise ValueError(
                            "Token length filtering requires dict-like dataset rows. "
                            f"Got {type(item)} instead."
                        )
                    mapping_items.append(dict(item))
                mapping_row = {"items": mapping_items}

                if sharegpt_instance is not None:
                    mapping_row = sharegpt_instance(mapping_row)  # type: ignore[assignment]

                mapped = data_column_mapper_instance({"items": mapping_row["items"]})

                input_tokens = compute_input_tokens(
                    mapped,
                    processor_factory=processor_factory,
                    include_prefix_in_input=True,
                )
                output_tokens = compute_output_tokens(
                    mapped,
                    processor_factory=processor_factory,
                )

                if input_tokens is None or output_tokens is None:
                    continue

                # Apply filtering criteria
                passes_filter = True
                
                # Check token budget total if specified
                if token_budget_total is not None:
                    if input_tokens + output_tokens > token_budget_total:
                        passes_filter = False
                
                # Check max input length if specified
                if max_input_length is not None:
                    if input_tokens > max_input_length:
                        passes_filter = False
                
                # Check max output length if specified
                if max_output_length is not None:
                    if output_tokens > max_output_length:
                        passes_filter = False

                if passes_filter:
                    for index, item in enumerate(items):
                        filtered_data[index].append(item)
                    filtered_count += 1
                    prefiltered_lengths.append(input_tokens)

            for index, rows in enumerate(filtered_data):
                if not rows:
                    raise ValueError(
                        f"Token length filtering produced no rows for dataset index "
                        f"{index}. Try relaxing the filter constraints."
                    )

            if console:
                console.print_update(
                    title=f"Filtered {filtered_count} samples from dataset",
                    status="success",
                )

            # Cache the filtered data if caching is enabled
            if cache is not None and cached_data is None:
                try:
                    cache.set(
                        data_sources=data,
                        filter_params=filter_params,
                        filtered_data=filtered_data,
                        data_args=data_args,
                        processor_name=processor_name,
                    )
                    if console:
                        console.print_update(
                            title="Saved filtered dataset to cache",
                            status="success",
                        )
                except Exception as e:
                    if console:
                        console.print_update(
                            title=f"Cache save failed: {e}",
                            status="warning",
                        )

            cached_data = filtered_data

        # Use the cached or newly filtered data
        data = [Dataset.from_list(rows) for rows in cached_data]
        data_args = [{} for _ in data]

    # Add column mapper
    preprocessors_list.append(data_column_mapper_instance)

    # Optional input length stats AFTER filtering, BEFORE formatting
    if input_length_stats:
        lengths = prefiltered_lengths
        if lengths is None:
            stats_iterator = DatasetsIterator(
                data=data,
                data_args=data_args,
                data_samples=data_samples,
                processor_factory=processor_factory,
                preprocessors=preprocessors_list,
                random_seed=random_seed,
            )
            lengths = []
            max_items = data_samples if data_samples and data_samples > 0 else None
            for row in stats_iterator.generator(max_items=max_items):
                input_tokens = compute_input_tokens(
                    row,
                    processor_factory=processor_factory,
                    include_prefix_in_input=True,
                )
                if input_tokens is not None:
                    lengths.append(input_tokens)

        if console and lengths:
            stats = DistributionSummary.from_values(lengths)
            headers = ["metric", "value"]
            values = [
                [
                    "count",
                    "mean",
                    "std_dev",
                    "min",
                    "p25",
                    "p50",
                    "p75",
                    "p95",
                    "max",
                ],
                [
                    f"{stats.count}",
                    f"{stats.mean:.2f}",
                    f"{stats.std_dev:.2f}",
                    f"{stats.min:.2f}",
                    f"{stats.percentiles.p25:.2f}",
                    f"{stats.percentiles.p50:.2f}",
                    f"{stats.percentiles.p75:.2f}",
                    f"{stats.percentiles.p95:.2f}",
                    f"{stats.max:.2f}",
                ],
            ]
            console.print_tables(
                header_cols_groups=[headers],
                value_cols_groups=[values],
                title="Input length distribution (tokens)",
            )

    # Add request formatter
    preprocessors_list.append(data_request_formatter_instance)

    request_loader: DataLoader[GenerationRequest] = DataLoader(
        data=data,
        data_args=data_args,
        data_samples=data_samples,
        processor_factory=processor_factory,
        preprocessors=preprocessors_list,
        collator=(
            data_collator if callable(data_collator) else GenerativeRequestCollator()
        ),
        sampler=data_sampler,
        num_workers=data_num_workers,
        random_seed=random_seed,
        **(dataloader_kwargs or {}),
    )

    if console_step:
        console_step.finish(
            title=(
                f"Request loader initialized with "
                f"{data_samples if data_samples > 0 else 'inf'} "
                "unique requests"
            ),
            details=InfoMixin.extract_from_obj(request_loader),
            status_level="success",
        )

    return request_loader


async def resolve_profile(
    profile: StrategyType | ProfileType | Profile,
    rate: list[float] | None,
    random_seed: int,
    rampup: float,
    constraints: MutableMapping[str, ConstraintInitializer | Any],
    max_seconds: int | float | None,
    max_requests: int | None,
    max_errors: int | None,
    max_error_rate: float | None,
    max_global_error_rate: float | None,
    over_saturation: dict[str, Any] | None = None,
    phases: str | None = None,
    repeat: int = 1,
    console: Console | None = None,
) -> Profile:
    """
    Resolve and configure a benchmark profile with rate and constraint settings.

    Constructs a Profile instance from type identifiers or validates pre-configured
    profiles. Constraint parameters are merged into the constraints dictionary before
    profile creation.

    :param profile: Profile type identifier or pre-configured Profile instance
    :param rate: Request rate(s) for the benchmark execution
    :param random_seed: Seed for reproducible random operations
    :param warmup: Warm-up phase configuration for the benchmark execution
        (used for ramp-up duration calculation)
    :param constraints: Dictionary of constraint initializers for benchmark limits
    :param max_seconds: Maximum duration in seconds for the benchmark
    :param max_requests: Maximum number of requests to process
    :param max_errors: Maximum number of errors before stopping
    :param max_error_rate: Maximum error rate threshold before stopping
    :param max_global_error_rate: Maximum global error rate threshold before stopping
    :param over_saturation: Over-saturation detection configuration (dict)
    :param console: Console instance for progress reporting, or None
    :return: Configured Profile instance ready for benchmarking
    :raises ValueError: If constraints are provided with a pre-configured Profile
    """
    console_step = (
        console.print_update_step(title=f"Resolving profile {profile}")
        if console
        else None
    )

    for key, val in {
        "max_seconds": max_seconds,
        "max_requests": max_requests,
        "max_errors": max_errors,
        "max_error_rate": max_error_rate,
        "max_global_error_rate": max_global_error_rate,
        "over_saturation": over_saturation,
    }.items():
        if val is not None:
            constraints[key] = val

    if not isinstance(profile, Profile):
        profile_kwargs: dict[str, Any] = {
            "rampup_duration": rampup,
            "constraints": {**constraints},
        }
        # Add phases and repeat for bursty profile
        if phases is not None:
            profile_kwargs["phases"] = phases
        if repeat is not None:
            profile_kwargs["repeat"] = repeat
        profile = Profile.create(
            rate_type=profile,
            rate=rate,
            random_seed=random_seed,
            **profile_kwargs,
        )
    elif constraints:
        raise ValueError(
            "Constraints must be empty when providing a Profile instance. "
            f"Provided constraints: {constraints} ; provided profile: {profile}"
        )
    elif rampup > 0.0:
        raise ValueError(
            "Ramp-up duration must not be set when providing a Profile instance. "
            f"Provided rampup: {rampup} ; provided profile: {profile}"
        )

    if console_step:
        console_step.finish(
            title=f"{profile.__class__.__name__} profile resolved",
            details=InfoMixin.extract_from_obj(profile),
            status_level="success",
        )

    return profile


async def resolve_output_formats(
    outputs: list[str] | tuple[str],
    output_dir: str | Path | None,
    console: Console | None = None,
) -> dict[str, GenerativeBenchmarkerOutput]:
    """
    Resolve output format specifications into configured output handler instances.

    :param outputs: Specification of desired output files/types
    :param output_dir: Base path for output file generation, or None for default
    :param console: Console instance for progress reporting, or None
    :return: Dictionary mapping format names to configured output handler instances
    """
    console_step = (
        console.print_update_step(title="Resolving output formats") if console else None
    )

    resolved = GenerativeBenchmarkerOutput.resolve(
        outputs=outputs, output_dir=output_dir
    )

    if console_step:
        console_step.finish(
            title="Output formats resolved",
            details={key: str(val) for key, val in resolved.items()},
            status_level="success",
        )

    return resolved


# Main Entrypoints Functions


def _get_benchmark_key(benchmark: GenerativeBenchmark) -> tuple[str, float | int | None]:
    """
    Extract identifying key from benchmark for matching.

    :param benchmark: Benchmark to extract key from
    :return: Tuple of (strategy_type, rate_or_streams) for matching
    """
    strategy = benchmark.config.strategy
    strategy_type = strategy.type_

    # Extract rate or streams depending on strategy type
    if hasattr(strategy, "rate"):
        # Async strategies (constant, poisson) have rate
        return (strategy_type, float(strategy.rate))
    elif hasattr(strategy, "streams"):
        # Concurrent strategy has streams
        return (strategy_type, int(strategy.streams))
    else:
        # Synchronous, throughput, bursty - use type only
        return (strategy_type, None)


def _merge_benchmark_reports(
    existing_report: GenerativeBenchmarksReport,
    new_report: GenerativeBenchmarksReport,
    console: Console | None = None,
) -> GenerativeBenchmarksReport:
    """
    Merge new benchmarks into existing report, replacing matching ones.

    :param existing_report: Report loaded from file
    :param new_report: Report with new benchmarks
    :param console: Console for status messages
    :return: Merged report with updated benchmarks
    """
    # Create dict of existing benchmarks by key
    existing_by_key: dict[tuple[str, float | int | None], GenerativeBenchmark] = {}
    for benchmark in existing_report.benchmarks:
        key = _get_benchmark_key(benchmark)
        existing_by_key[key] = benchmark

    # Track what gets updated vs added
    updated_keys: list[tuple[str, float | int | None]] = []
    new_keys: list[tuple[str, float | int | None]] = []

    # Replace matching benchmarks with new ones
    for benchmark in new_report.benchmarks:
        key = _get_benchmark_key(benchmark)
        if key in existing_by_key:
            updated_keys.append(key)
        else:
            new_keys.append(key)
        existing_by_key[key] = benchmark

    # Create merged report
    merged_report = GenerativeBenchmarksReport(
        metadata=new_report.metadata,  # Use new metadata
        args=new_report.args,  # Use new args
        benchmarks=list(existing_by_key.values()),
    )

    if console:
        console.print_update(
            title=f"Updated {len(updated_keys)} existing benchmark(s), "
            f"added {len(new_keys)} new benchmark(s)",
            details=(
                f"Total benchmarks in report: {len(merged_report.benchmarks)}"
            ),
            status="success",
        )

    return merged_report


async def benchmark_generative_text(
    args: BenchmarkGenerativeTextArgs,
    progress: GenerativeConsoleBenchmarkerProgress | None = None,
    console: Console | None = None,
    **constraints: str | ConstraintInitializer | Any,
) -> tuple[GenerativeBenchmarksReport, dict[str, Any]]:
    """
    Execute a comprehensive generative text benchmarking workflow.

    Orchestrates the full benchmarking pipeline by resolving all components from
    provided arguments, executing benchmark runs across configured profiles, and
    finalizing results in specified output formats. Components include backend
    initialization, data loading, profile configuration, and output generation.

    :param args: Configuration arguments for the benchmark execution
    :param progress: Progress tracker for benchmark execution, or None for no tracking
    :param console: Console instance for status reporting, or None for silent operation
    :param constraints: Additional constraint initializers for benchmark limits
    :return: Tuple of GenerativeBenchmarksReport and dictionary of output format
        results
    """
    backend, model = await resolve_backend(
        backend=args.backend,
        target=args.target,
        model=args.model,
        console=console,
        **(args.backend_kwargs or {}),
    )
    processor = await resolve_processor(
        processor=args.processor, model=model, console=console
    )
    request_loader = await resolve_request_loader(
        data=args.data,
        model=model,
        data_args=args.data_args,
        data_samples=args.data_samples,
        processor=processor,
        processor_args=args.processor_args,
        data_column_mapper=args.data_column_mapper,
        data_request_formatter=args.data_request_formatter,
        data_collator=args.data_collator,
        data_sampler=args.data_sampler,
        data_num_workers=args.data_num_workers,
        random_seed=args.random_seed,
        sharegpt_preprocessor=getattr(args, 'sharegpt_preprocessor', None),
        token_budget_total=args.token_budget_total,
        max_input_length=getattr(args, 'max_input_length', None),
        max_output_length=getattr(args, 'max_output_length', None),
        use_filter_cache=getattr(args, 'use_filter_cache', True),
        input_length_stats=args.input_length_stats,
        console=console,
        **(args.dataloader_kwargs or {}),
    )

    warmup = TransientPhaseConfig.create_from_value(args.warmup)
    cooldown = TransientPhaseConfig.create_from_value(args.cooldown)
    if console:
        console.print_update(
            title="Resolved transient phase configurations",
            details="\n".join(
                [
                    f"Warmup: {warmup}",
                    f"Cooldown: {cooldown}",
                    f"Rampup (Throughput/Concurrent): {args.rampup}",
                ]
            ),
            status="success",
        )

    profile = await resolve_profile(
        profile=args.profile,
        rate=args.rate,
        random_seed=args.random_seed,
        rampup=args.rampup,
        constraints=constraints,
        max_seconds=args.max_seconds,
        max_requests=args.max_requests,
        max_errors=args.max_errors,
        max_error_rate=args.max_error_rate,
        max_global_error_rate=args.max_global_error_rate,
        over_saturation=args.over_saturation,
        phases=args.phases,
        repeat=args.repeat,
        console=console,
    )
    output_formats = await resolve_output_formats(
        outputs=args.outputs, output_dir=args.output_dir, console=console
    )

    # Load existing report if update mode is enabled
    existing_report: GenerativeBenchmarksReport | None = None
    if args.update:
        # Try to load existing report from output directory
        try:
            output_file = args.output_dir / "benchmarks.json"
            if output_file.exists():
                existing_report = GenerativeBenchmarksReport.load_file(output_file)
                if console:
                    console.print_update(
                        title=f"Loaded existing report with {len(existing_report.benchmarks)} benchmark(s)",
                        status="info",
                    )
        except Exception as e:
            if console:
                console.print_update(
                    title=f"Could not load existing report: {e}. Creating new report.",
                    status="warning",
                )

    report = GenerativeBenchmarksReport(args=args)
    if console:
        console.print_update(
            title="Setup complete, starting benchmarks...", status="success"
        )
        console.print("\n\n")

    benchmarker: Benchmarker[
        GenerativeBenchmark, GenerationRequest, GenerationResponse
    ] = Benchmarker()
    async for benchmark in benchmarker.run(
        accumulator_class=GenerativeBenchmarkAccumulator,
        benchmark_class=GenerativeBenchmark,
        requests=request_loader,
        backend=backend,
        profile=profile,
        environment=NonDistributedEnvironment(),
        progress=progress,
        sample_requests=args.sample_requests,
        warmup=warmup,
        cooldown=cooldown,
        prefer_response_metrics=args.prefer_response_metrics,
        delay=args.delay,
        restart_backend_between_runs=args.restart_backend_between_runs,
        pause_for_enter=args.pause_for_enter,
    ):
        if benchmark:
            report.benchmarks.append(benchmark)

    # Merge with existing benchmarks if update mode
    if existing_report is not None:
        report = _merge_benchmark_reports(existing_report, report, console)

    output_format_results = {}
    for key, output in output_formats.items():
        output_result = await output.finalize(report)
        output_format_results[key] = output_result

    if console:
        await GenerativeBenchmarkerConsole(console=console).finalize(report)
        console.print("\n\n")
        console.print_update(
            title=(
                "Benchmarking complete, generated "
                f"{len(report.benchmarks)} benchmark(s)"
            ),
            status="success",
        )
        for key, value in output_format_results.items():
            console.print_update(title=f"  {key:<8}: {value}", status="debug")

    return report, output_format_results


async def reimport_benchmarks_report(
    file: Path,
    output_path: Path | None,
    output_formats: OutputFormatT = ("console", "json", "html", "csv"),
) -> tuple[GenerativeBenchmarksReport, dict[str, Any]]:
    """
    Load and re-export an existing benchmarks report in specified output formats.

    :param file: Path to the existing benchmark report file to load
    :param output_path: Base path for output file generation, or None for default
    :param output_formats: Specification of desired output formats for the report
    :return: Tuple of loaded GenerativeBenchmarksReport and dictionary of output
        results
    """
    console = Console()

    with console.print_update_step(
        title=f"Loading benchmarks from {file}..."
    ) as console_step:
        report = GenerativeBenchmarksReport.load_file(file)
        console_step.finish(
            "Import of old benchmarks complete;"
            f" loaded {len(report.benchmarks)} benchmark(s)"
        )

    resolved_output_formats = await resolve_output_formats(
        output_formats,  # type: ignore[arg-type]
        output_path,
        console=console,
    )
    output_format_results = {}
    for key, output in resolved_output_formats.items():
        output_result = await output.finalize(report)
        output_format_results[key] = output_result

    for key, value in output_format_results.items():
        console.print_update(title=f"  {key:<8}: {value}", status="debug")

    return report, output_format_results
