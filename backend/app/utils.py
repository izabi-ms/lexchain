import html

def sanitize_input(text: str) -> str:
    if text is None:
        return ""
    return html.escape(text)