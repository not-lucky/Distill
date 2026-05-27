# Card schema reference

Distill supports three card layouts (Basic, Cloze, MCQ) and eight
pedagogical card types (Concept, Code, Procedure, Syntax, Behavior,
Constraint, ErrorHandling, TradeOff). The schema is enforced by Zod in
`src/pipeline/schemas/card-zod.js` and exported as a JSON Schema at
`schemas/stage3-deck.schema.json` for the LLM enforcement prompt.

## Top-level shape

```ts
type Deck = {
  title: string; // Title of the concept, problem, or document section
  topic: string; // Main category hierarchy or path (e.g. "CS/Algorithms/Sorting")
  difficulty: 'Basic' | 'Intermediate' | 'Advanced';
  cards: Card[]; // At least one card
};
```

## Card layouts

### Basic Q&A

```ts
type BasicCard = {
  card_format: 'Basic';
  card_type: CardType; // one of the eight pedagogical types
  tags: string[]; // alphanumeric, hyphen, underscore, slash (no spaces)
  front: string; // Active-recall question
  back: string; // Short, punchy answer (required)
  explanation: string; // Detailed background, code, trade-offs, pitfalls
};
```

### Cloze deletion

```ts
type ClozeCard = {
  card_format: 'Cloze';
  card_type: CardType;
  tags: string[];
  front: string; // Must contain at least one {{c1::…}} cloze marker
  back?: never; // Forbidden for Cloze
  options?: never; // Forbidden for Cloze
  correct_answer?: never; // Forbidden for Cloze
  explanation: string;
};
```

The `front` must contain at least one cloze marker matching the regex
`\{\{c[0-9]+::…\}\}`. The `c1`, `c2`, … numbers let you have multiple
cloze deletions on a single card; Anki treats them as a single card
with multiple "blanks" in the review UI.

### MCQ (multiple choice)

```ts
type MCQCard = {
  card_format: 'MCQ';
  card_type: CardType;
  tags: string[];
  front: string; // The question stem
  options: [string, string] | [string, string, string] | [string, string, string, string];
  correct_answer: 'A' | 'B' | 'C' | 'D';
  back?: never; // Forbidden for MCQ
  explanation: string;
};
```

Rules:

- `options` must have between 2 and 4 entries.
- If `correct_answer === "C"`, `options` must have at least 3 entries.
- If `correct_answer === "D"`, `options` must have at least 4 entries.

## Pedagogical card types

| `card_type`     | Use it for                                                           |
| --------------- | -------------------------------------------------------------------- |
| `Concept`       | Definitions, terminology, "what is X?" cards.                        |
| `Code`          | Code snippets, syntax, idioms, language features.                    |
| `Procedure`     | Step-by-step algorithms, ordered operations, recipes.                |
| `Syntax`        | Grammar, declaration forms, parameter shapes, format strings.        |
| `Behavior`      | Runtime semantics, evaluation order, side effects.                   |
| `Constraint`    | Pre-conditions, post-conditions, invariants, limits.                 |
| `ErrorHandling` | Error codes, exception types, recovery procedures, debug strategies. |
| `TradeOff`      | Performance vs. memory, readability vs. speed, etc.                  |

## Tags

Tags follow the pattern `^[A-Za-z0-9-_/]+$`. Use slashes for hierarchies
(e.g. `algorithms/sorting/quick-sort`). The `postProcess.js` step
normalises tags by lowercasing, trimming, and deduplicating after the
pipeline runs, so a card that says `Quick-Sort` and another that says
`quick-sort` will share a single tag in the final `.apkg`.

## Worked example

A single-topic JSON file consumed by `src/compile.py`:

```json
{
  "title": "Quicksort Partition Step",
  "topic": "CS/Algorithms/Sorting",
  "difficulty": "Intermediate",
  "cards": [
    {
      "card_format": "Basic",
      "card_type": "Procedure",
      "tags": ["algorithms/sorting/quicksort"],
      "front": "What is the invariant of the Lomuto partition scheme?",
      "back": "All elements left of the pivot index are ≤ pivot; all elements right of the pivot index are > pivot.",
      "explanation": "The Lomuto scheme maintains a single index `i` that is incremented whenever an element ≤ pivot is found. After the scan, `i+1` is the final position of the pivot, and the partition is complete."
    },
    {
      "card_format": "Cloze",
      "card_type": "Concept",
      "tags": ["algorithms/sorting/quicksort", "complexity"],
      "front": "Quicksort's average-case time complexity is {{c1::O(n log n)}}, while its worst case is {{c2::O(n²)}}.",
      "explanation": "Average case assumes a balanced partition. Worst case occurs when the pivot is always the smallest or largest element, e.g. already-sorted input with a first-element pivot."
    }
  ]
}
```

The full machine-readable contract lives at
[`schemas/stage3-deck.schema.json`](https://github.com/not-lucky/Distill/blob/master/schemas/stage3-deck.schema.json).
