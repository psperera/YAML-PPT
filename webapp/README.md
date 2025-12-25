# HyFlux PPT Generator Web Application

A Docker-based web interface for creating and generating PowerPoint presentations from YAML specifications.

## Features

- 📝 **YAML Editor**: Create and edit presentation specifications
- 📄 **Template Loading**: Start with a pre-built template
- 📤 **File Upload**: Upload existing YAML files
- ✅ **Validation**: Validate YAML syntax and structure
- 🎨 **PPT Generation**: Generate PowerPoint presentations
- 💾 **Download**: Download generated presentations

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

The web application will be available at: http://localhost:5000

### Manual Docker Build

```bash
# Build the image
docker build -t hyflux-webapp -f webapp/Dockerfile .

# Run the container
docker run -d \
  -p 5000:5000 \
  -v $(pwd)/hyflux-ppt-automation/templates:/app/templates:ro \
  -v $(pwd)/hyflux-ppt-automation/input:/app/input:ro \
  -v $(pwd)/hyflux-ppt-automation/output/generated:/app/output \
  --name hyflux-ppt-generator \
  hyflux-webapp
```

## Usage

1. **Load Template**: Click "Load Template" to start with a sample YAML
2. **Edit Content**: Modify the YAML in the editor
3. **Validate**: Click "Validate" to check your YAML syntax
4. **Generate**: Click "Generate PPT" to create your presentation
5. **Download**: Download the generated PowerPoint file

## API Endpoints

- `GET /` - Main web interface
- `GET /api/template` - Get sample YAML template
- `POST /api/validate` - Validate YAML content
- `POST /api/generate` - Generate PowerPoint from YAML
- `GET /api/download/<filename>` - Download generated file
- `POST /api/upload` - Upload YAML file

## Requirements

- Docker and Docker Compose
- Template file: `HyFlux_Template_-.pptx` in `templates/` directory

## Troubleshooting

- **Template not found**: Ensure `HyFlux_Template_-.pptx` is in the `hyflux-ppt-automation/templates/` directory
- **Port already in use**: Change the port in `docker-compose.yml` (e.g., `5001:5000`)
- **Permission errors**: Check that output directory is writable

