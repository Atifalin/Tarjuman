# Local Arabic → Urdu Translation Workstation App name : Tarjuman (add it in ui branding)


## 1. Product objective

Build a **Mac-first, completely local Arabic → Urdu document translation application** for Apple Silicon Macs, especially:

* Apple M-series Macs
* Target machine: MacBook M4 with 32 GB unified memory
* No paid AI APIs
* No mandatory cloud services
* No OpenAI API
* No Anthropic API
* No Gemini API for actual translation
* All translation inference must happen locally

The user should be able to install the application, install/select a local AI engine, download models with buttons, choose a folder containing Arabic PDFs, start translation, review translations visually, approve/reject/edit them, or enable a fully automatic bypass mode that processes the entire collection unattended.

The application should feel like a **local translation workstation**, not a developer tool.

---

# 2. Core workflow

The primary workflow is:

1. Launch application.
2. Application checks Mac hardware and software.
3. Detect whether Ollama and/or LM Studio are installed.
4. If neither exists, show:

   * "Install Ollama"
   * "Install LM Studio"
5. User clicks one.
6. Application gives clear installation instructions and, where technically safe, opens the official download page.
7. Detect the installed engine automatically.
8. Show compatible models that can be downloaded.
9. User clicks "Download Model".
10. Application downloads/verifies the model.
11. User selects Arabic PDF folder.
12. Application scans PDFs.
13. Show document queue:

    * filename
    * pages
    * estimated text/pages
    * status
14. User chooses translation mode:

    * Review Mode
    * Automatic Mode
    * Hybrid Mode
15. Translation starts.
16. Show live progress.
17. For each translated chunk/page:

    * display original Arabic
    * display Urdu translation
    * show model used
    * show confidence/QA information when available
18. In Review Mode user can:

    * Approve
    * Edit Urdu
    * Reject / regenerate
    * Choose alternate translation
19. In Automatic Mode the system continues without waiting for approval.
20. Save progress continuously.
21. If application crashes or Mac restarts, resume automatically from the last completed chunk.
22. Export final translated material.

---

# 3. AI engine architecture

Support two local inference backends:

## Backend A: Ollama

Official site:

https://ollama.com/

Detect whether Ollama is installed and whether its local API is reachable.

Typical endpoint:

http://127.0.0.1:11434

Do not hardcode assumptions if the port has been customized.

Provide buttons:

* Check Ollama
* Install Ollama
* Start Ollama
* Stop Ollama
* Download Model
* Refresh Models
* Test Model

## Backend B: LM Studio

Official site:

https://lmstudio.ai/

Detect whether LM Studio is installed and whether its local server is available.

Provide:

* Install LM Studio
* Detect LM Studio
* Start/stop local server where the API permits it
* Refresh available models
* Test connection

Use the local OpenAI-compatible API when appropriate.

The application must abstract both engines behind a common interface:

```text
LocalAIProvider
├── OllamaProvider
└── LMStudioProvider
```

The rest of the application must not care which backend is being used.

---

# 4. Translation models

The application must NOT pretend that every model supports Arabic → Urdu.

Maintain an explicit model registry with:

* model name
* provider
* source language support
* target language support
* model type
* approximate memory requirements
* recommended use
* download location
* whether the application has verified the model

## Primary translation model

Prefer a dedicated translation model such as:

**Google MADLAD-400 7B MT**

Official model:

https://huggingface.co/google/madlad400-7b-mt

MADLAD-400 is a multilingual machine translation model covering 400+ languages.

Important:
Do not automatically assume that an arbitrary GGUF conversion has identical capabilities to the original model. Verify the exact downloaded model and record its source.

## Secondary translation model

Support:

**NLLB-200**

Arabic:

```text
arb_Arab
```

Urdu:

```text
urd_Arab
```

NLLB must use the correct source/target language codes rather than guessing.

Use NLLB as an independent translation engine / comparison engine.

## General-purpose reviewer

Support:

**Qwen3 8B**

Use it primarily for:

* translation review
* comparing two candidate translations
* terminology consistency
* Urdu fluency improvement
* detecting omissions
* detecting hallucinations
* regenerating problematic chunks

Do NOT treat Qwen3 automatically as the authoritative translator.

---

# 5. Recommended translation pipeline

Implement this pipeline:

```text
PDF
 ↓
Text extraction
 ↓
Arabic cleanup
 ↓
Paragraph reconstruction
 ↓
Chunking
 ↓
Primary translation
 ↓
Optional secondary translation
 ↓
QA/reviewer
 ↓
Final Urdu
 ↓
Human approval OR automatic acceptance
 ↓
Persist result
```

For high-quality mode:

```text
Arabic
   ↓
MADLAD
   ↓
Translation A

Arabic
   ↓
NLLB
   ↓
Translation B

A + B + Arabic
   ↓
Qwen3 reviewer
   ↓
Final Urdu
```

Allow the user to disable any stage for speed.

---

# 6. Critical requirement: translation modes

Provide three modes.

## REVIEW MODE

The default mode.

For every chunk/page, display:

LEFT:

```text
Original Arabic
```

RIGHT:

```text
Generated Urdu
```

Buttons:

* Approve
* Edit
* Regenerate
* Compare Models
* Reject
* Previous
* Next

Do not continue to the next chunk until the user approves or explicitly chooses another action.

## AUTOMATIC MODE

No human intervention.

The pipeline should:

* translate
* QA
* accept
* save
* continue

Display:

```text
AUTO MODE — NO APPROVAL REQUIRED
```

The user should be able to pause at any time.

## HYBRID MODE

Automatically approve translations above configurable QA thresholds.

Send questionable chunks to the review queue.

Example:

```text
High confidence → automatic
Medium confidence → automatic + flag
Low confidence → human review
```

Do not invent a fake probabilistic confidence score.

Clearly distinguish:

* model-generated quality signals
* heuristic checks
* actual model confidence when available

---

# 7. PDF processing

The application must support:

* native text PDFs
* scanned PDFs
* mixed PDFs

For PDFs containing selectable Arabic text:

Use reliable local text extraction.

For scanned PDFs:

Provide an OCR pipeline.

Prefer local OCR where possible.

Arabic OCR must be supported.

Do not silently produce garbage text from an image-only PDF.

Show:

```text
Text PDF
OCR PDF
Mixed PDF
Unknown
```

Allow the user to manually trigger OCR.

---

# 8. Page preservation

This is extremely important.

Maintain:

```text
PDF
 ├── page 1
 │    ├── paragraph 1
 │    ├── paragraph 2
 │    └── paragraph 3
 ├── page 2
 ...
```

Every translated chunk must retain:

* PDF filename
* page number
* paragraph/chunk number
* source text
* translation
* approval status
* model used
* timestamp

The final export must preserve page ordering.

---

# 9. Chunking

Do NOT send an entire book to the model.

Implement intelligent chunking.

Prefer paragraph/sentence boundaries.

Never split in the middle of a sentence unless necessary.

Maintain overlap/context when needed.

Configurable settings:

```text
Chunk size
Context overlap
Maximum output length
Batch size
Translation temperature
```

For deterministic translation use a low temperature / deterministic decoding configuration where supported.

Default temperature should be close to 0.

---

# 10. Terminology / glossary system

Implement a persistent glossary.

Example:

```text
Arabic                         Preferred Urdu

الله                          اللہ
رسول الله                     رسول اللہ
الصلاة                        نماز
الزكاة                        زکوٰۃ
التقوى                        تقویٰ
```

The user can:

* add term
* edit term
* delete term
* import CSV
* export CSV

Glossary rules should be passed to the translation/reviewer pipeline.

Add a feature:

**"Suggest new terminology"**

The system detects recurring Arabic terminology and proposes Urdu equivalents.

The user can approve them.

Approved terms become persistent translation memory.

---

# 11. Translation memory

Store previously approved translations.

When the same or highly similar Arabic sentence appears again:

* show previous translation
* optionally reuse it
* optionally ask the model to verify it

Do not blindly replace a translation if context differs.

Use similarity matching.

Store translation memory locally.

---

# 12. Human review UI

Create a professional document-review interface.

Example:

```text
┌─────────────────────────────────────────────────────┐
│ BOOK_001.pdf                         Page 37 / 812  │
├────────────────────────┬────────────────────────────┤
│                        │                            │
│       ARABIC           │          اردو             │
│                        │                            │
│       text...          │       ترجمہ...            │
│                        │                            │
├────────────────────────┴────────────────────────────┤
│ Model: MADLAD                                      │
│ Secondary: NLLB                                    │
│ QA: PASS                                           │
│                                                    │
│ [Approve] [Edit] [Regenerate] [Compare] [Reject]   │
└─────────────────────────────────────────────────────┘
```

Urdu rendering must be proper RTL.

Arabic rendering must be proper RTL.

The review editor must support:

* RTL
* Unicode correctly
* copy/paste
* keyboard shortcuts
* undo/redo

---

# 13. Side-by-side model comparison

When requested, show:

```text
SOURCE

MADLAD
translation A

NLLB
translation B

QWEN REVIEW
final recommendation
```

Allow:

* choose A
* choose B
* use Qwen final
* manually edit

---

# 14. Automatic QA checks

Before accepting a translation, run deterministic checks.

Check:

* source exists
* output exists
* output is not suspiciously short
* output does not contain Arabic unless expected
* output is not identical to source
* numbers preserved
* paragraph count reasonably preserved
* headings preserved
* special markers preserved
* no obvious model refusal
* no English meta-commentary
* no "Here is the translation:"
* no hallucinated explanatory text

Flag suspicious results.

Example:

```text
⚠ Translation may be incomplete.
Source: 146 words
Urdu:   42 words
```

This is a warning, not an automatic declaration of failure.

---

# 15. Resume/reliability system

This is mandatory.

Every chunk must be persisted immediately.

Use a local database such as SQLite.

Possible status:

```text
pending
extracting
translating
qa
awaiting_review
approved
rejected
failed
```

If the application crashes:

```text
Resume translation
```

must continue from the last unfinished chunk.

Never require the user to manually remember where the process stopped.

---

# 16. Batch PDF manager

User should be able to choose:

```text
Select folder
```

and the application discovers:

```text
001.pdf
002.pdf
003.pdf
004.pdf
...
```

Show:

| PDF     | Pages | Status      | Progress |
| ------- | ----: | ----------- | -------: |
| 001.pdf |   842 | Complete    |     100% |
| 002.pdf |   614 | Translating |      43% |
| 003.pdf |   921 | Waiting     |       0% |

Support:

* pause
* resume
* retry failed
* skip PDF
* restart PDF
* prioritize PDF

---

# 17. Hardware monitoring

The application must actively monitor the Mac while translation is running.

Display:

```text
CPU
RAM
GPU / Apple GPU utilisation where available
Memory pressure
Disk space
Model memory footprint where available
Process CPU usage
Process memory usage
Translation speed
```

Also provide temperature information where the operating system exposes reliable data.

IMPORTANT:

Do NOT fabricate temperature readings.

macOS does not provide all hardware temperature sensors through a simple stable public API. Use safe/local system facilities where available and otherwise display:

```text
Temperature: Not available through macOS
```

rather than inventing values.

If temperature/sensor information requires an optional helper such as macOS system tooling or a user-installed utility, make that optional.

Never require disabling macOS security features.

---

# 18. RAM safety

For a 32 GB Mac, implement memory protection.

Show:

```text
RAM
17.4 / 32 GB
54%

Memory Pressure
LOW
```

Define safe operating states.

Example:

```text
GREEN
Normal operation

YELLOW
Reduce concurrency / batch size

RED
Pause new model inference
```

When memory pressure becomes high:

1. Stop starting new translation jobs.
2. Allow the current request to finish if safe.
3. Reduce concurrency to 1.
4. Notify user.
5. Automatically resume when memory pressure returns to normal.

