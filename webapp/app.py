#!/usr/bin/env python3
"""
HyFlux PPT Generator Web Application
Flask-based web interface for creating and generating presentations
"""

import os
import sys
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


@app.route('/api/chat', methods=['POST'])
def chat_with_ollama():
    """Chat with Ollama API."""
    try:
        data = request.json
        message = data.get('message', '')
        model = data.get('model', 'llama3.2')  # Default model
        
        # Use host.docker.internal in Docker, localhost otherwise
        import os
        if os.path.exists('/.dockerenv'):
            ollama_base = 'http://host.docker.internal:11434'
        else:
            ollama_base = 'http://localhost:11434'
        
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
            
            return jsonify({
                'success': True,
                'response': result.get('response', 'No response generated'),
                'model': model
            })
        except requests.exceptions.ConnectionError:
            return jsonify({
                'success': False,
                'error': 'Cannot connect to Ollama. Make sure Ollama is running on localhost:11434'
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


@app.route('/api/chat/models', methods=['GET'])
def get_ollama_models():
    """Get available Ollama models."""
    try:
        # Use host.docker.internal in Docker, localhost otherwise
        import os
        if os.path.exists('/.dockerenv'):
            ollama_base = 'http://host.docker.internal:11434'
        else:
            ollama_base = 'http://localhost:11434'
        
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
            return jsonify({
                'success': False,
                'error': 'Cannot connect to Ollama. Make sure Ollama is running on localhost:11434',
                'models': []
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

