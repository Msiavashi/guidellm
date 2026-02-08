# ShareGPT Dataset Support

GuideLLM provides built-in support for ShareGPT-style conversational datasets through a dedicated preprocessor. This allows you to benchmark models using realistic conversational data while automatically extracting prompt/response pairs and computing appropriate output token lengths.

## ShareGPT Format

ShareGPT datasets typically have a nested conversational structure like:

```json
{
  "conversations": [
    {"from": "human", "value": "Hello, how are you?"},
    {"from": "gpt", "value": "I'm doing well, thank you for asking!"},
    {"from": "human", "value": "What can you help me with?"},
    {"from": "gpt", "value": "I can help with various tasks..."}
  ]
}
```

## Usage

To use ShareGPT datasets with GuideLLM, add the `--sharegpt-format` flag to your benchmark command:

```bash
guidellm benchmark run \
  --target http://localhost:8000 \
  --request-type text_completions \
  --data "openchat/openchat_sharegpt_v3" \
  --sharegpt-format \
  --compute-output-tokens-from-response \
  --processor Qwen/Qwen3-30B-A3B
```

## Configuration Options

### Basic ShareGPT Options

- `--sharegpt-format`: Enable ShareGPT conversational dataset processing
- `--sharegpt-conversations-column`: Column name containing conversations (default: "conversations")
- `--sharegpt-human-role`: Role identifier for human messages (default: "human")
- `--sharegpt-assistant-role`: Role identifier for assistant messages (default: "gpt")
- `--sharegpt-use-last-turn`: Use the last conversation turn (default: true)

### Response Token Computation

- `--compute-output-tokens-from-response`: Automatically compute output token counts from response text

## Examples

### Basic ShareGPT Usage

```bash
guidellm benchmark run \
  --target http://localhost:8000 \
  --request-type text_completions \
  --data "openchat/openchat_sharegpt_v3" \
  --sharegpt-format \
  --compute-output-tokens-from-response
```

### Custom Role Names

For datasets with different role identifiers:

```bash
guidellm benchmark run \
  --target http://localhost:8000 \
  --request-type chat_completions \
  --data "your/custom_sharegpt_dataset" \
  --sharegpt-format \
  --sharegpt-human-role "user" \
  --sharegpt-assistant-role "assistant" \
  --compute-output-tokens-from-response
```

### Different Conversation Column

For datasets with non-standard column names:

```bash
guidellm benchmark run \
  --target http://localhost:8000 \
  --request-type text_completions \
  --data "your/dataset" \
  --sharegpt-format \
  --sharegpt-conversations-column "messages" \
  --compute-output-tokens-from-response
```

### Using First Turn Instead of Last

To use the first conversation turn instead of the last:

```bash
guidellm benchmark run \
  --target http://localhost:8000 \
  --request-type text_completions \
  --data "your/dataset" \
  --sharegpt-format \
  --no-sharegpt-use-last-turn \
  --compute-output-tokens-from-response
```

## How It Works

1. **Conversation Extraction**: The ShareGPT preprocessor parses the nested conversation structure
2. **Turn Selection**: Extracts human-assistant pairs, using either the first or last turn as specified
3. **Flat Transformation**: Converts the selected turn into flat `prompt` and `response` fields
4. **Token Computation**: When `--compute-output-tokens-from-response` is enabled, uses the specified tokenizer to compute exact token counts from response text
5. **Request Generation**: Creates benchmark requests with appropriate `max_tokens` settings based on original response lengths

## Benefits

- **Realistic Benchmarking**: Generate exactly as many tokens as the original responses
- **Automatic Processing**: No manual preprocessing required
- **Flexible Configuration**: Support for different dataset structures and role names
- **Token Accuracy**: Uses the same tokenizer as your model for precise token counting

