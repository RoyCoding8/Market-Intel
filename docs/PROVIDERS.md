# LLM Provider Configuration

## How It Works

The engine uses [litellm](https://docs.litellm.ai) for provider routing and [instructor](https://python.useinstructor.com) for structured output extraction.

```
extract_structured(prompt, response_model)
    │
    ▼
instructor.from_litellm(acompletion)
    │
    ▼
litellm.acompletion(model="openai/gpt-4o", messages=[...])
    │
    ▼
Provider API (OpenAI, Anthropic, Google, etc.)
```

litellm reads the `LLM_MODEL` environment variable (format: `provider/model-name`) and routes to the correct provider API. Instructor converts the Pydantic `response_model` into tool/function definitions that the LLM uses to return structured JSON.

## Supported Providers

### OpenAI
```bash
LLM_MODEL=openai/gpt-4o
OPENAI_API_KEY=sk-...
```

### Anthropic (Claude)
```bash
LLM_MODEL=anthropic/claude-sonnet-4-20250514
ANTHROPIC_API_KEY=sk-ant-...
```

### Google Gemini (AI Studio)
```bash
LLM_MODEL=gemini/gemini-2.5-pro
GEMINI_API_KEY=...
```

### Google Vertex AI
```bash
LLM_MODEL=vertex_ai/gemini-2.0-flash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
VERTEX_PROJECT=your-gcp-project
VERTEX_LOCATION=us-central1
```

### Azure OpenAI
```bash
LLM_MODEL=azure/gpt-4o
AZURE_API_KEY=...
AZURE_API_BASE=https://your-resource.openai.azure.com/
AZURE_API_VERSION=2024-02-15-preview
AZURE_DEPLOYMENT=gpt-4o-deployment
```

### DeepSeek
```bash
LLM_MODEL=deepseek/deepseek-chat
DEEPSEEK_API_KEY=...
```

### Mistral
```bash
LLM_MODEL=mistral/mistral-large-latest
MISTRAL_API_KEY=...
```

### Groq
```bash
LLM_MODEL=groq/llama-3.3-70b-versatile
GROQ_API_KEY=...
```

### Together AI
```bash
LLM_MODEL=together_ai/meta-llama/Llama-3-70b-chat-hf
TOGETHERAI_API_KEY=...
```

### Ollama (local)
```bash
LLM_MODEL=ollama/llama3.1
OLLAMA_API_BASE=http://localhost:11434
```

### Xiaomi MiMo (via Opengateway)
```bash
LLM_MODEL=openai/mimo-v2.5-pro
OPENAI_API_KEY=ogw_live_...
OPENAI_API_BASE=https://opengateway.gitlawb.com/v1
```

### Xiaomi MiMo (direct)
```bash
LLM_MODEL=xiaomi_mimo/mimo-v2.5-pro
XIAOMI_MIMO_API_KEY=...
```

### Any OpenAI-compatible endpoint
```bash
LLM_MODEL=openai/your-model-name
OPENAI_API_KEY=sk-no-key-needed
OPENAI_API_BASE=http://localhost:8080/v1
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_MODEL` | Model identifier in litellm format | `openai/gpt-4o` |
| `LLM_TIMEOUT_SECONDS` | Per-call timeout | `60` |

Each provider has its own API key environment variable. litellm automatically resolves the correct key based on the model prefix. See `.env.example` for the full list.

## Structured Output

All LLM calls use instructor's `response_model` parameter to enforce structured output. The LLM receives a JSON schema derived from the Pydantic model and is instructed to return valid JSON matching that schema.

**Retry behavior:** If the LLM returns invalid JSON or data that fails Pydantic validation, instructor automatically re-prompts with the validation error up to `max_retries` times (default: 3).

**Temperature:** All calls use `temperature=0.0` for deterministic output.

## Extraction Models

Each agent defines internal Pydantic models for extraction:

| Agent | Models |
|-------|--------|
| Analyzer | `_PricingExtraction`, `_FeatureExtraction`, `_TeamExtraction`, `_NewsExtraction`, `_ClaimExtraction` |
| Verifier | `_VerificationJudgement` |
| Reporter | `_ReportDraft` |

These are separate from the `contracts/engine.py` models because they include LLM-specific fields (e.g., `is_custom`, `limitations`, `exact_match`) that aren't needed in the pipeline contracts.
