# ScholarAI Technical Deep Dive

This document explains how each component of ScholarAI works under the hood.

---

## 🏗️ Architecture Overview

ScholarAI follows an **agentic AI architecture** where specialized agents work together:

```
User Input → Research Agent → Web Search → Synthesizer Agent → Structured Report
                    ↓              ↓              ↓
                Function Calls  API Calls   Structured Output
```

**Key Design Principles:**

1. **Separation of Concerns**: Each component has a single responsibility
2. **Tool-Based Design**: Agents use tools (functions) to accomplish tasks
3. **Structured Data Flow**: Data moves through well-defined formats
4. **Provider Agnosticism**: Easy to swap search providers

---

## 🔧 Component Breakdown

### 1. Configuration Management (`src/config.py`)

**Purpose**: Centralize all configuration and environment variable management

**How it works:**

```python
class Config:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    # ... other configs
    
    @classmethod
    def validate(cls) -> None:
        # Validates required keys exist
        if not cls.OPENAI_API_KEY:
            raise ValueError("Missing API key")
```

**Key Features:**

- **Environment Variables**: Uses `python-dotenv` to load `.env` file
- **Validation**: Checks required keys on import
- **Type Hints**: Clear indication of expected types
- **Class Methods**: Configuration accessed statically (`Config.OPENAI_API_KEY`)

**Why this approach?**

- Prevents API keys in code (security)
- Single source of truth for configuration
- Easy to mock in tests
- Fails fast if misconfigured

---

### 2. Web Search Tool (`src/tools/search.py`)

**Purpose**: Unified interface for web search across multiple providers

**Architecture:**

```
WebSearchTool (Facade)
    ├── TavilySearch (Implementation)
    └── SerpAPISearch (Implementation)
```

**How it works:**

#### SearchResult Dataclass

```python
@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    score: Optional[float] = None
```

**Why use a dataclass?**

- Immutable, structured data
- Type checking
- Easy serialization
- Consistent format regardless of provider

#### Provider Implementations

**Tavily:**
```python
def search(self, query: str, k: int = 10) -> List[SearchResult]:
    response = self.client.search(
        query=query,
        max_results=k,
        search_depth="advanced"  # More thorough results
    )
    # Normalize response → SearchResult
```

**Why Tavily?**
- Designed for AI applications
- Returns high-quality, relevant content
- Built-in relevance scoring
- Optimized for LLM consumption

**SerpAPI:**
```python
def search(self, query: str, k: int = 10) -> List[SearchResult]:
    params = {"q": query, "api_key": self.api_key, "num": k}
    search = self.GoogleSearch(params)
    results = search.get_dict()
    # Normalize → SearchResult
```

**Why SerpAPI?**
- Access to Google search results
- Academic paper availability
- Broader coverage
- More familiar results to users

#### WebSearchTool Facade

```python
class WebSearchTool:
    def __init__(self, provider: Optional[str] = None):
        provider = provider or Config.get_search_provider()
        if provider == "tavily":
            self.provider = TavilySearch(...)
        elif provider == "serpapi":
            self.provider = SerpAPISearch(...)
    
    def search(self, query: str, k: int) -> List[SearchResult]:
        return self.provider.search(query, k)
```

**Benefits of Facade Pattern:**

- Agents don't need to know which provider is used
- Easy to add new providers
- Consistent interface
- Can switch providers at runtime

---

### 3. Research Agent (`src/agents/research.py`)

**Purpose**: Intelligently search for and curate relevant sources

**How it works:**

#### Function Calling Setup

The agent uses OpenAI's **function calling** (also called tool use):

```python
self.tools = [{
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web...",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", ...},
                "k": {"type": "integer", ...}
            }
        }
    }
}]
```

**What this does:**

1. Tells the model a `web_search` function exists
2. Describes what it does and its parameters
3. Model can "call" this function by outputting structured JSON
4. We intercept and execute the actual function

#### Research Flow

