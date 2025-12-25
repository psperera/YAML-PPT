#!/usr/bin/env python3
"""
HyFlux PPT Generator Web Application
Flask-based web interface for creating and generating presentations
"""

import os
import sys
import re
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
import yaml
import tempfile
import shutil
from datetime import datetime
import requests

# Add current directory to path to import ppt_generator
# In Docker, ppt_generator.py will be copied to /app/
sys.path.insert(0, str(Path(__file__).parent))
try:
    from ppt_generator import HyFluxPPTGenerator
except ImportError:
    # Fallback: try relative path (for local development)
    sys.path.insert(0, str(Path(__file__).parent.parent / 'hyflux-ppt-automation' / 'scripts'))
    from ppt_generator import HyFluxPPTGenerator

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = '/app/uploads'
app.config['OUTPUT_FOLDER'] = '/app/output'

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Paths
TEMPLATE_PATH = Path('/app/ppt_templates/HyFlux_Template_-.pptx')
SAMPLE_YAML_PATH = Path('/app/input/sample_content_spec.yaml')


def find_template():
    """Find template file in various locations."""
    possible_paths = [
        TEMPLATE_PATH,
        Path('/app/ppt_templates/HyFlux_Template_-.pptx'),
        Path('/app/templates/HyFlux_Template_-.pptx'),  # Fallback
        Path('/app/hyflux-ppt-automation/templates/HyFlux_Template_-.pptx'),
        Path('templates/HyFlux_Template_-.pptx'),
        Path('../templates/HyFlux_Template_-.pptx'),
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    return None


@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/api/template', methods=['GET'])
def get_template():
    """Get the sample YAML template."""
    try:
        # Try multiple locations
        template_paths = [
            SAMPLE_YAML_PATH,
            Path('/app/hyflux-ppt-automation/input/sample_content_spec.yaml'),
            Path('hyflux-ppt-automation/input/sample_content_spec.yaml'),
            Path('input/sample_content_spec.yaml'),
        ]
        
        for path in template_paths:
            if path.exists():
                with open(path, 'r') as f:
                    content = f.read()
                return jsonify({
                    'success': True,
                    'content': content
                })
        
        # Return default template if file not found
        default_template = """# HyFlux Presentation Content Specification

presentation:
  title: "My Presentation"
  author: "Your Name"
  date: "2025-12-25"

slides:
  - type: title_white
    title: "My Presentation Title"
    subtitle: "Subtitle here"
  
  - type: divider
    title: "Section 1"
  
  - type: text_only
    title: "Content Slide"
    content: |
      Your content here
      • Point 1
      • Point 2
  
  - type: end_slide
    title: "Thank You"
    contact: "Contact information"
"""
        return jsonify({
            'success': True,
            'content': default_template
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def validate_yaml_strict(yaml_content):
    """Strict YAML→PPT validation according to HyFlux render-safe rules."""
    errors = []
    warnings = []
    lines = yaml_content.split('\n')
    patch_suggestions = []
    
    try:
        spec = yaml.safe_load(yaml_content)
        
        # Check top-level keys
        if not isinstance(spec, dict):
            errors.append("Line 1: YAML must be a dictionary/object")
            return {'errors': errors, 'warnings': warnings, 'valid': False, 'patch': ''}
        
        top_level_keys = set(spec.keys())
        required_keys = {'presentation', 'slides'}
        if not required_keys.issubset(top_level_keys):
            missing = required_keys - top_level_keys
            errors.append(f"Line 1: Missing required top-level keys: {', '.join(missing)}")
        if len(top_level_keys) > len(required_keys):
            extra = top_level_keys - required_keys
            errors.append(f"Line 1: Unexpected top-level keys: {', '.join(extra)}. Must be exactly 'presentation' and 'slides'.")
        
        # Check presentation section
        if 'presentation' in spec:
            if not isinstance(spec['presentation'], dict):
                errors.append("Line 2: 'presentation' must be a dictionary")
        
        # Check slides
        if 'slides' not in spec:
            errors.append("Missing 'slides' section")
            return {'errors': errors, 'warnings': warnings, 'valid': False, 'patch': ''}
        
        if not isinstance(spec['slides'], list):
            errors.append("'slides' must be a list")
            return {'errors': errors, 'warnings': warnings, 'valid': False, 'patch': ''}
        
        # Validate each slide
        valid_types = {
            'title_white', 'divider', 'text_only', 'two_column', 
            'three_column', 'quote', 'title_only', 'end_slide'
        }
        
        # Required fields per type
        required_fields = {
            'title_white': {'title', 'subtitle'},
            'divider': {'title'},
            'text_only': {'title', 'content'},
            'two_column': {'title', 'left_content', 'right_content'},
            'three_column': {'title', 'left_content', 'middle_content', 'right_content'},
            'quote': {'quote', 'attribution'},
            'title_only': {'title'},
            'end_slide': {'title'}  # end_slide MUST have title only
        }
        
        # Allowed fields per type (required + optional)
        allowed_fields = {
            'title_white': {'type', 'title', 'subtitle'},
            'divider': {'type', 'title'},
            'text_only': {'type', 'title', 'content'},
            'two_column': {'type', 'title', 'left_content', 'right_content'},
            'three_column': {'type', 'title', 'left_content', 'middle_content', 'right_content'},
            'quote': {'type', 'quote', 'attribution'},
            'title_only': {'type', 'title'},
            'end_slide': {'type', 'title'}  # end_slide: title ONLY, no content/contact
        }
        
        for i, slide in enumerate(spec['slides']):
            slide_num = i + 1
            line_num = None
            
            # Find line number for this slide
            for line_idx, line in enumerate(lines, 1):
                if f'- type: {slide.get("type", "")}' in line:
                    line_num = line_idx
                    break
                elif line.strip().startswith('-') and i == 0:
                    line_num = line_idx
                    break
            
            if not isinstance(slide, dict):
                errors.append(f"Slide {slide_num} (line ~{line_num or '?'}): must be an object")
                continue
            
            slide_type = slide.get('type', '')
            if not slide_type:
                errors.append(f"Slide {slide_num} (line ~{line_num or '?'}): missing 'type' field")
                continue
            
            if slide_type not in valid_types:
                errors.append(f"Slide {slide_num} (line ~{line_num or '?'}): invalid type '{slide_type}'. Must be one of: {', '.join(sorted(valid_types))}")
                continue
            
            # Check required fields
            required = required_fields.get(slide_type, set())
            slide_keys = set(slide.keys())
            missing = required - slide_keys
            if missing:
                errors.append(f"Slide {slide_num} (type: {slide_type}, line ~{line_num or '?'}): missing required fields: {', '.join(missing)}")
            
            # Check for forbidden fields (render-blocking)
            allowed = allowed_fields.get(slide_type, set())
            forbidden = slide_keys - allowed
            
            # Special handling for end_slide and title_only
            if slide_type == 'end_slide':
                if 'content' in slide or 'contact' in slide:
                    errors.append(f"Slide {slide_num} (end_slide, line ~{line_num or '?'}): MUST NOT contain 'content' or 'contact' - text will not render. Use 'title' only.")
                    patch_suggestions.append(f"Slide {slide_num}: Remove 'content'/'contact' from end_slide (only 'title' renders)")
            
            if slide_type == 'title_only':
                if 'content' in slide:
                    warnings.append(f"Slide {slide_num} (title_only, line ~{line_num or '?'}): 'content' field present but will not render. title_only is for title only.")
                    patch_suggestions.append(f"Slide {slide_num}: Remove 'content' from title_only or change to text_only")
            
            if slide_type == 'divider':
                if 'content' in slide:
                    warnings.append(f"Slide {slide_num} (divider, line ~{line_num or '?'}): 'content' field present but divider is title-only.")
                    patch_suggestions.append(f"Slide {slide_num}: Remove 'content' from divider or change to text_only")
            
            # Check for other unexpected fields
            if forbidden:
                # Filter out the special cases we already handled
                forbidden_filtered = forbidden - {'content', 'contact'}
                if forbidden_filtered:
                    warnings.append(f"Slide {slide_num} (type: {slide_type}, line ~{line_num or '?'}): unexpected fields (may not render): {', '.join(forbidden_filtered)}")
        
        # Check indentation (tabs are errors)
        for line_idx, line in enumerate(lines, 1):
            if '\t' in line:
                errors.append(f"Line {line_idx}: Tabs detected. Use 2 spaces for indentation.")
        
        # Check block scalar indentation
        in_block_scalar = False
        scalar_start_line = None
        for line_idx, line in enumerate(lines, 1):
            if '|' in line and ':' in line:
                in_block_scalar = True
                scalar_start_line = line_idx
                continue
            if in_block_scalar:
                if line.strip() and ':' in line and not line.strip().startswith('-') and not line.startswith(' '):
                    in_block_scalar = False
                elif in_block_scalar and line.strip():
                    # Check if content is properly indented (at least 2 spaces after the key)
                    if not (line.startswith('      ') or line.startswith('        ') or not line.strip()):
                        if line.startswith('    ') and ':' in lines[scalar_start_line-1]:
                            # This might be okay if it's the first content line
                            pass
                        else:
                            warnings.append(f"Line {line_idx}: Block scalar content may have incorrect indentation (should be 2+ spaces)")
        
        # Generate minimal patch if there are errors
        patch = ""
        if errors:
            patch = "Minimal patch suggestions:\n"
            for suggestion in patch_suggestions:
                patch += f"  - {suggestion}\n"
            if not patch_suggestions:
                patch += "  - Fix the errors listed above\n"
        
        valid = len(errors) == 0
        return {
            'valid': valid,
            'errors': errors,
            'warnings': warnings,
            'slide_count': len(spec.get('slides', [])),
            'patch': patch
        }
        
    except yaml.YAMLError as e:
        # Try to extract line number from error
        error_str = str(e)
        line_match = re.search(r'line (\d+)', error_str)
        line_num = line_match.group(1) if line_match else '?'
        errors.append(f"Line {line_num}: Invalid YAML syntax - {error_str}")
        return {'errors': errors, 'warnings': warnings, 'valid': False, 'patch': ''}
    except Exception as e:
        errors.append(f"Validation error: {str(e)}")
        return {'errors': errors, 'warnings': warnings, 'valid': False, 'patch': ''}


@app.route('/api/validate', methods=['POST'])
def validate_yaml():
    """Validate YAML content with strict rules."""
    try:
        data = request.json
        yaml_content = data.get('yaml', '')
        
        if not yaml_content:
            return jsonify({
                'success': False,
                'error': 'No YAML content provided'
            }), 400
        
        # Run strict validation
        result = validate_yaml_strict(yaml_content)
        
        if result['valid']:
            message = f"✓ PASS: Valid YAML with {result['slide_count']} slides"
            if result['warnings']:
                message += f"\n\n⚠️  Warnings ({len(result['warnings'])}):"
                for warning in result['warnings']:
                    message += f"\n  • {warning}"
            
            return jsonify({
                'success': True,
                'message': message,
                'warnings': result['warnings'],
                'slide_count': result['slide_count']
            })
        else:
            error_msg = "✗ FAIL: Validation errors found\n\n"
            error_msg += "Blocking Errors:\n"
            for error in result['errors']:
                error_msg += f"  • {error}\n"
            
            if result['warnings']:
                error_msg += "\nWarnings (likely blank rendering):\n"
                for warning in result['warnings']:
                    error_msg += f"  • {warning}\n"
            
            if result.get('patch'):
                error_msg += f"\n{result['patch']}"
            
            return jsonify({
                'success': False,
                'error': error_msg,
                'errors': result['errors'],
                'warnings': result['warnings'],
                'patch': result.get('patch', '')
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _normalize_yaml_content(spec):
    """Normalize YAML content before PPT generation.
    
    Rules:
    - Every bullet line starts with •
    - No headings without bullets inside text_only
    - No blank lines inside bullet blocks
    - Section labels are written as bullet text (e.g. • Core pack:)
    - No reliance on formatting semantics the renderer doesn't support
    """
    def normalize_text_content(content):
        """Normalize text content according to rules."""
        if not content or not isinstance(content, str):
            return content
        
        lines = content.split('\n')
        normalized_lines = []
        in_bullet_block = False
        last_was_bullet = False
        
        for line in lines:
            stripped = line.strip()
            
            # Skip completely empty lines inside bullet blocks
            if not stripped:
                if not in_bullet_block:
                    normalized_lines.append('')
                continue
            
            # Check if line looks like a bullet
            is_bullet = stripped.startswith('•') or \
                       stripped.startswith('-') or \
                       stripped.startswith('*') or \
                       re.match(r'^\d+[\.\)]\s', stripped)
            
            # Check if line looks like a heading (ends with :, no bullet, short)
            is_heading = not is_bullet and stripped.endswith(':') and len(stripped) < 50
            
            if is_bullet:
                in_bullet_block = True
                last_was_bullet = True
                # Ensure it starts with •
                if not stripped.startswith('•'):
                    if stripped.startswith('-') or stripped.startswith('*'):
                        stripped = '•' + stripped[1:].strip()
                    elif re.match(r'^\d+[\.\)]\s', stripped):
                        # Keep numbered items
                        pass
                    else:
                        stripped = '• ' + stripped
                normalized_lines.append(stripped)
            elif is_heading:
                # Convert heading to bullet text
                normalized_lines.append('• ' + stripped)
                in_bullet_block = True
                last_was_bullet = True
            else:
                # Regular text line
                if in_bullet_block and last_was_bullet:
                    if len(stripped) < 100 and not stripped.startswith('•'):
                        normalized_lines.append('• ' + stripped)
                    else:
                        in_bullet_block = False
                        normalized_lines.append('')
                        normalized_lines.append(stripped)
                else:
                    normalized_lines.append(stripped)
                last_was_bullet = False
        
        return '\n'.join(normalized_lines)
    
    # Normalize each slide's content
    for slide in spec.get('slides', []):
        slide_type = slide.get('type', '')
        
        if slide_type == 'text_only' and 'content' in slide:
            slide['content'] = normalize_text_content(slide['content'])
        
        if slide_type == 'two_column':
            if 'left_content' in slide:
                slide['left_content'] = normalize_text_content(slide['left_content'])
            if 'right_content' in slide:
                slide['right_content'] = normalize_text_content(slide['right_content'])
        
        if slide_type == 'three_column':
            if 'left_content' in slide:
                slide['left_content'] = normalize_text_content(slide['left_content'])
            if 'middle_content' in slide:
                slide['middle_content'] = normalize_text_content(slide['middle_content'])
            if 'right_content' in slide:
                slide['right_content'] = normalize_text_content(slide['right_content'])
    
    return spec


@app.route('/api/generate', methods=['POST'])
def generate_presentation():
    """Generate PowerPoint from YAML."""
    try:
        data = request.json
        yaml_content = data.get('yaml', '')
        
        # Validate YAML first
        spec = yaml.safe_load(yaml_content)
        if not spec or 'slides' not in spec:
            return jsonify({
                'success': False,
                'error': 'Invalid YAML structure'
            }), 400
        
        # Normalize content before generation
        spec = _normalize_yaml_content(spec)
        
        # Find template
        template_path = find_template()
        if not template_path:
            return jsonify({
                'success': False,
                'error': 'Template file not found. Please ensure HyFlux_Template_-.pptx is in templates/ directory.'
            }), 500
        
        # Create temporary YAML file with normalized content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(spec, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            temp_yaml = f.name
        
        try:
            # Generate output filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            project_name = spec.get('presentation', {}).get('title', 'presentation')
            project_name = secure_filename(project_name.replace(' ', '_'))[:50]
            output_filename = f"{timestamp}_{project_name}.pptx"
            output_path = Path(app.config['OUTPUT_FOLDER']) / output_filename
            
            # Generate presentation
            generator = HyFluxPPTGenerator(str(template_path))
            result = generator.generate(temp_yaml, str(output_path))
            
            return jsonify({
                'success': True,
                'filename': output_filename,
                'slide_count': result['slide_count'],
                'message': f'Generated {result["slide_count"]} slides'
            })
        finally:
            # Clean up temp file
            if os.path.exists(temp_yaml):
                os.unlink(temp_yaml)
                
    except yaml.YAMLError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid YAML: {str(e)}'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Generation failed: {str(e)}'
        }), 500


@app.route('/api/download/<filename>')
def download_file(filename):
    """Download generated presentation."""
    try:
        file_path = Path(app.config['OUTPUT_FOLDER']) / secure_filename(filename)
        if not file_path.exists():
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
        
        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation'
        )
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/upload', methods=['POST'])
def upload_yaml():
    """Upload YAML file."""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        if not file.filename.endswith(('.yaml', '.yml')):
            return jsonify({
                'success': False,
                'error': 'File must be a YAML file (.yaml or .yml)'
            }), 400
        
        content = file.read().decode('utf-8')
        
        # Validate it's valid YAML
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            return jsonify({
                'success': False,
                'error': f'Invalid YAML: {str(e)}'
            }), 400
        
        return jsonify({
            'success': True,
            'content': content
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def clean_yaml_content(yaml_content):
    """Clean YAML content to ensure it's a single valid document."""
    if not yaml_content:
        return None
    
    # Remove document separators (---)
    lines = yaml_content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        stripped = line.strip()
        # Skip standalone document separators
        if stripped == '---' or stripped == '...':
            continue
        # Skip lines that are just separators with whitespace
        if stripped.startswith('---') and len(stripped) <= 5:
            continue
        cleaned_lines.append(line)
    
    yaml_content = '\n'.join(cleaned_lines).strip()
    
    # Remove any leading/trailing separators
    yaml_content = re.sub(r'^---+\s*\n', '', yaml_content, flags=re.MULTILINE)
    yaml_content = re.sub(r'\n---+\s*$', '', yaml_content, flags=re.MULTILINE)
    yaml_content = re.sub(r'\n\.\.\.\s*$', '', yaml_content, flags=re.MULTILINE)
    
    # If content still has multiple documents, take the first one
    if '---' in yaml_content:
        parts = yaml_content.split('---')
        # Find the part with 'presentation:' or 'slides:'
        for part in parts:
            if 'presentation:' in part or 'slides:' in part:
                yaml_content = part.strip()
                break
        else:
            # If no part has presentation/slides, use the first non-empty part
            yaml_content = parts[0].strip() if parts else yaml_content
    
    return yaml_content


def get_ollama_base_url():
    """Get the appropriate Ollama base URL based on environment."""
    import os
    # Check if we're in Docker
    if os.path.exists('/.dockerenv'):
        # Try multiple methods to reach host
        # host.docker.internal works on Docker Desktop (Mac/Windows)
        # On Linux, we might need to use the host's IP or gateway
        import socket
        try:
            # Try host.docker.internal first (Docker Desktop)
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(1)
            result = test_socket.connect_ex(('host.docker.internal', 11434))
            test_socket.close()
            if result == 0:
                return 'http://host.docker.internal:11434'
        except:
            pass
        
        # Fallback: try gateway IP (Linux Docker)
        try:
            with open('/etc/hosts', 'r') as f:
                for line in f:
                    if 'gateway' in line.lower():
                        gateway_ip = line.split()[0]
                        return f'http://{gateway_ip}:11434'
        except:
            pass
        
        # Last resort: try host.docker.internal anyway
        return 'http://host.docker.internal:11434'
    else:
        # Not in Docker, use localhost
        return 'http://localhost:11434'


@app.route('/api/chat', methods=['POST'])
def chat_with_ollama():
    """Chat with Ollama API."""
    try:
        data = request.json
        message = data.get('message', '')
        model = data.get('model', 'llama3.2')  # Default model
        
        # Get Ollama base URL
        ollama_base = get_ollama_base_url()
        ollama_url = f'{ollama_base}/api/generate'
        
        if not message:
            return jsonify({
                'success': False,
                'error': 'No message provided'
            }), 400
        
        # Prepare prompt - add context about PPT generation
        context_prompt = """You are an AI assistant helping users create PowerPoint presentations using YAML specifications for the HyFlux template.

You must follow STRICT YAML→PPT validation rules. Your output will be validated against these rules:

STRICT VALIDATION RULES (render-safe):
1. Top-level keys MUST be exactly: 'presentation' and 'slides' (nothing else)
2. Slides must be under 'slides:' and indented with 2 spaces (NO TABS)
3. Supported slide types ONLY: title_white, divider, text_only, two_column, three_column, quote, title_only, end_slide
4. Required fields per type:
   - title_white: MUST have 'title' and 'subtitle'
   - divider: MUST have 'title' only (divider is title-only, no content)
   - text_only: MUST have 'title' and 'content'
   - two_column: MUST have 'title', 'left_content', 'right_content'
   - three_column: MUST have 'title', 'left_content', 'middle_content', 'right_content'
   - quote: MUST have 'quote' and 'attribution'
   - title_only: MUST have 'title' only (title_only should not be used for body text)
   - end_slide: MUST have 'title' only (MUST NOT contain 'content' or 'contact' - text will NOT render)
5. Render rules:
   - end_slide: Template-only, text in 'content' or 'contact' will NOT render. Use 'title' only.
   - title_only: Should not be used for body text. Use text_only if you need content.
   - divider: Title-only, no content field.
6. Block scalars (|) must have correctly indented content (2+ spaces)
7. Use 2 spaces for indentation throughout (NO TABS)
8. All YAML must be valid and parseable


CRITICAL YAML REQUIREMENTS:
1. Output ONLY a SINGLE YAML document - NO document separators (---)
2. Always start with 'presentation:' section at the top with title, author, date
3. Use proper indentation (2 spaces, no tabs)
4. Use double quotes for strings with special characters
5. Do NOT include multiple YAML documents or separators
6. The YAML must be a single, continuous document

SUPPORTED SLIDE TYPES (use lowercase):
- title_white: Title slide
- divider: Section divider slide
- text_only: Text content slide
- two_column: Two-column layout
- three_column: Three-column layout
- title_only: Title only (for charts/images)
- quote: Quote slide
- end_slide: Closing slide

FIELD NAMES - USE THESE EXACT NAMES:

For TITLE slides (type: title_white):
```yaml
- type: title_white
  title: "Main Title"
  subtitle: "Subtitle text (can include \\n for line breaks)"
```

For DIVIDER slides:
```yaml
- type: divider
  title: "Section Name"
```

For TEXT_ONLY slides:
```yaml
- type: text_only
  title: "Slide Title"
  content: |
    • Bullet point 1
    • Bullet point 2
    • Section label: (headings must be bullets)
    • More content
    # Note: No blank lines inside bullet blocks, all bullets start with •
```

For TWO_COLUMN slides:
```yaml
- type: two_column
  title: "Slide Title"
  left_content: |
    Left column content
    • Item 1
    • Item 2
  right_content: |
    Right column content
    • Item 1
    • Item 2
```

For THREE_COLUMN slides:
```yaml
- type: three_column
  title: "Slide Title"
  left_content: |
    Left content
    • Item 1
  middle_content: |
    Middle content
    • Item 1
  right_content: |
    Right content
    • Item 1
```

For QUOTE slides:
```yaml
- type: quote
  quote: "The quote text here"
  attribution: "Author Name"
```

For END_SLIDE (CRITICAL: title only, content/contact will NOT render):
```yaml
- type: end_slide
  title: "Thank You"
  # DO NOT use 'content' or 'contact' - they will NOT render!
  # end_slide is template-only, only 'title' displays
```

COMPLETE WORKING EXAMPLE:
```yaml
presentation:
  title: "Presentation Title"
  author: "Author Name"
  date: "2025-12-25"

slides:
  - type: title_white
    title: "Main Title"
    subtitle: "Subtitle here"
  
  - type: divider
    title: "Section 1"
  
  - type: text_only
    title: "Agenda"
    content: |
      1. First item
      2. Second item
      3. Third item
  
  - type: two_column
    title: "Two Column Slide"
    left_content: |
      Left side
      • Point 1
      • Point 2
    right_content: |
      Right side
      • Point 1
      • Point 2
  
  - type: three_column
    title: "Three Column Slide"
    left_content: "Left"
    middle_content: "Middle"
    right_content: "Right"
  
  - type: end_slide
    title: "Thank You"
    # Note: 'content' and 'contact' fields will NOT render on end_slide
```

CRITICAL FIELD NAME RULES:
- Use 'subtitle' for title_white slides (NOT 'content')
- Use 'left_content' and 'right_content' for two_column (NOT 'content.left' or nested structures)
- Use 'left_content', 'middle_content', 'right_content' for three_column
- Use 'content' for text_only slides (as multi-line string with |)
- Use 'quote' and 'attribution' for quote slides
- end_slide: Use 'title' ONLY. Do NOT use 'content' or 'contact' - they will NOT render
- Always use the exact field names shown above
- Do NOT use nested content structures like content.left/right
- Use multi-line strings (|) for content that spans multiple lines
- Use 2 spaces for indentation (NO TABS)

CONTENT NORMALIZATION RULES (applied automatically before PPT generation):
1. Every bullet line MUST start with • (convert -, *, numbered lists to •)
2. No headings without bullets inside text_only - convert headings to bullets (e.g. "Core pack:" → "• Core pack:")
3. No blank lines inside bullet blocks (blank lines break bullet formatting)
4. Section labels MUST be written as bullet text (e.g. "• Core pack:" not "Core pack:")
5. No reliance on formatting semantics the renderer doesn't support

VALIDATION CHECKLIST BEFORE OUTPUTTING:
✓ Top-level has only 'presentation' and 'slides'
✓ All slides have correct 'type' from supported list
✓ Each slide has ALL required fields for its type
✓ end_slide has ONLY 'title' (no content/contact)
✓ title_only has ONLY 'title' (no content)
✓ divider has ONLY 'title' (no content)
✓ All bullet points start with • (not -, *, or numbers)
✓ No headings without bullets in text content
✓ No blank lines inside bullet blocks
✓ Section labels are bullet text (e.g. • Section:)
✓ Indentation uses 2 spaces (no tabs)
✓ Block scalars are properly indented
✓ YAML is valid and parseable

User question: """
        
        full_prompt = context_prompt + message
        
        # Call Ollama API
        try:
            response = requests.post(
                ollama_url,
                json={
                    'model': model,
                    'prompt': full_prompt,
                    'stream': False
                },
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            ai_response = result.get('response', 'No response generated')
            
            # Extract YAML from response if present
            yaml_content = None
            
            # Try to find YAML code blocks (more flexible pattern)
            yaml_blocks = re.findall(r'```yaml\s*\n(.*?)```', ai_response, re.DOTALL)
            if not yaml_blocks:
                # Try without language tag but check if it looks like YAML
                all_blocks = re.findall(r'```\s*\n(.*?)```', ai_response, re.DOTALL)
                for block in all_blocks:
                    # Check if it looks like YAML (has 'slides:' or 'presentation:')
                    if 'slides:' in block or 'presentation:' in block or 'type:' in block:
                        yaml_blocks = [block]
                        break
            
            if yaml_blocks:
                yaml_content = yaml_blocks[0].strip()
                
                # Clean YAML: Remove document separators and multiple documents
                yaml_content = clean_yaml_content(yaml_content)
                # Validate and fix YAML if needed
                try:
                    # Try to load as single document
                    parsed = yaml.safe_load(yaml_content)
                    
                    # If None or not a dict, try loading all documents and taking first
                    if parsed is None:
                        # Try loading all and taking first
                        try:
                            all_docs = list(yaml.safe_load_all(yaml_content))
                            if all_docs and len(all_docs) > 0:
                                parsed = all_docs[0]
                                # Re-dump as single document
                                yaml_content = yaml.dump(parsed, default_flow_style=False, sort_keys=False, allow_unicode=True)
                        except:
                            yaml_content = None
                    
                    # Ensure it has the required structure
                    if not isinstance(parsed, dict):
                        yaml_content = None
                    elif 'slides' in parsed and 'presentation' not in parsed:
                        # Fix: add presentation section if missing
                        yaml_content = f"presentation:\n  title: \"Generated Presentation\"\n  author: \"User\"\n  date: \"{datetime.now().strftime('%Y-%m-%d')}\"\n\n{yaml.dump({'slides': parsed.get('slides', [])}, default_flow_style=False, sort_keys=False, allow_unicode=True)}"
                        # Re-validate
                        parsed = yaml.safe_load(yaml_content)
                except yaml.YAMLError as e:
                    # Try to fix common YAML errors
                    try:
                        error_str = str(e).lower()
                        
                        # Handle multiple documents error
                        if 'single document' in error_str and 'found another document' in error_str:
                            # Try to extract first document only
                            try:
                                all_docs = list(yaml.safe_load_all(yaml_content))
                                if all_docs and len(all_docs) > 0:
                                    parsed = all_docs[0]
                                    if isinstance(parsed, dict):
                                        yaml_content = yaml.dump(parsed, default_flow_style=False, sort_keys=False, allow_unicode=True)
                                    else:
                                        yaml_content = None
                                else:
                                    yaml_content = None
                            except:
                                # If safe_load_all fails, try manual extraction
                                # Remove everything after first ---
                                if '---' in yaml_content:
                                    first_part = yaml_content.split('---')[0].strip()
                                    if first_part:
                                        yaml_content = first_part
                                        parsed = yaml.safe_load(yaml_content)
                                        if parsed:
                                            yaml_content = yaml.dump(parsed, default_flow_style=False, sort_keys=False, allow_unicode=True)
                                        else:
                                            yaml_content = None
                                    else:
                                        yaml_content = None
                                else:
                                    yaml_content = None
                        # If error is about missing document start or block mapping
                        elif 'document start' in error_str or 'block mapping' in error_str:
                            # Check if it starts with 'slides:' - add presentation section
                            if yaml_content.strip().startswith('slides:'):
                                # Extract just the slides content
                                slides_content = yaml_content.strip()
                                yaml_content = f"presentation:\n  title: \"Generated Presentation\"\n  author: \"User\"\n  date: \"{datetime.now().strftime('%Y-%m-%d')}\"\n\n{slides_content}"
                                # Re-validate
                                parsed = yaml.safe_load(yaml_content)
                                if parsed:
                                    # Re-dump to ensure proper formatting
                                    yaml_content = yaml.dump(parsed, default_flow_style=False, sort_keys=False, allow_unicode=True)
                            else:
                                # Try wrapping in presentation
                                try:
                                    temp_parsed = yaml.safe_load(yaml_content)
                                    if isinstance(temp_parsed, dict):
                                        yaml_content = yaml.dump({
                                            'presentation': {
                                                'title': 'Generated Presentation',
                                                'author': 'User',
                                                'date': datetime.now().strftime('%Y-%m-%d')
                                            },
                                            **temp_parsed
                                        }, default_flow_style=False, sort_keys=False, allow_unicode=True)
                                except:
                                    yaml_content = None
                        else:
                            # Try to parse and re-dump to fix formatting
                            try:
                                parsed = yaml.safe_load(yaml_content)
                                if parsed:
                                    yaml_content = yaml.dump(parsed, default_flow_style=False, sort_keys=False, allow_unicode=True)
                                else:
                                    yaml_content = None
                            except:
                                yaml_content = None
                    except Exception as fix_error:
                        # If we can't fix it, set to None and let user see the error
                        print(f"Could not fix YAML: {fix_error}")
                        yaml_content = None
            
            # Validate extracted YAML if present
            validation_result = None
            if yaml_content:
                validation_result = validate_yaml_strict(yaml_content)
                
                if not validation_result['valid']:
                    # Add validation errors to response
                    error_summary = "\n\n⚠️ **YAML Validation Issues Detected:**\n\n"
                    error_summary += "**Errors:**\n"
                    for error in validation_result['errors']:
                        error_summary += f"- {error}\n"
                    if validation_result['warnings']:
                        error_summary += "\n**Warnings:**\n"
                        for warning in validation_result['warnings']:
                            error_summary += f"- {warning}\n"
                    error_summary += "\nThe YAML has been extracted but needs fixes before use."
                    ai_response = ai_response + error_summary
                else:
                    # Add usage instructions if YAML is valid
                    instructions = """

### How to use the YAML

1. **Copy the YAML block** above into the editor on the left.
2. **Replace placeholders**:
   - Update `title`, `author`, and `date` with your own values
   - Modify slide content to match your needs
   - Adjust slide types and layouts as required
3. **Validate** the YAML using the Validate button (already validated ✓)
4. **Generate** your PowerPoint presentation
5. **Review** the generated slides and fine-tune if needed

The YAML has been automatically extracted and validated. It's ready to use in the editor."""
                    ai_response = ai_response + instructions
                    
                    # If there are warnings, add them
                    if validation_result['warnings']:
                        warnings_text = "\n\n⚠️ **Validation Warnings:**\n"
                        for warning in validation_result['warnings']:
                            warnings_text += f"- {warning}\n"
                        ai_response = ai_response + warnings_text
            
            # Only send YAML if it's valid
            send_yaml = yaml_content if (yaml_content and (not validation_result or validation_result['valid'])) else None
            
            return jsonify({
                'success': True,
                'response': ai_response,
                'yaml_content': send_yaml,  # Only send if valid
                'model': model,
                'validation': validation_result if validation_result else None
            })
        except requests.exceptions.ConnectionError:
            error_msg = f'Cannot connect to Ollama at {ollama_base}. '
            error_msg += 'Please ensure:\n'
            error_msg += '1. Ollama is installed and running\n'
            error_msg += '2. Ollama is accessible at the expected URL\n'
            if os.path.exists('/.dockerenv'):
                error_msg += '3. For Docker: Ensure host networking is accessible\n'
                error_msg += '   Try: docker run --add-host=host.docker.internal:host-gateway ...'
            return jsonify({
                'success': False,
                'error': error_msg,
                'ollama_url': ollama_base
            }), 503
        except requests.exceptions.Timeout:
            return jsonify({
                'success': False,
                'error': 'Request to Ollama timed out'
            }), 504
        except requests.exceptions.RequestException as e:
            return jsonify({
                'success': False,
                'error': f'Ollama API error: {str(e)}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/save', methods=['POST'])
def save_yaml():
    """Save YAML content to file."""
    try:
        data = request.json
        yaml_content = data.get('yaml', '')
        filename = data.get('filename', '')
        
        if not yaml_content:
            return jsonify({
                'success': False,
                'error': 'No YAML content provided'
            }), 400
        
        # Validate YAML
        try:
            yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            return jsonify({
                'success': False,
                'error': f'Invalid YAML: {str(e)}'
            }), 400
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'presentation_{timestamp}.yaml'
        else:
            # Ensure .yaml extension
            if not filename.endswith(('.yaml', '.yml')):
                filename += '.yaml'
            filename = secure_filename(filename)
        
        # Save to input directory
        input_dir = Path('/app/input')
        input_dir.mkdir(parents=True, exist_ok=True)
        file_path = input_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'message': f'YAML saved as {filename}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/saved-files', methods=['GET'])
def list_saved_files():
    """List all saved YAML files."""
    try:
        input_dir = Path('/app/input')
        saved_files = []
        
        if input_dir.exists():
            for file_path in sorted(input_dir.glob('*.yaml'), reverse=True):
                if file_path.is_file() and file_path.name != 'sample_content_spec.yaml':
                    stat = file_path.stat()
                    saved_files.append({
                        'filename': file_path.name,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        
        return jsonify({
            'success': True,
            'files': saved_files
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'files': []
        }), 500


@app.route('/api/load-file/<filename>', methods=['GET'])
def load_saved_file(filename):
    """Load a saved YAML file."""
    try:
        filename = secure_filename(filename)
        file_path = Path('/app/input') / filename
        
        if not file_path.exists():
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'success': True,
            'content': content,
            'filename': filename
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/download-yaml/<filename>', methods=['GET'])
def download_yaml_file(filename):
    """Download a YAML file."""
    try:
        filename = secure_filename(filename)
        file_path = Path('/app/input') / filename
        
        if not file_path.exists():
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
        
        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=filename,
            mimetype='text/yaml'
        )
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/chat/test', methods=['GET'])
def test_ollama_connection():
    """Test Ollama connection."""
    try:
        ollama_base = get_ollama_base_url()
        test_url = f'{ollama_base}/api/tags'
        
        response = requests.get(test_url, timeout=5)
        response.raise_for_status()
        
        return jsonify({
            'success': True,
            'message': 'Ollama connection successful',
            'ollama_url': ollama_base,
            'status': 'connected'
        })
    except requests.exceptions.ConnectionError:
        return jsonify({
            'success': False,
            'message': 'Cannot connect to Ollama',
            'ollama_url': ollama_base,
            'status': 'disconnected',
            'suggestions': [
                'Ensure Ollama is installed and running',
                'Check if Ollama is accessible at the URL',
                'For Docker: Verify host networking configuration'
            ]
        }), 503
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error testing connection: {str(e)}',
            'ollama_url': ollama_base,
            'status': 'error'
        }), 500


@app.route('/api/chat/models', methods=['GET'])
def get_ollama_models():
    """Get available Ollama models."""
    try:
        ollama_base = get_ollama_base_url()
        ollama_url = f'{ollama_base}/api/tags'
        
        try:
            response = requests.get(ollama_url, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            models = [model.get('name', '') for model in result.get('models', [])]
            
            return jsonify({
                'success': True,
                'models': models
            })
        except requests.exceptions.ConnectionError:
            error_msg = f'Cannot connect to Ollama at {ollama_base}. '
            error_msg += 'Make sure Ollama is running and accessible.'
            return jsonify({
                'success': False,
                'error': error_msg,
                'models': [],
                'ollama_url': ollama_base
            }), 503
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'models': []
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'models': []
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

