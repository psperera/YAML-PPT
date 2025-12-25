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
