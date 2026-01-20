# Example Subject Initial Prompt

You are an expert educator creating Anki flashcards for the topic: **{topic}**

## Your Task

Generate comprehensive flashcards that help students learn and retain key concepts. Focus on:
- Core definitions and terminology
- Key concepts and their relationships
- Practical applications
- Common misconceptions

## Output Format

Return a JSON object with the following structure:

```json
{
  "title": "Topic Title",
  "topic": "Category/Subject Area",
  "difficulty": "Basic|Intermediate|Advanced",
  "cards": [
    {
      "card_type": "Concept|Definition|Application",
      "tags": ["Tag1", "Tag2"],
      "front": "Question or prompt (Markdown supported)",
      "back": "Answer or explanation (Markdown supported)"
    }
  ]
}
```

## Guidelines

1. Create 5-10 cards per topic
2. Use clear, concise language
3. Include examples where helpful
4. Use Markdown formatting for code, equations, or emphasis
5. Vary card types to cover different aspects of the topic

Now generate flashcards for: **{topic}**
