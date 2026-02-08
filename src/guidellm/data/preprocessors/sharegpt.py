"""ShareGPT dataset preprocessor for conversational data.

This module provides a preprocessor that can handle ShareGPT-style conversational
datasets and extract prompt/response pairs from the nested conversation structure.
"""

from __future__ import annotations

from typing import Any

from guidellm.data.preprocessors.preprocessor import (
    DatasetPreprocessor,
    PreprocessorRegistry,
)

__all__ = ["ShareGPTPreprocessor"]


@PreprocessorRegistry.register("sharegpt")
class ShareGPTPreprocessor(DatasetPreprocessor):
    """
    Preprocessor for ShareGPT-style conversational datasets.
    
    Transforms conversational data with nested structures like:
    {
        "conversations": [
            {"from": "human", "value": "Hello, how are you?"},
            {"from": "gpt", "value": "I'm doing well, thank you!"},
            ...
        ]
    }
    
    Into flat prompt/response format:
    {
        "prompt": "Hello, how are you?",
        "response": "I'm doing well, thank you!"
    }
    """
    
    def __init__(
        self,
        conversations_column: str = "conversations",
        human_role: str = "human",
        assistant_role: str = "gpt",
        use_last_turn: bool = True,
    ):
        """
        Initialize the ShareGPT preprocessor.
        
        :param conversations_column: Name of the column containing conversation data
        :param human_role: Role identifier for human messages (e.g., "human", "user")
        :param assistant_role: Role identifier for assistant messages (e.g., "gpt", "assistant")
        :param use_last_turn: If True, use the last human-assistant turn. If False, use the first turn.
        """
        self.conversations_column = conversations_column
        self.human_role = human_role
        self.assistant_role = assistant_role
        self.use_last_turn = use_last_turn

    def __call__(self, item: dict[str, Any]) -> dict[str, Any]:
        """
        Process a single dataset item to extract prompt/response from conversations.
        
        :param item: Raw dataset item wrapper with structure {"items": [dataset_row, ...]}
        :return: Processed item with flat prompt/response structure added to the dataset row
        """
        # The item comes as {"items": [dataset_row, ...]} from DatasetsIterator
        items = item.get("items")
        if not items or not isinstance(items, list):
            return item
        
        # Process each dataset row
        for dataset_row in items:
            if not isinstance(dataset_row, dict):
                continue
                
            # Get conversations from the dataset row
            conversations = dataset_row.get(self.conversations_column, [])
            if not conversations or not isinstance(conversations, list):
                continue
            
            # Extract human-assistant pairs
            pairs = []
            human_msg = None
            
            for message in conversations:
                if not isinstance(message, dict):
                    continue
                    
                role = message.get("from", "").lower()
                value = message.get("value", "")
                
                if role == self.human_role.lower():
                    human_msg = value
                elif role == self.assistant_role.lower() and human_msg is not None:
                    pairs.append((human_msg, value))
                    human_msg = None  # Reset for next pair
            
            if not pairs:
                # No valid pairs found, skip
                continue
            
            # Select which turn to use
            if self.use_last_turn:
                prompt, response = pairs[-1]
            else:
                prompt, response = pairs[0]
            
            # Add flat structure to the dataset row for column mapper to pick up
            dataset_row["prompt"] = prompt
            dataset_row["response"] = response
        
        return item
