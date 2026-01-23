from __future__ import annotations

import ast
from collections.abc import Callable, Iterator
from random import Random
from typing import Any

from datasets import DatasetInfo, Features, IterableDataset, Value
from datasets.iterable_dataset import _BaseExamplesIterable
from faker import Faker
from transformers import PreTrainedTokenizerBase

from guidellm.data.deserializers.deserializer import (
    DataNotSupportedError,
    DatasetDeserializer,
    DatasetDeserializerFactory,
)
from guidellm.data.schemas import DistributionDatasetConfig

__all__ = [
    "DistributionDataset",
    "DistributionDatasetDeserializer",
]


def parse_dist_uri(uri: str) -> DistributionDatasetConfig:
    """
    Parse a dist:// URI into a DistributionDatasetConfig.

    Format: dist://prompt_tokens=[...];prompt_probs=[...];output_tokens=[...];output_probs=[...]

    :param uri: The dist:// URI string
    :return: DistributionDatasetConfig instance
    :raises ValueError: If the URI format is invalid
    """
    if not uri.startswith("dist://"):
        raise ValueError(f"Expected URI to start with 'dist://', got: {uri}")

    # Remove the dist:// prefix
    content = uri[7:].strip()

    # Parse semicolon-separated key-value pairs
    config_dict: dict[str, Any] = {}
    parts = content.split(";")

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if "=" not in part:
            raise ValueError(f"Invalid key-value pair format: {part}")

        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()

        # Parse list values (e.g., [32,128,512])
        if value.startswith("[") and value.endswith("]"):
            try:
                # Use ast.literal_eval for safe parsing
                parsed_value = ast.literal_eval(value)
                if not isinstance(parsed_value, list):
                    raise ValueError(f"Expected list value for {key}, got {type(parsed_value)}")
                config_dict[key] = parsed_value
            except (ValueError, SyntaxError) as e:
                raise ValueError(f"Invalid list format for {key}: {value}") from e
        else:
            # Try to parse as a number or keep as string
            try:
                if "." in value:
                    config_dict[key] = float(value)
                else:
                    config_dict[key] = int(value)
            except ValueError:
                config_dict[key] = value

    # Validate required fields
    required_fields = ["prompt_tokens", "prompt_probs", "output_tokens", "output_probs"]
    for field in required_fields:
        if field not in config_dict:
            raise ValueError(f"Missing required field: {field}")

    return DistributionDatasetConfig.model_validate(config_dict)


