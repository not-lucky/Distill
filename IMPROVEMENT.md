# IMPROVEMENT.md

Improvement ideas for LLM2Deck - features, quality of life enhancements, and technical debt cleanup.

---

## 🎯 High Priority

### 1. Progress Visualization ✅ IMPLEMENTED
**Problem:** Large generation runs (100+ questions) provide minimal feedback during execution.

**Improvements:**
- [x] Add rich progress bar with `rich` library showing per-question status
- [x] Real-time provider status indicators (✓ success, ⏳ pending, ✗ failed)
- [x] ETA estimation based on completed questions
- [x] Live token usage/cost tracking per provider

*Implementation: See `src/progress.py`, integrated in `src/orchestrator.py`*

### 2. Resume Failed Runs ✅ IMPLEMENTED
**Problem:** If generation crashes mid-way, all progress is lost.

**Improvements:**
- [x] Add `--resume <run_id>` flag to continue from last successful question
- [x] Store question processing status in database
- [x] Skip already-processed questions on resume
- [x] Merge partial results with resumed results

*Implementation: See `src/orchestrator.py`, `src/repositories.py`, `src/queries.py`*

### 3. Selective Question Generation
**Problem:** Currently generates all questions in a subject. No way to pick specific ones.

**Improvements:**
- [ ] Add `--category "Arrays"` flag to generate only specific categories
- [ ] Add `--question "Two Sum"` flag for single question generation
- [ ] Add `--limit N` to generate first N questions (for testing)
- [ ] Add `--skip-until "Binary Search"` for partial runs

### 4. Cost Estimation & Budgeting
**Problem:** No visibility into API costs before or during generation.

**Improvements:**
- [ ] Pre-run cost estimation based on question count and provider token rates
- [ ] `--budget <amount>` flag to stop generation when budget exceeded
- [ ] Post-run cost summary per provider
- [ ] Track cumulative costs in database across runs

---

## 🛠 Quality of Life

### 5. Interactive Mode
**Improvements:**
- [ ] `llm2deck interactive` - TUI for browsing/managing runs
- [ ] Preview generated cards before saving
- [ ] Edit/regenerate individual cards
- [ ] Side-by-side comparison of provider outputs

### 6. Better Error Recovery
**Problem:** Single question failures can cascade or produce confusing logs.

**Improvements:**
- [ ] Per-question retry with exponential backoff (independent of provider retry)
- [ ] Fallback provider chain (if Cerebras fails, try OpenRouter)
- [ ] Save partial results even on crash (graceful degradation)
- [ ] Clearer error messages with suggested fixes

### 7. Card Quality Analysis
**Improvements:**
- [ ] Analyze generated cards for common issues:
  - Duplicate content across cards
  - Cards that are too long/short
  - Missing explanations or incomplete answers
  - Code blocks without language tags
- [ ] `llm2deck validate <file>.json` command
- [ ] Quality score per card/problem
- [ ] Suggestions for improvement

### 8. Template/Prompt Management
**Improvements:**
- [ ] `llm2deck prompts list` - Show available prompts
- [ ] `llm2deck prompts edit <subject>` - Edit prompts in $EDITOR
- [ ] `llm2deck prompts test <subject>` - Test prompt with single question
- [ ] Prompt versioning with rollback
- [ ] Prompt A/B testing framework

### 9. Export Formats
**Problem:** Only exports to Anki `.apkg` format.

**Improvements:**
- [ ] CSV export for spreadsheet users
- [ ] Quizlet import format
- [ ] Mochi SRS format
- [ ] RemNote format
- [ ] Plain text/PDF study guide generation
- [ ] Obsidian-compatible markdown with backlinks

### 10. Watch Mode
**Improvements:**
- [ ] `llm2deck watch <subject>` - Auto-generate when questions file changes
- [ ] Hot-reload config.yaml changes
- [ ] Useful for iterating on prompts

---

## 🔧 Technical Improvements

### 11. Provider Enhancements
**Improvements:**
- [ ] Health check endpoint testing before run starts
- [ ] Dynamic provider selection based on latency/availability
- [ ] Provider-specific retry strategies (some need longer waits)
- [ ] Connection pooling for high-throughput runs
- [ ] Add more providers:
  - [ ] Anthropic Claude direct API
  - [ ] Groq
  - [ ] Together AI
  - [ ] Fireworks AI
  - [ ] Local LLMs (Ollama, llama.cpp)

### 12. Caching Improvements
**Problem:** Cache is all-or-nothing, no partial matching.

**Improvements:**
- [ ] Semantic cache - reuse similar (not identical) prompts
- [ ] Cache TTL configuration per provider
- [ ] Cache size limits with LRU eviction
- [ ] Cache warming from previous runs
- [ ] `llm2deck cache export/import` for backup

### 13. Database Improvements
**Improvements:**
- [ ] Add full-text search on card content (SQLite FTS5)
- [ ] Database migrations system (Alembic)
- [ ] Database backup/restore commands
- [ ] Optional PostgreSQL/MySQL backend for teams
- [ ] Card deduplication across runs