```python
def research(self, topic: str, num_results: int = 10) -> Dict:
    # 1. Create system prompt with instructions
    system_prompt = f"You are a research assistant. Search for {num_results} sources..."
    
    # 2. Start conversation
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": topic}
    ]
    
    # 3. Conversation loop
    while iteration < max_iterations:
        # Call OpenAI
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.tools,
            tool_choice="auto"  # Model decides when to use tools
        )
        
        # Check if model wants to call function
        if response_message.tool_calls:
            # Execute function
            for tool_call in response_message.tool_calls:
                result = self._execute_tool_call(tool_call)
                # Add result to conversation
                messages.append({
                    "role": "tool",
                    "content": result
                })
        else:
            # Model is done, return results
            break
```

**Key Concepts:**

1. **Agentic Loop**: Agent makes multiple decisions and tool calls
2. **Conversation Context**: Full history passed each time
3. **Tool Execution**: We run actual Python code when "function called"
4. **Iterative Refinement**: Agent can search multiple times with different queries

**Why this approach?**

- Model determines search strategy (not hardcoded)
- Can refine queries based on initial results
- Flexible - adapts to different topics
- More intelligent than single search

#### Example Execution Trace

```
User: "Research CRISPR applications in medicine"
    ↓
Agent: "I'll search for recent CRISPR medical applications"
    ↓ [calls web_search("CRISPR medical applications 2024")]
Search Tool: Returns 10 results
    ↓
Agent: "Let me get more specific on clinical trials"
    ↓ [calls web_search("CRISPR clinical trials results")]
Search Tool: Returns 10 more results
    ↓
Agent: "I've found 20 relevant sources. The top 10 are..."
    ↓
Return: {sources: [...], reasoning: "..."}
```

---

### 4. Synthesizer Agent (`src/agents/synthesizer.py`)

**Purpose**: Transform sources into structured, cited research report

**How it works:**

#### ResearchReport Structure

```python
@dataclass
class ResearchReport:
    topic: str
    tldr: str  # ≤120 words
    key_findings: List[Dict]  # [{finding, citation}]
    conflicts_and_caveats: str
    top_sources: List[Dict]  # [{title, url, why_matters}]
    synthesis_date: str
```

**Why this structure?**

- Forces consistent output format
- Easy to validate
- Serializable to JSON/Markdown
- Clear requirements for the model

#### Synthesis Prompt Engineering

The prompt is carefully engineered:

```python
prompt = f"""You are synthesizing research on: {topic}

SOURCES PROVIDED:
[1] Title: ...
    URL: ...
    Content: ...

TASK: Create a comprehensive research report with:
1. TL;DR (≤120 words) - concise summary
2. Key Findings (3-7) - MUST include citation [Source #]
3. Conflicts & Caveats - limitations, disagreements
4. Top 5 Sources - ranked with explanation

STYLE: {style_instructions}
TONE: {tone_instructions}

IMPORTANT:
- Base ALL findings on provided sources
- ALWAYS cite with [Source #]
- Be specific, avoid generic statements

Output as JSON: {{...}}
"""
```

**Prompt Engineering Techniques:**

1. **Clear Structure**: Numbered sections with explicit requirements
2. **Constraints**: Word limits, citation requirements
3. **Examples**: Format specification
4. **Emphasis**: CAPS for critical requirements
5. **Context**: Style and tone customization
6. **Output Format**: JSON schema provided

#### Structured Output

```python
response = self.client.chat.completions.create(
    model=self.model,
    messages=[...],
    response_format={"type": "json_object"},  # Force JSON
    temperature=0.7
)
```

**Why JSON format?**

- Guaranteed parseable output
- No markdown/formatting issues
- Direct mapping to ResearchReport
- Programmatically processable

#### Temperature Setting

`temperature=0.7` balances:

- **0.0**: Deterministic, but boring and repetitive
- **1.0**: Creative, but inconsistent
- **0.7**: Sweet spot for research synthesis

---

### 5. Export System (`src/exporters/export.py`)

**Purpose**: Convert ResearchReport to shareable formats

**Architecture:**

```
ReportExporter (Facade)
    ├── MarkdownExporter
    └── JSONExporter
```

#### Markdown Export

```python
def export(report: ResearchReport) -> str:
    lines = []
    lines.append(f"# {report.topic}\n")
    lines.append(f"## 📋 Executive Summary\n{report.tldr}\n")
    # ... format each section with markdown
    return "\n".join(lines)
```

