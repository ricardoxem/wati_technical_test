# WATI Automation Agent

CLI-based AI agent that converts natural-language automation requests into previewable WATI API execution plans.

## What This Project Does

This project is a lightweight terminal-based AI agent for the WATI CAB engineering assignment.

The goal is simple:

- A user writes a business request in plain English
- The agent turns that request into a clear WATI API plan
- The plan is shown before execution
- The user confirms the action
- The system executes the workflow and returns a readable summary

This is intentionally built as a focused MVP. The priority is not a polished UI. The priority is showing clear system design, thoughtful UX, and clean execution flow.

## MVP Scope

The first version of this project is intentionally limited to a few strong flows that demonstrate multi-step orchestration across WATI domains.

### Supported request types

1. Find contacts and send a template message

Example:

```text
Send the renewal_reminder template to all VIP contacts
```

2. Escalate a contact to a team and add a tag

Example:

```text
Escalate 6281234567890 to the Support team and add the escalated tag
```

3. Send a broadcast to a filtered audience

Example:

```text
Send a broadcast with the flash_sale template to contacts with city Jakarta
```

### Supported API domains in the MVP

- Contacts
- Tags
- Messages
- Templates
- Broadcasts
- Operators and tickets

### What this agent is not trying to do

- It is not a general-purpose chatbot
- It is not trying to support every WATI endpoint
- It is not trying to solve complex long-running workflow automation
- It is not focused on frontend polish

## Expected Input And Output

### Input

The main input is a natural-language business instruction written in English.

Example:

```text
Send the renewal_reminder template to all VIP contacts
```

### Intermediate output

Before execution, the agent must produce a structured `ExecutionPlan`.

This object is the contract between planning and execution.

It includes:

- `summary`
- `requires_confirmation`
- `missing_information`
- `steps`

Example:

```json
{
  "user_request": "Send the renewal_reminder template to all VIP contacts",
  "summary": "Find VIP contacts, check the template, and send the template message to each contact.",
  "status": "ready",
  "requires_confirmation": true,
  "missing_information": [],
  "steps": [
    {
      "id": "step-1",
      "domain": "contacts",
      "action": "get_contacts_by_tag",
      "description": "Find contacts tagged VIP.",
      "endpoint_hint": "GET /api/v1/getContacts",
      "params": {
        "tag": "VIP"
      }
    },
    {
      "id": "step-2",
      "domain": "templates",
      "action": "get_template_by_name",
      "description": "Check that the renewal_reminder template exists.",
      "endpoint_hint": "GET /api/v1/getMessageTemplates",
      "params": {
        "template_name": "renewal_reminder"
      }
    },
    {
      "id": "step-3",
      "domain": "messages",
      "action": "send_template_message",
      "description": "Send the renewal_reminder template to each matching contact.",
      "endpoint_hint": "POST /api/v1/sendTemplateMessage/{whatsappNumber}",
      "params": {
        "template_name": "renewal_reminder"
      }
    }
  ]
}
```

If the request is unclear, the planner should not guess. Instead, it should return a plan with missing information.

Example:

```json
{
  "user_request": "Send a reminder to my customers",
  "summary": "The user wants to send a reminder message, but important details are still missing.",
  "status": "needs_clarification",
  "requires_confirmation": true,
  "missing_information": [
    "Which template or message should be sent?",
    "Which audience should receive the message?"
  ],
  "steps": []
}
```

### Final output

The system does not jump straight to execution.

It produces:

1. A structured execution plan
2. A human-readable preview
3. A confirmation step
4. A final execution result summary

After confirmation, the executor returns an `ExecutionResult`.

This final result includes:

- overall success or failure
- completed steps
- failed steps
- a short summary
- execution details that are useful for the user

Example:

```json
{
  "success": true,
  "summary": "Sent the renewal_reminder template to 2 VIP contacts.",
  "completed_steps": [
    "step-1",
    "step-2",
    "step-3"
  ],
  "failed_steps": [],
  "details": [
    "Found 2 contacts tagged VIP.",
    "Template renewal_reminder is available.",
    "2 messages were accepted by the mock WATI API."
  ]
}
```

If the request is unclear, the system should ask for missing information instead of guessing.

## Planned Technical Shape

- Terminal-first UX
- Provider-agnostic LLM layer with `ollama` as the default local option
- Mock WATI API built with FastAPI
- Structured planning, validation, preview, and execution flow

## Project Structure

```text
src/wati_agent/
  agent/
  app/
  domain/
  integrations/
  llm/
  mock_api/
```

