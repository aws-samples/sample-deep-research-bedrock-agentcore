# Research Methodology

This document explains how the Dimensional Research Agent conducts multi-dimensional research using a sophisticated LangGraph workflow.

## Overview

The agent breaks down complex research topics into multiple **dimensions** (major themes), then subdivides each dimension into specific **aspects** (research questions). It conducts parallel research across all aspects, synthesizes findings, and produces a comprehensive report with visualizations.

## Workflow Architecture

The research process follows a 13-node LangGraph workflow with **map-reduce parallelism** for efficient execution:

```
┌─────────────────────┐
│ Initialize Session  │ ← Setup logging, status tracking
└──────────┬──────────┘
           │
┌──────────▼───────────┐
│ Reference Preparation│ ← Process URLs/PDFs given as references
└──────────┬───────────┘
           │
┌──────────▼──────────┐
│  Topic Analysis     │ ← Identify key dimensions (2-5)
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  Aspect Analysis    │ ← Break dimensions → aspects (can be parallel)
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│ Research Planning   │ ← Unified refinement + integration
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│     Research        │ ← Deep research per aspect (can be parallel)
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│ Dimension Reduction │ ← Synthesize per dimension (can be parallel)
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  Report Writing     │ ← Merge + edit final report
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│ Chart Generation    │ ← Create and insert visualizations
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│ Document Conversion │ ← Markdown → DOCX → PDF
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│     Finalize        │ ← Upload to S3, log completion
└─────────────────────┘
```

## Stage Details

### 1. Initialize Session

**Purpose:** Set up research session infrastructure

**Actions:**
- Generate unique session ID
- Create workspace directory
- Initialize status tracking in DynamoDB
- Set up logging and tracing

**Output:** Session metadata

---

### 2. Reference Preparation

**Purpose:** Process user-provided references to extract knowledge

**Actions:**
- Extract content from URLs (web scraping)
- Parse PDF documents
- Process references **sequentially** (one at a time)
- Store extracted content in memory

**Output:** Processed reference documents

**Notes:**
- Sequential processing prevents rate limiting
- Extracted content informs later analysis

---

### 3. Topic Analysis

**Purpose:** Identify major research dimensions

**Actions:**
- Analyze research topic and user context
- Consider processed references
- Identify 2-5 **dimensions** (major themes)
- Generate brief dimension descriptions

**Example:**
```
Topic: "AI Safety in Healthcare"
Dimensions:
1. Clinical Decision Support Systems
2. Data Privacy & Security
3. Regulatory Compliance
4. Human-AI Collaboration
5. Bias & Fairness
```

**Output:** List of dimensions with descriptions

---

### 4. Aspect Analysis

**Purpose:** Break each dimension into specific research aspects

**Execution:** **Parallel by dimension**

**Actions per dimension:**
- Generate 2-5 **aspects** (specific research questions)
- Define reasoning for each aspect
- Formulate key questions to investigate
- Check if references already answer aspect (skip research if complete)

**Example:**
```
Dimension: "Clinical Decision Support Systems"
Aspects:
1. Diagnostic Accuracy
   - Key Questions: How accurate are AI diagnostics vs physicians?
   - Reasoning: Critical for patient safety
2. Integration Challenges
   - Key Questions: What are EHR integration barriers?
   - Reasoning: Affects adoption rates
3. Cost-Benefit Analysis
   - Key Questions: ROI of AI-CDSS implementations?
   - Reasoning: Drives investment decisions
```

**Output:** Structured aspects with metadata

---

### 5. Research Planning

**Purpose:** Unified refinement and reference integration

**Actions:**
- Review all aspects across dimensions
- Integrate insights from processed references
- Mark aspects as complete if fully answered by references
- Refine remaining aspects for deeper research
- Optimize research scope

**Output:** Finalized research plan with completion markers

**Benefits:**
- Avoids redundant research
- Focuses effort on knowledge gaps
- Ensures reference insights are incorporated

