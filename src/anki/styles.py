
# Catppuccin Mocha & Latte Theme Variables
# Adapted from Catppuccin (https://github.com/catppuccin/catppuccin)

BASE_CSS = '''
.card {
    /* Default to Latte (light) colors */
    --ctp-base: #eff1f5;
    --ctp-mantle: #e6e9ef;
    --ctp-crust: #dce0e8;
    --ctp-surface0: #ccd0da;
    --ctp-surface1: #bcc0cc;
    --ctp-surface2: #acb0be;
    --ctp-overlay0: #9ca0b0;
    --ctp-overlay1: #8c8fa1;
    --ctp-overlay2: #7c7f93;
    --ctp-text: #4c4f69;
    --ctp-subtext1: #5c5f77;
    --ctp-subtext0: #6c6f85;
    --ctp-green: #40a02b;
    --ctp-blue: #1e66f5;
    --ctp-mauve: #8839ef;
    --ctp-red: #d20f39;
    --ctp-peach: #fe640b;
    --ctp-yellow: #df8e1d;
    --ctp-teal: #179299;
    --ctp-pink: #ea76cb;
    --ctp-lavender: #7287fd;
    --ctp-rosewater: #dc8a78;
    --ctp-flamingo: #dd7878;
    --ctp-sky: #04a5e5;
    --ctp-sapphire: #209fb5;
    --ctp-maroon: #e64553;
}

/* Dark mode - Catppuccin Mocha */
.night_mode .card,
.nightMode .card,
.night-mode .card,
[class*="night"] .card {
    --ctp-base: #1e1e2e;
    --ctp-mantle: #181825;
    --ctp-crust: #11111b;
    --ctp-surface0: #313244;
    --ctp-surface1: #45475a;
    --ctp-surface2: #585b70;
    --ctp-overlay0: #6c7086;
    --ctp-overlay1: #7f849c;
    --ctp-overlay2: #9399b2;
    --ctp-text: #cdd6f4;
    --ctp-subtext1: #bac2de;
    --ctp-subtext0: #a6adc8;
    --ctp-green: #a6e3a1;
    --ctp-blue: #89b4fa;
    --ctp-mauve: #cba6f7;
    --ctp-red: #f38ba8;
    --ctp-peach: #fab387;
    --ctp-yellow: #f9e2af;
    --ctp-teal: #94e2d5;
    --ctp-pink: #f5c2e7;
    --ctp-lavender: #b4befe;
    --ctp-rosewater: #f5e0dc;
    --ctp-flamingo: #f2cdcd;
    --ctp-sky: #89dceb;
    --ctp-sapphire: #74c7ec;
    --ctp-maroon: #eba0ac;
}

.card {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
    font-size: 18px;
    text-align: left;
    color: var(--ctp-text);
    background-color: var(--ctp-base);
    padding: 25px;
    line-height: 1.7;
    min-height: 100vh;
    box-sizing: border-box;
}

.card-type {
    background: linear-gradient(135deg, var(--ctp-mauve), var(--ctp-blue));
    color: var(--ctp-crust);
    padding: 6px 14px;
    border-radius: 8px;
    display: inline-block;
    font-size: 13px;
    margin-bottom: 12px;
    text-transform: uppercase;
    font-weight: 700;
    letter-spacing: 0.5px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.source {
    color: var(--ctp-subtext0);
    font-size: 15px;
    font-style: italic;
    margin-bottom: 12px;
    padding: 8px 12px;
    background-color: var(--ctp-mantle);
    border-radius: 6px;
    border-left: 3px solid var(--ctp-lavender);
}

.question {
    font-size: 20px;
    font-weight: 600;
    color: var(--ctp-text);
    margin: 25px 0;
    padding: 15px;
    background-color: var(--ctp-surface0);
    border-radius: 10px;
    border: 1px solid var(--ctp-surface1);
    letter-spacing: 0.3px;
}

.answer {
    font-size: 18px;
    color: var(--ctp-subtext1);
    margin: 25px 0;
    padding: 15px;
    background-color: var(--ctp-mantle);
    border-radius: 10px;
    border: 1px solid var(--ctp-surface0);
    line-height: 1.8;
}

/* Code block styling */
.highlight {
    margin: 16px 0;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

.highlight pre {
    background-color: var(--ctp-crust);
    border: 1px solid var(--ctp-surface0);
    padding: 16px;
    margin: 0;
    overflow-x: auto;
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
    font-size: 15px;
    white-space: pre-wrap;
    word-wrap: break-word;
    line-height: 1.6;
}

/* Inline code styling */
code {
    background-color: var(--ctp-surface0);
    color: var(--ctp-pink);
    padding: 3px 6px;
    border-radius: 4px;
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
    font-size: 15px;
    font-weight: 500;
    border: 1px solid var(--ctp-surface1);
}

.highlight code {
    background-color: transparent;
    color: var(--ctp-text);
    padding: 0;
    border: none;
    font-weight: normal;
}

/* Pygments Syntax Highlighting with Catppuccin */
.highlight .hll { background-color: var(--ctp-surface2); }
.highlight .c, .highlight .ch, .highlight .cm, .highlight .cpf, .highlight .c1, .highlight .cs { color: var(--ctp-overlay0); font-style: italic; } /* Comments */
.highlight .err { color: var(--ctp-red); background-color: var(--ctp-mantle); } /* Error */
.highlight .k, .highlight .kc, .highlight .kd, .highlight .kn, .highlight .kp, .highlight .kr, .highlight .kt { color: var(--ctp-mauve); font-weight: bold; } /* Keywords */
.highlight .m, .highlight .mb, .highlight .mf, .highlight .mh, .highlight .mi, .highlight .mo, .highlight .il { color: var(--ctp-peach); } /* Numbers */
.highlight .s, .highlight .sa, .highlight .sb, .highlight .sc, .highlight .dl, .highlight .sd, .highlight .s2, .highlight .se, .highlight .sh, .highlight .si, .highlight .sx, .highlight .sr, .highlight .s1, .highlight .ss { color: var(--ctp-green); } /* Strings */
.highlight .na, .highlight .py { color: var(--ctp-teal); } /* Attributes */
.highlight .nb, .highlight .bp { color: var(--ctp-lavender); } /* Builtins */
.highlight .nc, .highlight .nn { color: var(--ctp-yellow); font-weight: bold; } /* Classes */
.highlight .no, .highlight .nv, .highlight .vc, .highlight .vg, .highlight .vi, .highlight .vm { color: var(--ctp-blue); } /* Variables */
.highlight .nd, .highlight .ni { color: var(--ctp-pink); } /* Decorators, Entities */
.highlight .ne, .highlight .fm { color: var(--ctp-sapphire); font-weight: bold; } /* Exceptions, Functions */
.highlight .nf { color: var(--ctp-blue); font-weight: bold; } /* Functions */
.highlight .nl { color: var(--ctp-rosewater); } /* Labels */
.highlight .nt { color: var(--ctp-red); font-weight: bold; } /* Tags */
.highlight .ow { color: var(--ctp-sky); font-weight: bold; } /* Operators */
.highlight .w { color: var(--ctp-surface1); } /* Whitespace */
.highlight .cp { color: var(--ctp-flamingo); font-weight: bold; } /* Preprocessor */
.highlight .gd { color: var(--ctp-red); background-color: var(--ctp-mantle); } /* Deleted */
.highlight .ge { font-style: italic; color: var(--ctp-text); } /* Emph */
.highlight .gh { color: var(--ctp-lavender); font-weight: bold; } /* Heading */
.highlight .gi { color: var(--ctp-green); background-color: var(--ctp-mantle); } /* Inserted */
.highlight .go { color: var(--ctp-subtext0); } /* Output */
.highlight .gp { color: var(--ctp-overlay2); font-weight: bold; } /* Prompt */
.highlight .gs { font-weight: bold; } /* Strong */
.highlight .gu { color: var(--ctp-lavender); font-weight: bold; } /* Subheading */
.highlight .gt { color: var(--ctp-red); } /* Traceback */
.highlight .gr { color: var(--ctp-red); } /* Generic Error */

hr {
    border: none;
    border-top: 2px solid var(--ctp-surface1);
    margin: 20px 0;
    opacity: 0.5;
}

/* Links styling */
a {
    color: var(--ctp-blue);
    text-decoration: none;
    border-bottom: 1px dotted var(--ctp-blue);
    transition: all 0.2s ease;
}

a:hover {
    color: var(--ctp-sky);
    border-bottom-color: var(--ctp-sky);
}

/* Lists styling */
ul, ol {
    color: var(--ctp-text);
    padding-left: 25px;
    margin: 15px 0;
}

li {
    margin: 8px 0;
    color: var(--ctp-subtext1);
}

/* Strong and emphasis */
strong, b {
    color: var(--ctp-lavender);
    font-weight: 600;
}

em, i {
    color: var(--ctp-yellow);
    font-style: italic;
}

/* Blockquotes */
blockquote {
    border-left: 4px solid var(--ctp-mauve);
    padding-left: 20px;
    margin: 20px 0;
    color: var(--ctp-subtext0);
    font-style: italic;
    background-color: var(--ctp-mantle);
    padding: 15px 20px;
    border-radius: 0 8px 8px 0;
}

/* Tables */
table {
    border-collapse: collapse;
    width: 100%;
    margin: 20px 0;
}

th {
    background-color: var(--ctp-surface0);
    color: var(--ctp-lavender);
    padding: 12px;
    text-align: left;
    font-weight: 600;
    border: 1px solid var(--ctp-surface1);
}

td {
    padding: 10px;
    border: 1px solid var(--ctp-surface1);
    color: var(--ctp-text);
}

tr:nth-child(even) {
    background-color: var(--ctp-mantle);
}

/* Ensure good contrast for all text */
* {
    text-shadow: none !important;
}

/* Mobile responsiveness */
@media (max-width: 600px) {
    .card {
        padding: 15px;
        font-size: 16px;
    }
    
    .question {
        font-size: 18px;
    }
    
    .answer {
        font-size: 16px;
    }
}
'''

