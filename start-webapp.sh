#!/bin/bash
# HyFlux PPT Generator - Web App Startup Script

set -e

echo "════════════════════════════════════════════════════════════════"
echo "HyFlux PPT Generator - Web Application"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if template exists
if [ ! -f "hyflux-ppt-automation/templates/HyFlux_Template_-.pptx" ]; then
    echo "⚠️  Warning: Template file not found at:"
    echo "   hyflux-ppt-automation/templates/HyFlux_Template_-.pptx"
    echo "   The web app will still start, but generation will fail without the template."
    echo ""
fi

# Create output directories if they don't exist
mkdir -p hyflux-ppt-automation/output/generated
mkdir -p hyflux-ppt-automation/output/uploads

echo "🚀 Starting Docker containers..."
echo ""

# Use docker compose (newer) or docker-compose (older)
if docker compose version &> /dev/null; then
    docker compose up -d --build
else
    docker-compose up -d --build
fi

echo ""
echo "✅ Web application is starting!"
echo ""
echo "📱 Access the application at: http://localhost:5001"
echo ""
echo "📋 Useful commands:"
echo "   View logs:    docker-compose logs -f"
echo "   Stop:         docker-compose down"
echo "   Restart:      docker-compose restart"
echo ""

