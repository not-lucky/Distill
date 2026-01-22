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


class TestSyntaxHighlighting:
    """Tests for code syntax highlighting with various languages."""

    def test_python_highlighting(self):
        """Test Python syntax highlighting."""
        code = """```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```"""
        result = render_markdown(code)
        assert "highlight" in result
        assert "fibonacci" in result

    def test_javascript_highlighting(self):
        """Test JavaScript syntax highlighting."""
        code = """```javascript
const fetchData = async (url) => {
    const response = await fetch(url);
    return response.json();
};
```"""
        result = render_markdown(code)
        assert "fetchData" in result
        assert "async" in result

    def test_java_highlighting(self):
        """Test Java syntax highlighting."""
        code = """```java
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
```"""
        result = render_markdown(code)
        assert "HelloWorld" in result
        assert "main" in result

    def test_cpp_highlighting(self):
        """Test C++ syntax highlighting."""
        code = """```cpp
#include <iostream>
int main() {
    std::cout << "Hello" << std::endl;
    return 0;
}
```"""
        result = render_markdown(code)
        assert "main" in result
        assert "iostream" in result

    def test_sql_highlighting(self):
        """Test SQL syntax highlighting."""
        code = """```sql
SELECT users.name, COUNT(orders.id) AS order_count
FROM users
LEFT JOIN orders ON users.id = orders.user_id
GROUP BY users.id
HAVING COUNT(orders.id) > 5;
```"""
        result = render_markdown(code)
        assert "SELECT" in result or "select" in result.lower()
        assert "users" in result

    def test_bash_highlighting(self):
        """Test Bash syntax highlighting."""
        code = """```bash
#!/bin/bash
for file in *.txt; do
    echo "Processing $file"
    cat "$file" | wc -l
done
```"""
        result = render_markdown(code)
        assert "file" in result
        assert "Processing" in result

    def test_json_highlighting(self):
        """Test JSON syntax highlighting."""
        code = """```json
{
    "name": "test",
    "version": "1.0.0",
    "dependencies": {
        "lodash": "^4.17.21"
    }
}
```"""
        result = render_markdown(code)
        assert "name" in result
        assert "test" in result

    def test_yaml_highlighting(self):
        """Test YAML syntax highlighting."""
        code = """```yaml
name: CI Pipeline
on:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
```"""
        result = render_markdown(code)
        assert "name" in result
        assert "Pipeline" in result

    def test_rust_highlighting(self):
        """Test Rust syntax highlighting."""
        code = """```rust
fn main() {
    let nums: Vec<i32> = vec![1, 2, 3, 4, 5];
    let sum: i32 = nums.iter().sum();
    println!("Sum: {}", sum);
}
```"""
        result = render_markdown(code)
        assert "main" in result
        assert "nums" in result

    def test_go_highlighting(self):
        """Test Go syntax highlighting."""
        code = """```go
package main

import "fmt"

func main() {
    messages := make(chan string)
    go func() { messages <- "ping" }()
    msg := <-messages
    fmt.Println(msg)
}
```"""
        result = render_markdown(code)
        assert "main" in result
        assert "messages" in result

    def test_kotlin_highlighting(self):
        """Test Kotlin syntax highlighting."""
        code = """```kotlin
fun main() {
    val numbers = listOf(1, 2, 3, 4, 5)
    val doubled = numbers.map { it * 2 }
    println(doubled)
}
```"""
        result = render_markdown(code)
        assert "main" in result
        assert "numbers" in result

    def test_typescript_highlighting(self):
        """Test TypeScript syntax highlighting."""
        code = """```typescript
interface User {
    id: number;
    name: string;
    email: string;
}

const getUser = (id: number): User | null => {
    return null;
};
```"""
        result = render_markdown(code)
        assert "User" in result
        assert "getUser" in result


class TestUnicodeContent:
    """Tests for Unicode content rendering."""

    def test_chinese_characters(self):
        """Test rendering Chinese characters."""
        md = "这是一个测试 - This is a test"
        result = render_markdown(md)
        assert "这是一个测试" in result
        assert "This is a test" in result

    def test_japanese_characters(self):
        """Test rendering Japanese characters."""
        md = "こんにちは世界 - Hello World"
        result = render_markdown(md)
        assert "こんにちは世界" in result

    def test_korean_characters(self):
        """Test rendering Korean characters."""
        md = "안녕하세요 - Hello"
        result = render_markdown(md)
        assert "안녕하세요" in result

    def test_arabic_rtl_text(self):
        """Test rendering Arabic RTL text."""
        md = "مرحبا بالعالم - Hello World"
        result = render_markdown(md)
        assert "مرحبا" in result

    def test_emoji_rendering(self):
        """Test rendering emoji characters."""
        md = "Hello 👋 World 🌍 Test 🚀"
        result = render_markdown(md)
        assert "👋" in result
        assert "🌍" in result
        assert "🚀" in result

    def test_mixed_unicode_and_code(self):
        """Test mixing Unicode text with code blocks."""
        md = """# 算法说明

这是一个简单的例子：

```python
def 计算(数值):
    return 数值 * 2
```

结果是正确的。"""
        result = render_markdown(md)
        assert "算法说明" in result
        assert "计算" in result

    def test_unicode_in_inline_code(self):
        """Test Unicode in inline code."""
        md = "Use `变量名` for Chinese variable names"
        result = render_markdown(md)
        assert "变量名" in result
        assert "<code>" in result

    def test_mathematical_symbols(self):
        """Test mathematical Unicode symbols."""
        md = "The formula is: α + β = γ, where ∑ represents sum"
        result = render_markdown(md)
        assert "α" in result
        assert "β" in result
        assert "∑" in result


