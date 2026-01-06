# LLM2Deck - Comprehensive Refactoring Report

## Executive Summary

The LLM2Deck project has significant organizational and code quality issues that stem from rapid development and organic growth. This report identifies **13 major refactoring opportunities** organized by impact and complexity.

---

## 🔴 CRITICAL ISSUES (High Impact, Must Fix)

### 1. **Duplicated CLI Script Logic** 
**Files:** `main.py`, `convert_to_apkg.py`, `merge_anki_json.py`, `json_to_md.py`

**Problem:**
- Each top-level script is independent with its own argument parsing, logging setup, error handling
- No shared CLI framework or command dispatcher
- Logging setup called differently in each file
- Error handling patterns are inconsistent

**Current State:**
```
main.py                    → Generates JSON cards
convert_to_apkg.py        → Converts JSON to .apkg
merge_anki_json.py        → Merges JSON files
json_to_md.py             → Converts to Markdown
```

**Issues:**
- 4 separate entry points doing similar things
- Duplicated `setup_logging()` calls
- Inconsistent argument parsing
- Each has different help/documentation

**Refactoring Solution:**
Create a unified CLI dispatcher: `src/cli/__init__.py` with subcommands
```
uv run main.py generate [subject] [--mode mcq]
uv run main.py convert <json_file> [--mode leetcode]
uv run main.py merge <subject>
uv run main.py export <json_file> [--format md]
```

**Effort:** Medium | **Impact:** High

---

### 2. **Scattered Configuration Files**
**Files:** `api_keys.json`, `nvidia_keys.json`, `openrouter_keys.json`, `python3ds.json`, `.env`

**Problem:**
- API keys stored in 4 different formats and locations
- No unified configuration/secrets management
- Environment variables scattered throughout code
- Configuration loading logic duplicated in `src/setup.py`

**Current State:**
- `api_keys.json` → List of objects with `api_key` field (Cerebras)
- `nvidia_keys.json` → List of strings OR list of dicts
- `openrouter_keys.json` → List of objects with nested `data.key`
- `python3ds.json` → Cookie-based credentials
- `.env` → Only CONCURRENT_REQUESTS, key paths (inconsistently)

**Issues:**
- No single source of truth for configuration
- Key loading code has multiple formats to handle (lines 18-72 in `setup.py`)
- Inconsistent path resolution (using `.env` vs hardcoded)
- Shuffle called twice for OpenRouter (line 48 in `setup.py`)

**Refactoring Solution:**
Create `src/config/secrets.py` with:
```python
class SecretsManager:
    @staticmethod
    def load_api_keys(provider: str) -> List[str]
    
    @staticmethod
    def load_gemini_clients() -> List[GeminiClient]
    
    @staticmethod
    def validate_config() -> bool
```

Create unified config schema: `config.yaml` or `.env.example`

**Effort:** Medium | **Impact:** High

---

### 3. **Duplicated Logging Setup**
**Files:** `src/logging_config.py`, `src/logging_utils.py`

**Problem:**
- Two separate modules for logging (config + utils)
- Logging setup repeated in every CLI script
- Rich console created multiple times unnecessarily
- Unclear responsibility split

**Current State:**
- `logging_config.py` → Sets up logging with RichHandler
- `logging_utils.py` → Context managers for log_section, log_status
- Scripts call `setup_logging()` independently
- Console object is global but can be recreated

**Issues:**
- Boilerplate in every script
- No centralized control over log levels
- Potential for multiple console instances
- Context managers are useful but scattered

**Refactoring Solution:**
Consolidate into `src/logging_utils.py`:
```python
# Initialize once at app startup
logger = setup_logging()

# Export context managers and logger globally
# Scripts import and use without re-initializing
```

**Effort:** Low | **Impact:** High

---

### 4. **Disorganized Provider System**
**Files:** `src/providers/*.py`, `src/setup.py`

**Problem:**
- Provider initialization logic bloated in `setup.py` (150+ lines)
- Each provider has different key loading format
- Commented-out providers cluttering code (lines 106-159 in setup.py)
- No clear provider registry or factory pattern
- Duplicate shuffle operations and key cycling

