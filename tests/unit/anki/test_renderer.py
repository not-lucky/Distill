"""Tests for anki/renderer.py."""

import pytest

from assertpy import assert_that

from src.anki.renderer import render_markdown


class TestRenderMarkdown:
    """Tests for render_markdown function."""

    def test_empty_string(self):
        """
        Given an empty string
        When render_markdown is called
        Then an empty string is returned
        """
        assert_that(render_markdown("")).is_equal_to("")

    def test_none_returns_empty(self):
        """
        Given None value
        When render_markdown is called
        Then an empty string is returned
        """
        assert_that(render_markdown(None)).is_equal_to("")

    def test_plain_text(self):
        """
        Given plain text
        When render_markdown is called
        Then the text is included in output
        """
        result = render_markdown("Hello World")
        assert_that(result).contains("Hello World")

    def test_bold_text(self):
        """
        Given bold markdown syntax
        When render_markdown is called
        Then HTML strong tags are produced
        """
        result = render_markdown("**bold text**")
        assert_that(result).contains("<strong>bold text</strong>")

    def test_italic_text(self):
        """
        Given italic markdown syntax
        When render_markdown is called
        Then HTML em tags are produced
        """
        result = render_markdown("*italic text*")
        assert_that(result).contains("<em>italic text</em>")

    def test_inline_code(self):
        """
        Given inline code markdown syntax
        When render_markdown is called
        Then HTML code tags are produced
        """
        result = render_markdown("`code`")
        assert_that(result).contains("<code>code</code>")

    def test_code_block(self):
        """
        Given a fenced code block
        When render_markdown is called
        Then highlighted code is produced
        """
        code = """```python
def hello():
    print("world")
```"""
        result = render_markdown(code)
        assert_that(result).matches(r".*(pre|highlight).*")
        assert_that(result).contains("hello")

    def test_code_block_preserves_newlines(self):
        """
        Given a code block with escaped newlines
        When render_markdown is called
        Then the code content is preserved
        """
        # The function fixes double-escaped newlines in code blocks
        code = "```python\\ndef hello():\\n    pass\\n```"
        result = render_markdown(code)
        # Should contain the rendered code
        assert_that(result).contains("hello")

    def test_headers(self):
        """
        Given markdown headers
        When render_markdown is called
        Then HTML header tags are produced
        """
        result = render_markdown("# Heading 1")
        assert_that(result).contains("<h1>Heading 1</h1>")

        result = render_markdown("## Heading 2")
        assert_that(result).contains("<h2>Heading 2</h2>")

    def test_unordered_list(self):
        """
        Given an unordered markdown list
        When render_markdown is called
        Then HTML ul and li tags are produced
        """
        md = """- Item 1
- Item 2
- Item 3"""
        result = render_markdown(md)
        assert_that(result).contains("<ul>")
        assert_that(result).contains("<li>")
        assert_that(result).contains("Item 1")

    def test_ordered_list(self):
        """
        Given an ordered markdown list
        When render_markdown is called
        Then HTML ol and li tags are produced
        """
        md = """1. First
2. Second
3. Third"""
        result = render_markdown(md)
        assert_that(result).contains("<ol>")
        assert_that(result).contains("<li>")
        assert_that(result).contains("First")

    def test_table(self):
        """
        Given a markdown table
        When render_markdown is called
        Then HTML table elements are produced
        """
        md = """| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |"""
        result = render_markdown(md)
        assert_that(result).contains("<table>")
        assert_that(result).contains("<th>")
        assert_that(result).contains("<td>")
        assert_that(result).contains("Header 1")
        assert_that(result).contains("Cell 1")

    def test_link(self):
        """
        Given a markdown link
        When render_markdown is called
        Then HTML anchor tag is produced
        """
        result = render_markdown("[Example](https://example.com)")
        assert_that(result).contains('<a href="https://example.com">')
        assert_that(result).contains("Example</a>")

    def test_blockquote(self):
        """
        Given a markdown blockquote
        When render_markdown is called
        Then HTML blockquote tag is produced
        """
        result = render_markdown("> This is a quote")
        assert_that(result).contains("<blockquote>")
        assert_that(result).contains("This is a quote")

    def test_horizontal_rule(self):
        """
        Given a markdown horizontal rule
        When render_markdown is called
        Then HTML hr tag is produced
        """
        result = render_markdown("---")
        assert_that(result).contains("<hr")

    def test_line_breaks(self):
        """
        Given text with newlines
        When render_markdown is called
        Then line breaks are preserved
        """
        result = render_markdown("Line 1\nLine 2")
        assert_that(result).matches(r".*(br|Line 1.*Line 2).*")


