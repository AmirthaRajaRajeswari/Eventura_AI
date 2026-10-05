# Eventura AI

> **Agentic AI Event Planning & Coordination Platform**

Eventura AI is an agentic event-planning platform that uses specialized
AI agents, retrieval-augmented generation (RAG), tool use, validation,
iterative critique, stateful workflows, and human-in-the-loop approval
to plan and coordinate events.

It is designed for events such as **Weddings, Birthdays, and College
Fests**.

## 1. Problem Statement

Traditional event-planning applications mostly behave as search, CRUD,
or recommendation systems. Users still have to manually search for
vendors, compare prices, check availability, verify constraints, build a
plan, monitor the budget, resolve conflicts, and replan when something
changes.

A plain LLM chatbot also has limitations: it may hallucinate vendors or
prices, ignore hard constraints, fail to ground decisions in evidence,
generate plans beyond the budget, and provide no controlled workflow for
approval before actions.

Eventura AI addresses this by combining:

-   Multi-agent orchestration
-   Structured event state
-   Agentic RAG
-   SQL and vector retrieval
-   Feasibility checking
-   Budget reasoning
-   Negotiation
-   Critic-based validation
-   Self-correction and replanning
-   Human-in-the-loop approval
-   Mock vendor booking
-   Evaluation and comparison

## 2. Objectives

The project aims to:

1.  Convert natural-language event requests into structured
    requirements.
2.  Check whether the requested event is feasible.
3.  Retrieve relevant vendor and knowledge evidence.
4.  Select vendors according to requirements and constraints.
5.  Reason about budget allocation.
6.  Detect conflicts and constraint violations.
7.  Critique and improve generated plans.
8.  Preserve state throughout the workflow.
9.  Request human approval before booking.
10. Execute controlled mock bookings after approval.
11. Expose agent activity for transparency.
12. Compare No-RAG, Basic-RAG, and Agentic-RAG approaches.
13. Evaluate planning quality using measurable metrics.

## 3. Key Features

### Natural-language intake

Users can provide a complete event request in natural language.

Example:

> Plan a wedding in Chennai for 200 guests with a budget of ₹5,00,000. I
> need a venue, catering, decoration, and photography.

The system extracts event type, location, date, guest count, budget,
duration, required categories, preferences, and constraints.

### Feasibility analysis

The Feasibility Agent checks whether available resources can satisfy the
event constraints, including budget, location, guest count, required
categories, capacity, and availability.

### Multi-agent planning

Specialized agents perform different stages rather than asking one LLM
to complete the entire workflow.

### Agentic RAG

The system supports adaptive evidence retrieval using SQL/vendor
retrieval, vector retrieval, evidence sufficiency checking, and
additional retrieval rounds when required.

### Budget reasoning

The system tracks total budget, allocated amount, remaining amount,
utilization, negotiation savings, and budget violations.

### Negotiation

The Negotiator Agent can reason about vendor pricing and attempt to
improve the allocation.

### Critic and self-correction

The Critic Agent evaluates the generated plan for budget issues, missing
mandatory categories, evidence problems, availability verification
issues, and other constraints. Failed plans can return to the Planner
for another iteration.

### Human-in-the-loop

The system pauses before booking so a human can approve, request
modification, or reject a vendor.

### Mock booking

The Booking Agent executes the approved plan against the synthetic/mock
vendor marketplace.

### Agent activity

The UI exposes workflow stages, retrieval activity, planning iterations,
critic feedback, approval, and booking progress.

### Dashboard

The dashboard summarizes event details, budget, selected vendors,
evidence, critic iterations, negotiation savings, and errors.

## 4. Why the System Is Agentic

Eventura AI is a workflow rather than a single LLM call.

``` text
User Goal
   ↓
Intake
   ↓
Feasibility
   ↓
Planning
   ↓
Research / Agentic RAG
   ↓
Budget
   ↓
Negotiation
   ↓
Critic
   ↓
Human Review
   ↓
Booking
```