**Current State:**
```
setup.py: 
  - load_cerebras_keys() → 15 lines
  - load_openrouter_keys() → 15 lines  
  - load_nvidia_keys() → 22 lines
  - load_gemini_clients() → 16 lines
  - initialize_providers() → 80 lines with commented code
```

**Issues:**
- Provider initialization mixed with key loading
- Hard to enable/disable providers without editing code
- Duplicate logic for key cycling (itertools.cycle)
- Commented providers make code unreadable

**Refactoring Solution:**
Create `src/providers/factory.py`:
```python
class ProviderFactory:
    @staticmethod
    def create_provider(provider_name: str, config: Dict) -> LLMProvider
    
    @staticmethod
    def initialize_all(config: ProviderConfig) -> List[LLMProvider]
    
    @staticmethod
    def get_available_providers() -> List[str]
```

Create `src/config/providers.yaml`:
```yaml
providers:
  cerebras:
    enabled: true
    models: ["gpt-oss-120b", "zai-glm-4.6"]
  nvidia:
    enabled: false
  openrouter:
    enabled: false
  gemini:
    enabled: false
```

**Effort:** High | **Impact:** High

---

## 🟠 MAJOR ISSUES (Medium Impact)

### 5. **Prompt Template Loading Inconsistency**
**Files:** `src/prompts.py`, `src/config/subjects.py`

**Problem:**
- Prompt files loaded at module import time (lines 17-22 in prompts.py)
- No error handling if files don't exist (raises FileNotFoundError at import)
- Hardcoded filename assumptions
- Lazy loading would be better

**Current State:**
```python
# src/prompts.py - These execute on import!
INITIAL_PROMPT_TEMPLATE = load_prompt("initial.md")
GENIUS_PERSONA_PROMPT_TEMPLATE = load_prompt("genius_cs.md")
```

**Issues:**
- App fails to start if any prompt file is missing
- Can't hotload prompts without module reload
- Wasteful if some prompts not used in execution path
- 7 prompts always loaded even if only using 1

**Refactoring Solution:**
Create `src/prompts/loader.py` with lazy loading:
```python
class PromptLoader:
    _cache = {}
    
    @classmethod
    def get(cls, prompt_name: str) -> str:
        if prompt_name not in cls._cache:
            cls._cache[prompt_name] = load_prompt(prompt_name)
        return cls._cache[prompt_name]
```

**Effort:** Low | **Impact:** Medium

---

### 6. **Questions Loading & Caching**
**Files:** `src/questions.py`, `src/config/subjects.py`

**Problem:**
- Questions loaded at module level (line 73 in questions.py)
- No way to reload/refresh questions without module reload
- Type handling scattered (categorized vs flat lists)
- get_indexed_questions() only works for categorized format

**Current State:**
```python
# Loaded once at startup, immutable
QUESTIONS, CS_QUESTIONS, PHYSICS_QUESTIONS = load_questions()
```

**Issues:**
- Can't add questions dynamically
- Mixing data loading with type conversion
- Flat list methods don't work on categorized (and vice versa)
- Questions stored in JSON at `src/data/questions.json` but no version control

**Refactoring Solution:**
Create `src/data/manager.py`:
```python
class QuestionsManager:
    @classmethod
    def load(cls, subject: str) -> Union[Dict, List]
    
    @classmethod
    def reload(cls) -> None  # For dynamic updates
    
    @classmethod
    def get_indexed(cls, subject: str) -> List[Tuple]
    
    @classmethod
    def add_question(cls, subject: str, category: str, question: str)
```

**Effort:** Low | **Impact:** Medium

---

### 7. **Code Generation Pipeline Unclear**
**Files:** `src/generator.py`, `src/models.py`

**Problem:**
- Mixing of concerns: LLM interaction, JSON handling, archival, combining
- No clear separation between generation stages
- Different behavior for MCQ vs standard (hidden in mode string check)
- Card combining logic conflated with initial generation