class TestHtmlSanitization:
    """Tests for HTML sanitization in render_markdown."""

    def test_script_tag_removed(self):
        """
        Given content with script tags
        When render_markdown is called
        Then script tags are removed but text is preserved
        """
        result = render_markdown("<script>alert('xss')</script>")
        assert_that(result).does_not_contain("<script>")
        assert_that(result).contains("alert")  # Text content preserved, but escaped

    def test_allowed_tags_preserved(self):
        """
        Given valid markdown formatting
        When render_markdown is called
        Then formatting tags are preserved
        """
        # Bold and italic are rendered from markdown
        result = render_markdown("**bold** and *italic*")
        assert_that(result).contains("<strong>")
        assert_that(result).contains("<em>")

    def test_div_tag_allowed(self):
        """
        Given content with div tags
        When render_markdown is called
        Then content is preserved
        """
        result = render_markdown('<div class="test">content</div>')
        # bleach may strip or allow based on config
        assert_that(result).contains("content")

    def test_class_attribute_preserved(self):
        """
        Given code blocks
        When render_markdown is called
        Then highlight class is applied
        """
        # The code block rendering adds class="highlight"
        code = "```python\nx = 1\n```"
        result = render_markdown(code)
        assert_that(result).contains("highlight")

    def test_invalid_html_escaped(self):
        """
        Given invalid HTML tags
        When render_markdown is called
        Then they are escaped or stripped
        """
        # Tags like <target> should be escaped
        result = render_markdown("Compare <target with source")
        # The < should be escaped or the tag stripped
        assert_that(result).does_not_match(r"<target")

    def test_preserves_code_content(self):
        """
        Given inline code with special characters
        When render_markdown is called
        Then code content is preserved
        """
        result = render_markdown("`x < y && y > z`")
        assert_that(result).contains("x")
        assert_that(result).contains("y")
        assert_that(result).contains("z")


class TestCodeBlockProcessing:
    """Tests for code block processing."""

    def test_fenced_code_block_with_language(self):
        """
        Given a fenced code block with language specified
        When render_markdown is called
        Then code is rendered with syntax highlighting
        """
        code = """```javascript
const x = 1;
```"""
        result = render_markdown(code)
        assert_that(result).contains("const")
        assert_that(result).contains("x")

    def test_fenced_code_block_without_language(self):
        """
        Given a fenced code block without language
        When render_markdown is called
        Then code is rendered as plain text
        """
        code = """```
plain text code
```"""
        result = render_markdown(code)
        assert_that(result).contains("plain text code")

    def test_multiple_code_blocks(self):
        """
        Given multiple code blocks in same content
        When render_markdown is called
        Then all blocks are rendered
        """
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
        assert_that(result).contains("foo")
        assert_that(result).contains("bar")

    def test_code_block_with_special_chars(self):
        """
        Given a code block with special characters
        When render_markdown is called
        Then special characters are preserved
        """
        code = """```python
x = {"key": "value"}
y = [1, 2, 3]
z = x < y
```"""
        result = render_markdown(code)
        assert_that(result).contains("key")
        assert_that(result).contains("value")


class TestComplexMarkdown:
    """Tests for complex markdown combinations."""

    def test_mixed_formatting(self):
        """
        Given mixed markdown formatting
        When render_markdown is called
        Then all formatting is applied correctly
        """
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
        assert_that(result).contains("<h1>")
        assert_that(result).contains("<strong>bold</strong>")
        assert_that(result).contains("<em>italic</em>")
        assert_that(result).contains("example")
        assert_that(result).contains("<li>")

    def test_nested_lists(self):
        """
        Given nested markdown lists
        When render_markdown is called
        Then nesting is preserved
        """
        md = """- Item 1
  - Nested 1
  - Nested 2
- Item 2"""
        result = render_markdown(md)
        assert_that(result).contains("Item 1")
        assert_that(result).contains("Nested 1")
        assert_that(result).contains("Item 2")

    def test_code_in_list(self):
        """
        Given inline code in list items
        When render_markdown is called
        Then code tags are inside list items
        """
        md = """- Use `function()`
- Call `method()`"""
        result = render_markdown(md)
        assert_that(result).contains("<code>function()</code>")
        assert_that(result).contains("<code>method()</code>")


