# Ollama Chat Integration

The web application includes an AI chat assistant powered by Ollama that can help you create and refine your YAML presentation specifications.

## Setup

### 1. Install Ollama

Download and install Ollama from [ollama.com](https://ollama.com)

### 2. Pull a Model

Pull at least one model to use with the chat:

```bash
ollama pull llama3.2
# or
ollama pull gemma2
# or
ollama pull mistral
```

### 3. Start Ollama

Ollama runs automatically as a service after installation. Make sure it's running:

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags
```

If you get a response, Ollama is running correctly.

## Using the Chat

1. **Access the Chat**: The chat interface is located in the right panel of the web application
2. **Select a Model**: Use the dropdown to select which Ollama model to use
3. **Ask Questions**: Type your question and press Enter or click the send button

## What the Chat Can Help With

- **YAML Creation**: Ask for help creating YAML content for specific slide types
- **Syntax Fixes**: Get help fixing YAML syntax errors
- **Content Ideas**: Get suggestions for presentation content
- **Slide Structure**: Ask for recommendations on how to structure your presentation

## Example Prompts

- "Create a YAML slide for a product launch presentation"
- "Help me write a two-column slide comparing two products"
- "What's the YAML structure for a quote slide?"
- "Fix this YAML syntax error: [paste your YAML]"
- "Suggest content for a Q4 business review presentation"

## Docker Considerations

When running in Docker, the application automatically uses `host.docker.internal` to connect to Ollama running on your host machine. This means:

- Ollama must be running on your **host machine** (not in Docker)
- The connection should work automatically
- If you have connection issues, ensure Ollama is accessible at `localhost:11434` on your host

## Troubleshooting

### "Cannot connect to Ollama"

- **Check Ollama is running**: `curl http://localhost:11434/api/tags`
- **Check Docker networking**: If in Docker, ensure `host.docker.internal` resolves correctly
- **Check firewall**: Ensure port 11434 is not blocked

### "No models available"

- Pull at least one model: `ollama pull llama3.2`
- Check models are available: `ollama list`

### Slow Responses

- Try a smaller/faster model
- Check your system resources
- Consider using a GPU-accelerated model if available

## API Endpoints

- `POST /api/chat` - Send a chat message
  ```json
  {
    "message": "Your question here",
    "model": "llama3.2"
  }
  ```

- `GET /api/chat/models` - Get available Ollama models

## Integration with YAML Editor

The chat assistant is context-aware and understands:
- YAML syntax for presentation specifications
- Slide types and their requirements
- Best practices for presentation content

You can copy YAML code blocks from chat responses directly into the editor!