**Current State:**
```python
# Line 67 in generator.py
combine_prompt = MCQ_COMBINE_PROMPT_TEMPLATE if 'mcq' in self.generation_mode else None
```

**Issues:**
- Mode string parsing scattered throughout code
- Different card types handled by different code paths
- Archival happens in generator (line 86) - should be separate concern
- No clear model validation pipeline

**Refactoring Solution:**
Create `src/pipeline/` with separate stages:
```
pipeline/
  ├── __init__.py
  ├── stage_initial_generation.py
  ├── stage_combining.py
  ├── stage_validation.py
  ├── stage_archival.py
  └── orchestrator.py
```

Each stage is composable, testable, swappable.

**Effort:** High | **Impact:** Medium

---

### 8. **Anki Generation Logic Duplicated**
**Files:** `src/anki/generator.py`, `src/anki/models.py`

**Problem:**
- Same rendering logic applied differently for MCQ vs basic (lines 128-131)
- Card type detection repeated (checking for 'options')
- Tag construction duplicated (lines 119-123)
- Deck path building has two different formats (categorized vs topic-based)

**Current State:**
```python
# Lines 128-131: Different paths for MCQ vs Basic
if 'options' in card_data and is_mcq_mode:
    self._add_mcq_card(...)
else:
    self._add_basic_card(...)
```

**Issues:**
- Hard to add new card types
- MCQ and basic cards treated as special cases
- Tag construction logic same but in two methods
- Deck path logic has fallback but inconsistent

**Refactoring Solution:**
Create `src/anki/card_types/`:
```
card_types/
  ├── base.py          # AbstractCardType
  ├── basic.py         # BasicCardType
  ├── mcq.py           # MCQCardType
  └── factory.py       # CardTypeFactory
```

Each card type handles its own rendering, tagging, field mapping.

**Effort:** High | **Impact:** Medium

---

### 9. **Root-Level Script Clutter**
**Files:** Multiple .py files in project root

**Problem:**
- 7 Python scripts in root directory (main.py, convert_to_apkg.py, merge_anki_json.py, json_to_md.py, g4f_test.py, plus generated/test files)
- No clear which scripts are core vs experimental
- g4f_test.py and other tests not in tests/ directory
- Generated output files (*.apkg, *.json) mixed with source

**Current State:**
```
LLM2Deck/
├── main.py                          (core)
├── convert_to_apkg.py              (core)
├── merge_anki_json.py              (core)
├── json_to_md.py                   (core)
├── g4f_test.py                     (test? experimental?)
├── leetcode_anki_deck_20251227.json (output)
├── physics_anki.apkg               (output)
├── tests/
│   └── (test files here)
```

**Issues:**
- Not clear which scripts are part of core workflow
- Generated files clutter the root
- No distinction between core and experimental
- Tests in separate directory but experimental code in root

**Refactoring Solution:**
Reorganize:
```
LLM2Deck/
├── src/
│   ├── cli/              # NEW: All CLI entry points
│   │   ├── __init__.py
│   │   ├── commands.py   # generate, convert, merge, export
│   │   └── main.py       # Click/Typer dispatcher
│   └── ...
├── tests/
│   ├── unit/
│   ├── integration/
│   └── experimental/     # g4f_test.py moves here
├── output/               # NEW: Generate files go here
├── main.py              # Single entry point dispatcher
└── ...
```

**Effort:** Medium | **Impact:** Medium

---

### 10. **Directory Structure Mismatch**
**Files:** Various

**Problem:**
- `anki_cards_archival/` and `anki_cards_markdown/` directories in root
- Questions, prompts, and data files distributed across `src/data/`
- No clear data directory structure
- Output files go to root, not organized by subject/date

**Current State:**
```
anki_cards_archival/           # archival
  ├── cs/
  ├── leetcode/
  └── physics/
anki_cards_markdown/           # exported markdown
src/data/
  ├── questions.json          # questions file
  └── prompts/                 # prompt templates
```

**Issues:**
- Generated files (archival) in source tree
- Output directories not intuitive
- Questions.json sits alongside prompts but different purposes
- No organization by date or run

