# 🚀 ScholarAI Quick Start

Get ScholarAI running in 5 minutes!

## Prerequisites

- Python 3.9+
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))
- Tavily API key ([Get one here](https://tavily.com/)) OR SerpAPI key

## Installation

```bash
# 1. Navigate to project directory
cd scholarai

# 2. Create virtual environment
python -m venv .venv

# 3. Activate it
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt
```

## Configuration

```bash
# 1. Copy example environment file
cp .env.example .env

# 2. Edit .env and add your API keys
# Use nano, vim, or your favorite editor:
nano .env
```

Your `.env` should contain:
```env
OPENAI_API_KEY=sk-your-key-here
TAVILY_API_KEY=tvly-your-key-here
```

## Verify Setup

```bash
# Run test script
python3 test_setup.py
```

You should see:
```
✓ PASS: Imports
✓ PASS: Configuration
✓ PASS: Search Tool
✓ PASS: Agents
✓ PASS: Exporters

🎉 All tests passed!
```

## Run the Application

```bash
python3 app.py
```

Open your browser to: **http://localhost:7860**

## First Research Query

Try this example:

1. **Topic**: "Impact of artificial intelligence on healthcare diagnostics"
2. **Number of Sources**: 10
3. **Style**: layperson
4. **Tone**: neutral
5. Click **"🚀 Start Research"**

Wait 30-60 seconds for the AI to:
- Search for relevant sources
- Analyze and synthesize information
- Generate a structured report with citations

## What's Next?

- **Explore**: Try different topics and settings
- **Learn**: Read `TECHNICAL_EXPLANATION.md` to understand how it works
- **Customize**: Modify prompts in `src/agents/synthesizer.py`
- **Deploy**: Follow `SETUP_GUIDE.md` for Docker/cloud deployment

## Troubleshooting

### "OPENAI_API_KEY is required"
→ Check `.env` file exists and has valid key

### "No search API key configured"
→ Add either TAVILY_API_KEY or SERPAPI_API_KEY to `.env`

### "Module not found"
→ Ensure venv is activated and run `pip install -r requirements.txt`

### More Help
See `SETUP_GUIDE.md` for detailed troubleshooting

---

**Happy Researching! 🎓**
