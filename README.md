# ScholarGraph

ScholarGraph checks whether a research paper's code really does what the paper says.

You give it an arXiv paper and the GitHub repository published with it. It reads both, finds each
claim the paper makes (optimizer, learning rate, loss function, model layers and so on), finds the
code that is supposed to implement that claim, and reports where the two match and where they don't.

Example: the paper says "trained with AdamW, learning rate 1e-4", but `train.py` sets `lr=1e-3`.
ScholarGraph flags that as a mismatch and shows the exact sentence in the paper and the exact lines
in the code.

---

## Why it was built

### The problem

Many AI papers come with a GitHub repo, and people assume the code matches the paper. Often it
doesn't quite:

- a hyperparameter in the code is different from the one in the paper
- the loss function in the code has an extra term, or is missing one
- the model in the repo has a different number of layers than the paper describes
- the important code is buried among tests, scripts and examples, so checking by hand takes hours

Anyone who wants to reproduce or build on a paper (researchers, students, engineers turning
research into products) has to do this checking manually, line by line.

### Why this project

- It is a real problem in applied AI work, especially where researchers and engineers work together
  and research has to be turned into working software.
- It needs the main parts of a modern AI application in one place: retrieval (RAG), vector
  databases, an agent workflow, a streaming backend and a live frontend.
- It was built to learn and practice that stack hands-on: LangGraph, Weaviate, Qdrant, local
  embeddings and FastAPI, with a React and TypeScript frontend on top.

---

## What the user sees

1. Open the React dashboard.
2. Paste an arXiv URL and a GitHub URL.
3. Click **Verify**.
4. Watch the agents work live, step by step, for example:
   - "Paper Analyst found 12 claims"
   - "Code Detective found the loss function in `models/losses.py`"
   - "Critic: optimizer not found, sending the Detective back to search `training/`"
5. Get a final scorecard:
   - **Overall match** (for example "Partial match, 2 mismatches")
   - **Hyperparameter table**: paper value vs code value, match or mismatch
   - **Loss and architecture check**: the paper's description next to the actual code
   - **Citations**: the sentence in the paper and the file and line numbers in the repo for every result

---

## How it works

```
        [ arXiv URL + GitHub URL ]
                    |
                    v
          [ FastAPI backend ]
                    |
        +-----------+-----------+
        v                       v
 [ Paper ingestion ]     [ Code ingestion ]
  download paper          clone repo
  extract text            parse Python into
  split into chunks       functions and classes
  embed chunks            tag file path, type,
                          test or not; embed
        |                       |
        v                       v
   [ Weaviate ]             [ Qdrant ]
   hybrid search            vector search with
   (vector + keyword)       payload filters
        |                       |
        +-----------+-----------+
                    v
      [ LangGraph agent workflow ]
      Supervisor -> Paper Analyst -> Code Detective
                         ^                |
                         |                v
                         +---- Critic ----+   (loops back if the match is weak)
                                  |
                                  v
                              Reporter
                    |
                    v   (Server-Sent Events)
       [ React + TypeScript dashboard ]
       live agent steps + final scorecard
```

### 1. Paper ingestion (Weaviate)

- Downloads the paper from arXiv and extracts the text.
- Splits it into chunks (paragraphs and sections), keeping the section name with each chunk so the
  report can cite where a claim came from.
- Creates embeddings locally with **fastembed** (no paid embedding API needed).
- Stores the chunks in **Weaviate**.

**Why Weaviate for the paper: hybrid search.** Papers mix ideas ("we use a contrastive loss") with
exact values ("lr = 0.0001", "AdamW", "temperature 0.07"). Vector search alone understands meaning
but is weak with exact numbers and names: "lr = 0.0001" and "lr = 0.01" look almost the same to it.
Weaviate's hybrid search combines vector search (meaning) with BM25 keyword search (exact words and
numbers), and an `alpha` setting controls the balance between the two. So both the idea and the
exact value are found.

### 2. Code ingestion (Qdrant)

- Clones the GitHub repository.
- Parses each Python file with Python's built-in **AST** (abstract syntax tree) module, so the code
  is split into real units: whole functions and whole classes, not random blocks of lines.
- Stores each piece with a **payload** (extra JSON data), for example:
  `{"file_path": "models/loss.py", "type": "function", "name": "focal_loss", "is_test": false}`
- Embeds each piece with fastembed and stores it in **Qdrant**.

**Why Qdrant for the code: payload filtering.** A repo has README files, tests, examples and
scripts next to the real model code. A search for "focal loss" could easily return a test or a
comment instead of the real implementation. Qdrant applies filters on the payload while searching
(for example "not a test file, only functions and classes"), so only real code comes back.

