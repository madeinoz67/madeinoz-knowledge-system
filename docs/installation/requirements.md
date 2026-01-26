---
title: "Installation Requirements"
description: "System requirements and prerequisites for Madeinoz Knowledge System installation"
---

# Installation Guide

This guide will walk you through installing the Madeinoz Knowledge System step by step. Don't worry if you're not a developer - we'll explain everything clearly.

## What You'll Need

Before starting, make sure you have:

1. **A computer with:**

- macOS, Linux, or Windows with WSL
- At least 2GB of free RAM
- At least 1GB of disk space

1. **Software installed:**

   - Podman or Docker (for running containers)
   - Bun (JavaScript runtime)
   - An OpenAI API key (or compatible service)

2. **Dependent systems:**

   - None (PAI Memory System is built-in to Claude Code)

## What is a Container?

Before we begin, a quick explanation: This system uses "containers" to run the knowledge graph software. Think of a container like a self-contained app that includes everything it needs to run. You don't need to install complex database software - the container handles all that for you.

## Step-by-Step Installation

### Step 1: Get Your API Key

The system uses AI to understand your knowledge, so you need an API key from an AI provider.

**For OpenAI (Recommended):**

1. Go to <https://platform.openai.com/api-keys>
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (it starts with `sk-`)
5. Keep it safe - you'll need it soon

**Cost:** About $0.50-2.00 per month for typical personal use. The system uses the efficient gpt-4o-mini model by default.

### Step 2: Check if You Have Podman

Podman is what runs the knowledge system in a container.

Open your terminal and type:

```bash
podman --version
```

**If you see a version number:** Great! Skip to Step 3.

**If you see "command not found":**

Install Podman:

**On macOS:**

```bash
brew install podman
podman machine init
podman machine start
```

**On Ubuntu/Debian:**

```bash
sudo apt update
sudo apt install podman
```

**On Windows:** Use Windows Subsystem for Linux (WSL) and follow Ubuntu instructions.

### Step 3: Check if You Have Bun

Bun is the JavaScript runtime that makes everything fast.

```bash
bun --version
```

**If you see a version number:** Great! Skip to Step 4.

**If you see "command not found":**

Install Bun:

```bash
curl -fsSL https://bun.sh/install | bash
```

Then close and reopen your terminal.

### Step 4: Navigate to the Pack Directory

The Madeinoz Knowledge System is in your PAI packs folder:

```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system
```

**Can't find it?** If you installed PAI somewhere else, look for `Packs/madeinoz-knowledge-system` in your PAI directory.

### Step 5: Configure Your API Key

Add your API key to your PAI configuration file. The config file location is:

- `$PAI_DIR/.env` if PAI_DIR is set, OR
- `~/.claude/.env` (default)

Open your config file:

```bash
nano "${PAI_DIR:-$HOME/.claude}/.env"
```

Add these lines (see `config/.env.example` for all options):

```bash
# Madeinoz Knowledge System
MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=sk-your-openai-api-key-here
MADEINOZ_KNOWLEDGE_MODEL_NAME=gpt-4o-mini
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openai
```

Replace `sk-your-openai-api-key-here` with your actual API key.

**Save the file:**

- Press `Ctrl + O` to save
- Press `Enter` to confirm
- Press `Ctrl + X` to exit

### Step 6: Start the Knowledge System

Now start the MCP server (this runs the knowledge graph):

```bash
bun run server-cli start
```

You'll see output like:

```
Starting Madeinoz Knowledge System...
Creating network: madeinoz-knowledge-net
Starting Neo4j container...
Starting Graphiti MCP server...
Server is running at http://localhost:8000
```

**This will take 1-2 minutes the first time** as it downloads the container images.

**Keep this terminal window open** - the server runs here.

### Step 7: Verify It's Working

Open a new terminal window and check the status:

```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system
bun run server-cli status
```

You should see:

```
Madeinoz Knowledge System Status:

Containers:
  madeinoz-knowledge-graph-mcp: running
  madeinoz-knowledge-neo4j: running

MCP Server: http://localhost:8000/sse
  Status: healthy
```

### Step 8: Install Memory Sync Hook (Optional but Recommended)

This hook automatically syncs your learning captures from the PAI Memory System to your knowledge graph:

