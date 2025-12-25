FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY webapp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY webapp/app.py .
COPY webapp/templates/ ./templates/
COPY webapp/static/ ./static/

# Copy the ppt_generator module
COPY hyflux-ppt-automation/scripts/ppt_generator.py ./ppt_generator.py

# Create necessary directories
# Note: PowerPoint template and input files are mounted via volumes in docker-compose.yml
# Flask templates are copied into the image, PowerPoint templates are mounted separately
RUN mkdir -p /app/uploads /app/output /app/ppt_templates /app/input

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Run the application
CMD ["python", "app.py"]

