"""Token budget filtering for generative datasets."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from transformers import PreTrainedTokenizerBase

from guidellm.data.preprocessors.preprocessor import (
    DatasetPreprocessor,
    PreprocessorRegistry,
    SkipDataRow,
)
from guidellm.logger import logger

__all__ = [
    "TokenBudgetFilter",
    "TokenLengthFilter",
    "compute_input_tokens",
    "compute_output_tokens",
]


def _join_text_values(values: list[Any]) -> str:
    return "".join(value for value in values if isinstance(value, str) and value)


def compute_input_tokens(
    columns: dict[str, list[Any]],
    processor_factory: Callable[[], PreTrainedTokenizerBase] | None,
    include_prefix_in_input: bool = True,
) -> int | None:
    if prompt_tokens := sum(
        count for count in columns.get("prompt_tokens_count_column", []) if count
    ):
        return int(prompt_tokens)

    if not processor_factory:
        return None

    prefix_text = ""
    if include_prefix_in_input:
        prefix_text = _join_text_values(columns.get("prefix_column", []))
    text = _join_text_values(columns.get("text_column", []))
    prompt = prefix_text + text
    if not prompt:
        return None

    tokenizer = processor_factory()
    return len(tokenizer.encode(prompt))


def compute_output_tokens(
    columns: dict[str, list[Any]],
    processor_factory: Callable[[], PreTrainedTokenizerBase] | None,
) -> int | None:
    if output_tokens := sum(
        count for count in columns.get("output_tokens_count_column", []) if count
    ):
        return int(output_tokens)

    if not processor_factory:
        return None

    response_text = _join_text_values(columns.get("response_column", []))
    if not response_text:
        return None

    tokenizer = processor_factory()
    return len(tokenizer.encode(response_text))


@PreprocessorRegistry.register("token_budget_filter")
class TokenBudgetFilter(DatasetPreprocessor):
    """Filter rows where input_tokens + output_tokens equals a target budget."""

    def __init__(
        self,
        token_budget_total: int,
        processor_factory: Callable[[], PreTrainedTokenizerBase] | None = None,
        include_prefix_in_input: bool = True,
    ) -> None:
        self.token_budget_total = token_budget_total
        self.processor_factory = processor_factory
        self.include_prefix_in_input = include_prefix_in_input

    def __call__(self, columns: dict[str, list[Any]]) -> dict[str, list[Any]]:
        input_tokens = compute_input_tokens(
            columns,
            self.processor_factory,
            include_prefix_in_input=self.include_prefix_in_input,
        )
        output_tokens = compute_output_tokens(columns, self.processor_factory)

        if input_tokens is None or output_tokens is None:
            logger.debug(
                "Skipping row for token budget filter due to missing token counts."
            )
            raise SkipDataRow()

        if input_tokens + output_tokens > self.token_budget_total:
            raise SkipDataRow()

        return columns


@PreprocessorRegistry.register("token_length_filter")
class TokenLengthFilter(DatasetPreprocessor):
    """
    Filter rows based on separate max input and output token lengths.
    
    This filter allows independent control over input and output token limits,
    enabling more flexible dataset filtering compared to a single total budget.
    """

    def __init__(
        self,
        max_input_length: int | None = None,
        max_output_length: int | None = None,
        processor_factory: Callable[[], PreTrainedTokenizerBase] | None = None,
        include_prefix_in_input: bool = True,
    ) -> None:
        """
        Initialize the token length filter.
        
        :param max_input_length: Maximum allowed input token length (None for no limit)
        :param max_output_length: Maximum allowed output token length (None for no limit)
        :param processor_factory: Factory function to create tokenizer instances
        :param include_prefix_in_input: Whether to include prefix in input token count
        """
        if max_input_length is None and max_output_length is None:
            raise ValueError(
                "At least one of max_input_length or max_output_length must be specified"
            )
        
        self.max_input_length = max_input_length
        self.max_output_length = max_output_length
        self.processor_factory = processor_factory
        self.include_prefix_in_input = include_prefix_in_input

    def __call__(self, columns: dict[str, list[Any]]) -> dict[str, list[Any]]:
        """
        Filter a dataset row based on token length constraints.
        
        :param columns: Dictionary mapping column types to values
        :return: The input columns if the row passes the filter
        :raises SkipDataRow: If the row exceeds length constraints
        """
        # Compute input tokens if we have a max input length constraint
        if self.max_input_length is not None:
            input_tokens = compute_input_tokens(
                columns,
                self.processor_factory,
                include_prefix_in_input=self.include_prefix_in_input,
            )
            
            if input_tokens is None:
                logger.debug(
                    "Skipping row for token length filter due to missing input token counts."
                )
                raise SkipDataRow()
            
            if input_tokens > self.max_input_length:
                logger.debug(
                    f"Skipping row: input tokens ({input_tokens}) exceeds max ({self.max_input_length})"
                )
                raise SkipDataRow()
        
        # Compute output tokens if we have a max output length constraint
        if self.max_output_length is not None:
            output_tokens = compute_output_tokens(columns, self.processor_factory)
            
            if output_tokens is None:
                logger.debug(
                    "Skipping row for token length filter due to missing output token counts."
                )
                raise SkipDataRow()
            
            if output_tokens > self.max_output_length:
                logger.debug(
                    f"Skipping row: output tokens ({output_tokens}) exceeds max ({self.max_output_length})"
                )
                raise SkipDataRow()
        
        return columns