The workflow includes specialized agents, tool use, retrieval,
structured state, conditional routing, iterative reasoning, reflection,
replanning, human intervention, and action execution.

## 5. Architecture

``` text
                    ┌─────────────────────┐
                    │        User         │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    React Frontend   │
                    │ Dashboard / Review  │
                    │ Activity / New Event│
                    └──────────┬──────────┘
                               │
                         REST / API
                               │
                               ▼
                    ┌─────────────────────┐
                    │      FastAPI        │
                    │      Backend        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     LangGraph       │
                    │   Agent Workflow    │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
   ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
   │ LLM Layer   │     │ Agentic RAG  │     │ Mock Vendor │
   │ Ollama etc. │     │ SQL + Vector │     │ Marketplace │
   └─────────────┘     └──────┬───────┘     └─────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │ PostgreSQL +    │
                     │ pgvector        │
                     └─────────────────┘
```

## 6. Agents

### Intake Agent

Converts natural-language input into structured requirements.

### Feasibility Agent

Checks budget, location, vendor availability, required categories, and
capacity.

### Planner Agent

Creates or revises the event plan using requirements, feasibility
results, retrieved evidence, budget constraints, rejected vendors, and
critic feedback.

### Research / Agentic RAG Agent

Retrieves evidence from SQL/vendor and vector sources, evaluates
evidence sufficiency, and can trigger additional retrieval rounds.

### Budget Agent

Evaluates allocation against the event budget and produces
budget-related state.

### Negotiator Agent

Attempts to improve vendor pricing and allocation while preserving
requirements.

### Critic Agent

Evaluates the current plan and produces structured issues or a pass
result.

### Booking Agent

Executes approved bookings through the mock marketplace.

## 7. Workflow and Reflection

The main graph is:

``` text
Intake
  ↓
Feasibility
  ↓
Planner
  ↓
Research
  ↓
Budget
  ↓
Negotiator
  ↓
Critic
  ↓
Human Review
  ↓
Booking
```

Critic failure can route back to planning:

``` text
Critic
  ├── PASS → Human Review
  └── FAIL
        ├── Iterations available → Planner
        └── Maximum iterations → Human Review
```

This provides a reflection loop:

``` text
Generate → Critique → Identify Problems → Replan → Critique
```

Rejected vendor IDs are carried through replanning and retrieval so that
a human-rejected vendor is not simply selected again.

## 8. Agentic RAG

Agentic RAG is a core experimental component.

Instead of always retrieving the same top-k records, the system
considers what evidence is needed for the current planning problem,
selects an appropriate retrieval route, checks whether evidence is
sufficient, and can perform additional retrieval.

``` text
Planner creates evidence needs
            ↓
      Retrieval Router
            ↓
     ┌──────┼──────┐
     ↓      ↓      ↓
    SQL   Vector  Other Tool
     │      │      │
     └──────┼──────┘
            ↓
     Evidence Registry
            ↓
      Sufficiency Check
         /            Sufficient    Insufficient
      ↓               ↓
 Continue        Refine Query
                      ↓
                 Retrieve Again
```

The current implementation uses deterministic/dynamic routing and
adaptive retrieval logic. It should therefore be described accurately as
an adaptive agentic retrieval workflow rather than claiming fully
autonomous LLM routing.

## 9. RAG Modes

### No RAG

``` text
Prompt → LLM → Plan
```

Used as a baseline.

### Basic RAG

``` text
Prompt → Fixed Top-K Retrieval → LLM → Plan
```

Used to represent conventional retrieval.

### Agentic RAG

``` text
Requirements
    ↓
Evidence Needs
    ↓
Dynamic Retrieval
    ↓
Sufficiency Check
    ↓
Re-retrieval if required
    ↓
Evidence-grounded Planning
```

Used to study whether adaptive retrieval improves planning quality.

## 10. Human-in-the-Loop

Human approval is deliberately positioned before booking.

``` text
AI Plan
   ↓
Critic
   ↓
Human Review
   ├── Approve → Booking
   ├── Modify → Replan
   └── Reject Vendor → Replan
```

