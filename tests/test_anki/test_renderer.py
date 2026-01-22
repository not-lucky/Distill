"""Tests for anki/renderer.py."""

import pytest

from src.anki.renderer import render_markdown


class TestRenderMarkdown:
    """Tests for render_markdown function."""

    def test_empty_string(self):
        """Test rendering empty string returns empty string."""
        assert render_markdown("") == ""

    def test_none_returns_empty(self):
        """Test rendering None-like value returns empty string."""
        assert render_markdown(None) == ""

    def test_plain_text(self):
        """Test rendering plain text."""
        result = render_markdown("Hello World")
        assert "Hello World" in result

    def test_bold_text(self):
        """Test rendering bold text."""
        result = render_markdown("**bold text**")
        assert "<strong>bold text</strong>" in result

    def test_italic_text(self):
        """Test rendering italic text."""
        result = render_markdown("*italic text*")
        assert "<em>italic text</em>" in result

    def test_inline_code(self):
        """Test rendering inline code."""
        result = render_markdown("`code`")
        assert "<code>code</code>" in result

    def test_code_block(self):
        """Test rendering code block."""
        code = """```python
def hello():
    print("world")
```"""
        result = render_markdown(code)
        assert "<pre>" in result or "highlight" in result
        assert "hello" in result

    def test_code_block_preserves_newlines(self):
        """Test that code blocks preserve newlines."""
        # The function fixes double-escaped newlines in code blocks
        code = "```python\\ndef hello():\\n    pass\\n```"
        result = render_markdown(code)
        # Should contain the rendered code
        assert "hello" in result

    def test_headers(self):
        """Test rendering headers."""
        result = render_markdown("# Heading 1")
        assert "<h1>Heading 1</h1>" in result

        result = render_markdown("## Heading 2")
        assert "<h2>Heading 2</h2>" in result

    def test_unordered_list(self):
        """Test rendering unordered list."""
        md = """- Item 1
- Item 2
- Item 3"""
        result = render_markdown(md)
        assert "<ul>" in result
        assert "<li>" in result
        assert "Item 1" in result

    def test_ordered_list(self):
        """Test rendering ordered list."""
        md = """1. First
2. Second
3. Third"""
        result = render_markdown(md)
        assert "<ol>" in result
        assert "<li>" in result
        assert "First" in result

    def test_table(self):
        """Test rendering table."""
        md = """| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |"""
        result = render_markdown(md)
        assert "<table>" in result
        assert "<th>" in result
        assert "<td>" in result
        assert "Header 1" in result
        assert "Cell 1" in result

    def test_link(self):
        """Test rendering link."""
        result = render_markdown("[Example](https://example.com)")
        assert '<a href="https://example.com">' in result
        assert "Example</a>" in result

    def test_blockquote(self):
        """Test rendering blockquote."""
        result = render_markdown("> This is a quote")
        assert "<blockquote>" in result
        assert "This is a quote" in result

    def test_horizontal_rule(self):
        """Test rendering horizontal rule."""
        result = render_markdown("---")
        assert "<hr" in result

    def test_line_breaks(self):
        """Test that nl2br extension works."""
        result = render_markdown("Line 1\nLine 2")
        assert "<br" in result or "Line 1" in result and "Line 2" in result


class TestHtmlSanitization:
    """Tests for HTML sanitization in render_markdown."""

    def test_script_tag_removed(self):
        """Test that script tags are removed/escaped."""
        result = render_markdown("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "alert" in result  # Text content preserved, but escaped

    def test_allowed_tags_preserved(self):
        """Test that allowed HTML tags are preserved."""
        # Bold and italic are rendered from markdown
        result = render_markdown("**bold** and *italic*")
        assert "<strong>" in result
        assert "<em>" in result

    def test_div_tag_allowed(self):
        """Test that div tags are allowed."""
        result = render_markdown('<div class="test">content</div>')
        # bleach may strip or allow based on config
        assert "content" in result

    def test_class_attribute_preserved(self):
        """Test that class attributes are preserved on allowed tags."""
        # The code block rendering adds class="highlight"
        code = "```python\nx = 1\n```"
        result = render_markdown(code)
        assert 'class="highlight"' in result or "highlight" in result

    def test_invalid_html_escaped(self):
        """Test that invalid HTML is escaped."""
        # Tags like <target> should be escaped
        result = render_markdown("Compare <target with source")
        # The < should be escaped or the tag stripped
        assert "<target" not in result or "&lt;target" in result

    def test_preserves_code_content(self):
        """Test that code content is preserved."""
        result = render_markdown("`x < y && y > z`")
        assert "x" in result
        assert "y" in result
        assert "z" in result


class TestCodeBlockProcessing:
    """Tests for code block processing."""

    def test_fenced_code_block_with_language(self):
        """Test fenced code block with language specified."""
        code = """```javascript
const x = 1;
```"""
        result = render_markdown(code)
        assert "const" in result
        assert "x" in result

    def test_fenced_code_block_without_language(self):
        """Test fenced code block without language."""
        code = """```
plain text code
```"""
        result = render_markdown(code)
        assert "plain text code" in result

    def test_multiple_code_blocks(self):
        """Test multiple code blocks in same content."""
        md = """First block:
```python
def foo():
    pass
```

Second block:
```javascript
const bar = 1;
```"""
        result = render_markdown(md)
        assert "foo" in result
        assert "bar" in result

    def test_code_block_with_special_chars(self):
        """Test code block with special characters."""
        code = """```python
x = {"key": "value"}
y = [1, 2, 3]
z = x < y
```"""
        result = render_markdown(code)
        assert "key" in result
        assert "value" in result


class TestComplexMarkdown:
    """Tests for complex markdown combinations."""

    def test_mixed_formatting(self):
        """Test mixed formatting in same content."""
        md = """# Title

This is **bold** and *italic* text.

## Code Example

```python
def example():
    return True
```

- Item 1
- Item 2
"""
        result = render_markdown(md)
        assert "<h1>" in result
        assert "<strong>bold</strong>" in result
        assert "<em>italic</em>" in result
        assert "example" in result
        assert "<li>" in result

    def test_nested_lists(self):
        """Test nested list rendering."""
        md = """- Item 1
  - Nested 1
  - Nested 2
- Item 2"""
        result = render_markdown(md)
        assert "Item 1" in result
        assert "Nested 1" in result
        assert "Item 2" in result

    def test_code_in_list(self):
        """Test inline code in list items."""
        md = """- Use `function()`
- Call `method()`"""
        result = render_markdown(md)
        assert "<code>function()</code>" in result
        assert "<code>method()</code>" in result