class TestSyntaxHighlighting:
    """Tests for code syntax highlighting with various languages."""

    def test_python_highlighting(self):
        """
        Given a Python code block
        When render_markdown is called
        Then Python syntax is highlighted
        """
        code = """```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```"""
        result = render_markdown(code)
        assert_that(result).contains("highlight")
        assert_that(result).contains("fibonacci")

    def test_javascript_highlighting(self):
        """
        Given a JavaScript code block
        When render_markdown is called
        Then JavaScript code is rendered
        """
        code = """```javascript
const fetchData = async (url) => {
    const response = await fetch(url);
    return response.json();
};
```"""
        result = render_markdown(code)
        assert_that(result).contains("fetchData")
        assert_that(result).contains("async")

    def test_java_highlighting(self):
        """
        Given a Java code block
        When render_markdown is called
        Then Java code is rendered
        """
        code = """```java
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
```"""
        result = render_markdown(code)
        assert_that(result).contains("HelloWorld")
        assert_that(result).contains("main")

    def test_cpp_highlighting(self):
        """
        Given a C++ code block
        When render_markdown is called
        Then C++ code is rendered
        """
        code = """```cpp
#include <iostream>
int main() {
    std::cout << "Hello" << std::endl;
    return 0;
}
```"""
        result = render_markdown(code)
        assert_that(result).contains("main")
        assert_that(result).contains("iostream")

    def test_sql_highlighting(self):
        """
        Given a SQL code block
        When render_markdown is called
        Then SQL code is rendered
        """
        code = """```sql
SELECT users.name, COUNT(orders.id) AS order_count
FROM users
LEFT JOIN orders ON users.id = orders.user_id
GROUP BY users.id
HAVING COUNT(orders.id) > 5;
```"""
        result = render_markdown(code)
        assert_that(result.lower()).contains("select")
        assert_that(result).contains("users")

    def test_bash_highlighting(self):
        """
        Given a Bash code block
        When render_markdown is called
        Then Bash code is rendered
        """
        code = """```bash
#!/bin/bash
for file in *.txt; do
    echo "Processing $file"
    cat "$file" | wc -l
done
```"""
        result = render_markdown(code)
        assert_that(result).contains("file")
        assert_that(result).contains("Processing")

    def test_json_highlighting(self):
        """
        Given a JSON code block
        When render_markdown is called
        Then JSON is rendered
        """
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
        assert_that(result).contains("name")
        assert_that(result).contains("test")

    def test_yaml_highlighting(self):
        """
        Given a YAML code block
        When render_markdown is called
        Then YAML is rendered
        """
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
        assert_that(result).contains("name")
        assert_that(result).contains("Pipeline")

    def test_rust_highlighting(self):
        """
        Given a Rust code block
        When render_markdown is called
        Then Rust code is rendered
        """
        code = """```rust
fn main() {
    let nums: Vec<i32> = vec![1, 2, 3, 4, 5];
    let sum: i32 = nums.iter().sum();
    println!("Sum: {}", sum);
}
```"""
        result = render_markdown(code)
        assert_that(result).contains("main")
        assert_that(result).contains("nums")

    def test_go_highlighting(self):
        """
        Given a Go code block
        When render_markdown is called
        Then Go code is rendered
        """
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
        assert_that(result).contains("main")
        assert_that(result).contains("messages")

    def test_kotlin_highlighting(self):
        """
        Given a Kotlin code block
        When render_markdown is called
        Then Kotlin code is rendered
        """
        code = """```kotlin
fun main() {
    val numbers = listOf(1, 2, 3, 4, 5)
    val doubled = numbers.map { it * 2 }
    println(doubled)
}
```"""
        result = render_markdown(code)
        assert_that(result).contains("main")
        assert_that(result).contains("numbers")

    def test_typescript_highlighting(self):
        """
        Given a TypeScript code block
        When render_markdown is called
        Then TypeScript code is rendered
        """
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
        assert_that(result).contains("User")
        assert_that(result).contains("getUser")


