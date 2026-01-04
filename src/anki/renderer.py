
import re
import bleach
import markdown

def render_markdown(text: str) -> str:
    """
    Convert markdown text to HTML using the markdown library.
    
    Args:
        text: Markdown text
        
    Returns:
        HTML formatted text
    """
    if not text:
        return ""

    # Fix double-escaped newlines inside code blocks only using regex split
    # This splits by code blocks (capturing the delimiters so we keep them)
    parts = re.split(r'(```.*?```)', text, flags=re.DOTALL)
    for i in range(len(parts)):
        # If it starts and ends with ```, it's a code block
        if parts[i].startswith('```') and parts[i].endswith('```'):
            parts[i] = parts[i].replace('\\n', '\n')
    
    text = "".join(parts)
        
    # Configure extensions
    html_content = markdown.markdown(
        text,
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
    allowed_tags = [
        'a', 'b', 'blockquote', 'br', 'code', 'div', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
        'hr', 'i', 'li', 'ol', 'p', 'pre', 'span', 'strong', 'table', 'tbody', 'td', 'th', 
        'thead', 'tr', 'ul'
    ]
    allowed_attrs = {
        '*': ['class', 'style'],
        'a': ['href', 'title', 'target'],
        'img': ['src', 'alt', 'title'],
    }
    
    clean_html = bleach.clean(
        html_content, 
        tags=allowed_tags, 
        attributes=allowed_attrs, 
        strip=False
    )
    
    return clean_html