MCQ_CSS = BASE_CSS + '''
.options {
    margin: 20px 0;
}

.option {
    display: flex;
    align-items: flex-start;
    padding: 12px 15px;
    margin: 8px 0;
    background-color: var(--ctp-mantle);
    border: 2px solid var(--ctp-surface1);
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.option:hover {
    border-color: var(--ctp-lavender);
    background-color: var(--ctp-surface0);
}

.option-letter {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    background: var(--ctp-surface1);
    color: var(--ctp-text);
    border-radius: 50%;
    font-weight: 700;
    margin-right: 12px;
    flex-shrink: 0;
}

/* Correct answer styling when revealed */
.answer-revealed .option[data-option="A"]:has(+ .correct-answer-badge:contains("A")),
.option.correct {
    background-color: var(--ctp-green);
    border-color: var(--ctp-green);
    color: var(--ctp-crust);
}

.correct-answer-badge {
    display: inline-block;
    background: linear-gradient(135deg, var(--ctp-green), var(--ctp-teal));
    color: var(--ctp-crust);
    padding: 10px 20px;
    border-radius: 8px;
    font-weight: 700;
    font-size: 16px;
    margin: 15px 0;
}

.explanation {
    font-size: 17px;
    color: var(--ctp-subtext1);
    margin: 20px 0;
    padding: 15px;
    background-color: var(--ctp-mantle);
    border-radius: 10px;
    border-left: 4px solid var(--ctp-teal);
    line-height: 1.8;
}

hr {
    border: none;
    border-top: 2px solid var(--ctp-surface1);
    margin: 20px 0;
    opacity: 0.5;
}

code {
    background-color: var(--ctp-surface0);
    color: var(--ctp-pink);
    padding: 3px 6px;
    border-radius: 4px;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 15px;
}

pre {
    background-color: var(--ctp-crust);
    border: 1px solid var(--ctp-surface0);
    padding: 16px;
    border-radius: 8px;
    overflow-x: auto;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 15px;
}
'''
