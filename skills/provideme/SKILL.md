---
name: provideme
description: "One-prompt provider bridge. Takes any coding agent CLI (name, docs URL, or install steps) and produces a modular local API server primarily compatible with Claude Code via Anthropic (/v1/messages). Optionally also exposes OpenAI (/v1/chat/completions) for other clients, plus a {provider}-claude launcher."
---

# Provideme

Given `$ARGUMENT` (a coding agent provider CLI), produce a **modular local provider bridge** so Claude Code can use it.

## What Claude Code actually expects (key compatibility facts)

- **Primary protocol**: Claude Code calls Anthropic **Messages** (`POST /v1/messages`).
- **Headers you must tolerate**: Your bridge should accept and ignore unknown `anthropic-*` headers rather than rejecting them.
- **Streaming**: Claude Code uses streaming heavily; implement **SSE** (`Content-Type: text/event-stream`) or safely emulate streaming with a single delta and a proper stop event.
- **Proxies and strict gateways**: some gateways reject newer/beta fields. Keep the `/v1/messages` handler permissive (parse what you need, pass-through/ignore the rest) so you don’t 400 on extra keys.

## Required shape (keep it modular)

- **Provider adapter**: the only code allowed to spawn the provider CLI
- **Core**: shared normalization + timeouts + streaming helpers + error mapping
- **Protocols**:
  - **Primary (Claude Code)**: Anthropic `POST /v1/messages`
  - **Optional (other clients)**: OpenAI `POST /v1/chat/completions`
- **Harness**: `/health`, a minimal smoke test, and a `{provider}-claude` launcher + README

## Hard constraints

- No secrets in code; env vars only (keychain lookup optional).
- Validate inputs + cap body size.
- Timeouts + consistent error responses.
- Streaming supported (native or safely emulated).

## Minimum `/v1/messages` behavior

- **Request**: accept JSON with at least `messages: [{ role, content }]` and optional `system`, `stream`, `model`, `max_tokens`, `temperature`.
- **Response (non-stream)**: return an object with `type: "message"`, `role: "assistant"`, and `content: [{ type: "text", text: "..." }]`.
- **Response (stream)**: emit SSE events that include at least:
  - `message_start`
  - one or more `content_block_delta` events (can be a single chunk)
  - `message_stop`

## Claude Code integration output (required in the README)

- **Environment**: document setting `ANTHROPIC_BASE_URL` to your local server (e.g. `http://127.0.0.1:<port>`).
- **Auth**: if you add bridge auth, use `BRIDGE_AUTH_TOKEN` and require `Authorization: Bearer ...` consistently across endpoints.
- **Smoke test**: must test `/health` and **both** `/v1/messages` and `/v1/chat/completions` (if the OpenAI protocol is included).

## High-Level Workflow

1) Run `/research` on the provider CLI (install/auth, invocation shape, streaming support).
2) Create a plan that produces the modular bridge + README + smoke test.
3) Run `/parallelize` (optional) and implement.
4) Return copy/paste instructions to run the bridge and point Claude Code at it.