The Plan Review page provides event summary, budget information, vendor
selections, critic feedback, vendor rejection, and approval controls.

## 11. State and Memory

Eventura AI maintains structured state containing information such as:

``` text
requirements
feasibility
plan
rejected_vendor_ids
evidence
retrieval_rounds
budget
negotiation_log
critic_feedback
critic_iterations
human_feedback
bookings
run_of_show
invite
guests
delivery_status
reminders
rag_mode
llm_provider
status
```

LangGraph checkpointing is backed by PostgreSQL for workflow
persistence. The application also stores a session state snapshot for
API/frontend access.

## 12. Technology Stack

### Frontend

-   React
-   TypeScript
-   Vite
-   Tailwind CSS
-   shadcn/ui
-   React Query
-   React Router
-   Recharts

### Backend

-   Python
-   FastAPI
-   Pydantic
-   SQLAlchemy
-   PostgreSQL
-   Alembic

### Agent orchestration

-   LangGraph
-   LangChain components where required

### LLM

Current local development:

-   Ollama
-   Llama 3.1 8B

The architecture is configurable for additional providers/models.

### Embeddings

Local models available in the development environment include:

-   `mxbai-embed-large`
-   `nomic-embed-text`

### Retrieval

-   PostgreSQL
-   pgvector
-   SQL retrieval
-   Vector similarity retrieval

### Infrastructure

-   Docker
-   Docker Compose

### Mock integrations

-   Synthetic vendor marketplace
-   Mock booking server

## 13. Project Structure

``` text
Eventura-AI/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── agents/
│   │   ├── graph/
│   │   ├── llm/
│   │   ├── rag/
│   │   ├── db/
│   │   ├── mock_vendors/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── config.py
│   │   ├── logger.py
│   │   └── main.py
│   ├── data/
│   ├── tests/
│   ├── requirements.txt
│   └── ...
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── lib/
│   ├── package.json
│   └── ...
│
├── docker-compose.yml
├── .env
├── .gitignore
└── README.md
```

## 14. Database

PostgreSQL is the primary application database.

Development uses Dockerized PostgreSQL with pgvector.

The database stores application information such as:

-   Sessions
-   Vendors
-   Vendor availability
-   Bookings
-   Knowledge chunks
-   State snapshots

Current development connection:

``` text
Host: localhost
Port: 5433
Database: eventura
User: eventura
```

Port `5433` is used because the default local PostgreSQL port `5432` is
occupied.

## 15. Synthetic Vendor Marketplace

The project uses synthetic vendor data for development and
demonstrations.

Possible categories include:

-   Venue
-   Catering
-   Decoration
-   Photography
-   Makeup
-   Music
-   Transport
-   Cake
-   Entertainment
-   Sound and lights
-   Stage
-   Performers
-   Security
-   Printing

A vendor record can contain:

``` text
Name
Category
City
Price
Capacity
Availability
Rating
Services
```

The mock marketplace allows booking behavior to be demonstrated without
real-world transactions.

## 16. Installation

### Prerequisites

Install:

-   Python 3.12+
-   Node.js 20+
-   npm
-   Docker Desktop
-   Ollama

Verify:

``` bash
python --version
node --version
npm --version
docker --version
ollama --version
```

## 17. Environment Configuration

Example `.env`:

``` env
LLM_PROVIDER=ollama

GEMINI_MODEL=gemini-2.5-flash
GROQ_MODEL=llama-3.3-70b-versatile

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

DATABASE_URL=postgresql+asyncpg://eventura:eventura@localhost:5433/eventura
SYNC_DATABASE_URL=postgresql+psycopg2://eventura:eventura@localhost:5433/eventura
```

Do not commit secrets to Git.

## 18. Running the Project

### Start database

``` bash
docker compose up -d
```

Verify:

``` bash
docker ps
```

### Start Ollama

``` bash
ollama list
ollama run llama3.1:8b
```

### Start backend