Never run multiple large models concurrently unless the hardware/memory check says it is safe.

---

# 19. Model concurrency

Default:

```text
1 large model at a time
```

For example:

Do NOT simultaneously load:

```text
MADLAD 7B
NLLB 3B
Qwen 8B
```

unless the application has explicitly determined that available memory is sufficient.

Prefer:

```text
Load translator
Translate
Unload / release
Load reviewer
Review
Release
```

This avoids unnecessary memory pressure.

---

# 20. Installation assistant

Create a first-run wizard:

```text
Welcome
 ↓
Hardware Check
 ↓
AI Backend
 ↓
Model Selection
 ↓
Download
 ↓
Test Translation
 ↓
Ready
```

Hardware page should display:

```text
Apple Silicon: ✅
RAM: 32 GB ✅
macOS version: ✅/⚠️
Disk space: XX GB
Ollama: Installed / Missing
LM Studio: Installed / Missing
```

Provide one-click actions wherever practical.

For downloads, always use official URLs.

Never download arbitrary executable files from unknown websites.

---

# 21. Model download manager

Create a dedicated model page:

```text
MODELS

MADLAD-400 7B MT
Translation
Arabic → Urdu
[Download]

NLLB
Translation
Arabic → Urdu
[Download]

Qwen3 8B
Review / QA
Arabic + Urdu
[Download]
```

Show:

* model size
* downloaded/not downloaded
* disk usage
* backend
* source URL
* verification status

The application should verify that the expected model actually responds before declaring it installed.

---

# 22. Backend/model compatibility

Do not assume:

"Model exists on Hugging Face = Ollama can run it."

Some translation models are T5/seq2seq architectures rather than standard decoder-only chat models.

Implement a compatibility registry.

Each model entry must specify:

```text
architecture
backend
download method
inference method
source language
target language
```

If a model cannot run through Ollama directly, do not fake support.

Use a local Python inference backend for that model if necessary.

This is especially important for dedicated translation models.

---

# 23. Architecture

Prefer a maintainable local architecture.

Suggested:

```text
Frontend:
React + TypeScript

Desktop shell:
Tauri if practical

Backend:
Python

API:
FastAPI

Database:
SQLite

PDF:
PyMuPDF / appropriate local PDF tooling

OCR:
Local OCR backend

AI:
Provider abstraction

Providers:
Ollama
LM Studio
Direct local Transformers/MLX where required

Monitoring:
macOS-native safe system APIs/commands

Storage:
Local filesystem + SQLite
```

Do not introduce unnecessary cloud infrastructure.

Do not require Docker unless it materially simplifies installation.

For a Mac desktop application, native/local processes are preferred over forcing the user to manage containers.

---

# 24. Safety and privacy

Display clearly:

```text
LOCAL ONLY

Your documents are processed on this Mac.
No document is uploaded to a cloud AI API.
```

Do not transmit document contents anywhere.

Do not add analytics.

Do not add telemetry.

Do not add accounts.

Do not add subscriptions.

No API keys should be required.

---

# 25. Cost requirement

The application must be usable with:

```text
$0 AI API cost
```

No paid AI service may be required.

Model downloads may be large, but there must be no per-token/per-page billing.

---

# 26. Output formats

Support:

```text
TXT
DOCX
PDF
JSON
```

For DOCX:

* preserve paragraph order
* proper Urdu RTL
* headings
* page references

Also export a project folder containing:

```text
project/
├── source/
├── extracted/
├── translations/
├── approved/
├── rejected/
├── glossary/
├── translation_memory/
├── database.sqlite
└── logs/
```

---

# 27. Progress dashboard

Main dashboard:

```text
Arabic → Urdu Translation

Current project:
Book Collection

Overall:
12,483 / 31,200 chunks

Estimated:
40%

Current PDF:
Book_17.pdf

Current page:
294 / 812

Model:
MADLAD-400

Review:
AUTO

Speed:
3.2 chunks/min

RAM:
18.6 / 32 GB

Memory pressure:
LOW

CPU:
62%

Status:
TRANSLATING
```