### 14. Testing & Reliability
**Improvements:**
- [ ] Integration tests with real (cheap) API calls (opt-in)
- [ ] Snapshot testing for card output stability
- [ ] Load testing for concurrent generation
- [ ] Chaos testing (random provider failures)
- [ ] Performance benchmarks

### 15. Configuration Validation
**Improvements:**
- [ ] `llm2deck config validate` - Check config before run
- [ ] Schema validation with helpful error messages
- [ ] Warn about deprecated config options
- [ ] Config file linting
- [ ] Environment-specific configs (dev/prod)

---

## 📚 Documentation & UX

### 16. Better Onboarding
**Improvements:**
- [ ] `llm2deck init` - Interactive setup wizard
  - Create config.yaml with user's providers
  - Guide API key setup
  - Test connection to each provider
  - Generate sample deck to verify setup
- [ ] Built-in help with examples (`llm2deck generate --examples`)

### 17. Web Dashboard
**Improvements:**
- [ ] Local web UI for run management
- [ ] View/search cards visually
- [ ] Real-time generation progress
- [ ] Provider performance analytics
- [ ] Cost tracking dashboard

### 18. Logging & Debugging
**Improvements:**
- [ ] `--verbose` / `-v` flags for debug output
- [ ] `--quiet` / `-q` flag for minimal output
- [ ] Structured JSON logging option
- [ ] Log rotation and compression
- [ ] Request/response dumping for debugging

---

## 🎨 Anki Card Enhancements

### 19. Card Customization
**Improvements:**
- [ ] Multiple theme options (not just Catppuccin)
- [ ] Custom CSS injection
- [ ] Font size configuration
- [ ] Card layout templates
- [ ] Mobile-optimized card variants

### 20. Media Support
**Improvements:**
- [ ] Image generation for concept cards (via DALL-E/Midjourney)
- [ ] Diagram generation (Mermaid → SVG)
- [ ] Audio pronunciation for terms
- [ ] LaTeX rendering for math formulas
- [ ] Embedded code execution (for CS cards)

### 21. Spaced Repetition Optimization
**Improvements:**
- [ ] Difficulty rating suggestions based on content
- [ ] Automatic card splitting for long answers
- [ ] Cloze deletion generation
- [ ] Prerequisite tagging (learn A before B)
- [ ] Integration with Anki scheduling data

---

## 🔄 Workflow Improvements

### 22. Pipeline Mode
**Improvements:**
- [ ] `llm2deck pipeline` - Define multi-step workflows
  ```yaml
  pipeline:
    - generate: {subject: leetcode, category: arrays}
    - validate: {min_cards: 5}
    - convert: {format: apkg}
    - upload: {destination: ankiweb}
  ```

### 23. Scheduling & Automation
**Improvements:**
- [ ] Cron-like scheduling for regular generation
- [ ] GitHub Actions integration example
- [ ] Webhook triggers for CI/CD
- [ ] Email/Slack notifications on completion

### 24. Collaboration Features
**Improvements:**
- [ ] Export/import run configurations
- [ ] Share prompt templates
- [ ] Merge decks from multiple users
- [ ] Conflict resolution for overlapping cards

---

## 🐛 Known Issues to Fix

### 25. Stability Fixes
- [ ] Handle graceful shutdown on Ctrl+C (save partial progress)
- [ ] Fix memory usage with very large question sets
- [ ] Handle network interruptions mid-request
- [ ] Better timezone handling in timestamps

### 26. Edge Cases
- [ ] Questions with special characters in titles
- [ ] Very long questions (> 4000 chars)
- [ ] Unicode/emoji in card content
- [ ] Empty responses from providers
- [ ] Malformed JSON with unescaped characters

---

## 📊 Analytics & Insights

### 27. Generation Analytics
**Improvements:**
- [ ] Provider performance comparison (speed, quality, cost)
- [ ] Success rate tracking over time
- [ ] Common failure patterns
- [ ] Question difficulty correlation with generation success

### 28. Learning Analytics Integration
**Improvements:**
- [ ] Import Anki review data
- [ ] Identify poorly-performing cards
- [ ] Suggest card improvements based on review patterns
- [ ] A/B test card variants

---

## 🚀 Future Vision

### 29. Multi-Modal Cards
- [ ] Video explanations (YouTube embeds)
- [ ] Interactive code playgrounds
- [ ] Animated diagrams
- [ ] Voice-over explanations

### 30. AI-Powered Enhancements
- [ ] Auto-detect optimal card structure per question type
- [ ] Personalized difficulty adjustment
- [ ] Related question suggestions
- [ ] Gap analysis (what topics need more cards?)

### 31. Community Features
- [ ] Public prompt template library
- [ ] Deck sharing marketplace
- [ ] Collaborative deck building
- [ ] Quality ratings and reviews

---

## Implementation Notes

**Suggested order of implementation:**
1. High Priority items (1-4) - Immediate value
2. QoL improvements (5-10) - User experience
3. Technical improvements (11-15) - Stability/scalability
4. Everything else based on user feedback

**Dependencies:**
- Items 17 (Web Dashboard) depends on 13 (Database Improvements)
- Item 21 (SR Optimization) requires external Anki integration
- Items 29-31 are long-term vision items

---

*Last updated: January 2026*
