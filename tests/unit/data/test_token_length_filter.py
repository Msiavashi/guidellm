"""Tests for the TokenLengthFilter preprocessor."""

import pytest

from guidellm.data.preprocessors.token_budget import TokenLengthFilter
from guidellm.data.preprocessors.preprocessor import SkipDataRow


class TestTokenLengthFilter:
    """Test suite for TokenLengthFilter preprocessor."""

    def test_init_requires_at_least_one_constraint(self):
        """Test that at least one constraint must be specified."""
        with pytest.raises(ValueError, match="At least one of"):
            TokenLengthFilter()

    def test_max_input_length_filter(self):
        """Test filtering by max input length."""
        filter_fn = TokenLengthFilter(max_input_length=100)
        
        # Should pass: input within limit
        columns = {
            "prompt_tokens_count_column": [50],
            "output_tokens_count_column": [200],  # Output doesn't matter
        }
        result = filter_fn(columns)
        assert result == columns
        
        # Should fail: input exceeds limit
        columns_fail = {
            "prompt_tokens_count_column": [150],
            "output_tokens_count_column": [50],
        }
        with pytest.raises(SkipDataRow):
            filter_fn(columns_fail)

    def test_max_output_length_filter(self):
        """Test filtering by max output length."""
        filter_fn = TokenLengthFilter(max_output_length=100)
        
        # Should pass: output within limit
        columns = {
            "prompt_tokens_count_column": [200],  # Input doesn't matter
            "output_tokens_count_column": [50],
        }
        result = filter_fn(columns)
        assert result == columns
        
        # Should fail: output exceeds limit
        columns_fail = {
            "prompt_tokens_count_column": [50],
            "output_tokens_count_column": [150],
        }
        with pytest.raises(SkipDataRow):
            filter_fn(columns_fail)

    def test_combined_filters(self):
        """Test filtering with both input and output constraints."""
        filter_fn = TokenLengthFilter(
            max_input_length=100,
            max_output_length=50
        )
        
        # Should pass: both within limits
        columns_pass = {
            "prompt_tokens_count_column": [80],
            "output_tokens_count_column": [30],
        }
        result = filter_fn(columns_pass)
        assert result == columns_pass
        
        # Should fail: input exceeds limit
        columns_fail_input = {
            "prompt_tokens_count_column": [120],
            "output_tokens_count_column": [30],
        }
        with pytest.raises(SkipDataRow):
            filter_fn(columns_fail_input)
        
        # Should fail: output exceeds limit
        columns_fail_output = {
            "prompt_tokens_count_column": [80],
            "output_tokens_count_column": [60],
        }
        with pytest.raises(SkipDataRow):
            filter_fn(columns_fail_output)
        
        # Should fail: both exceed limits
        columns_fail_both = {
            "prompt_tokens_count_column": [120],
            "output_tokens_count_column": [60],
        }
        with pytest.raises(SkipDataRow):
            filter_fn(columns_fail_both)

    def test_missing_token_counts(self):
        """Test behavior when token counts are missing."""
        filter_fn = TokenLengthFilter(max_input_length=100)
        
        # Missing token counts should skip the row
        columns = {
            "text_column": ["some text"],
            # No token counts provided, and no processor_factory
        }
        with pytest.raises(SkipDataRow):
            filter_fn(columns)

    def test_different_total_from_separate_limits(self):
        """Test that separate limits allow different totals than budget filter."""
        # With separate limits of 2047 input and 512 output,
        # total can be up to 2559 (2047 + 512)
        filter_fn = TokenLengthFilter(
            max_input_length=2047,
            max_output_length=512
        )
        
        # Should pass: input=2047, output=512, total=2559
        columns = {
            "prompt_tokens_count_column": [2047],
            "output_tokens_count_column": [512],
        }
        result = filter_fn(columns)
        assert result == columns
        
        # Should pass: input=1000, output=500, total=1500
        columns2 = {
            "prompt_tokens_count_column": [1000],
            "output_tokens_count_column": [500],
        }
        result2 = filter_fn(columns2)
        assert result2 == columns2
        
        # Should fail: input=2048 (exceeds max_input_length)
        columns_fail = {
            "prompt_tokens_count_column": [2048],
            "output_tokens_count_column": [100],
        }
        with pytest.raises(SkipDataRow):
            filter_fn(columns_fail)