```bash
cd ~/.claude/skills/Knowledge
bun run tools/install.ts
```

Follow the prompts to:

1. Verify your memory directory location (~/.claude/MEMORY)
2. Install the sync hook
3. Configure automatic syncing

**What does this do?** When you capture "learnings" or "research" in your AI sessions, they'll automatically be added to your knowledge graph.

### Step 9: Test the Installation

Time to test everything! In your AI assistant (like Claude Code), try:

```
Remember that the Madeinoz Knowledge System was just installed today.
```

The assistant should respond with something like:

```
Knowledge Captured

Stored episode: Madeinoz Knowledge System Installation

Entities extracted:
- Madeinoz Knowledge System (Tool)
- installation (Event)
- today (Temporal)

Relationships identified:
- Madeinoz Knowledge System -> was installed -> today
```

Then try searching:

```
What do I know about PAI?
```

You should see your newly stored knowledge!

## What Just Happened?

Let's review what you installed:

1. **Neo4j** - A graph database (like a smart filing cabinet)
2. **Graphiti MCP Server** - The AI brain that processes your knowledge
3. **PAI Skill** - The interface that lets you talk to the system naturally
4. **Sync Hook** - Automatically captures learnings to your knowledge graph

All of these work together so you can simply say "remember this" and have your AI build a knowledge graph automatically.

## Starting and Stopping

### To Stop the Server

In the terminal where it's running, press `Ctrl + C`.

Or from another terminal:

```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system
bun run server-cli stop
```

### To Start Again

```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system
bun run server-cli start
```

### Check Status Anytime

```bash
bun run server-cli status
```

### View Logs

If something goes wrong:

```bash
bun run server-cli logs
```

## Optional: Add to Your Shell Startup

Want the server to start automatically when you open your terminal?

Add this to your shell configuration file (`~/.zshrc` or `~/.bashrc`):

```bash
# Auto-start Madeinoz Knowledge System
if ! podman ps | grep -q "madeinoz-knowledge-graph-mcp"; then
    cd ~/.config/pai/Packs/madeinoz-knowledge-system && bun run server-cli start
fi
```

## Customization Options

### Using a Different AI Model

The default model is `gpt-4o-mini` (fast and cheap). You can change it to:

- `gpt-4o` - More accurate but costs more
- `gpt-3.5-turbo` - Cheaper but less accurate

Edit your PAI config (`$PAI_DIR/.env` or `~/.claude/.env`):

```bash
MADEINOZ_KNOWLEDGE_MODEL_NAME=gpt-4o
```

Then restart the server.

### Using Multiple Knowledge Graphs

Want separate graphs for work and personal? Use group IDs:

In your PAI config (`$PAI_DIR/.env` or `~/.claude/.env`):

```bash
MADEINOZ_KNOWLEDGE_GROUP_ID=work
```

Or specify when capturing:

```
Remember this in my work knowledge: [your information]
```

### Adjusting Concurrency

If you hit API rate limits, reduce the concurrent requests:

In your PAI config (`$PAI_DIR/.env` or `~/.claude/.env`):

```bash
MADEINOZ_KNOWLEDGE_SEMAPHORE_LIMIT=5
```

Lower numbers = slower but less likely to hit rate limits.

## Next Steps

Now that everything is installed:

1. Read the [Usage Guide](../usage/basic-usage.md) to learn all the commands
2. Check out [Concepts](../concepts/knowledge-graph.md) to understand how it works
3. Start using it! The more you capture, the more valuable it becomes

## Troubleshooting

**Problem: "Port already in use"**

- Another service is using port 8000 or 7687 (Neo4j)
- Stop the other service or change ports in the Docker Compose files

**Problem: "API key invalid"**

- Check your API key in PAI config (`$PAI_DIR/.env` or `~/.claude/.env`)
- Verify it has credits at <https://platform.openai.com/usage>

**Problem: "Container won't start"**

- Check Docker/Podman is running: `podman ps`
- View logs: `bun run server-cli logs`
- Try restarting: `bun run server-cli restart`

**Problem: "No entities extracted"**

- Add more detail to what you're capturing
- Try a different model (gpt-4o instead of gpt-4o-mini)
- Make sure your content has clear concepts and relationships

For more help, see the [Troubleshooting Guide](../troubleshooting/common-issues.md).
