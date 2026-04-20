

# Personal Assistant

A voice-enabled AI personal assistant application with speech recognition (ASR), text-to-speech (TTS), skill management, and tool execution capabilities.

## Features

- **AI Chat**: LLM-powered conversational agent with streaming responses
- **Voice Interaction**: Built-in ASR (speech-to-text) and TTS (text-to-speech) support
- **Skill System**: Extensible skill framework for adding custom capabilities
- **Tool Execution**: Built-in tools for URL fetching and bash command execution
- **MCP Integration**: Model Context Protocol server support
- **Web Interface**: Interactive chat UI

## Architecture

```
personal-assistant/
├── app.py                 # Application entry point
├── core/
│   ├── agent.py          # LLM agent implementation
│   ├── mcp_manager.py    # MCP server management
│   ├── my_asr.py         # Speech recognition
│   ├── my_tts.py         # Text-to-speech with streaming
│   ├── skill_manager.py # Skill scanning and management
│   └── tools.py          # Built-in tools
├── ui/
│   └── chat_tab.py       # Chat interface
├── skills/
│   ├── get-time/         # Time query skill
│   └── skill-creator/    # Skill creation framework
└── data/
    └── mcp_server.json  # MCP configuration
```

## Prerequisites

- Python 3.8+
- OpenAI API key or compatible LLM service
- For voice features: audio input/output devices

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Starting the Application

```bash
python app.py
```

### Voice Interaction

The assistant supports:
- Speech recognition via ASR
- Text-to-speech responses via TTS
- Real-time audio streaming

### Skill System

Skills are located in the `skills/` directory. Each skill is a self-contained module with its own `SKILL.md` definition.

#### Available Skills

- **get-time**: Query current time in various formats and timezones
- **skill-creator**: Framework for creating and evaluating new skills

### Tools

Built-in tools include:
- `fetch_url`: Fetch content from URLs
- `bash`: Execute shell commands

## Configuration

MCP server configuration is stored in `data/mcp_server.json`.

## Tech Stack

- Python异步框架
- LLM (大语言模型)
- WebSocket (实时语音流)
- MCP (Model Context Protocol)

## License

See individual skill directories for license information.