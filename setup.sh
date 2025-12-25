#!/bin/bash
# HyFlux PPT Automation - Quick Setup
# macOS Apple Silicon compatible

set -e  # Exit on error

echo "════════════════════════════════════════════════════════════════"
echo "HyFlux PowerPoint Automation - Setup"
echo "════════════════════════════════════════════════════════════════"

# Check Python version
echo ""
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Found Python $PYTHON_VERSION"

# Create directory structure
echo ""
echo "Creating directory structure..."
mkdir -p hyflux-ppt-automation/{templates,input,output/{generated,logs},scripts,config,tests}

echo "✓ Created directories:"
echo "  hyflux-ppt-automation/"
echo "  ├── templates/      (place HyFlux_Template_-.pptx here)"
echo "  ├── input/          (content specs and data)"
echo "  ├── output/"
echo "  │   ├── generated/  (output presentations)"
echo "  │   └── logs/       (generation logs)"
echo "  ├── scripts/        (generator and validator)"
echo "  ├── config/         (configuration files)"
echo "  └── tests/          (test specs)"

# Move scripts
echo ""
echo "Setting up scripts..."
cp ppt_generator.py hyflux-ppt-automation/scripts/
cp validator.py hyflux-ppt-automation/scripts/
cp sample_content_spec.yaml hyflux-ppt-automation/input/
chmod +x hyflux-ppt-automation/scripts/*.py

echo "✓ Scripts installed"

# Create requirements.txt
echo ""
echo "Creating requirements.txt..."
cat > hyflux-ppt-automation/requirements.txt << 'EOF'
python-pptx==0.6.23
PyYAML==6.0.1
Pillow==10.1.0
EOF

echo "✓ Requirements file created"

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip3 install --break-system-packages -q python-pptx PyYAML Pillow || \
pip3 install -q python-pptx PyYAML Pillow

echo "✓ Dependencies installed"

# Verify installation
echo ""
echo "Verifying installation..."
python3 -c "from pptx import Presentation; import yaml; print('✓ python-pptx and PyYAML ready')"

# Create config file
echo ""
echo "Creating default config..."
cat > hyflux-ppt-automation/config/hyflux_config.yaml << 'EOF'
# HyFlux PPT Automation Configuration

font_name: 'Outfit'
font_sizes:
  title: 24
  heading: 20
  body: 14
  caption: 12

validation:
  max_slides: 100
  max_file_size_mb: 50
  
output:
  default_path: 'output/generated'
  name_pattern: '%Y-%m-%d_{project}_v{version}.pptx'
EOF

echo "✓ Configuration created"

# Create minimal test spec
echo ""
echo "Creating test specification..."
cat > hyflux-ppt-automation/tests/minimal_spec.yaml << 'EOF'
presentation:
  title: "Test Presentation"
  
slides:
  - type: title_white
    title: "Test Slide"
    subtitle: "Validation Test"
  
  - type: end_slide
    title: "Test Complete"
EOF

echo "✓ Test spec created"

# Create README
echo ""
echo "Creating README..."
cat > hyflux-ppt-automation/README.md << 'EOF'
# HyFlux PowerPoint Automation

Automated presentation generation using HyFlux standard template.

## Quick Start

1. **Place template file:**
   ```bash
   cp /path/to/HyFlux_Template_-.pptx templates/
   ```

2. **Create content spec:**
   - Edit `input/sample_content_spec.yaml`
   - Or create your own YAML file

3. **Generate presentation:**
   ```bash
   cd scripts
   python3 ppt_generator.py ../input/sample_content_spec.yaml ../output/generated/my_presentation.pptx
   ```

4. **Validate output:**
   ```bash
   python3 validator.py ../output/generated/my_presentation.pptx
   ```

## Test Installation

```bash
cd scripts
python3 ppt_generator.py ../tests/minimal_spec.yaml ../output/generated/test.pptx
python3 validator.py ../output/generated/test.pptx
```

## Directory Structure

```
hyflux-ppt-automation/
├── templates/          ← HyFlux template goes here
├── input/              ← Your content specs
├── output/
│   └── generated/      ← Generated presentations
├── scripts/
│   ├── ppt_generator.py
│   └── validator.py
└── config/
    └── hyflux_config.yaml
```

## Rollback

If something breaks:
```bash
# Test with minimal spec
python3 scripts/ppt_generator.py tests/minimal_spec.yaml output/test_rollback.pptx

# Check template integrity
python3 scripts/validator.py templates/HyFlux_Template_-.pptx
```

## Support

- See `hyflux_ppt_standard.md` for full documentation
- Check `sample_content_spec.yaml` for examples
- Issues? Run validator for diagnostics
EOF

echo "✓ README created"

# Copy template if it exists in current directory
if [ -f "HyFlux_Template_-.pptx" ]; then
    echo ""
    echo "Found template in current directory, copying..."
    cp HyFlux_Template_-.pptx hyflux-ppt-automation/templates/
    echo "✓ Template copied"
elif [ -f "/mnt/user-data/uploads/HyFlux_Template_-.pptx" ]; then
    echo ""
    echo "Found template in uploads, copying..."
    cp /mnt/user-data/uploads/HyFlux_Template_-.pptx hyflux-ppt-automation/templates/
    echo "✓ Template copied"
else
    echo ""
    echo "⚠️  Template not found in current directory"
    echo "   Please copy HyFlux_Template_-.pptx to:"
    echo "   hyflux-ppt-automation/templates/"
fi

# Final summary
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ Setup Complete!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo ""
echo "1. If template wasn't auto-copied:"
echo "   cp /path/to/HyFlux_Template_-.pptx hyflux-ppt-automation/templates/"
echo ""
echo "2. Test the installation:"
echo "   cd hyflux-ppt-automation/scripts"
echo "   python3 ppt_generator.py ../tests/minimal_spec.yaml ../output/generated/test.pptx"
echo ""
echo "3. Validate test output:"
echo "   python3 validator.py ../output/generated/test.pptx"
echo ""
echo "4. Create your first presentation:"
echo "   - Edit input/sample_content_spec.yaml"
echo "   - Run generator with your spec"
echo ""
echo "Documentation: hyflux_ppt_standard.md"
echo ""
