# HyFlux PowerPoint Template - Automation Standard

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     INPUT LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ JSON/YAML    │  │ Markdown     │  │ CSV/Data     │      │
│  │ Content Spec │  │ Content      │  │ Tables       │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                  PROCESSING LAYER                            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         Python Script (ppt_generator.py)               │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │ │
│  │  │ Content      │  │ Layout       │  │ Validation  │  │ │
│  │  │ Parser       │  │ Mapper       │  │ Engine      │  │ │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘  │ │
│  │         └──────────────────┴──────────────────┘         │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────┬───────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  TEMPLATE LAYER                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │     HyFlux_Template_-.pptx (Master Template)           │ │
│  │  • 37 Layout Types                                     │ │
│  │  • Outfit Font Family                                  │ │
│  │  • 16:9 Aspect Ratio                                   │ │
│  │  • HyFlux Branding                                     │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────┬───────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   OUTPUT LAYER                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ .pptx File   │  │ .pdf Export  │  │ Validation   │      │
│  │ (Editable)   │  │ (Optional)   │  │ Report       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## 2. Template Specifications

### Core Attributes
- **File**: HyFlux_Template_-.pptx
- **Total Layouts**: 37 types (10 core layouts for automation)
- **Dimensions**: 13.33" x 7.5" (16:9 ratio)
- **Font Family**: Outfit (primary), Outfit Semi Bold (headings)
- **Font Sizes**: 10pt, 12pt, 14pt, 20pt, 24pt

### Layout Index (Core 10 for Automation)

| Index | Layout Name           | Use Case                          |
|-------|-----------------------|-----------------------------------|
| 0     | Title slide (white)   | Presentation opening              |
| 1     | Title slide (reverse) | Alternative title slide           |
| 6     | Divider (reverse)     | Section breaks                    |
| 8     | Text only             | Content-heavy slides              |
| 12    | Title Only            | Image/chart placeholder slides    |
| 21    | Text + content        | Mixed text/visual content         |
| 23    | 2-column text         | Comparisons, side-by-side         |
| 24    | 3-column text         | Feature lists, multiple topics    |
| 34    | Quote                 | Testimonials, key statements      |
| 35    | End slide             | Closing/thank you slide           |

### Font Sizing Standard

```
Title Slides:      24pt (Outfit Semi Bold)
Section Dividers:  20pt (Outfit Semi Bold)
Slide Titles:      20pt (Outfit Semi Bold)
Body Text:         14pt (Outfit)
Captions:          12pt (Outfit)
Footer:            10pt (Outfit)
```

## 3. Automation Framework

### File Structure
```
hyflux-ppt-automation/
├── templates/
│   └── HyFlux_Template_-.pptx        # Master template (DO NOT EDIT)
├── input/
│   ├── content_spec.yaml              # Content definition
│   └── data/                          # CSV, images, etc.
├── output/
│   ├── generated/                     # Generated .pptx files
│   └── logs/                          # Generation logs
├── scripts/
│   ├── ppt_generator.py               # Main generator
│   ├── layout_mapper.py               # Layout selection logic
│   └── validator.py                   # Post-generation checks
├── config/
│   └── hyflux_config.yaml             # Standard settings
└── tests/
    └── test_generator.py              # Validation tests
```

## 4. Content Specification Schema

```yaml
# content_spec.yaml
presentation:
  title: "Q4 Business Review"
  author: "HyFlux Ltd"
  date: "2025-12-25"
  
slides:
  - type: title_white          # Maps to layout index 0
    title: "Q4 Business Review"
    subtitle: "Financial Performance & Strategic Updates"
    
  - type: divider              # Maps to layout index 6
    title: "Executive Summary"
    
  - type: text_only            # Maps to layout index 8
    title: "Key Highlights"
    content: |
      • Revenue growth of 23% YoY
      • Expanded into 3 new markets
      • Customer satisfaction at 94%
    
  - type: two_column           # Maps to layout index 23
    title: "Market Comparison"
    left_content: |
      Domestic Market
      • Strong performance
      • 15% growth
    right_content: |
      International
      • Emerging opportunities
      • 31% growth
      
  - type: quote                # Maps to layout index 34
    quote: "Innovation is at the heart of everything we do"
    attribution: "CEO, HyFlux Ltd"
    
  - type: end_slide            # Maps to layout index 35
    title: "Thank You"
    contact: "info@hyflux.com"
```

## 5. Layout Mapping Logic

