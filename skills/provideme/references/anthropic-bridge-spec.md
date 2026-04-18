# Anthropic Bridge API Specification

This document specifies the Anthropic Messages protocol requirements and constraints that the provider bridge must implement to integrate with Claude Code.

## Protocol Overview

Claude Code calls Anthropic **Messages API** (`POST /v1/messages`) exclusively. The bridge must implement only this protocol shape.

## Request/Response Compatibility

### Headers: Permissive Handling

- **What Claude Code sends**: Various `anthropic-*` headers (e.g., `anthropic-version`, `anthropic-beta`, custom beta flags)
- **Bridge requirement**: Accept and tolerate unknown headers rather than rejecting them
- **Why**: Newer/beta fields may come from Claude Code updates or strict gateways that modify requests
- **Implementation**: Parse only what you need; pass-through or safely ignore the rest

### Streaming Protocol

Claude Code uses streaming heavily. The bridge must implement one of:

1. **Native SSE (text/event-stream)**
   - Respond with `Content-Type: text/event-stream`
   - Emit properly formatted SSE events
2. **Safely emulated streaming**
   - Return a single delta event followed by a proper stop event
   - Do not break the SSE contract

### Request Structure

Accept JSON with:
- `messages` (required): array of `[{ role: string, content: string | object[] }]`
- `system` (optional): system prompt
- `stream` (optional): boolean to enable streaming
- `model` (optional): model identifier
- `max_tokens` (optional): token limit
- `temperature` (optional): temperature value

### Response Structure (Non-Streaming)

Return an object:
```json
{
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "..."
    }
  ]
}
```

### Response Structure (Streaming)

Emit SSE events in sequence:
1. `message_start` event (minimum: message object with type/role/content)
2. One or more `content_block_delta` events (can be a single chunk)
3. `message_stop` event

## Modular Bridge Architecture

Organize the bridge into clear, isolated modules:

### Provider Adapter
- Only module allowed to spawn the provider CLI
- Handles provider-specific invocation, arg transformation, output parsing
- Returns normalized request/response objects to core

### Core Module
- Shared normalization + timeouts + streaming helpers + error mapping
- Converts between provider-specific formats and Anthropic Messages shape
- Implements consistent error responses across all paths

### Protocol Handler (Anthropic)
- Implements `/v1/messages` endpoint only
- Validates inputs, caps body size
- Delegates to core for streaming/normalization
- Do not implement OpenAI or other API shapes

### Harness
- `/health` endpoint (optional but required for smoke tests)
- Minimal smoke test included in README
- `{provider}-claude` launcher script
- README with integration instructions

## Hard Constraints

### Secrets & Environment Variables
- No secrets in code; use env vars only
- Optional: keychain lookup support
- Required env vars for bridge auth (if implemented): `BRIDGE_AUTH_TOKEN`
- Required env var for Claude Code: `ANTHROPIC_BASE_URL` (e.g., `http://127.0.0.1:<port>`)

### Input Validation & Resource Limits
- Validate request structure before passing to provider
- Cap request body size to prevent runaway memory usage
- Validate streaming response format before forwarding

### Timeouts & Error Handling
- Implement request timeouts (provider-dependent; recommend 30-60s)
- Return consistent error responses (JSON, not raw stderr)
- Map provider errors to sensible HTTP status codes

### Streaming Support
- Required: support `stream: true` requests
- If provider does not natively stream, safely emulate with single delta + stop
- Do not break the SSE event format contract

## Claude Code Integration Output

The README must document:

### Environment Setup
```bash
export ANTHROPIC_BASE_URL=http://127.0.0.1:<port>
```

### Authentication (if bridge auth is added)
```bash
export BRIDGE_AUTH_TOKEN=<token>
# Bridge enforces: Authorization: Bearer <token>
```

### Smoke Test
Must test:
1. `/health` endpoint (if implemented)
2. `/v1/messages` with non-streaming request
3. `/v1/messages` with streaming request

Example:
```bash
# Non-stream
curl -X POST http://127.0.0.1:<port>/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "hi"}], "stream": false}'

# Stream
curl -X POST http://127.0.0.1:<port>/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "hi"}], "stream": true}'
```

## Implementation Checklist

- [ ] Provider adapter module created and tested
- [ ] Core normalization module with error mapping
- [ ] `/v1/messages` handler (streaming + non-streaming)
- [ ] Request validation (body size, input schema)
- [ ] Timeout handling on provider calls
- [ ] Error responses in consistent JSON format
- [ ] `/health` endpoint (optional)
- [ ] SSE protocol compliance verified
- [ ] `{provider}-claude` launcher script
- [ ] README with integration instructions and smoke test
- [ ] Tested with Claude Code at `ANTHROPIC_BASE_URL`
