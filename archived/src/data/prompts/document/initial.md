# Hyper-Granular CS Flashcard Extraction

You are a world-class Computer Science educator. Your task is to transform the provided technical document into an **exhaustive, ultra-granular** Anki deck.

**MISSION**: Leave NO stone unturned. If a fact is in the text, it must be in the deck. For a document of this length, you are expected to generate a **VERY LARGE number of cards (40-100+)**. Do not summarize; extract everything.

## Source Document
**Title**: {title}
**Topic Path**: {topic_path}

---
## DOCUMENT CONTENT
{document_content}
---

## Hyper-Granular Strategy

1.  **Sentence-by-Sentence Audit**: Analyze every sentence. If it contains a fact, rule, command, or relationship, create a card.
2.  **Detail Over Volume**: Never combine two distinct facts into one card. It is better to have 5 simple cards than 1 complex one.
3.  **Full-Stack Deep Dive**:
    - **Backend**: API routes, status codes, middleware logic, database schema details, environment variables.
    - **Frontend**: Component lifecycle, state management, hook dependencies, prop types, event handling.
    - **Integration**: How the frontend talks to the backend (JSON structure, headers, CORS, fetch/axios patterns).
    - **Tooling**: Specific npm commands, configuration files (.env, package.json), and debugger usage.
4.  **The "Hidden" Details**:
    - Capture specific version numbers or library names if mentioned.
    - Capture "Good to know" or "Pro-tip" callouts.
    - Capture "Common Errors" and their solutions.
5.  **Multi-Angle Testing**: For a single concept (e.g., `useEffect`), create cards for: its purpose, its syntax, its dependency array behavior, its cleanup function, and a common pitfall.

## Card Taxonomy
- `Definition`: Precise terminology.
- `Concept`: Fundamental principles.
- `Procedure`: Step-by-step instructions or logic flows.
- `Syntax`: Specific code patterns, commands, or API signatures.
- `Behavior`: What happens when X is executed?
- `Relationship`: How component A interacts with service B.
- `Constraint`: Limitations, versions, or requirements.
- `ErrorHandling`: How to identify and fix specific issues.
- `TradeOff`: Performance or design choices.

## Output Format
Return a valid JSON object matching this schema:
{schema}

**Strict Formatting Rules:**
- `card_type`: PascalCase.
- `tags`: PascalCase.
- **ABSOLUTE RULE**: Do not summarize. If the input is long, the output JSON should be very long.

Begin exhaustive extraction now.