class _DistributionExamplesIterable(_BaseExamplesIterable):
    """Custom examples iterable for distribution-based text generation."""

    def __init__(
        self,
        config: DistributionDatasetConfig,
        processor: PreTrainedTokenizerBase,
        random_seed: int,
    ):
        super().__init__()
        self.config = config
        self.processor = processor
        self.random_seed = random_seed
        self.iteration_count = 0

    def __iter__(self) -> Iterator[tuple[int, dict[str, Any]]]:
        iter_random_seed = self.random_seed + self.iteration_count
        self.iteration_count += 1

        faker = Faker()
        faker.seed_instance(iter_random_seed)
        rand = Random(iter_random_seed)

        # Normalize probabilities for categorical sampling
        prompt_probs_normalized = self._normalize_probs(self.config.prompt_probs)
        output_probs_normalized = self._normalize_probs(self.config.output_probs)

        # Create prefix iterator (empty for now, can be extended later)
        prefix_iter = self._create_prefix_iter(faker, rand)
        samples_count = 0

        while True:
            # Sample token counts from categorical distributions
            prompt_tokens_count = rand.choices(
                self.config.prompt_tokens, weights=prompt_probs_normalized, k=1
            )[0]
            output_tokens_count = rand.choices(
                self.config.output_tokens, weights=output_probs_normalized, k=1
            )[0]

            yield (
                samples_count,
                {
                    "prefix": next(prefix_iter),
                    "prompt": self._create_prompt(
                        prompt_tokens_count,
                        faker,
                        f"{self.iteration_count} {samples_count} ",
                    ),
                    "prompt_tokens_count": prompt_tokens_count,
                    "output_tokens_count": output_tokens_count,
                },
            )
            samples_count += 1

    @staticmethod
    def _normalize_probs(probs: list[float]) -> list[float]:
        """Normalize probabilities to sum to 1.0."""
        total = sum(probs)
        if total == 0:
            raise ValueError("Probabilities sum to zero")
        return [p / total for p in probs]

    @property
    def is_typed(self) -> bool:
        return True

    @property
    def features(self) -> Features:
        return Features(
            {
                "prefix": Value("string"),
                "prompt": Value("string"),
                "prompt_tokens_count": Value("int32"),
                "output_tokens_count": Value("int32"),
            }
        )

    @property
    def num_shards(self) -> int:
        return 1

    def shuffle_data_sources(
        self,
        generator: Any,  # np.random.Generator
    ) -> _DistributionExamplesIterable:
        """Return self since distribution data doesn't have fixed sources to shuffle."""
        return self

    def shard_data_sources(
        self,
        num_shards: int,  # noqa: ARG002
        index: int,  # noqa: ARG002
        contiguous: bool = True,  # noqa: ARG002
    ) -> _DistributionExamplesIterable:
        """Return self since distribution data generation is infinite and stateless."""
        return self

    def load_state_dict(self, state_dict: dict) -> None:
        """Load the state from a state dict."""
        self.iteration_count = state_dict.get("iteration_count", 0)

    def _init_state_dict(self) -> dict:
        """Initialize the state dict for the iterable."""
        self._state_dict = {"iteration_count": self.iteration_count}
        return self._state_dict

    def _create_prompt(
        self, prompt_tokens_count: int, faker: Faker, unique: str = ""
    ) -> str:
        prompt_token_ids: list[int] = []
        avg_chars_per_token = 5
        margin_of_safety = 1.5
        attempts = 0

        while len(prompt_token_ids) < prompt_tokens_count:
            attempts += 1
            num_chars = int(
                prompt_tokens_count * avg_chars_per_token * margin_of_safety * attempts
            )
            text = unique + faker.text(max_nb_chars=num_chars)
            prompt_token_ids = self.processor.encode(text)

        return self.processor.decode(
            prompt_token_ids[:prompt_tokens_count], skip_special_tokens=True
        )

    def _create_prefix_iter(self, faker: Faker, rand: Random) -> Iterator[str]:
        """Create an iterator that yields empty prefixes."""
        while True:
            yield ""


class DistributionDataset(IterableDataset):
    def __init__(
        self,
        config: DistributionDatasetConfig,
        processor: PreTrainedTokenizerBase,
        random_seed: int = 42,
    ):
        self.config = config
        self.processor = processor
        self.random_seed = random_seed

        # Create the examples iterable
        ex_iterable = _DistributionExamplesIterable(
            config=config,
            processor=processor,
            random_seed=random_seed,
        )

        # Initialize parent with proper ex_iterable
        super().__init__(
            ex_iterable=ex_iterable,
            info=DatasetInfo(
                description="Distribution-based text dataset generator",
                features=ex_iterable.features,
            ),
        )

    def set_epoch(self, epoch: int):
        """Set the epoch for the dataset iteration."""
        if isinstance(self._ex_iterable, _DistributionExamplesIterable):
            self._ex_iterable.iteration_count = epoch


@DatasetDeserializerFactory.register("distribution")
class DistributionDatasetDeserializer(DatasetDeserializer):
    def __call__(
        self,
        data: Any,
        processor_factory: Callable[[], PreTrainedTokenizerBase],
        random_seed: int,
        **data_kwargs: dict[str, Any],
    ) -> IterableDataset:
        # Handle dist:// URI format
        if isinstance(data, str) and data.startswith("dist://"):
            config = parse_dist_uri(data)
            return DistributionDataset(
                config=config,
                processor=processor_factory(),
                random_seed=random_seed,
            )

        # Handle DistributionDatasetConfig directly
        if isinstance(data, DistributionDatasetConfig):
            return DistributionDataset(
                config=data,
                processor=processor_factory(),
                random_seed=random_seed,
            )

        raise DataNotSupportedError(
            "Unsupported data for DistributionDatasetDeserializer, "
            "expected dist:// URI string or DistributionDatasetConfig, "
            f"got {type(data)}"
        )