**Refactoring Solution:**
```
LLM2Deck/
├── data/                        # MOVED: Question & config data
│   ├── questions/
│   │   ├── leetcode.json
│   │   ├── cs.json
│   │   └── physics.json
│   └── prompts/
│       ├── generation/
│       ├── combining/
│       └── README.md
├── output/                      # MOVED: Generated files
│   ├── decks/
│   │   ├── 2025-01-15/
│   │   │   ├── leetcode_deck.json
│   │   │   └── leetcode_deck.apkg
│   │   └── latest/              # symlink to recent
│   ├── archival/
│   │   ├── 2025-01-15/
│   │   │   ├── leetcode/
│   │   │   ├── cs/
│   │   │   └── physics/
│   │   └── markdown/
│   │       └── 2025-01-15/
├── src/
└── tests/
```

**Effort:** Medium | **Impact:** Medium

---

## 🟡 MODERATE ISSUES (Lower Impact)

### 11. **Provider Base Class Too Minimal**
**File:** `src/providers/base.py`

**Problem:**
- Only 2 abstract methods defined
- No shared utilities or error handling
- Each provider implements same retry/error logic independently
- No provider metadata or capabilities

**Current State:**
```python
class LLMProvider(ABC):
    @abstractmethod
    async def generate_initial_cards(...): pass
    
    @abstractmethod
    async def combine_cards(...): pass
```

**Issues:**
- No way to query provider capabilities
- No standard error handling
- No rate limiting interface
- Each provider duplicates JSON parsing logic

**Refactoring Solution:**
Enhance base class:
```python
class LLMProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass
    
    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities: pass
    
    async def generate_with_retry(...): pass  # Shared logic
    
    async def parse_json_response(...): pass  # Shared logic
```

**Effort:** Low | **Impact:** Low

---

### 12. **Model Validation Scattered**
**Files:** `src/models.py`, `src/generator.py`, `src/config/subjects.py`

**Problem:**
- Post-processing happens in generator (lines 72-76)
- Tag normalization hardcoded (replace spaces)
- No centralized validation schema
- Different models for MCQ vs standard

**Current State:**
```python
# Line 72-76 in generator.py - Post-processing!
for card in final_card_data.get('cards', []):
    if 'tags' in card:
        card['tags'] = [tag.replace(' ', '') for tag in card['tags']]
```

**Issues:**
- Post-processing after model parsing
- Normalization rules scattered
- No validation framework
- Hard to add new validation rules

**Refactoring Solution:**
Add validators to Pydantic models:
```python
class AnkiCard(BaseModel):
    card_type: str = Field(...)
    tags: List[str] = Field(...)
    
    @field_validator('tags')
    def normalize_tags(cls, tags):
        return [tag.replace(' ', '') for tag in tags]
```

**Effort:** Low | **Impact:** Low

---

### 13. **Type Hints Inconsistent**
**Files:** Multiple

**Problem:**
- Some files have full type hints, others minimal
- Return type `Optional[Dict]` is vague
- Union types not used where appropriate (e.g., CategorizedQuestions | FlatQuestions)
- Function signatures inconsistent

**Examples:**
```python
# Line 29 in generator.py - Good!
def process_question(
    self, 
    question: str, 
    prompt_template: Optional[str] = None, 
    ...
) -> Optional[Dict]:

# Line 9 in json_to_md.py - Missing types!
def convert_json_to_md(source_directory: str, target_directory: str):
    # Missing return type
```

**Issues:**
- IDE autocomplete unreliable
- Type checking incomplete
- Refactoring harder without types
- Documentation unclear

**Refactoring Solution:**
Add `py.typed` marker, enforce mypy with minimal config:
```
[tool.mypy]
python_version = "3.12"
strict = false
warn_unused_ignores = true
warn_redundant_casts = true
```

**Effort:** Medium | **Impact:** Low

---

## 📊 Refactoring Priority Matrix

