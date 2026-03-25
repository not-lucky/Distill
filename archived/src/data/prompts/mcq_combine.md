You are an expert educator combining Multiple Choice Questions.
I have multiple sets of MCQ Anki cards generated for the topic "{question}".

Inputs:
{inputs}

**Task**:
1. Combine these sets into a SINGLE, high-quality MCQ deck.
2. **Preserve DIVERSITY**: Keep questions that test different aspects (conceptual, application, analysis, tricky edge cases).
3. **Remove exact duplicates**, but keep questions that test the same concept from different angles.
4. Ensure the final deck has **60+ high-quality MCQs** with well-crafted distractors.
5. **Strictly adhere** to the following JSON schema for the output.

**CRITICAL MCQ RULES:**
1. Each question must have EXACTLY 4 options (A, B, C, D).
2. Only ONE correct answer per question.
3. Distractors must be plausible but clearly wrong.
4. `correct_answer` must be exactly "A", "B", "C", or "D".
5. `explanation` should teach why the answer is correct.
6. **NO SPACES** in `card_type` or `tags`. Use `PascalCase`.

Output MUST be valid JSON matching the schema.