**Why two databases instead of one:** each one is used for what it is best at. Papers need exact
keyword plus meaning search; code needs structured filtering. It also keeps the two kinds of data
cleanly separate.

### 3. The agents (LangGraph)

Instead of one huge prompt that tries to do everything at once (which is fragile and hard to debug),
the work is split into small steps run by **LangGraph**. LangGraph models the workflow as a graph:

- **State**: a shared object every step reads and writes (the claims, the code found, the verdicts,
  how many retries have been used).
- **Nodes**: the steps (agents).
- **Edges**: which step runs next, including **conditional edges** that decide at runtime where to
  go.

The agents:

1. **Supervisor**: starts the run and decides which claims to check.
2. **Paper Analyst**: searches Weaviate and turns the paper into a list of specific, checkable
   claims (optimizer, learning rate, batch size, loss formula, number of layers...), each with its
   source sentence.
3. **Code Detective**: for each claim, searches Qdrant for the code that should implement it and
   returns the file, function and lines.
4. **Critic**: compares the claim with the code it was given. If the evidence is weak or missing,
   it sends the Detective back with a better search ("look in `training/` for the optimizer
   setup"). A retry limit stops it from looping forever.
5. **Reporter**: collects every verdict into the final scorecard with citations.

**Why LangGraph:** the critic loop ("not good enough, go look again") is a cycle, and LangGraph is
built for workflows with cycles, shared state and branching. Each step can be tested, logged and
improved on its own, and every step can be streamed to the UI. LangGraph builds on LangChain's
basic pieces (model connections, prompts, tools).

### 4. Backend (FastAPI + SSE)

- **FastAPI** (Python) exposes the verify endpoint.
- As each agent step finishes, the backend sends an update to the browser with **Server-Sent
  Events (SSE)**: a one-way stream from server to browser, simpler than WebSockets because the
  browser only needs to listen.

### 5. Frontend (React + TypeScript)

- A form for the arXiv and GitHub URLs.
- A live timeline of agent steps as they stream in.
- The final scorecard, with the paper text and the matching code side by side.

### 6. Running it

- **Docker Compose** starts Weaviate and Qdrant locally.
- Python environment and dependencies are managed with **uv**.
- Embeddings run locally with fastembed; the LLM provider is set in config.

---

## Where RAG fits

RAG (retrieval-augmented generation) means the AI first **looks things up** in your own data and
then answers using what it found, instead of answering from memory.

In ScholarGraph, every judgement is based on retrieved evidence: the Paper Analyst works from
chunks retrieved from Weaviate, and the Critic judges code retrieved from Qdrant. Each result
carries its citation (paper sentence, file and lines), so a person can check the answer quickly.
This is how the project keeps the AI honest: it can't just say "matches"; it has to show both sides.

---

## Tech stack

| Part | Technology | Why |
|---|---|---|
| Agent workflow | LangGraph | Shared state, steps, conditional loops (critic retry) |
| Paper search | Weaviate | Hybrid search: vectors + BM25 keywords for exact values |
| Code search | Qdrant | Payload filters on file path, code type, test or not |
| Code parsing | Python `ast` | Splits code into whole functions and classes |
| Embeddings | fastembed | Local, fast, free embeddings |
| Backend | Python, FastAPI | Async API + Server-Sent Events streaming |
| Frontend | React, TypeScript | Live agent timeline and scorecard |
| Infrastructure | Docker Compose, uv | Local databases and Python environment |

---

## Main design choices (short version)

- **Two vector databases**: Weaviate for papers (hybrid search), Qdrant for code (payload filters).
- **AST-based code chunks**: whole functions and classes keep meaning intact.
- **Agents instead of one prompt**: easier to control, debug and improve; the critic loop catches
  weak matches.
- **Citations on every result**: answers are grounded and easy to verify.
- **Streaming with SSE**: the user sees the work happening, not just a spinner.

---

## Ideas for next steps

- **Evaluation set**: repos with planted mismatches (wrong learning rate, changed loss) to measure
  how many the system catches.
- **LaTeX source instead of PDF**: arXiv often provides the LaTeX source, which keeps math and
  numbers cleaner than PDF text extraction.
- **Read config files**: many hyperparameters live in YAML/JSON configs or command-line arguments,
  not in the Python code itself.
- **Swappable LLM provider** through config.

---

## In one line

ScholarGraph checks whether a research paper's code matches the paper, using RAG over two vector
databases (Weaviate for the paper, Qdrant for the code) and a LangGraph team of agents with a critic
that double-checks every match.
