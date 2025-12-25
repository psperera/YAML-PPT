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


@app.route('/api/validate', methods=['POST'])
def validate_yaml():
    """Validate YAML content."""
    try:
        data = request.json
        yaml_content = data.get('yaml', '')
        
        # Try to parse YAML
        spec = yaml.safe_load(yaml_content)
        
        # Basic validation
        if not isinstance(spec, dict):
            return jsonify({
                'success': False,
                'error': 'YAML must be a dictionary/object'
            }), 400
        
        if 'slides' not in spec:
            return jsonify({
                'success': False,
                'error': 'Missing "slides" section'
            }), 400
        
        if not isinstance(spec['slides'], list):
            return jsonify({
                'success': False,
                'error': '"slides" must be a list'
            }), 400
        
        # Validate slide types
        valid_types = [
            'title_white', 'title_reverse', 'divider', 'text_only',
            'title_only', 'text_content', 'two_column', 'three_column',
            'quote', 'end_slide'
        ]
        
        errors = []
        for i, slide in enumerate(spec['slides']):
            if not isinstance(slide, dict):
                errors.append(f"Slide {i+1}: must be an object")
                continue
            
            slide_type = slide.get('type', '')
            if slide_type not in valid_types:
                errors.append(f"Slide {i+1}: invalid type '{slide_type}'")
        
        if errors:
            return jsonify({
                'success': False,
                'error': 'Validation errors:\n' + '\n'.join(errors)
            }), 400
        
        return jsonify({
            'success': True,
            'message': f'Valid YAML with {len(spec["slides"])} slides'
        })
    except yaml.YAMLError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid YAML syntax: {str(e)}'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
        
        # Find template
        template_path = find_template()
        if not template_path:
            return jsonify({
                'success': False,
                'error': 'Template file not found. Please ensure HyFlux_Template_-.pptx is in templates/ directory.'
            }), 500
        
        # Create temporary YAML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
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
        context_prompt = """You are an AI assistant helping users create PowerPoint presentations using YAML specifications.
You can help with:
- Writing YAML content for slides
- Suggesting slide structures
- Fixing YAML syntax errors
- Providing content ideas for presentations

CRITICAL YAML REQUIREMENTS:
1. Output ONLY a SINGLE YAML document - NO document separators (---)
2. Always start with 'presentation:' section at the top
. Must be complete and valid YAML
3. Use proper indentation (2 spaces, no tabs)
4. Use double quotes for strings with special characters
5. Do NOT include multiple YAML documents or separators
6. The YAML must be a single, continuous document

Example structure (CORRECT):
```yaml
presentation:
  title: "Presentation Title"
  author: "Author Name"
  date: "2025-12-25"

slides:
  - type: title_white
    title: "Slide Title"
    subtitle: "Subtitle"
```

WRONG (do NOT do this):
```yaml
---
presentation:
  title: "Title"
---
slides:
  - type: title_white
```

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
            
            # Add usage instructions if YAML was generated
            if yaml_content:
                instructions = """

### How to use the YAML

1. **Copy the YAML block** above into the editor on the left.
2. **Replace placeholders**:
   - Update `title`, `author`, and `date` with your own values
   - Modify slide content to match your needs
   - Adjust slide types and layouts as required
3. **Validate** the YAML using the Validate button
4. **Generate** your PowerPoint presentation
5. **Review** the generated slides and fine-tune if needed

The YAML has been automatically extracted and is ready to use in the editor."""
                ai_response = ai_response + instructions
            
            return jsonify({
                'success': True,
                'response': ai_response,
                'yaml_content': yaml_content,  # Send extracted YAML separately
                'model': model
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

