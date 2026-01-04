# Refactoring & Code Quality Report for LLM2Deck

This document provides a comprehensive analysis of the code quality, architectural integrity, and potential improvements for the `LLM2Deck` project. The code references are based on the state of the project as of December 2025.

## 1. Architectural & Structural Improvements

### 1.1 `convert_to_apkg.py` - Separation of Concerns
**Severity: High**
**Current State:**
The file `convert_to_apkg.py` is a monolithic script (~1000 lines) that handles:
- File I/O (loading JSON)
- Data transformation
- Content rendering (Markdown to HTML)
- Anki Model definitions (Python objects)
- CSS styling (embedded large strings)
- CLI argument handling

**Problem:**
- **Violation of Single Responsibility Principle (SRP):** This class does everything related to Anki generation.
- **Hard to Maintain:** Changing the CSS theme requires scrolling through hundreds of lines of python code.
- **Hard to Test:** Testing the markdown renderer requires instantiating the whole generator.

**Recommendation:**
Refactor into a package `src/anki/` with the following structure:
- `src/anki/models.py`: Definitions of `genanki.Model` instances.
- `src/anki/styles.py` or `src/anki/css/`: Separate files for CSS. Read them at runtime.
- `src/anki/renderer.py`: A class or module dedicated to `markdown -> html` conversion and sanitization (`render_markdown`).
- `src/anki/generator.py`: The orchestrator that uses the above components.

### 1.2 `main.py` - Open/Closed Principle Check
**Severity: Medium**
**Current State:**
`main.py` contains explicit `if/elif/else` chains to determine:
- `target_questions` based on `subject`
- `prompt_template` based on `subject` and `card_type`
- `target_model` schema based on `subject`

**Problem:**
- **Violation of Open/Closed Principle (OCP):** To add a new subject (e.g., "Chemistry"), you must modify `main.py` logic.
- **Coupling:** `main.py` knows too much about the specific configurations of each subject.

**Recommendation:**
Implement a `Registry` or `Configuration` pattern.
- Create a `src/config/subjects.py` that maps `subject` strings to a config object containing:
    - `questions_list`
    - `prompt_template`
    - `model_schema`
    - `output_prefix`
- `main.py` should simply lookup `SUBJECT_CONFIG[args.subject]` and pass it to the generator.

### 1.3 `src/generator.py` - Mode Logic
**Severity: Medium**
**Current State:**
The `CardGenerator` uses a string `mode` to decide behavior (e.g., checking `if 'mcq' in self.mode`).
**Problem:**
- **Stringly-typed programming:** Prone to typos ("mcq" vs "MCQ").
- **Implicit logic:** The behavior of the generic `CardGenerator` changes based on substring matching.

**Recommendation:**
- Pass a configuration object or specific flags (`is_mcq: bool`) to the `CardGenerator` instead of a raw mode string.
- Or use an Enum `GenerationMode`.

## 2. Code Quality & Type Safety

### 2.1 Generic Type Hints
**Severity: Low**
**Current State:**
Many functions use `Dict[str, Any]`.
- `generate_initial_cards` -> `str` (returns raw JSON string?)
- `combine_cards` -> `Optional[Dict[str, Any]]`

**Recommendation:**
- Use **TypedDict** or the existing **Pydantic Models** (`AnkiCard`, `MCQProblem`) wherever possible.
- If `generate_initial_cards` returns a string that is expected to be JSON, document it clearly or return a validated object.

### 2.2 Error Handling
**Severity: Medium**
**Current State:**
- In `src/providers/gemini.py`:
  ```python
  except Exception as e:
      logger.error(f"[Gemini] Error: {e}")
      return ""
  ```
- This swallows the exception. If the API fails due to authentication, the program continues and returns an empty string, potentially leading to confusion downstream.

**Recommendation:**
- Define custom exceptions in `src/exceptions.py` (e.g., `ProviderError`, `GenerationError`).
- Let the generic generator handle the error policy (retry, skip, or crash).

### 2.3 Hardcoded Resources by `questions.py` and `prompts.py`
**Severity: Low (Polish)**
**Current State:**
- `src/prompts.py` contains massive string constants.
- `src/questions.py` contains lists of strings.

**Recommendation:**
- **Prompts**: Move to `src/resources/prompts/*.md` or `*.txt`. This allows editing prompts without touching Python code and enables syntax highlighting for the prompt text itself (markdown).
- **Questions**: Move to `data/questions/*.json` or `*.yaml`. This separates data from logic.

## 3. Specific File Observations

### 3.1 `convert_to_apkg.py`
- **Regex Fragility**: The regex used to split code blocks `re.split(r'(```.*?```)', ...)` is simple but might fail on edge cases (e.g., backticks inside code). Consider a robust parsing strategy or trusting the `markdown` library extensions more.
- **Bleach Configuration**: The list of `allowed_tags` is hardcoded. Move this to a constant or config.
- **HTML/CSS Mixing**: The `afmt` (Answer Format) template includes `<style>` but the CSS is also passed to the Model constructor. ensure this is consistent.

### 3.2 `src/models.py`
- **Duplicate Fields**: `AnkiCard` and `MCQCard` share `tags`, `card_type`.
- **Refactor**: Create a `BaseCard` model.
  ```python
  class BaseCard(BaseModel):
      card_type: str
      tags: List[str]
  ```

### 3.3 `src/utils.py` (Assumed based on usage)
- Check if file verification (checking if file exists before writing) is robust.

## 4. Testing Implications
- Currently, there seems to be a lack of unit tests for the logic in `convert_to_apkg.py` (e.g., "Does the regex properly handle nested code blocks?", "Does the ID generation remain consistent?").
- Refactoring `convert_to_apkg.py` into smaller components will make unit testing significantly easier.

## Summary of Action Items

1.  **Refactor `convert_to_apkg.py`**: Break it down into `AnkiRenderer`, `AnkiModelFactory`, and `DeckBuilder`.
2.  **Refactor `main.py`**: Implement a config-driven approach for Subjects and Modes.
3.  **Enhance Type Safety**: Replace `Dict[str, Any]` with Pydantic models in Provider interfaces.
4.  **Externalize Data**: Move prompts and question lists to external resource files.
