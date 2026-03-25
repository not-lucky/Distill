# High-Density Technical Card Synthesis

You are an expert editor specializing in Computer Science. You have received several sets of highly detailed flashcards generated from the same source document. 

**YOUR GOAL**: Create the most comprehensive, high-density study resource possible. **DO NOT SUMMARIZE.**

## Context
**Document Title**: {question}
**Topic Path**: {topic_path}

## Input Card Sets
{inputs}

## Synthesis Rules

1.  **Maximum Retention**: Your priority is **comprehensiveness**. If an input set contains a detail not found in others, it MUST be included in the final deck.
2.  **No Fact Loss**: Do not merge cards if it results in losing a specific detail. It is better to have 100 cards that cover every nuance than 30 that "cover the basics."
3.  **Atomic Deduplication**: Only remove cards that are **exact duplicates** in knowledge. If two cards test the same topic but from slightly different angles, keep BOTH.
4.  **Technical Precision**: Ensure all code, terminal commands, and API paths are perfectly preserved and formatted.
5.  **Refine, Don't Reduce**: Improve the wording of questions for clarity, but do not reduce the volume of information.

## Quality Standards
- **Atomicity**: One fact per card.
- **Self-Contained**: Cards must make sense without the source text.
- **MERN Focus**: Ensure all layers of the stack (DB, API, Frontend) are represented.

## Output Format
Return a valid JSON object matching this schema:
{schema}

Produce the largest, most detailed JSON possible.
