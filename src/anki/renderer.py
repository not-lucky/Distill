
import re
import bleach
import markdown

def render_markdown(markdown_text: str) -> str:
    """
    Convert markdown text to HTML using the markdown library.
    
    Args:
        markdown_text: Markdown text
        
    Returns:
        HTML formatted text
    """
    if not markdown_text:
        return ""

    # Fix double-escaped newlines inside code blocks only using regex split
    # This splits by code blocks (capturing the delimiters so we keep them)
    text_parts = re.split(r'(```.*?```)', markdown_text, flags=re.DOTALL)
    for part_index in range(len(text_parts)):
        # If it starts and ends with ```, it's a code block
        if text_parts[part_index].startswith('```') and text_parts[part_index].endswith('```'):
            text_parts[part_index] = text_parts[part_index].replace('\\n', '\n')
    
    processed_text = "".join(text_parts)
        
    # Configure extensions
    html_content = markdown.markdown(
        processed_text,
        extensions=['fenced_code', 'codehilite', 'tables', 'nl2br', 'sane_lists'],
        extension_configs={
            'codehilite': {
                'css_class': 'highlight',
                'linenums': False,
                'use_pygments': True,
                'noclasses': False
            }
        }
    )
    
    # Sanitize HTML to escape invalid tags (like <target) while preserving valid ones
    allowed_html_tags = [
        'a', 'b', 'blockquote', 'br', 'code', 'div', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
        'hr', 'i', 'li', 'ol', 'p', 'pre', 'span', 'strong', 'table', 'tbody', 'td', 'th', 
        'thead', 'tr', 'ul'
    ]
    allowed_html_attributes = {
        '*': ['class'],
        'a': ['href', 'title', 'target'],
        'img': ['src', 'alt', 'title'],
    }
    
    sanitized_html = bleach.clean(
        html_content, 
        tags=allowed_html_tags, 
        attributes=allowed_html_attributes, 
        strip=False
    )
    
    return sanitized_html