**Features:**

- Clean, readable formatting
- Emoji section headers for visual scanning
- Proper markdown links
- Compatible with GitHub, Obsidian, etc.

#### JSON Export

```python
def export(report: ResearchReport, pretty: bool = True) -> str:
    data = report.to_dict()
    return json.dumps(data, indent=2 if pretty else None)
```

**Features:**

- Structured data format
- API-ready
- Database-compatible
- Programmatically processable

---

### 6. Gradio Application (`app.py`)

**Purpose**: Provide user-friendly web interface

**Architecture:**

```python
class ScholarAIApp:
    def __init__(self):
        self.research_agent = ResearchAgent()
        self.synthesizer_agent = SynthesizerAgent()
    
    def conduct_research(self, topic, num_sources, style, tone):
        # Orchestrate full pipeline
        research_result = self.research_agent.research(...)
        report = self.synthesizer_agent.synthesize(...)
        return formatted_outputs
    
    def build_interface(self):
        # Create Gradio UI components
        with gr.Blocks() as interface:
            # Input components
            topic_input = gr.Textbox(...)
            research_button = gr.Button(...)
            
            # Output components
            summary_output = gr.Markdown(...)
            sources_table = gr.Dataframe(...)
            
            # Connect events
            research_button.click(
                fn=self.conduct_research,
                inputs=[...],
                outputs=[...]
            )
```

**Key Gradio Concepts:**

#### Components

- **Inputs**: Textbox, Slider, Dropdown
- **Outputs**: Markdown, Dataframe, Code
- **Layout**: Rows, Columns, Tabs

#### Event Handling

```python
button.click(
    fn=function_to_call,       # What to run
    inputs=[input1, input2],   # Function arguments
    outputs=[output1, output2] # Where to display results
)
```

#### Progressive Updates

```python
def conduct_research(self, progress=gr.Progress()):
    progress(0.2, desc="Searching...")
    # ... research
    progress(0.6, desc="Synthesizing...")
    # ... synthesis
    progress(1.0, desc="Complete!")
```

**Why Gradio?**

- Rapid prototyping
- Automatic API creation
- Easy sharing (public links)
- Python-native (no JS required)
- Built-in hosting options

---

## 🔄 Data Flow

### Complete Pipeline

```
1. User Input
   ↓
   topic: "CRISPR in medicine"
   num_sources: 10
   style: "layperson"
   tone: "neutral"

2. Research Agent
   ↓
   [LLM decides]: "I'll search for CRISPR medical applications"
   ↓
   [Calls]: web_search("CRISPR medical applications")
   ↓
   [Tool executes]: TavilySearch.search(...)
   ↓
   [Returns]: List[SearchResult(title, url, snippet, score)]
   ↓
   [LLM reviews]: "Good results, but need clinical trials info"
   ↓
   [Calls]: web_search("CRISPR clinical trials")
   ↓
   [Tool executes]: TavilySearch.search(...)
   ↓
   [Returns]: More results
   ↓
   [LLM concludes]: "I have 20 sources, here are top 10"
   ↓
   Output: {query, sources: [...], reasoning}

3. Synthesizer Agent
   ↓
   Input: {query, sources: [...]}
   ↓
   [Builds prompt]: Detailed instructions + sources + format
   ↓
   [LLM processes]: Reads all sources, extracts findings
   ↓
   [Structured output]: JSON matching ResearchReport schema
   ↓
   Output: ResearchReport(topic, tldr, key_findings, ...)

4. Export
   ↓
   ResearchReport → MarkdownExporter.export()
   ↓
   Markdown string
   ↓
   ResearchReport → JSONExporter.export()
   ↓
   JSON string

5. Display
   ↓
   Gradio renders:
   - Markdown in Summary tab
   - Sources in table
   - JSON in Export tab
```

---

## 🎯 Advanced Topics

### Function Calling Deep Dive

**How OpenAI function calling works:**

