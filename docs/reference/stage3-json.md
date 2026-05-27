# Stage 3 JSON contract

The Stage 3 JSON contract is the machine-readable shape that Distill's
Stage 3 (schema enforcement) stage produces, and that Stage 4
(`src/compile.py`) consumes to build the final `.apkg`. It is the only
stable contract in the pipeline — Stages 1 and 2 produce free-form text.

## File shape

The file is a single JSON object or an array of objects, where each
object is one topic with its cards:

```ts
// Single topic
{ "title": "...", "topic": "...", "difficulty": "...", "cards": [...] }

// Multiple topics (merged runs)
[
  { "title": "...", "topic": "...", "difficulty": "...", "cards": [...] },
  { "title": "...", "topic": "...", "difficulty": "...", "cards": [...] }
]
```

The `compile_deck` orchestrator normalises the single-topic shape into
the array shape internally, so both forms are accepted.

## Fields

| Field        | Type   | Required | Notes                                                                         |
| ------------ | ------ | -------- | ----------------------------------------------------------------------------- |
| `title`      | string | yes      | Title of the concept, problem, or document section.                           |
| `topic`      | string | yes      | Main category hierarchy or path. Becomes the deck name for single-topic runs. |
| `difficulty` | enum   | yes      | `Basic`, `Intermediate`, or `Advanced`.                                       |
| `cards`      | array  | yes      | One or more card objects. See [Card schema reference](card-schema.md).        |

## Card fields

See the [card schema reference](card-schema.md) for the per-card field
list. The contract is enforced by Zod at
`src/pipeline/schemas/card-zod.js` and is published as a JSON Schema at
`schemas/stage3-deck.schema.json`.

## Validation

You can validate a Stage 3 file against the contract from the command
line:

```bash
# Using the bundled Zod schema via a tiny Node script
node -e "
  import('./src/pipeline/schemas/card-zod.js').then(({ CARD_VALIDATION_SCHEMA }) => {
    const data = JSON.parse(require('fs').readFileSync(process.argv[1], 'utf8'));
    const topics = Array.isArray(data) ? data : [data];
    for (const t of topics) CARD_VALIDATION_SCHEMA.parse(t);
    console.log('OK');
  });
" ./output/LeetCode.json

# Using the published JSON Schema
uv run --with jsonschema python -c "
import json, jsonschema
schema = json.load(open('schemas/stage3-deck.schema.json'))
data = json.load(open('./output/LeetCode.json'))
topics = data if isinstance(data, list) else [data]
for t in topics: jsonschema.validate(t, schema)
print('OK')
"
```

## How Stage 3 enforces the contract

1. The orchestrator sends the synthesis output plus the JSON Schema to
   the configured Stage 3 model with a `format: json` hint and the
   schema text appended to the prompt.
2. The model's reply is parsed as JSON and run through
   `CARD_VALIDATION_SCHEMA.parse()`.
3. On failure, the orchestrator retries with the validation error
   attached to the prompt (up to `global.enforcement_max_attempts`
   times).
4. After the final retry, `null` fields are sanitised: if `back`,
   `options`, or `correct_answer` is `null` and the card format doesn't
   allow that field, the field is stripped. This is what
   `src/pipeline/validation.js` handles.

See `src/pipeline/validation.js` and
`src/pipeline/stages/stage3-enforcement.js` for the implementation.

## Versioning

The Stage 3 contract is **not** semver-versioned yet. Breaking changes
are announced in `CHANGELOG.md` (or `docs/changelog.md` in the docs
site) and shipped with a migration script in `scripts/`. Until a
contract version is added, treat the published JSON Schema as the
source of truth.