---

### 6. Research

**Purpose:** Deep research for each aspect using ReAct agents

**Execution:** **Sequential** (Gateway concurrency limitation)

**Actions per aspect:**
- Create ReAct agent with research tools
- Iteratively search, analyze, and reason
- Extract key findings and insights
- Store results with source citations

**Available Tools:**
- **Search:** DuckDuckGo, Google, Tavily
- **Knowledge:** Wikipedia
- **Academic:** ArXiv
- **Finance:** Stock quotes, history, news, analysis
- **Code Interpreter:** Data analysis and computation

**Research Process:**
1. **Search** - Query multiple sources
2. **Extract** - Pull relevant information
3. **Analyze** - Evaluate quality and relevance
4. **Synthesize** - Combine insights
5. **Verify** - Cross-reference findings
6. **Iterate** - Repeat until questions answered

**Output:** Comprehensive findings per aspect

---

### 7. Dimension Reduction

**Purpose:** Synthesize aspect findings into dimension documents

**Execution:** **Parallel by dimension**

**Actions per dimension:**
- Review all aspect findings for the dimension
- Identify patterns and themes
- Synthesize into coherent narrative
- Highlight key insights and evidence
- Generate dimension-level conclusions

**Output:** Synthesized dimension documents (markdown)

---

### 8. Report Writing

**Purpose:** Create final research report

**Actions:**
- Merge dimension documents
- Generate executive summary
- Create introduction and methodology section
- Structure findings by dimension
- Write conclusions and recommendations
- Edit for clarity and coherence
- Format as markdown

**Report Structure:**
```markdown
# [Research Topic]

## Executive Summary
- Key findings
- Major insights

## Introduction
- Background
- Research scope
- Methodology

## Findings
### Dimension 1: [Name]
- Aspect findings
- Key insights

### Dimension 2: [Name]
...

## Conclusions
- Summary
- Recommendations

## References
- Citations
```

**Output:** Complete markdown report

---

### 9. Chart Generation

**Purpose:** Create data visualizations

**Actions:**
- Analyze report content
- Identify data suitable for visualization
- Generate charts using matplotlib:
  - Bar charts
  - Line graphs
  - Pie charts
  - Comparison tables
- Insert chart images into report
- Add captions and references

**Output:** Report with embedded visualizations

---

### 10. Document Conversion

**Purpose:** Generate multiple output formats

**Actions:**
- Convert markdown to DOCX (Microsoft Word)
- Convert DOCX to PDF
- Preserve formatting and images
- Maintain document structure

**Output:** Report in markdown, DOCX, and PDF formats

---

### 11. Finalize

**Purpose:** Complete research session

**Actions:**
- Upload all outputs to S3:
  - Markdown report
  - Word document
  - PDF document
  - Chart images
- Generate pre-signed URLs (24h expiry)
- Update DynamoDB status to COMPLETED
- Log completion event to Memory
- Clean up workspace

**Output:** Research session metadata with download URLs

---

## Parallelism Strategy

The workflow uses **map-reduce patterns** for efficiency:

### Parallel Execution

1. **Aspect Analysis** - Each dimension analyzed in parallel
2. **Dimension Reduction** - Each dimension synthesized in parallel

### Sequential Execution

1. **Research** - Aspects researched sequentially (Gateway limitation)
2. **Reference Preparation** - References processed one at a time

### Aggregation Barriers

1. **Prepare Research** - Waits for all aspect analysis
2. **Prepare Dimension Reduction** - Waits for all research

## Research Types

The agent supports different research strategies:

### Basic Web
- Tools: DuckDuckGo, Wikipedia
- Best for: General topics, quick research
- Speed: Fast

### Advanced Web
- Tools: Google Search, Tavily, Wikipedia
- Best for: In-depth web research
- Speed: Medium