1. **Schema Definition**: You define function signature in JSON Schema
2. **Model Decision**: Model sees functions as available "tools"
3. **Structured Output**: Model outputs JSON specifying function + args
4. **Code Execution**: You parse JSON and run actual Python function
5. **Result Injection**: Function output added to conversation
6. **Iteration**: Process repeats until model "decides" it's done

**Example:**

```python
# Model output (internal):
{
    "tool_calls": [{
        "function": {
            "name": "web_search",
            "arguments": '{"query": "CRISPR", "k": 10}'
        }
    }]
}

# Your code:
args = json.loads(tool_call.function.arguments)
result = web_search(args["query"], args["k"])

# Add to conversation:
messages.append({
    "role": "tool",
    "content": json.dumps(result)
})

# Model sees result and can call again or finish
```

### Prompt Engineering Best Practices

**For Research Agent:**

- Clear role definition ("You are a research assistant")
- Explicit instructions ("Search for X, analyze Y")
- Constraints ("Find exactly N sources")
- Context ("For academic/general audience")

**For Synthesizer:**

- Structured output requirement
- Citation enforcement (MUST cite)
- Length constraints (TL;DR ≤120 words)
- Style and tone parameters
- Example format

**General Tips:**

- Be specific, not vague
- Use examples when possible
- Emphasize critical requirements
- Test prompts iteratively
- Use temperature to control creativity

### Error Handling Strategies

**Configuration Errors:**

```python
try:
    Config.validate()
except ValueError as e:
    # Fail fast, clear message
    print(f"Configuration error: {e}")
    sys.exit(1)
```

**API Errors:**

```python
try:
    response = self.client.chat.completions.create(...)
except OpenAI APIError as e:
    # Specific error handling
    if e.status_code == 429:
        # Rate limit
    elif e.status_code == 401:
        # Invalid key
```

**Search Errors:**

```python
try:
    results = self.provider.search(query, k)
except Exception as e:
    print(f"Search failed: {e}")
    return []  # Graceful degradation
```

### Performance Optimization

**Caching:**

```python
# Add caching decorator
@lru_cache(maxsize=100)
def search(self, query: str, k: int):
    # Expensive operation cached
```

**Parallel Processing:**

```python
# For multiple independent searches
with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = [
        executor.submit(self.search, query)
        for query in queries
    ]
    results = [f.result() for f in futures]
```

**Token Management:**

- Use gpt-3.5-turbo for simple tasks
- Reserve gpt-4 for complex synthesis
- Truncate long sources if needed
- Monitor token usage

---

## 🧪 Testing Strategies

### Unit Tests

```python
def test_search_normalization():
    # Test SearchResult creation
    result = SearchResult(
        title="Test",
        url="https://test.com",
        snippet="Content"
    )
    assert result.to_dict()["title"] == "Test"

def test_config_validation():
    # Test config fails without keys
    with pytest.raises(ValueError):
        Config.OPENAI_API_KEY = ""
        Config.validate()
```

### Integration Tests

```python
def test_research_flow():
    agent = ResearchAgent()
    result = agent.research("test query", num_results=3)
    assert len(result["sources"]) > 0
    assert "reasoning" in result

def test_synthesis_flow():
    agent = SynthesizerAgent()
    report = agent.synthesize("topic", mock_sources)
    assert len(report.tldr.split()) <= 120
    assert len(report.key_findings) > 0
```

### End-to-End Tests

```python
def test_full_pipeline():
    # Research
    research_agent = ResearchAgent()
    research_result = research_agent.research("test", 5)
    
    # Synthesize
    synthesizer = SynthesizerAgent()
    report = synthesizer.synthesize_from_research_result(research_result)
    
    # Export
    md = MarkdownExporter.export(report)
    json_str = JSONExporter.export(report)
    
    assert len(md) > 0
    assert json.loads(json_str)  # Valid JSON
```

---

## 📚 Further Reading

- [OpenAI Function Calling Guide](https://platform.openai.com/docs/guides/function-calling)
- [Gradio Documentation](https://gradio.app/docs)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Dataclasses Guide](https://docs.python.org/3/library/dataclasses.html)
- [Prompt Engineering](https://www.promptingguide.ai/)

---

**Next Steps**: Experiment with the code, modify prompts, and add new features!