| Issue | Effort | Impact | Priority | Status |
|-------|--------|--------|----------|--------|
| Duplicated CLI Scripts | Medium | High | **1** | 🔴 |
| Scattered Configuration | Medium | High | **2** | 🔴 |
| Duplicated Logging | Low | High | **3** | 🔴 |
| Disorganized Provider System | High | High | **4** | 🔴 |
| Prompt Loading Inconsistency | Low | Medium | **5** | 🟠 |
| Questions Loading & Caching | Low | Medium | **6** | 🟠 |
| Code Generation Pipeline | High | Medium | **7** | 🟠 |
| Anki Generation Duplication | High | Medium | **8** | 🟠 |
| Root-Level Script Clutter | Medium | Medium | **9** | 🟠 |
| Directory Structure Mismatch | Medium | Medium | **10** | 🟠 |
| Provider Base Class | Low | Low | **11** | 🟡 |
| Model Validation | Low | Low | **12** | 🟡 |
| Type Hints | Medium | Low | **13** | 🟡 |

---

## 🎯 Recommended Refactoring Phases

### Phase 1: Foundation (1-2 weeks)
Focus on reducing complexity and consolidating duplication
1. **Unify CLI scripts** → Single dispatcher
2. **Consolidate logging** → Single setup + utilities
3. **Centralize configuration** → Unified secrets/config manager
4. **Reorganize directory structure** → Data/output separation

**Benefit:** Cleaner codebase, easier to maintain, clearer workflows

---

### Phase 2: Modularity (2-3 weeks)
Focus on extracting patterns and improving extensibility
1. **Extract provider factory** → Enable/disable providers easily
2. **Improve prompt loading** → Lazy loading, hot reload
3. **Enhance base classes** → Provider, Card type frameworks
4. **Add validation layer** → Pydantic validators

**Benefit:** Easier to add new providers/models, testable components

---

### Phase 3: Polish (1-2 weeks)
Focus on code quality and documentation
1. **Add type hints** → Full mypy compliance
2. **Improve error handling** → Consistent, informative
3. **Create documentation** → Refactoring guide, architecture docs
4. **Add integration tests** → End-to-end workflows

**Benefit:** Production-ready, maintainable, documented code

---

## 📝 Implementation Notes

### Testing Strategy
Before refactoring, create integration tests to verify:
```
tests/integration/
├── test_cli_generate.py
├── test_cli_convert.py
├── test_anki_generation.py
├── test_provider_initialization.py
└── test_end_to_end.py
```

### Backward Compatibility
- Keep old script names as wrappers during transition
- Support old `.env` format while migrating to new config
- Keep questions.json location while deprecating

### Code Review Checklist
- [ ] All imports work from new paths
- [ ] No circular dependencies
- [ ] Type hints complete
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Old code removed/deprecated

---

## 🔗 Dependencies to Consider

**Current Tech Stack:**
- Python 3.12
- Pydantic (models)
- Genanki (Anki generation)
- Rich (logging/output)
- Python dotenv

**Recommended Additions:**
- `typer` or `click` → Better CLI framework
- `pydantic-settings` → Config management
- `pytest` → Test framework
- `mypy` → Type checking
- `black`, `ruff` → Code formatting

---

## 📚 References

### Architecture Patterns to Consider
- **Factory Pattern**: Provider creation, Card type creation
- **Strategy Pattern**: Different generation strategies (MCQ vs standard)
- **Observer Pattern**: Event system for generation stages
- **Pipeline Pattern**: Stage-based processing

### Similar Projects for Inspiration
- Click CLI framework: https://click.palletsprojects.com/
- FastAPI dependency injection: https://fastapi.tiangolo.com/
- Pydantic Settings: https://docs.pydantic.dev/latest/

---

## ⏭️ Next Steps

1. **Review this report** with the team
2. **Create issues** for each refactoring item
3. **Prioritize phases** based on development bandwidth
4. **Create integration tests** as safety net
5. **Begin Phase 1** with CLI consolidation
6. **Document progress** in architecture guide

---

**Report Generated:** 2025-01-15
**Project:** LLM2Deck
**Status:** Pre-Refactoring Analysis
