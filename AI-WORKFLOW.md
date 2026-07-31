# AI Tooling & Workflow Log

## Tools Used
- **Cursor / Claude Code / Antigravity AI**: Core domain engine scaffolding, MST graph algorithms, FastAPI endpoints, React UI, and test suites.

## AI Delegation vs. Human Engineering

1. **What was Delegated**:
   - Boilerplate FastAPI endpoints and model definitions.
   - Initial layout for the 2 a.m. High-Contrast Operator Console in React.
   - Synthetic data generation loops for substations and distribution transformers.

2. **Where AI was Misleading / Corrected**:
   - **Timestamp Ordering Flaw**: AI originally suggested sorting incoming telemetry messages by `ts`. Corrected to use device monotonic `seq` numbers due to ±90s clock skew across IoT hardware.
   - **Over-building Auth**: AI initially attempted to scaffold JWT authentication and RBAC roles. Stripped out as explicitly prohibited by project brief.
   - **LLM Localization Premature Optimization**: AI suggested using an LLM prompt to localize line faults. Rejected in favor of deterministic graph traversal which is instant, free, 100% explainable, and reproducible.

## AI Code Ratio Estimate
- ~75% AI-generated code, 100% verified, refined, and tested by human engineering.