``` bash
cd backend
python -m uvicorn app.main:app --reload
```

Backend:

``` text
http://localhost:8000
```

API documentation:

``` text
http://localhost:8000/docs
```

### Start mock vendor server

``` bash
python -m uvicorn app.mock_vendors.server:app --port 8001 --reload
```

### Start frontend

``` bash
cd frontend
npm install
npm run dev
```

Frontend:

``` text
http://localhost:5173
```

## 19. Typical User Flow

``` text
Create Event
    ↓
Enter natural-language request
    ↓
Intake
    ↓
Feasibility
    ↓
Planning
    ↓
Research / RAG
    ↓
Budget
    ↓
Negotiation
    ↓
Critic
    ↓
Plan Review
    ↓
Human Approval
    ↓
Booking
    ↓
Booking Confirmation
```

## 20. Example Prompt

``` text
Plan a wedding in Chennai on 20 December 2026 for 200 guests
with a total budget of ₹5,00,000.

I need:
- a venue
- catering
- decoration
- photography

The event should be elegant and well-organized while staying
within the given budget.

Please find suitable vendors, create a complete plan, verify
the important constraints, and present the plan for my approval
before booking.
```

## 21. Evaluation

The project should be evaluated as a decision-making system, not only by
text quality.

### RAG comparison

Compare:

``` text
No RAG
Basic RAG
Agentic RAG
```

Recommended metrics:

-   Constraint satisfaction
-   Budget adherence
-   Evidence grounding
-   Hallucination rate
-   Task completion
-   Infeasibility detection
-   Latency
-   Token usage
-   Cost
-   Consistency across repeated runs

### LLM comparison

Different LLM configurations can be evaluated using the same scenarios
and metrics.

### Critic ablation

Compare:

``` text
With Critic
vs
Without Critic
```

This tests the contribution of iterative validation.

### Scenario-based evaluation

A representative evaluation set can contain around 15 scenarios
covering:

-   Valid event requests
-   Tight budgets
-   Missing vendors
-   Large guest counts
-   Availability conflicts
-   Multiple mandatory categories
-   Vendor rejection
-   Replanning
-   Budget violations
-   Evidence requirements

Results should be based on actual measured runs rather than assumed
improvements.

## 22. Research Contribution / Experimental Direction

The project's main technical themes are:

-   Agentic orchestration
-   Agentic RAG
-   Evidence-grounded decision making
-   Reflection and self-correction
-   Human-in-the-loop execution
-   Stateful workflows
-   Comparative evaluation

The important distinction from a simple chatbot is that Eventura AI
evaluates whether decisions satisfy constraints and are supported by
retrieved evidence.

## 23. Current Implementation Notes

### Local LLM

The current development setup uses:

``` text
Ollama
└── llama3.1:8b
```

This enables local inference without relying entirely on external API
quotas.

### Persistent workflow checkpoints

A PostgreSQL-backed LangGraph checkpointer supports pause/resume
behavior for human approval workflows.

### State snapshot

The current event state is also persisted as a session snapshot for
frontend/API access.

### Rejected vendors

When a human rejects a vendor during review, its ID is carried through
the replanning/retrieval path so that the same vendor is excluded from
subsequent selection.

### Booking confirmation

After a successful booking state, the dashboard displays a simple
confirmation dialog:

``` text
Booking Confirmed

Your selected vendors have been successfully booked.

[ Continue ]
```

## 24. Future Enhancements

Potential extensions include:

### Run of Show

Generate detailed event schedules for setup, vendor arrival, guest
arrival, main event, catering, photography, and cleanup.

### Invitations

Generate digital invitations and manage guest information.

### Reminders

Schedule vendor, payment, and event-preparation reminders.

### Calendar integration

Synchronize event schedules with calendar systems.

### Weather-aware replanning

For outdoor events:

``` text
Weather disruption
       ↓
Feasibility re-check
       ↓
Alternative plan
       ↓
Human approval
```

### Additional vendor tools

Potential additions:

-   Vendor negotiation
-   Availability checking
-   Pricing comparison
-   Contract verification
-   Payment tracking

### More autonomous retrieval

Future versions can investigate an LLM-based retrieval controller that
selects tools and retrieval strategies based on current evidence
requirements.

## 25. Troubleshooting

### Backend does not start

Check Python and the virtual environment:

``` bash
python --version
```

Ensure backend dependencies are installed.

### PostgreSQL connection error

Check:

``` bash
docker ps
```

Confirm the database is available on port `5433` and that the `.env`
connection strings match.

### Ollama connection error

Check:

``` bash
ollama list
ollama run llama3.1:8b
```

Verify:

``` env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

### Frontend issue

Run:

``` bash
npm install
npm run dev
```

Refresh the browser after frontend code changes.

### Infeasible event

An infeasible result can be a legitimate planning result when the
available synthetic marketplace cannot satisfy the requested combination
of budget, location, guest count, mandatory categories, capacity, or
availability.

Use the Agent Activity and feasibility output to determine why the event
was rejected before modifying code.

### HITL resume issue

Check that:

1.  The event reached human approval.
2.  The approval endpoint was called.
3.  The PostgreSQL LangGraph checkpointer initialized.
4.  The session status changed after approval.
5.  The booking agent was reached.

## 26. Academic / Demo Value

Eventura AI demonstrates:

### Agentic AI

Multiple specialized agents cooperate to complete a goal.

### Agent orchestration

LangGraph controls state, routing, conditional execution, iteration,
interruption, and resumption.

### RAG

The system retrieves supporting evidence instead of relying exclusively
on model knowledge.

### Agentic RAG

Retrieval can adapt to evidence requirements and sufficiency.

### Reflection

The Critic Agent evaluates and improves generated plans.

### Human-in-the-loop

The user controls consequential booking actions.

### Stateful AI

Event state persists across multiple stages.

### Tool use

Agents interact with structured vendor/database and retrieval tools.

### Evaluation

Different RAG and LLM configurations can be compared with measurable
metrics.

## 27. Demo Flow

For a project demonstration, the recommended narrative is:

1.  Create an event using natural language.
2.  Show the extracted requirements.
3.  Show feasibility analysis.
4.  Open Agent Activity.
5.  Demonstrate vendor retrieval.
6.  Show budget allocation.
7.  Show Critic feedback.
8.  Open Plan Review.
9.  Reject a vendor or modify the plan if demonstrating replanning.
10. Approve the final plan.
11. Show booking progress.
12. Show the Booking Confirmed dialog.
13. Explain the RAG mode and agent workflow.
14. Show evaluation results.

## 28. Quick Start

``` bash
# Database
docker compose up -d

# Ollama
ollama run llama3.1:8b

# Backend
cd backend
python -m uvicorn app.main:app --reload

# Mock vendor server
python -m uvicorn app.mock_vendors.server:app --port 8001 --reload

# Frontend
cd frontend
npm install
npm run dev
```

Open:

``` text
http://localhost:5173
```

## 29. System Summary

``` text
                    EVENTURA AI
                         │
              Natural Language Goal
                         │
                         ▼
                  Intake Agent
                         │
                         ▼
               Feasibility Agent
                         │
                         ▼
                   Planner Agent
                         │
                         ▼
              Agentic RAG / Research
                         │
                         ▼
                   Budget Agent
                         │
                         ▼
                 Negotiator Agent
                         │
                         ▼
                   Critic Agent
                         │
                  ┌──────┴──────┐
                  │             │
                FAIL           PASS
                  │             │
                  ▼             ▼
                Replan      Human Review
                  │             │
                  └─────────────┤
                                ▼
                             Booking
                                │
                                ▼
                       Booking Confirmed
```

**Eventura AI transforms event planning from a manual search-and-compare
process into a structured, evidence-aware, self-correcting agentic
workflow with human oversight.**

## License

This project is intended as an academic/educational project. Add an
appropriate open-source license if the project is later released
publicly.