---

# 28. Error handling

Never silently fail.

If something goes wrong:

```text
Translation failed

Reason:
Local model unavailable

[Retry]
[Change Model]
[View Details]
```

Save detailed local logs.

For a failed chunk:

```text
Retry
Retry with secondary model
Send to review
Skip
```

---

# 29. User experience priority

The user is NOT a developer.

The normal workflow should be:

```text
Open app
→ Select folder
→ Select model
→ Download
→ Start
→ Review OR Automatic
```

The user should NOT need to:

* manually write curl commands
* manually manage APIs
* manually edit configuration files
* understand Python environments
* understand model quantization
* manually chunk PDFs
* manually track pages
* manually restart failed jobs

The developer/debug view can expose these options, but the default interface should hide them.

---

# 30. Developer/debug mode

Provide an advanced settings section for me as the developer.

Expose:

* raw provider URL
* model identifier
* context length
* temperature
* top-p
* max tokens
* concurrency
* chunk size
* OCR settings
* logs
* database inspection
* retry policies
* hardware thresholds
* provider diagnostics
* model test console

---

# 31. Initial implementation order

Do NOT attempt everything simultaneously.

Build in stages.

## Phase 1

Working local application:

* Mac detection
* Ollama detection
* LM Studio detection
* model selection
* model download instructions
* basic local chat/test
* PDF folder selection
* PDF text extraction
* Arabic → Urdu translation
* side-by-side review
* approve/edit/regenerate

## Phase 2

* batch PDFs
* SQLite jobs
* resume support
* automatic mode
* progress
* logs
* retry

## Phase 3

* second translation model
* Qwen reviewer
* model comparison
* QA system
* glossary
* translation memory

## Phase 4

* OCR
* DOCX/PDF output
* advanced hardware monitoring
* automatic memory throttling
* polished installation wizard

Do not build fake placeholder features just to claim they exist.

---

# 32. Critical testing requirement

Before declaring the application complete, create a built-in test suite.

Use a small Arabic test dataset containing:

1. Simple Modern Standard Arabic
2. Long paragraphs
3. Arabic with numbers
4. Arabic with names
5. Religious terminology
6. Quotations
7. Headings
8. Multiple paragraphs
9. Arabic punctuation
10. Difficult/classical Arabic

Run the same samples through each configured model.

Show:

```text
Model comparison

MADLAD
NLLB
Qwen

Translation output
QA checks
Latency
```

This is important because the application should be able to empirically determine which local model works best for the user's specific Arabic material.

---

# 33. Non-negotiable rules

1. No cloud AI requirement.
2. No paid API requirement.
3. Do not claim a model supports Arabic → Urdu without verifying it.
4. Do not claim a backend supports a model architecture unless it actually does.
5. Do not fabricate hardware temperature data.
6. Never lose completed translations.
7. Always support resume.
8. Never overwrite approved translations without explicit user action.
9. Never silently skip failed pages/chunks.
10. Keep original Arabic untouched.
11. Use proper RTL Urdu rendering.
12. Keep model/provider abstractions modular.
13. The application must work even if only one local backend is installed.
14. Automatic mode must genuinely run unattended.
15. Review mode must genuinely wait for approval.
16. All data remains local by default.

---

# 34. Final success criterion

A non-technical user should be able to take a MacBook M4 with 32 GB RAM, install this application, point it at a folder containing hundreds of Arabic PDFs, download the required local models with buttons, choose:

```text
REVIEW MODE
```

or:

```text
AUTOMATIC MODE
```

and process the collection without touching Terminal.

The user should always be able to see:

* what PDF is being processed
* what page is being processed
* the Arabic source
* the Urdu result
* which model generated it
* whether QA passed
* what the Mac's resource usage is
* whether the process is paused or running
* how to resume after interruption

The application is successful only when it behaves like a **real local document-translation workstation**, not merely a chat interface wrapped around Ollama.
