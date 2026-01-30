"""
Canvas renderer for converting canvas elements to HTML/SVG.
"""

import json
from typing import Dict, Any
from .canvas import Canvas, CanvasElement, CanvasType


class CanvasRenderer:
    """Renders canvas elements to various formats."""
    
    def __init__(self, canvas: Canvas):
        self.canvas = canvas
        
    def to_html(self) -> str:
        """Render canvas to HTML."""
        elements_html = []
        
        for element in self.canvas.elements.values():
            elem_html = self._render_element(element)
            elements_html.append(f'''
                <div class="canvas-element" id="elem-{element.id}" 
                     style="position: absolute; left: {element.position.get('x', 0)}px; 
                            top: {element.position.get('y', 0)}px;
                            width: {element.size.get('width', 'auto')}px;
                            {self._style_to_css(element.style)}">
                    {elem_html}
                </div>
            ''')
            
        return f'''
<!DOCTYPE html>
<html>
<head>
    <title>TWIZZY Canvas - {self.canvas.id}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 20px; background: #1a1a2e; color: #fff; }}
        .canvas {{ position: relative; min-height: 100vh; }}
        .canvas-element {{ background: #16213e; border-radius: 8px; padding: 16px; margin: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }}
        .canvas-title {{ font-size: 14px; font-weight: 600; color: #0f3460; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .canvas-text {{ line-height: 1.6; }}
        .canvas-code {{ background: #0f0f23; padding: 12px; border-radius: 4px; font-family: 'Monaco', monospace; font-size: 13px; overflow-x: auto; }}
        .canvas-table {{ width: 100%; border-collapse: collapse; }}
        .canvas-table th, .canvas-table td {{ padding: 8px; text-align: left; border-bottom: 1px solid #0f3460; }}
        .canvas-table th {{ color: #e94560; }}
        .canvas-card {{ border-left: 3px solid #e94560; padding-left: 12px; }}
        .canvas-list {{ padding-left: 20px; }}
        .canvas-list li {{ margin: 4px 0; }}
        .canvas-image {{ max-width: 100%; border-radius: 4px; }}
        .canvas-form {{ display: flex; flex-direction: column; gap: 12px; }}
        .canvas-form input, .canvas-form textarea, .canvas-form select {{ 
            padding: 8px; border: 1px solid #0f3460; border-radius: 4px; background: #0f0f23; color: #fff; 
        }}
        .canvas-form button {{ 
            padding: 10px 20px; background: #e94560; color: #fff; border: none; 
            border-radius: 4px; cursor: pointer; font-weight: 600; 
        }}
        .canvas-form button:hover {{ background: #ff6b6b; }}
    </style>
</head>
<body>
    <div class="canvas" id="canvas-{self.canvas.id}">
        <h1>TWIZZY Canvas</h1>
        {''.join(elements_html)}
    </div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        // Initialize any charts
        {self._get_chart_scripts()}
    </script>
</body>
</html>
        '''
        
    def _render_element(self, element: CanvasElement) -> str:
        """Render a single element to HTML."""
        title_html = f'<div class="canvas-title">{element.title}</div>' if element.title else ''
        
        if element.type == CanvasType.TEXT:
            return f'{title_html}<div class="canvas-text">{self._escape_html(element.content)}</div>'
            
        elif element.type == CanvasType.MARKDOWN:
            # Simple markdown to HTML conversion
            content = self._markdown_to_html(element.content)
            return f'{title_html}<div class="canvas-markdown">{content}</div>'
            
        elif element.type == CanvasType.CODE:
            code = element.content.get('code', '')
            lang = element.content.get('language', 'python')
            return f'{title_html}<div class="canvas-code"><code class="language-{lang}">{self._escape_html(code)}</code></div>'
            
        elif element.type == CanvasType.IMAGE:
            url = element.content.get('url', '')
            alt = element.content.get('alt', '')
            return f'{title_html}<img class="canvas-image" src="{url}" alt="{alt}">'
            
        elif element.type == CanvasType.TABLE:
            headers = element.content.get('headers', [])
            rows = element.content.get('rows', [])
            
            header_html = ''.join(f'<th>{h}</th>' for h in headers)
            rows_html = ''.join(
                f'<tr>{"".join(f"<td>{cell}</td>" for cell in row)}</tr>'
                for row in rows
            )
            
            return f'''
{title_html}
<table class="canvas-table">
    <thead><tr>{header_html}</tr></thead>
    <tbody>{rows_html}</tbody>
</table>
            '''
            
        elif element.type == CanvasType.CARD:
            card_title = element.content.get('title', '')
            body = element.content.get('body', '')
            return f'''
{title_html}
<div class="canvas-card">
    <h3>{card_title}</h3>
    <p>{body}</p>
</div>
            '''
            
        elif element.type == CanvasType.LIST:
            items = element.content.get('items', [])
            ordered = element.content.get('ordered', False)
            items_html = ''.join(f'<li>{self._escape_html(item)}</li>' for item in items)
            tag = 'ol' if ordered else 'ul'
            return f'{title_html}<{tag} class="canvas-list">{items_html}</{tag}>'
            
        elif element.type == CanvasType.CHART:
            chart_type = element.content.get('type', 'bar')
            data = element.content.get('data', {})
            chart_id = f"chart-{element.id}"
            
            return f'''
{title_html}
<canvas id="{chart_id}"></canvas>
<script>
    new Chart(document.getElementById('{chart_id}'), {{
        type: '{chart_type}',
        data: {json.dumps(data)}
    }});
</script>
            '''
            
        elif element.type == CanvasType.FORM:
            fields = element.content.get('fields', [])
            submit_label = element.content.get('submit_label', 'Submit')
            
            fields_html = ''
            for field in fields:
                field_type = field.get('type', 'text')
                name = field.get('name', '')
                label = field.get('label', name)
                required = 'required' if field.get('required') else ''
                
                if field_type == 'textarea':
                    input_html = f'<textarea name="{name}" {required}></textarea>'
                elif field_type == 'select':
                    options = field.get('options', [])
                    options_html = ''.join(f'<option value="{opt}">{opt}</option>' for opt in options)
                    input_html = f'<select name="{name}" {required}>{options_html}</select>'
                else:
                    input_html = f'<input type="{field_type}" name="{name}" {required}>'
                    
                fields_html += f'''
                    <label>
                        {label}
                        {input_html}
                    </label>
                '''
                
            return f'''
{title_html}
<form class="canvas-form" onsubmit="event.preventDefault(); alert('Form submitted!');">
    {fields_html}
    <button type="submit">{submit_label}</button>
</form>
            '''
            
        else:
            return f'{title_html}<div>{self._escape_html(str(element.content))}</div>'
            
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;'))
                
    def _markdown_to_html(self, markdown: str) -> str:
        """Simple markdown to HTML conversion."""
        import re
        
        # Headers
        markdown = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', markdown, flags=re.MULTILINE)
        markdown = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', markdown, flags=re.MULTILINE)
        markdown = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', markdown, flags=re.MULTILINE)
        
        # Bold and italic
        markdown = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', markdown)
        markdown = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', markdown)
        markdown = re.sub(r'\*(.*?)\*', r'<em>\1</em>', markdown)
        
        # Code
        markdown = re.sub(r'`(.*?)`', r'<code>\1</code>', markdown)
        
        # Links
        markdown = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', markdown)
        
        # Paragraphs
        paragraphs = markdown.split('\n\n')
        paragraphs = [f'<p>{p}</p>' if not p.startswith('<') else p for p in paragraphs]
        
        return '\n\n'.join(paragraphs)
        
    def _style_to_css(self, style: Dict[str, str]) -> str:
        """Convert style dict to CSS string."""
        if not style:
            return ''
        return '; '.join(f'{k}: {v}' for k, v in style.items()) + ';'
        
    def _get_chart_scripts(self) -> str:
        """Get JavaScript for initializing charts."""
        scripts = []
        for element in self.canvas.elements.values():
            if element.type == CanvasType.CHART:
                chart_type = element.content.get('type', 'bar')
                data = element.content.get('data', {})
                chart_id = f"chart-{element.id}"
                scripts.append(f'''
                    new Chart(document.getElementById('{chart_id}'), {{
                        type: '{chart_type}',
                        data: {json.dumps(data)},
                        options: {{ responsive: true, maintainAspectRatio: false }}
                    }});
                ''')
        return '\n'.join(scripts)
        
    def to_json(self) -> str:
        """Export canvas as JSON."""
        return self.canvas.to_json()
