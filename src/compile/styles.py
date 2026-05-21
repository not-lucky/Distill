"""
Catppuccin Mocha CSS theme for LLM2Deck Anki cards.

Centralizing the stylesheet here keeps compile.py focused on Python logic and
lets us swap themes (e.g., for a light variant) without touching card generation.
"""

CARD_CSS = """
:root {
  --ctp-rosewater: #f5e0dc;
  --ctp-flamingo: #f2cdcd;
  --ctp-pink: #f5c2e7;
  --ctp-mauve: #cba6f7;
  --ctp-red: #f38ba8;
  --ctp-maroon: #eba0ac;
  --ctp-peach: #fab387;
  --ctp-yellow: #f9e2af;
  --ctp-green: #a6e3a1;
  --ctp-teal: #94e2d5;
  --ctp-sky: #89dceb;
  --ctp-sapphire: #74c7ec;
  --ctp-blue: #89b4fa;
  --ctp-lavender: #b4befe;
  --ctp-text: #cdd6f4;
  --ctp-subtext1: #bac2de;
  --ctp-subtext0: #a6adc8;
  --ctp-overlay2: #9399b2;
  --ctp-overlay1: #7f849c;
  --ctp-overlay0: #6c7086;
  --ctp-surface2: #585b70;
  --ctp-surface1: #45475a;
  --ctp-surface0: #313244;
  --ctp-base: #1e1e2e;
  --ctp-mantle: #181825;
  --ctp-crust: #11111b;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background-color: var(--ctp-base);
  color: var(--ctp-text);
  margin: 0;
  padding: 10px;
}

.card {
  background-color: var(--ctp-base);
  color: var(--ctp-text);
  padding: 24px;
  max-width: 750px;
  margin: 16px auto;
  border-radius: 12px;
  border: 1px solid var(--ctp-surface0);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
  text-align: left;
}

/* Card metadata styling */
.card-type {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  color: var(--ctp-mauve);
  background-color: var(--ctp-surface0);
  padding: 4px 10px;
  border-radius: 20px;
  margin-bottom: 8px;
  border: 1px solid var(--ctp-surface1);
}

.source {
  font-size: 0.85rem;
  color: var(--ctp-subtext0);
  margin-bottom: 12px;
  font-weight: 500;
}

hr {
  border: 0;
  height: 1px;
  background: var(--ctp-surface1);
  margin: 20px 0;
}

.question, .cloze-text, .answer, .explanation {
  font-size: 1.05rem;
  line-height: 1.6;
}

.explanation {
  margin-top: 20px;
  font-size: 0.95rem;
  color: var(--ctp-subtext1);
  background-color: var(--ctp-surface0);
  padding: 14px 18px;
  border-left: 4px solid var(--ctp-blue);
  border-radius: 4px;
}

.cloze {
  color: var(--ctp-blue) !important;
  font-weight: bold !important;
}

/* MCQ Options styling */
.options {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.option {
  padding: 12px 16px;
  background-color: var(--ctp-surface0);
  border: 1px solid var(--ctp-surface1);
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 1rem;
}

.option-letter {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  background-color: var(--ctp-surface2);
  border-radius: 50%;
  font-weight: bold;
  font-size: 0.85rem;
  color: var(--ctp-text);
  flex-shrink: 0;
}

/* MCQ Answer Revealed Styling */
.options.answer-revealed .option {
  opacity: 0.6;
}

.correct-answer-badge {
  display: inline-block;
  margin-top: 14px;
  padding: 6px 14px;
  background-color: rgba(166, 227, 161, 0.12);
  border: 1px solid var(--ctp-green);
  color: var(--ctp-green);
  border-radius: 6px;
  font-weight: 700;
  font-size: 0.9rem;
}

/* Typography, lists & formatting */
h1, h2, h3, h4, h5, h6 {
  color: var(--ctp-lavender);
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  font-weight: 600;
}

h1 { font-size: 1.5rem; }
h2 { font-size: 1.35rem; }
h3 { font-size: 1.2rem; }

p {
  margin-top: 0;
  margin-bottom: 1em;
}

ul, ol {
  margin-top: 0;
  margin-bottom: 1em;
  padding-left: 24px;
}

li {
  margin-bottom: 0.4em;
}

a {
  color: var(--ctp-blue);
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

/* Monospace code styling */
pre, code {
  font-family: "JetBrains Mono", "Fira Code", "Courier New", Courier, monospace;
}

code {
  background-color: var(--ctp-surface1);
  color: var(--ctp-peach);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
}

pre {
  background-color: var(--ctp-surface0);
  border: 1px solid var(--ctp-surface1);
  padding: 14px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 16px 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

pre code {
  background-color: transparent;
  color: var(--ctp-text);
  padding: 0;
  border-radius: 0;
  font-size: 0.9em;
}

/* Tables styling */
table {
  border-collapse: collapse;
  width: 100%;
  margin: 16px 0;
  font-size: 0.95rem;
}

th, td {
  border: 1px solid var(--ctp-surface1);
  padding: 10px 14px;
  text-align: left;
}

th {
  background-color: var(--ctp-surface0);
  color: var(--ctp-blue);
  font-weight: 600;
}

tr:nth-child(even) {
  background-color: rgba(255, 255, 255, 0.02);
}

/* Mobile adjustments */
@media (max-width: 600px) {
  .card {
    padding: 16px;
    margin: 8px auto;
  }
  .option {
    padding: 10px 12px;
  }
}
"""
