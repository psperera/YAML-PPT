# Ollama Setup Guide

This guide will help you set up Ollama to work with the HyFlux PPT Generator web application.

## Quick Setup

### 1. Install Ollama

**macOS:**
```bash
brew install ollama
# or download from https://ollama.com/download
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download the installer from [ollama.com/download](https://ollama.com/download)

### 2. Start Ollama

Ollama runs as a service. After installation, it should start automatically.

**Check if it's running:**
```bash
curl http://localhost:11434/api/tags
```

If you get a JSON response, Ollama is running correctly.

**Manual start (if needed):**
```bash
ollama serve
```

### 3. Pull a Model

You need at least one model to use the chat feature:

```bash
# Recommended: Small and fast
ollama pull llama3.2

# Or try these alternatives:
ollama pull gemma2
ollama pull mistral
ollama pull phi3
```

**List available models:**
```bash
ollama list
```

### 4. Verify Connection

**From your host machine:**
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Hello"
}'
```

**From Docker container (if using Docker):**
```bash
docker exec hyflux-ppt-generator curl http://host.docker.internal:11434/api/tags
```

## Docker Configuration

The `docker-compose.yml` file includes `extra_hosts` to enable `host.docker.internal` access. This allows the Docker container to connect to Ollama running on your host machine.

### If Connection Still Fails

**Option 1: Use host network mode (Linux only)**
```yaml
# In docker-compose.yml, add:
network_mode: "host"
```

**Option 2: Find your host IP**
```bash
# On macOS/Windows Docker Desktop, use:
host.docker.internal

# On Linux, find your host IP:
ip route show default | awk '/default/ {print $3}'
```

Then update the connection in the app code or use environment variable.

**Option 3: Run Ollama in Docker**
```yaml
# Add to docker-compose.yml:
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
```

## Troubleshooting

### Error: "Cannot connect to Ollama"

1. **Check Ollama is running:**
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. **Check Docker can reach host:**
   ```bash
   docker exec hyflux-ppt-generator ping -c 1 host.docker.internal
   ```

3. **Check firewall settings:**
   - Ensure port 11434 is not blocked
   - On macOS, check System Preferences > Security & Privacy > Firewall

4. **Try restarting:**
   ```bash
   # Restart Ollama
   ollama serve
   
   # Restart Docker container
   docker-compose restart
   ```

### Error: "Model not found"

1. **Pull the model:**
   ```bash
   ollama pull llama3.2
   ```

2. **List available models:**
   ```bash
   ollama list
   ```

3. **Use a model that's available** in the chat interface dropdown

### Slow Responses

- Use a smaller model (llama3.2 is good)
- Ensure you have enough RAM (models need 2-8GB depending on size)
- Consider using GPU acceleration if available

## Testing the Connection

The web application automatically tests the Ollama connection when it loads. You'll see a message in the chat interface indicating whether Ollama is connected.

You can also test manually:
```bash
curl http://localhost:5001/api/chat/test
```

## Environment Variables (Optional)

You can configure a custom Ollama URL by modifying the `get_ollama_base_url()` function in `webapp/app.py` or adding an environment variable.

## Need Help?

- Check Ollama logs: `ollama logs`
- Check Docker logs: `docker-compose logs hyflux-webapp`
- Verify Ollama API: `curl http://localhost:11434/api/tags`
- Test from container: `docker exec hyflux-ppt-generator curl http://host.docker.internal:11434/api/tags`

