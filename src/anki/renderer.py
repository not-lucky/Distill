
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

    # Configure extensions
    html_content = markdown.markdown(
        markdown_text,
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