## Architecture At A Glance

The system is separated into a few small parts so each responsibility is easy to understand:

- `app`
  CLI entrypoints and runtime configuration
- `agent`
  Planning, validation, orchestration, memory, and execution flow
- `llm`
  LLM provider layer, currently prepared for Ollama and future hosted providers
- `integrations/wati`
  WATI client layer, designed so the mock and real API can share the same contract
- `mock_api`
  A realistic FastAPI-based mock of the WATI endpoints used by the MVP
- `domain`
  Shared data models and schemas

## Planning Flow

The planner is intentionally narrow.

It does not ask the model to freely invent workflows. Instead, it asks the model to map the user's text into a small set of supported actions and return pure JSON.

For the MVP, the planner is restricted to:

- `get_contacts_by_tag`
- `get_template_by_name`
- `send_template_message`
- `assign_ticket_to_team`
- `add_tag_to_contact`
- `send_broadcast_to_segment`

The planning flow is:

1. Receive a natural-language request
2. Send a strict prompt to the LLM
3. Ask for JSON only
4. Parse the JSON response
5. Normalize the response into an `ExecutionPlan`
6. Hand the plan to validation before execution

This narrow planning contract helps keep the system easier to test, easier to explain, and more reliable with a local model.

## Core Layer Diagram

```text
Natural-language request
          |
          v
     Planning Layer
     - turns text into a structured ExecutionPlan
     - uses the LLM only for intent understanding
          |
          v
    Validation Layer
    - checks supported actions
    - checks required parameters
    - detects ambiguity
    - decides whether the plan is safe to run
          |
          v
     Execution Layer
     - runs steps in order
     - reuses results from previous steps
     - collects success, failure, and detail lines
          |
          v
 API Integration Layer
 - translates each step into HTTP calls
 - talks to the Mock WATI API today
 - can be swapped for the real WATI API later
```

## Validation Flow

The validator exists so the LLM is not trusted blindly.

After the planner returns an `ExecutionPlan`, the validator checks:

- whether the plan has steps
- whether each step uses a supported action
- whether required parameters are present
- whether confirmation is required before execution
- whether the original request is still ambiguous

Examples of validator responsibilities:

- reject unsupported actions
- require `tag` for `get_contacts_by_tag`
- require `template_name` for `send_template_message`
- require `whatsapp_number` and `team_name` for escalation
- force confirmation for sends, broadcasts, and team assignment

This makes the overall system more reliable:

- the LLM suggests a plan
- the validator turns that suggestion into a safe product decision
- only then is the plan allowed to move forward

## Mock WATI API

To keep the MVP fast to build and easy to demo, this project uses a FastAPI-based mock WATI backend.

The mock API simulates a realistic HTTP integration layer and currently includes:

- `GET /api/v1/getContacts`
- `GET /api/v1/getContactInfo/{whatsappNumber}`
- `GET /api/v1/getMessageTemplates`
- `GET /api/v1/getOperators`
- `POST /api/v1/sendTemplateMessage/{whatsappNumber}`
- `POST /api/v1/tickets/assign`
- `POST /api/v1/addTag/{whatsappNumber}`
- `POST /api/v1/sendBroadcastToSegment`

This gives the agent a real HTTP surface to call during local development, while keeping the architecture ready for a future real WATI client.

## Mock Data

The mock API includes realistic seed data for the demo flows:

- contacts with tags and custom attributes
- templates for renewal, support follow-up, and promotions
- operators mapped to named teams
- teams such as Support, Sales, and Retention
- segments such as `jakarta_customers`, `vip_customers`, and `renewal_candidates`

This makes the local demo feel more like a real business workflow instead of a toy example.

## WATI Client Layer

The agent does not call the mock API directly from the planner or executor.

Instead, all WATI communication is encapsulated in a client layer.

For the mock backend, the `MockWatiClient` uses `httpx` and exposes small, readable methods such as:

- `get_contacts`
- `get_templates`
- `get_operators`
- `send_template_message`
- `assign_ticket_to_team`
- `add_tag_to_contact`
- `send_broadcast_to_segment`

This keeps the architecture clean:

- the planner focuses on intent
- the validator focuses on safety
- the executor focuses on step order
- the WATI client focuses on HTTP integration

## Execution Flow

The executor reads the validated plan one step at a time and runs it in order.

It is responsible for:

- calling the right WATI client method
- carrying context forward from earlier steps
- stopping if a step fails
- collecting readable execution details
- returning a final `ExecutionResult`

