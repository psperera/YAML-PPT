# HyFlux PPT Generator - Web Application

A modern, Docker-based web interface for creating and generating PowerPoint presentations from YAML specifications.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Template file: `HyFlux_Template_-.pptx` in `hyflux-ppt-automation/templates/`

### Start the Application

```bash
# Option 1: Use the startup script
./start-webapp.sh

# Option 2: Use Docker Compose directly
docker-compose up -d --build
```

The web application will be available at: **http://localhost:5001**

## 📋 Features

- ✏️ **YAML Editor**: Full-featured text editor for creating presentation specs
- 📄 **Template Loading**: Load the sample template with one click
- 📤 **File Upload**: Upload existing YAML files
- ✅ **Real-time Validation**: Validate YAML syntax and structure
- 🎨 **PPT Generation**: Generate PowerPoint presentations instantly
- 💾 **Download**: Download generated presentations
- 💾 **Auto-save**: Content is saved to browser localStorage

## 🎯 Usage

1. **Load Template**: Click "Load Template" to start with a sample YAML
2. **Edit Content**: Modify the YAML in the editor to customize your presentation
3. **Validate**: Click "Validate" to check your YAML syntax before generating
4. **Generate**: Click "Generate PPT" to create your presentation
5. **Download**: Click "Download" to get your PowerPoint file

## 📁 Project Structure

```
PPT-HyFlux/
├── webapp/
│   ├── app.py                 # Flask backend
│   ├── Dockerfile             # Docker image definition
│   ├── requirements.txt       # Python dependencies
│   ├── templates/
│   │   └── index.html        # Frontend HTML
│   └── static/
│       ├── css/
│       │   └── style.css     # Styling
│       └── js/
│           └── app.js        # Frontend JavaScript
├── docker-compose.yml         # Docker Compose configuration
└── start-webapp.sh           # Startup script
```

## 🔧 API Endpoints

- `GET /` - Main web interface
- `GET /api/template` - Get sample YAML template
- `POST /api/validate` - Validate YAML content
  ```json
  {
    "yaml": "your yaml content here"
  }
  ```
- `POST /api/generate` - Generate PowerPoint from YAML
  ```json
  {
    "yaml": "your yaml content here"
  }
  ```
- `GET /api/download/<filename>` - Download generated file
- `POST /api/upload` - Upload YAML file (multipart/form-data)

## 🐳 Docker Commands

```bash
# Start the application
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down

# Rebuild after changes
docker-compose up -d --build

# View running containers
docker ps

# Access container shell
docker exec -it hyflux-ppt-generator bash
```

## 🛠️ Troubleshooting

### Template Not Found
**Error**: "Template file not found"

**Solution**: Ensure `HyFlux_Template_-.pptx` exists in:
```
hyflux-ppt-automation/templates/HyFlux_Template_-.pptx
```

### Port Already in Use
**Error**: Port 5000 is already in use

**Solution**: Change the port in `docker-compose.yml`:
```yaml
ports:
  - "8080:5000"  # Change 5001 to your preferred port
```

### Permission Errors
**Error**: Cannot write to output directory

**Solution**: Ensure output directory is writable:
```bash
chmod -R 755 hyflux-ppt-automation/output/generated
```

### Module Import Errors
**Error**: Cannot import ppt_generator

**Solution**: Rebuild the Docker image:
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 📝 Slide Types

The following slide types are supported:

- `title_white` - White background title slide
- `title_reverse` - Reverse/inverted title slide
- `divider` - Section divider slide
- `text_only` - Text content slide
- `title_only` - Title only (for charts/images)
- `two_column` - Two-column layout
- `three_column` - Three-column layout
- `quote` - Quote/testimonial slide
- `end_slide` - Closing/thank you slide

## 🔒 Security Notes

- The application runs in a Docker container for isolation
- File uploads are limited to 16MB
- Only `.yaml` and `.yml` files can be uploaded
- Generated files are stored in the container's output directory

## 📚 Additional Resources

- See `hyflux_ppt_standard.md` for full YAML specification
- See `sample_content_spec.yaml` for example content
- Check `hyflux-ppt-automation/README.md` for CLI usage

## 🎨 Customization

To customize the web interface:

1. Edit `webapp/static/css/style.css` for styling
2. Edit `webapp/templates/index.html` for layout
3. Edit `webapp/static/js/app.js` for functionality
4. Rebuild the Docker image after changes

## 📞 Support

For issues or questions:
1. Check the logs: `docker-compose logs -f`
2. Validate your YAML syntax
3. Ensure the template file exists
4. Check file permissions

---

**Happy Presenting! 🎉**