### Academic
- Tools: ArXiv, Wikipedia, Google Scholar
- Best for: Scientific papers, research publications
- Speed: Medium

### Financial
- Tools: Stock APIs, Financial news, Web search
- Best for: Market research, company analysis
- Speed: Medium

### Comprehensive
- Tools: All available tools
- Best for: Complex topics requiring diverse sources
- Speed: Slower but thorough

## Depth Configurations

Control research thoroughness:

### Quick (2×2)
- Dimensions: 2
- Aspects per dimension: 2
- Total aspects: 4
- Best for: Rapid overview

### Balanced (3×3) 
- Dimensions: 3
- Aspects per dimension: 3
- Total aspects: 9
- Best for: Standard research

### Deep (5×3)
- Dimensions: 5
- Aspects per dimension: 3
- Total aspects: 15
- Best for: Comprehensive analysis

## Memory Integration

### AgentCore Memory
- **Usage:**
  - Store research events and findings
  - Enable semantic search across past research
  - Support chat agent context awareness

### Event Tracking
- Session start/end
- Dimension discoveries
- Aspect completions
- Research findings
- Report generation

### Chat Context
The chat agent can access research memory to:
- Answer questions about past research
- Provide context-aware responses
- Reference specific findings

## Status Tracking

Real-time progress updates via DynamoDB:

**Status Fields:**
- `session_id` - Unique identifier
- `status` - INITIALIZING, RESEARCHING, COMPLETED, FAILED
- `current_stage` - Active workflow node
- `dimensions` - List of identified dimensions
- `aspects` - List of aspects with completion status
- `progress_percentage` - 0-100%
- `start_time` - Session start timestamp
- `update_time` - Last update timestamp
- `output_urls` - S3 pre-signed URLs for downloads

**UI Polling:**
Frontend polls DynamoDB every 2 seconds for live progress updates.

## Cancellation Support

Users can cancel research at any time:
- Graceful shutdown of active agents
- Save partial progress
- Update status to CANCELLED
- Upload partial outputs

## Model Selection

See [MODEL_CONFIGURATION.md](./MODEL_CONFIGURATION.md) for customization.

## Optimization Techniques

### Prompt Caching
- Cache system prompts to reduce costs
- Cache points at agent creation
- Reduce latency for repeated calls

### Reference-Aware Planning
- Skip research for aspects fully answered by references
- Mark aspects as complete during planning
- Focus research on knowledge gaps

### Concurrency Control
- Parallel aspect analysis speeds up planning
- Parallel dimension reduction speeds up synthesis

### Workspace Management
- Organized file structure per session
- Efficient cleanup after completion
- Temporary storage for intermediate outputs

## Quality Assurance

### Source Verification
- Multiple sources per aspect
- Cross-reference findings
- Citation tracking

### Synthesis Quality
- LLM-powered editing
- Coherence checks
- Formatting validation

## Output Formats

### Markdown Report
- Structured with headers
- Embedded images
- Citation links
- Easy to edit

### Word Document (DOCX)
- Professional formatting
- Embedded visualizations
- Compatible with MS Office

### PDF Document
- Print-ready format
- Preserved layout
- Universal compatibility

### Chart Images
- PNG format
- High resolution
- Labeled axes and legends

## Extensibility

### Adding Custom Tools
1. Implement tool function
2. Register in tool catalog
3. Map to research types
4. Update Gateway if Lambda-based

### Custom Workflow Nodes
1. Create node function in `research-agent/src/nodes/`
2. Update workflow graph in `workflow.py`
3. Add to state management
4. Update UI for status tracking

### Custom Models
1. Add to `shared/model_registry.json`
2. Configure combinations
3. Update frontend model selector
4. Test with workflow

---

For deployment and configuration details, see:
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment guide
- [MODEL_CONFIGURATION.md](./MODEL_CONFIGURATION.md) - Model setup
- [README.md](./README.md) - Quick start guide
