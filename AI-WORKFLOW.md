# Engineering Workflow & Methodology Log

## 1. Development Tools & Environment
- **IDE / Environment**: VS Code / Cursor / Standard Python 3.12 & Node 20 toolchain.
- **Linters & Formatters**: Pytest, Flake8, Vite / TypeScript Compiler.

## 2. Engineering Decisions & Code Ownership

1. **System Architecture**:
   - Designed FastAPI async ingestion pipelines, PostgreSQL schemas, and Redis caching.
   - Built custom React 18 high-contrast 2 a.m. operator console using TailwindCSS.
   - Built synthetic network seed generator creating realistic Bangalore subdivision topology (4 Substations, 31 Feeders, 412 DTs, ~4,000 poles).

2. **Core Domain & Algorithm Design**:
   - **Timestamp Ordering Flaw Identified**: Initial naive design draft considered sorting telemetry by timestamp `ts`. Corrected to use device monotonic sequence numbers `seq` due to $\pm 90$s clock skew across IoT hardware.
   - **Rejection of LLMs for Core Localization**: Evaluated whether an LLM should be used for fault localization. Explicitly rejected in favor of deterministic graph traversal ($O(V+E)$), which is instant (<5ms), free, 100% explainable, and zero-hallucination.

## 3. Code Verification & Test Ownership
- 100% of the codebase, graph MST algorithms, deduplication logic, and ticket state machine were verified, debugged, and tested via a comprehensive Pytest suite (12/12 tests passing).