One important example is template sending:

- the planner can first fetch matching contacts
- the executor can then reuse that contact list
- the executor sends the template to each matching contact one by one

This makes the flow feel like a real orchestration engine instead of a simple one-shot API call.

## CLI Experience

The CLI is designed to be simple and demo-friendly.

The user can:

- preview a request
- run a request with confirmation
- use a lightweight chat loop for multiple requests in one session

Command summary:

- `preview`
  Generates and shows the execution plan without executing anything.
- `run`
  Generates the plan, asks for confirmation, and then executes it.
- `chat`
  Starts an interactive terminal loop so multiple requests can be tested in the same session.

The CLI experience is intentionally structured like a product flow:

1. show the original request
2. show a readable plan summary
3. show missing information when needed
4. show the execution steps
5. ask for confirmation
6. show the final result with success, failure, and details

This keeps the interface minimal while still showing product thinking and safe execution.

## Why This Scope

This assignment is time-boxed, so the project favors:

- a small number of convincing flows
- strong clarity in architecture
- safe execution with preview and confirmation
- readable code over clever code

That trade-off is deliberate.

## Problem Framing

I framed this assignment as a translation problem between business intent and API execution.

The user should not need to know:

- which WATI endpoints exist
- which endpoint should run first
- what parameters are required
- when an action should be confirmed

Instead, the agent should bridge that gap in a safe and understandable way.

For the MVP, I treated the product as a planning-and-execution assistant rather than a fully autonomous workflow engine. That led to a few guiding choices:

- keep the interaction model simple
- prioritize preview before execution
- constrain the LLM instead of letting it improvise
- validate every plan before it can run
- use a realistic mock backend to demonstrate orchestration without external dependency risk

## Architecture

The system is intentionally split into a few small layers:

1. `CLI`
   Receives the user's request, shows the preview, asks for confirmation, and prints the result.

2. `Planner`
   Sends a narrow prompt to the LLM and asks for strict JSON output.

3. `Validator`
   Applies product rules, required parameter checks, supported action checks, and ambiguity detection.

4. `Executor`
   Runs the validated plan step by step, carries forward context from previous steps, and stops on failure.

5. `WATI Client`
   Encapsulates the HTTP calls, keeping planner and executor independent from raw API details.

6. `Mock WATI API`
   Provides a realistic HTTP surface for local development and demo scenarios.

This separation keeps each layer easy to reason about and easy to explain in a short demo.

## Architecture Diagram

```text
User
  |
  v
CLI (Typer + Rich)
  |
  v
Agent Orchestrator
  |
  +--> Planner
  |      |
  |      v
  |    LLM Provider
  |      |
  |      v
  |    Ollama
  |
  +--> Validator
  |
  +--> Executor
          |
          v
      WATI Client
          |
          v
   Mock WATI API (FastAPI)
          |
          v
      In-memory mock data
```

## Request Lifecycle

The system follows a simple request lifecycle from natural language to HTTP execution.

### 1. User sends a request

Example:

```text
Send the renewal_reminder template to all VIP contacts
```

The request enters through the CLI.

### 2. The planner builds a structured plan

The orchestrator sends the user's text to the planner.

The planner calls the selected LLM provider, which sends a strict prompt to Ollama and asks for JSON only.

The model returns a structured plan such as:

- find contacts tagged `VIP`
- check the `renewal_reminder` template
- send the template message

### 3. The validator checks the plan

Before anything can run, the validator checks:

- whether the actions are supported
- whether required parameters are present
- whether the request is still ambiguous
- whether confirmation is required

If the request is unclear, execution stops here and the CLI shows missing information.

### 4. The CLI shows a preview

If the plan is valid, the user sees:

- the original request
- a summary of what will happen
- the step-by-step plan
- whether confirmation is required

### 5. The executor runs the plan

After confirmation, the executor processes the steps in order.

For a template send flow, the path is:

```text
CLI
  -> Orchestrator
  -> Planner
  -> Ollama
  -> Validator
  -> Executor
  -> MockWatiClient
  -> GET /api/v1/getContacts
  -> GET /api/v1/getMessageTemplates
  -> POST /api/v1/sendTemplateMessage/{whatsappNumber}
```

If the first step returns multiple contacts, the executor reuses that result and sends one message per contact.

### 6. The result comes back to the CLI

The executor collects:

- completed steps
- failed steps
- detail lines
- a final human-readable summary

That final result is printed in the terminal for the user.

## LLM Usage