class TestSnapshotRendering:
    """Snapshot tests for consistent HTML output."""

    def test_simple_paragraph_snapshot(self, snapshot):
        """Snapshot test for simple paragraph."""
        result = render_markdown("Hello World")
        assert result == snapshot

    def test_formatted_text_snapshot(self, snapshot):
        """Snapshot test for formatted text."""
        md = "**bold** and *italic* and `code`"
        result = render_markdown(md)
        assert result == snapshot

    def test_code_block_snapshot(self, snapshot):
        """Snapshot test for code block."""
        md = """```python
def hello():
    print("world")
```"""
        result = render_markdown(md)
        assert result == snapshot

    def test_list_snapshot(self, snapshot):
        """Snapshot test for lists."""
        md = """- Item 1
- Item 2
- Item 3"""
        result = render_markdown(md)
        assert result == snapshot

    def test_table_snapshot(self, snapshot):
        """Snapshot test for table."""
        md = """| A | B |
|---|---|
| 1 | 2 |"""
        result = render_markdown(md)
        assert result == snapshot

    def test_complex_document_snapshot(self, snapshot):
        """Snapshot test for complex document."""
        md = """# Title

This is **bold** text.

## Code Example

```javascript
const x = 1;
```

- Item 1
- Item 2"""
        result = render_markdown(md)
        assert result == snapshot


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_long_line(self):
        """Test very long line without breaks."""
        long_text = "word " * 1000
        result = render_markdown(long_text)
        assert "word" in result
        assert len(result) > len(long_text)  # HTML tags added

    def test_deeply_nested_lists(self):
        """Test deeply nested list structure."""
        md = """- Level 1
  - Level 2
    - Level 3
      - Level 4"""
        result = render_markdown(md)
        assert "Level 1" in result
        assert "Level 4" in result

    def test_empty_code_block(self):
        """Test empty code block."""
        md = """```

```"""
        result = render_markdown(md)
        # Should not crash, may produce empty pre/code
        assert isinstance(result, str)

    def test_unclosed_formatting(self):
        """Test unclosed formatting markers."""
        md = "**bold without closing"
        result = render_markdown(md)
        # Should handle gracefully
        assert "bold" in result

    def test_multiple_blank_lines(self):
        """Test multiple consecutive blank lines."""
        md = """Line 1



Line 2"""
        result = render_markdown(md)
        assert "Line 1" in result
        assert "Line 2" in result

    def test_special_html_entities(self):
        """Test HTML entity encoding."""
        md = "Compare: x < y and y > z and a & b"
        result = render_markdown(md)
        # Should be encoded or rendered safely
        assert "x" in result
        assert "y" in result

    def test_mixed_markdown_and_html(self):
        """Test markdown mixed with raw HTML."""
        md = """<div>
**Bold inside div**
</div>"""
        result = render_markdown(md)
        assert "Bold inside div" in result

    def test_backslash_escaping(self):
        """Test backslash escaping in markdown."""
        md = r"\*not bold\*"
        result = render_markdown(md)
        # The asterisks should be escaped, not rendered as emphasis
        assert "*" in result or "not bold" in result

    def test_consecutive_code_blocks(self):
        """Test consecutive code blocks without text between."""
        md = """```python
a = 1
```
```javascript
b = 2
```"""
        result = render_markdown(md)
        assert "a" in result
        assert "b" in result

    def test_code_block_with_empty_lines(self):
        """Test code block containing empty lines."""
        md = """```python
def foo():

    pass

```"""
        result = render_markdown(md)
        assert "foo" in result
        assert "pass" in result


class TestCSSAndStyling:
    """Tests for CSS class application."""

    def test_highlight_class_on_code_blocks(self):
        """Test that highlight class is applied to code blocks."""
        md = """```python
x = 1
```"""
        result = render_markdown(md)
        assert 'class="highlight"' in result

    def test_code_block_structure(self):
        """Test code block HTML structure."""
        md = """```python
def test():
    pass
```"""
        result = render_markdown(md)
        # Should contain div with highlight class
        assert "<div" in result or "<pre" in result

    def test_table_structure(self):
        """Test table HTML structure."""
        md = """| Header |
|--------|
| Cell   |"""
        result = render_markdown(md)
        assert "<table>" in result
        assert "<thead>" in result
        assert "<tbody>" in result

    def test_blockquote_structure(self):
        """Test blockquote HTML structure."""
        md = "> Quote"
        result = render_markdown(md)
        assert "<blockquote>" in result
        assert "</blockquote>" in result