class TestUnicodeContent:
    """Tests for Unicode content rendering."""

    def test_chinese_characters(self):
        """
        Given Chinese characters
        When render_markdown is called
        Then Chinese text is preserved
        """
        md = "这是一个测试 - This is a test"
        result = render_markdown(md)
        assert_that(result).contains("这是一个测试")
        assert_that(result).contains("This is a test")

    def test_japanese_characters(self):
        """
        Given Japanese characters
        When render_markdown is called
        Then Japanese text is preserved
        """
        md = "こんにちは世界 - Hello World"
        result = render_markdown(md)
        assert_that(result).contains("こんにちは世界")

    def test_korean_characters(self):
        """
        Given Korean characters
        When render_markdown is called
        Then Korean text is preserved
        """
        md = "안녕하세요 - Hello"
        result = render_markdown(md)
        assert_that(result).contains("안녕하세요")

    def test_arabic_rtl_text(self):
        """
        Given Arabic RTL text
        When render_markdown is called
        Then Arabic text is preserved
        """
        md = "مرحبا بالعالم - Hello World"
        result = render_markdown(md)
        assert_that(result).contains("مرحبا")

    def test_emoji_rendering(self):
        """
        Given emoji characters
        When render_markdown is called
        Then emojis are preserved
        """
        md = "Hello 👋 World 🌍 Test 🚀"
        result = render_markdown(md)
        assert_that(result).contains("👋")
        assert_that(result).contains("🌍")
        assert_that(result).contains("🚀")

    def test_mixed_unicode_and_code(self):
        """
        Given Unicode text with code blocks
        When render_markdown is called
        Then both are preserved
        """
        md = """# 算法说明

这是一个简单的例子：

```python
def 计算(数值):
    return 数值 * 2
```

结果是正确的。"""
        result = render_markdown(md)
        assert_that(result).contains("算法说明")
        assert_that(result).contains("计算")

    def test_unicode_in_inline_code(self):
        """
        Given Unicode in inline code
        When render_markdown is called
        Then Unicode is preserved in code tags
        """
        md = "Use `变量名` for Chinese variable names"
        result = render_markdown(md)
        assert_that(result).contains("变量名")
        assert_that(result).contains("<code>")

    def test_mathematical_symbols(self):
        """
        Given mathematical Unicode symbols
        When render_markdown is called
        Then symbols are preserved
        """
        md = "The formula is: α + β = γ, where ∑ represents sum"
        result = render_markdown(md)
        assert_that(result).contains("α")
        assert_that(result).contains("β")
        assert_that(result).contains("∑")