The project uses an LLM only for intent understanding and plan generation.

More specifically, the model is responsible for:

- reading the user's natural-language instruction
- mapping it to a small set of supported actions
- returning a structured JSON plan

The model is not trusted to decide execution safety on its own.

That is why:

- the prompt is strict
- the output format is constrained
- supported actions are limited
- the validator re-checks the plan before execution

For this submission, I used a provider-agnostic LLM layer and targeted `Ollama` as the default local provider. This avoided dependency on paid hosted APIs while still satisfying the requirement to use an LLM.

## Trade-offs

The main trade-offs I made were:

- `CLI over web UI`
  Faster to build, easier to demo, and enough to show product flow clearly.

- `Mock API over real WATI sandbox`
  Lower delivery risk and easier reproducibility, while still showing real HTTP orchestration.

- `Narrow action set over broad endpoint coverage`
  Better reliability and better explanation in a time-boxed assignment.

- `Strict planning contract over open-ended agent behavior`
  More testable and safer, especially with a local model.

- `Simple in-memory state over persistent storage`
  Good enough for the MVP, while keeping the project focused on orchestration logic.

## Time Spent

Approximate time allocation for this MVP:

- `20%` problem framing, scope selection, and architecture
- `20%` LLM planning contract and validation design
- `25%` mock API and WATI client layer
- `20%` executor and CLI experience
- `15%` testing, README, and submission preparation

I intentionally optimized for a smaller, explainable system rather than broad surface area.

## What Was Not Built

To stay within the spirit of the assignment, I intentionally did not build:

- a polished web frontend
- support for all WATI endpoints
- conversational memory beyond a lightweight session helper
- rollback or compensating actions
- persistent storage
- authentication and multi-user support
- production-grade observability
- real WATI sandbox integration

## V2 Roadmap

If I continued this project, the next improvements would be:

1. Add a real WATI client and make the backend selectable by environment.
2. Improve clarification flow so the agent can ask focused follow-up questions instead of stopping.
3. Add better batch handling for large audiences, including progress reporting and partial retry logic.
4. Add persistent execution history and audit logs.
5. Add support for more WATI domains and richer parameter extraction.
6. Add a lightweight web UI once the workflow engine is stable.
7. Add evaluation fixtures for prompt regression testing against multiple example requests.

## Local Development

1. Start Ollama:

```bash
ollama serve
```

2. Pull the default model:

```bash
ollama pull llama3.1:8b
```

3. Install project dependencies:

```bash
pip install -e ".[dev]"
```

4. Start the mock WATI API:

```bash
uvicorn wati_agent.mock_api.main:app --reload --port 8001
```

If the local model is running on CPU and the first request is slow, increase the timeout in `.env`:

```bash
OLLAMA_TIMEOUT_SECONDS=300
```

5. Run the CLI preview:

```bash
python -m wati_agent.app.cli preview "Send the renewal_reminder template to all VIP contacts"
```

6. Run the full request flow:

```bash
python -m wati_agent.app.cli run "Send the renewal_reminder template to all VIP contacts"
```

7. Start the interactive terminal mode:

```bash
python -m wati_agent.app.cli chat
```

## Tests

Run the scenario tests with:

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 pytest -p no:cacheprovider tests/test_step_10_scenarios.py
```

## Local Test Commands

Below is the quickest way to test the project locally.

### Terminal 1: Start Ollama

```bash
ollama serve
```

### Terminal 2: Start the mock WATI API

```bash
cd /home/ricardoxem/Documents/RICARDOXEM/repositories/wati_technical_test
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn wati_agent.mock_api.main:app --reload --port 8001
```

### Terminal 3: Run the CLI

```bash
cd /home/ricardoxem/Documents/RICARDOXEM/repositories/wati_technical_test
source .venv/bin/activate
```

Preview a plan:

```bash
python -m wati_agent.app.cli preview "Send the renewal_reminder template to all VIP contacts"
```

Run a full happy-path flow:

```bash
python -m wati_agent.app.cli run "Send the renewal_reminder template to all VIP contacts"
```

Run the escalation flow:

```bash
python -m wati_agent.app.cli run "Escalate 6281234567890 to the Support team and add the escalated tag"
```

Run an ambiguous request:

```bash
python -m wati_agent.app.cli run "Send a reminder to my customers"
```

Start the interactive terminal mode:

```bash
python -m wati_agent.app.cli chat
```

Run the automated tests from the `tests` folder:

```bash
pytest -p no:cacheprovider tests/
```
