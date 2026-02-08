"""Preprocessor for tokenized OpenChat ShareGPT datasets.

This module provides a preprocessor for pre-tokenized ShareGPT datasets
like openchat/openchat_sharegpt_v3 which contain token IDs rather than text.
"""

from __future__ import annotations

from typing import Any, Callable

from transformers import PreTrainedTokenizerBase

from guidellm.data.preprocessors.preprocessor import (
    DatasetPreprocessor,
    PreprocessorRegistry,
)

__all__ = ["TokenizedShareGPTPreprocessor"]


@PreprocessorRegistry.register("tokenized_sharegpt")
class TokenizedShareGPTPreprocessor(DatasetPreprocessor):
    """
    Preprocessor for tokenized ShareGPT datasets like openchat/openchat_sharegpt_v3.
    
    These datasets contain pre-tokenized data with fields like:
    - nz_input_ids: Concatenated input token IDs
    - nz_shifted_label_ids: Concatenated label/response token IDs  
    - seqlens: Sequence lengths for each turn
    - num_seqs: Number of conversation turns
    
    This preprocessor extracts the last turn and decodes it back to text.
    """
    
    def __init__(
        self,
        processor_factory: Callable[[], PreTrainedTokenizerBase],
        use_last_turn: bool = True,
    ):
        """
        Initialize the tokenized ShareGPT preprocessor.
        
        :param processor_factory: Factory function to get the tokenizer
        :param use_last_turn: If True, use the last turn. If False, use the first turn.
        """
        self.processor_factory = processor_factory
        self.use_last_turn = use_last_turn
        self._tokenizer = None

    @property
    def tokenizer(self) -> PreTrainedTokenizerBase:
        """Lazy load the tokenizer."""
        if self._tokenizer is None:
            self._tokenizer = self.processor_factory()
        return self._tokenizer

    def __call__(self, item: dict[str, Any]) -> dict[str, Any]:
        """
        Process a tokenized dataset item to extract prompt/response text.
        
        :param item: Raw dataset item with tokenized data
        :return: Processed item with text prompt/response
        """
        # Get tokenized data
        input_ids = item.get('nz_input_ids', [])
        label_ids = item.get('nz_shifted_label_ids', [])
        seqlens = item.get('seqlens', [])
        num_seqs = item.get('num_seqs', 0)
        
        if not input_ids or not label_ids or not seqlens or num_seqs == 0:
            # Return original if data is missing
            return item
        
        # Split sequences by lengths
        input_seqs = []
        label_seqs = []
        start_idx = 0
        
        for length in seqlens:
            end_idx = start_idx + length
            input_seqs.append(input_ids[start_idx:end_idx])
            label_seqs.append(label_ids[start_idx:end_idx])
            start_idx = end_idx
        
        # Select which turn to use
        if self.use_last_turn:
            # Use the last turn
            prompt_tokens = input_seqs[-1] if input_seqs else []
            response_tokens = label_seqs[-1] if label_seqs else []
        else:
            # Use the first turn
            prompt_tokens = input_seqs[0] if input_seqs else []
            response_tokens = label_seqs[0] if label_seqs else []
        
        if not prompt_tokens or not response_tokens:
            return item
        
        # Decode tokens to text
        try:
            prompt_text = self.tokenizer.decode(prompt_tokens, skip_special_tokens=True)
            response_text = self.tokenizer.decode(response_tokens, skip_special_tokens=True)
        except Exception:
            # If decoding fails, return original item
            return item
        
        # Create result with flat structure
        result = item.copy()
        result["prompt"] = prompt_text
        result["response"] = response_text
        result["text_column"] = prompt_text
        result["response_column"] = response_text
        
        return result