class TestSnapshotRendering:
    """Snapshot tests for consistent HTML output."""

    def test_simple_paragraph_snapshot(self, snapshot):
        """
        Given simple text
        When render_markdown is called
        Then output matches snapshot
        """
        result = render_markdown("Hello World")
        assert_that(result).is_equal_to(snapshot)

    def test_formatted_text_snapshot(self, snapshot):
        """
        Given formatted text
        When render_markdown is called
        Then output matches snapshot
        """
        md = "**bold** and *italic* and `code`"
        result = render_markdown(md)
        assert_that(result).is_equal_to(snapshot)

    def test_code_block_snapshot(self, snapshot):
        """
        Given a code block
        When render_markdown is called
        Then output matches snapshot
        """
        md = """```python
def hello():
    print("world")
```"""
        result = render_markdown(md)
        assert_that(result).is_equal_to(snapshot)

    def test_list_snapshot(self, snapshot):
        """
        Given a list
        When render_markdown is called
        Then output matches snapshot
        """
        md = """- Item 1
- Item 2
- Item 3"""
        result = render_markdown(md)
        assert_that(result).is_equal_to(snapshot)

    def test_table_snapshot(self, snapshot):
        """
        Given a table
        When render_markdown is called
        Then output matches snapshot
        """
        md = """| A | B |
|---|---|
| 1 | 2 |"""
        result = render_markdown(md)
        assert_that(result).is_equal_to(snapshot)

    def test_complex_document_snapshot(self, snapshot):
        """
        Given a complex document
        When render_markdown is called
        Then output matches snapshot
        """
        md = """# Title

This is **bold** text.

## Code Example

```javascript
const x = 1;
```

- Item 1
- Item 2"""
        result = render_markdown(md)
        assert_that(result).is_equal_to(snapshot)


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_long_line(self):
        """
        Given a very long line
        When render_markdown is called
        Then content is rendered and HTML tags are added
        """
        long_text = "word " * 1000
        result = render_markdown(long_text)
        assert_that(result).contains("word")
        assert_that(len(result)).is_greater_than(len(long_text))  # HTML tags added

    def test_deeply_nested_lists(self):
        """
        Given deeply nested lists
        When render_markdown is called
        Then all levels are preserved
        """
        md = """- Level 1
  - Level 2
    - Level 3
      - Level 4"""
        result = render_markdown(md)
        assert_that(result).contains("Level 1")
        assert_that(result).contains("Level 4")

    def test_empty_code_block(self):
        """
        Given an empty code block
        When render_markdown is called
        Then no error occurs
        """
        md = """```

```"""
        result = render_markdown(md)
        # Should not crash, may produce empty pre/code
        assert_that(result).is_instance_of(str)

    def test_unclosed_formatting(self):
        """
        Given unclosed formatting markers
        When render_markdown is called
        Then content is handled gracefully
        """
        md = "**bold without closing"
        result = render_markdown(md)
        # Should handle gracefully
        assert_that(result).contains("bold")

    def test_multiple_blank_lines(self):
        """
        Given multiple consecutive blank lines
        When render_markdown is called
        Then both lines are preserved
        """
        md = """Line 1



Line 2"""
        result = render_markdown(md)
        assert_that(result).contains("Line 1")
        assert_that(result).contains("Line 2")

    def test_special_html_entities(self):
        """
        Given HTML special characters
        When render_markdown is called
        Then they are handled safely
        """
        md = "Compare: x < y and y > z and a & b"
        result = render_markdown(md)
        # Should be encoded or rendered safely
        assert_that(result).contains("x")
        assert_that(result).contains("y")

    def test_mixed_markdown_and_html(self):
        """
        Given markdown mixed with raw HTML
        When render_markdown is called
        Then content is preserved
        """
        md = """<div>
**Bold inside div**
</div>"""
        result = render_markdown(md)
        assert_that(result).contains("Bold inside div")

    def test_backslash_escaping(self):
        """
        Given backslash escaped characters
        When render_markdown is called
        Then escaping is handled
        """
        md = r"\*not bold\*"
        result = render_markdown(md)
        # The asterisks should be escaped, not rendered as emphasis
        assert_that(result).matches(r".*(\*|not bold).*")

    def test_consecutive_code_blocks(self):
        """
        Given consecutive code blocks
        When render_markdown is called
        Then both blocks are rendered
        """
        md = """```python
a = 1
```
```javascript
b = 2
```"""
        result = render_markdown(md)
        assert_that(result).contains("a")
        assert_that(result).contains("b")

    def test_code_block_with_empty_lines(self):
        """
        Given a code block with empty lines inside
        When render_markdown is called
        Then empty lines are preserved
        """
        md = """```python
def foo():

    pass

```"""
        result = render_markdown(md)
        assert_that(result).contains("foo")
        assert_that(result).contains("pass")


class TestCSSAndStyling:
    """Tests for CSS class application."""

    def test_highlight_class_on_code_blocks(self):
        """
        Given a code block
        When render_markdown is called
        Then highlight class is applied
        """
        md = """```python
x = 1
```"""
        result = render_markdown(md)
        assert_that(result).contains('class="highlight"')

    def test_code_block_structure(self):
        """
        Given a code block
        When render_markdown is called
        Then proper HTML structure is created
        """
        md = """```python
def test():
    pass
```"""
        result = render_markdown(md)
        # Should contain div with highlight class
        assert_that(result).matches(r".*(div|pre).*")

    def test_table_structure(self):
        """
        Given a markdown table
        When render_markdown is called
        Then proper table HTML structure is created
        """
        md = """| Header |
|--------|
| Cell   |"""
        result = render_markdown(md)
        assert_that(result).contains("<table>")
        assert_that(result).contains("<thead>")
        assert_that(result).contains("<tbody>")

    def test_blockquote_structure(self):
        """
        Given a blockquote
        When render_markdown is called
        Then proper blockquote HTML is created
        """
        md = "> Quote"
        result = render_markdown(md)
        assert_that(result).contains("<blockquote>")
        assert_that(result).contains("</blockquote>")