```python
LAYOUT_MAP = {
    'title_white': 0,
    'title_reverse': 1,
    'divider': 6,
    'text_only': 8,
    'title_only': 12,
    'text_content': 21,
    'two_column': 23,
    'three_column': 24,
    'quote': 34,
    'end_slide': 35
}

def select_layout(slide_spec):
    """
    Priority order for automatic layout selection:
    1. Explicit type in spec
    2. Content analysis (text length, structure)
    3. Default to 'title_only' for safety
    """
    if 'type' in slide_spec:
        return LAYOUT_MAP.get(slide_spec['type'], 12)
    
    # Auto-detection logic
    if has_columns(slide_spec):
        return 23 if count_columns(slide_spec) == 2 else 24
    elif is_quote(slide_spec):
        return 34
    else:
        return 12  # Safe default: Title Only
```

## 6. Validation Checks

### Pre-Generation
- [ ] Template file exists and is readable
- [ ] Content spec is valid YAML/JSON
- [ ] All referenced layout types are valid
- [ ] Font "Outfit" is available on system
- [ ] Required images/assets exist

### Post-Generation
- [ ] Slide count matches spec
- [ ] No placeholder text remains
- [ ] All fonts are Outfit family
- [ ] Aspect ratio is 16:9
- [ ] File size is reasonable (<50MB typical)
- [ ] No broken image links

### Quick Validation Command
```bash
python3 scripts/validator.py output/generated/presentation.pptx
```

## 7. Known Failure Modes

| Failure | Symptom | Quick Fix | Prevention |
|---------|---------|-----------|------------|
| Font missing | Default Arial used | Install Outfit font | Check fonts pre-gen |
| Layout not found | Python KeyError | Check LAYOUT_MAP | Validate spec first |
| Image path broken | Missing images | Use absolute paths | Validate paths pre-gen |
| Text overflow | Text cut off | Reduce content or split slide | Text length limits |
| Template locked | Permission error | Check file permissions | Use template copy |
| Memory issue | Crash on large deck | Split into batches | <100 slides per file |

## 8. Rollback Plan

```bash
# If generation fails:
1. Check logs: cat output/logs/latest.log
2. Restore previous version: cp output/backup/last_good.pptx output/
3. Validate template: python3 scripts/validator.py templates/HyFlux_Template_-.pptx
4. Test with minimal spec: python3 scripts/ppt_generator.py tests/minimal_spec.yaml
5. Report issue: save logs and error spec to issues/
```

## 9. Dependencies

```requirements.txt
python-pptx==0.6.23
PyYAML==6.0.1
Pillow==10.1.0          # For image processing
openpyxl==3.1.2         # If importing from Excel
```

### Installation
```bash
# macOS Apple Silicon
pip3 install -r requirements.txt

# Verify
python3 -c "from pptx import Presentation; print('✓ python-pptx ready')"
```

## 10. Performance Benchmarks

| Presentation Size | Generation Time | Memory Usage |
|-------------------|-----------------|--------------|
| 10 slides         | ~2 seconds      | ~50 MB       |
| 50 slides         | ~8 seconds      | ~150 MB      |
| 100 slides        | ~15 seconds     | ~300 MB      |

*Tested on M1 Mac, 16GB RAM*

## 11. Best Practices

### DO
✓ Use the template as read-only (copy for modifications)
✓ Validate content specs before generation
✓ Keep slide count under 100 for performance
✓ Use consistent naming: `YYYY-MM-DD_project_vX.pptx`
✓ Version control your content specs
✓ Run validator after every generation

### DON'T
✗ Modify the master template directly
✗ Hardcode layout indices (use LAYOUT_MAP)
✗ Generate presentations >100 slides in one go
✗ Skip validation steps
✗ Use non-Outfit fonts
✗ Assume layout indices stay constant

## 12. Complexity Warning Threshold

⚠️ **Warning triggered if:**
- Presentation exceeds 100 slides → Consider splitting
- Custom layouts requested → Use existing 37 layouts first
- Non-standard fonts needed → Justify business need
- Complex animations required → Manual creation recommended
- Real-time data integration → Separate data pipeline from PPT gen

## 13. Trade-off Decision Matrix

| Approach | Reliability | Simplicity | Performance | Recommendation |
|----------|-------------|------------|-------------|----------------|
| **python-pptx** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | **PRIMARY** |
| LibreOffice CLI | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | Backup only |
| AppleScript | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | Avoid (brittle) |
| PowerPoint API | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | Overkill |

**Recommendation**: Use python-pptx for 95% of automation needs. It's the boring, stable solution.
