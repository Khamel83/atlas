#!/usr/bin/env python3
"""
OOS Context Engineering MCP Server

Provides context engineering capabilities as slash commands in Claude Code.
Install once, use everywhere with automatic optimization.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

# MCP imports
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource, Tool, TextContent, ImageContent, EmbeddedResource,
    CallToolRequest, CallToolResult, ListResourcesRequest, ListResourcesResult,
    ListToolsRequest, ListToolsResult, ReadResourceRequest, ReadResourceResult
)

# OOS imports
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from clarification_workflow import get_clarification_workflow, ClarificationResponse
from token_optimization import optimize_for_budget, estimate_context_tokens
from auto_documentation import get_auto_documentation_system


class OOSContextEngineeringServer:
    """OOS Context Engineering MCP Server"""

    def __init__(self):
        self.server = Server("oos-context-engineering")
        self.logger = logging.getLogger("oos-mcp")

        # Initialize systems
        self.clarification_workflow = get_clarification_workflow()
        self.auto_doc_system = get_auto_documentation_system()

        # Auto-optimization settings
        self.auto_optimize = True
        self.token_budget = 4000

        self._setup_handlers()

    def _setup_handlers(self):
        """Setup MCP handlers"""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available context engineering tools"""
            return [
                Tool(
                    name="help_me",
                    description="Smart context engineering help - automatically analyzes and optimizes your request",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "request": {"type": "string", "description": "Your request or question"}
                        },
                        "required": ["request"]
                    }
                ),
                Tool(
                    name="brain_dump",
                    description="Process rambling/messy input into clear, structured requests with auto-optimization",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "rambling_input": {"type": "string", "description": "Your unstructured thoughts or requests"}
                        },
                        "required": ["rambling_input"]
                    }
                ),
                Tool(
                    name="clarify",
                    description="Get targeted clarification questions for vague requests",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "vague_request": {"type": "string", "description": "The unclear request that needs clarification"}
                        },
                        "required": ["vague_request"]
                    }
                ),
                Tool(
                    name="meta_ai",
                    description="Generate prompt for external AI assistance (ChatGPT, Claude, etc.)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "questions": {"type": "string", "description": "Current clarification questions or context"}
                        },
                        "required": ["questions"]
                    }
                ),
                Tool(
                    name="optimize_context",
                    description="Optimize current context for token efficiency",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "context": {"type": "object", "description": "Context to optimize"},
                            "target_tokens": {"type": "number", "description": "Target token count", "default": 3000}
                        },
                        "required": ["context"]
                    }
                ),
                Tool(
                    name="smart_commit",
                    description="Generate intelligent commit message for current changes",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "changed_files": {"type": "array", "items": {"type": "string"}, "description": "List of changed files"}
                        },
                        "required": ["changed_files"]
                    }
                ),
                Tool(
                    name="doc_check",
                    description="Check documentation completeness and code consistency",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_paths": {"type": "array", "items": {"type": "string"}, "description": "Files to check"}
                        },
                        "required": ["file_paths"]
                    }
                ),
                Tool(
                    name="context_stats",
                    description="Show current context token usage and optimization statistics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "context": {"type": "object", "description": "Context to analyze", "default": {}}
                        }
                    }
                ),
                Tool(
                    name="auto_workflow",
                    description="Start automatic structured workflow for complex tasks",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "complex_task": {"type": "string", "description": "Complex task description"}
                        },
                        "required": ["complex_task"]
                    }
                ),
                Tool(
                    name="toggle_auto_optimize",
                    description="Toggle automatic context optimization on/off",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "enabled": {"type": "boolean", "description": "Enable or disable auto-optimization"}
                        },
                        "required": ["enabled"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls"""

            try:
                if name == "help_me":
                    return await self._help_me(arguments["request"])

                elif name == "brain_dump":
                    return await self._brain_dump(arguments["rambling_input"])

                elif name == "clarify":
                    return await self._clarify(arguments["vague_request"])

                elif name == "meta_ai":
                    return await self._meta_ai(arguments["questions"])

                elif name == "optimize_context":
                    return await self._optimize_context(
                        arguments["context"],
                        arguments.get("target_tokens", 3000)
                    )

                elif name == "smart_commit":
                    return await self._smart_commit(arguments["changed_files"])

                elif name == "doc_check":
                    return await self._doc_check(arguments["file_paths"])

                elif name == "context_stats":
                    return await self._context_stats(arguments.get("context", {}))

                elif name == "auto_workflow":
                    return await self._auto_workflow(arguments["complex_task"])

                elif name == "toggle_auto_optimize":
                    return await self._toggle_auto_optimize(arguments["enabled"])

                else:
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"Unknown tool: {name}")]
                    )

            except Exception as e:
                self.logger.error(f"Error in tool {name}: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")]
                )

    async def _help_me(self, request: str) -> CallToolResult:
        """Smart help with automatic optimization"""

        # Auto-optimize if enabled
        if self.auto_optimize:
            context = {"user_request": request}
            original_tokens = await estimate_context_tokens(context)

            if original_tokens > self.token_budget:
                optimized_context, opt_result = await optimize_for_budget(context, self.token_budget)
                optimization_info = f"\n🔧 Auto-optimized: {opt_result.reduction_percentage:.1f}% token reduction\n"
            else:
                optimization_info = ""
        else:
            optimization_info = ""

        # Process through clarification workflow
        session = await self.clarification_workflow.start_workflow(request)

        response = f"""🧠 Smart Context Engineering Analysis
{optimization_info}
📊 Input Analysis:
   • Intent: {session.cleaned_input.extracted_intent}
   • Confidence: {session.cleaned_input.confidence:.1%}
   • Entities found: {len(session.cleaned_input.key_entities)}

"""

        if session.cleaned_input.confidence < 0.7:
            response += "❓ Clarification needed. Use /clarify for targeted questions.\n"
            response += "💡 Tip: Use /meta-ai to get external AI help with responses.\n"
        else:
            response += "✅ Request is clear! Ready to proceed.\n"

            if session.cleaned_input.extracted_intent == "optimization":
                response += "\n🔧 I'll help you optimize with systematic analysis and recommendations."
            elif session.cleaned_input.extracted_intent == "implementation":
                response += "\n🏗️ I'll guide you through structured implementation planning."
            elif session.cleaned_input.extracted_intent == "analysis":
                response += "\n🔍 I'll provide comprehensive analysis and insights."

        response += f"\n\n🚀 What would you like to focus on first?"

        return CallToolResult(
            content=[TextContent(type="text", text=response)]
        )

    async def _brain_dump(self, rambling_input: str) -> CallToolResult:
        """Process messy input into structured format"""

        # Process through input processor
        session = await self.clarification_workflow.start_workflow(rambling_input)

        response = f"""🧹 Brain Dump Processing Complete!

📝 **Original input cleaned and structured:**

**Intent detected:** {session.cleaned_input.extracted_intent}
**Key entities:** {', '.join(session.cleaned_input.key_entities) if session.cleaned_input.key_entities else 'None identified'}

**Structured version:** {session.cleaned_input.cleaned_text}

"""

        if session.cleaned_input.ambiguities:
            response += f"⚠️ **Ambiguities to clarify:**\n"
            for ambiguity in session.cleaned_input.ambiguities:
                response += f"   • {ambiguity}\n"
            response += "\n💡 Use /clarify to get specific questions about these ambiguities.\n"

        if session.cleaned_input.confidence > 0.7:
            response += "✅ **Ready to proceed!** Your thoughts are now clear and actionable.\n"
        else:
            response += "❓ **Needs refinement.** Use /clarify to get targeted questions.\n"

        # Auto-optimize the context
        if self.auto_optimize:
            context = {
                "original_input": rambling_input,
                "processed_input": session.cleaned_input.cleaned_text,
                "session_data": session.cleaned_input.__dict__
            }

            original_tokens = await estimate_context_tokens(context)
            if original_tokens > 2000:
                optimized_context, result = await optimize_for_budget(context, 2000)
                response += f"\n🔧 Context auto-optimized: {result.reduction_percentage:.1f}% reduction"

        return CallToolResult(
            content=[TextContent(type="text", text=response)]
        )

    async def _clarify(self, vague_request: str) -> CallToolResult:
        """Generate clarification questions"""

        session = await self.clarification_workflow.start_workflow(vague_request)

        if not session.questions:
            return CallToolResult(
                content=[TextContent(type="text", text="✅ Your request is already clear! No clarification needed.")]
            )

        response = f"""❓ **Clarification Questions for:** "{vague_request}"

**Confidence level:** {session.cleaned_input.confidence:.1%}

"""

        for i, question in enumerate(session.questions, 1):
            response += f"**{i}. {question.text}**\n"

            if question.options:
                for j, option in enumerate(question.options, 1):
                    response += f"   {j}) {option}\n"
                response += "\n"
            else:
                response += "   (Open-ended response needed)\n\n"

        response += "💡 **Pro tip:** Use /meta-ai to generate a prompt for getting help with these questions from ChatGPT or another AI.\n"
        response += "🔄 Once you have answers, I can create a detailed implementation plan."

        return CallToolResult(
            content=[TextContent(type="text", text=response)]
        )

    async def _meta_ai(self, questions: str) -> CallToolResult:
        """Generate meta-AI prompt"""

        # Create a structured prompt for external AI
        prompt = f"""I'm working with a clarification system and need help formulating optimal responses to these questions.

**Context**: Working on a software development task that needs clarification.

**Questions to Answer**:
{questions}

**Please provide**:
1. Your recommended answers to each question
2. Brief reasoning for each choice
3. Any additional context that would be helpful

**Format your response as**:
Question 1: [Your answer] - [Brief reasoning]
Question 2: [Your answer] - [Brief reasoning]
Additional context: [Any relevant context or suggestions]

Focus on being clear, specific, and technically accurate. Consider what would lead to the most successful outcome.
"""

        response = f"""🤖 **Meta-AI Assistance Prompt**

Copy this entire prompt to ChatGPT, Claude, or any other AI to get structured help:

```
{prompt}
```

**How to use:**
1. Copy the prompt above
2. Paste it into ChatGPT or another Claude instance
3. Get the AI's structured response
4. Come back and use those answers in your workflow

**What you'll get:**
• Clear, structured answers to each question
• Technical reasoning behind the suggestions
• Additional context and recommendations

**After you get the response:** Just continue our conversation with the AI's suggestions and I'll create an optimized implementation plan!
"""

        return CallToolResult(
            content=[TextContent(type="text", text=response)]
        )

    async def _optimize_context(self, context: Dict[str, Any], target_tokens: int) -> CallToolResult:
        """Optimize context for token efficiency"""

        original_tokens = await estimate_context_tokens(context)

        if original_tokens <= target_tokens:
            return CallToolResult(
                content=[TextContent(type="text", text=f"✅ Context already optimized: {original_tokens} tokens (target: {target_tokens})")]
            )

        optimized_context, result = await optimize_for_budget(context, target_tokens)

        response = f"""🔧 **Context Optimization Complete**

**Results:**
• Original: {result.original_tokens} tokens
• Optimized: {result.optimized_tokens} tokens
• Reduction: {result.reduction_percentage:.1f}%
• Techniques: {', '.join(result.techniques_used)}

**Details:**
• Chunks offloaded: {result.chunks_offloaded}
• Chunks compressed: {result.chunks_compressed}
• Cache hits: {result.cache_hits}

✅ Context now fits within your {target_tokens} token budget!
"""

        return CallToolResult(
            content=[TextContent(type="text", text=response)]
        )

    async def _smart_commit(self, changed_files: List[str]) -> CallToolResult:
        """Generate smart commit message"""

        message = await self.auto_doc_system.git_integration.suggest_commit_message(changed_files)

        response = f"""📝 **Smart Commit Message Generated**

```
{message}
```

**Files included:** {len(changed_files)} files
• {chr(10).join(f'  • {file}' for file in changed_files[:5])}
{f'  • ... and {len(changed_files) - 5} more' if len(changed_files) > 5 else ''}

**Features:**
✅ Conventional commit format
✅ Automatic scope detection
✅ Claude Code attribution
✅ Co-author credit

**To use:** Copy the commit message above when you're ready to commit.
"""

        return CallToolResult(
            content=[TextContent(type="text", text=response)]
        )

    async def _doc_check(self, file_paths: List[str]) -> CallToolResult:
        """Check documentation and consistency"""

        result = await self.auto_doc_system.process_files(file_paths)

        response = f"""📚 **Documentation & Consistency Check**

**Summary:**
• Files processed: {len(result.files_processed)}
• Documentation gaps: {len(result.documentation_generated)}
• Consistency issues: {len(result.consistency_issues)}

"""

        if result.consistency_issues:
            response += "**Issues found:**\n"
            for issue in result.consistency_issues[:5]:
                severity_icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}[issue['severity']]
                response += f"{severity_icon} {Path(issue['file']).name}:{issue['line']} - {issue['message']}\n"

            if len(result.consistency_issues) > 5:
                response += f"... and {len(result.consistency_issues) - 5} more issues\n"

        if result.documentation_generated:
            response += f"\n**Documentation needed:**\n"
            for doc in result.documentation_generated[:3]:
                response += f"• {doc}\n"

        auto_fixable = len([i for i in result.consistency_issues if i.get('auto_fix', False)])
        if auto_fixable > 0:
            response += f"\n💡 {auto_fixable} issues can be auto-fixed! Use /auto-fix to apply them."

        if result.commit_suggested and result.commit_message:
            response += f"\n📝 Suggested commit message ready! Use /smart-commit to see it."

        return CallToolResult(
            content=[TextContent(type="text", text=response)]
        )

    async def _context_stats(self, context: Dict[str, Any]) -> CallToolResult:
        """Show context statistics"""

        tokens = await estimate_context_tokens(context) if context else 0

        # Get optimization stats
        from token_optimization import get_token_optimizer
        optimizer = get_token_optimizer()
        opt_stats = optimizer.get_optimization_stats()

        response = f"""📊 **Context Engineering Statistics**

**Current Context:**
• Estimated tokens: {tokens}
• Auto-optimization: {'🟢 Enabled' if self.auto_optimize else '🔴 Disabled'}
• Token budget: {self.token_budget}

**Cache Performance:**
• Memory cache size: {opt_stats['cache']['memory_cache_size']}
• Cache hit rate: {opt_stats['cache']['hit_rate']:.1%}
• Total cache hits: {opt_stats['cache']['cache_hits']}

**Storage Usage:**
• Offloaded chunks: {opt_stats['offload']['total_chunks']}
• Storage size: {opt_stats['offload']['storage_size_mb']:.1f} MB
• Total storage: {opt_stats['total_storage_mb']:.1f} MB

**Tips:**
• Use /optimize-context to manually optimize large contexts
• Use /toggle-auto-optimize to control automatic optimization
• Context is automatically optimized when over {self.token_budget} tokens
"""

        return CallToolResult(
            content=[TextContent(type="text", text=response)]
        )

    async def _auto_workflow(self, complex_task: str) -> CallToolResult:
        """Start automatic workflow for complex tasks"""

        # Start workflow and auto-optimize
        session = await self.clarification_workflow.start_workflow(complex_task)

        response = f"""🔄 **Automatic Workflow Started**

**Task:** {complex_task}

**Analysis:**
• Intent: {session.cleaned_input.extracted_intent}
• Confidence: {session.cleaned_input.confidence:.1%}
• Complexity: {'High' if len(session.cleaned_input.ambiguities) > 2 else 'Medium' if session.cleaned_input.ambiguities else 'Low'}

"""

        if session.questions:
            response += "**Workflow Steps:**\n"
            response += "1. ❓ Clarification needed (use /clarify for questions)\n"
            response += "2. 🎯 Planning phase (after clarification)\n"
            response += "3. 🚀 Implementation guidance\n"
            response += "4. ✅ Validation and testing\n\n"
            response += "**Next:** Use /clarify to get specific clarification questions.\n"
            response += "**Pro tip:** Use /meta-ai to get external help with the questions."
        else:
            response += "**Workflow Steps:**\n"
            response += "1. ✅ Input analysis complete\n"
            response += "2. 🎯 Planning phase (ready)\n"
            response += "3. 🚀 Implementation guidance\n"
            response += "4. ✅ Validation and testing\n\n"
            response += "**Ready to proceed!** What aspect would you like me to focus on first?"

        # Auto-optimize context
        if self.auto_optimize:
            context = {"task": complex_task, "session": session.cleaned_input.__dict__}
            tokens = await estimate_context_tokens(context)
            if tokens > self.token_budget:
                response += f"\n🔧 Context auto-optimized for efficiency"

        return CallToolResult(
            content=[TextContent(type="text", text=response)]
        )

    async def _toggle_auto_optimize(self, enabled: bool) -> CallToolResult:
        """Toggle auto-optimization"""

        self.auto_optimize = enabled
        status = "enabled" if enabled else "disabled"
        icon = "🟢" if enabled else "🔴"

        response = f"""{icon} **Auto-optimization {status}**

**Current settings:**
• Auto-optimize: {status}
• Token budget: {self.token_budget}

**What this means:**
"""

        if enabled:
            response += """• Context will be automatically optimized when it exceeds your token budget
• Token usage will be minimized without you having to think about it
• Large contexts will be compressed and offloaded intelligently
• All slash commands will include automatic optimization"""
        else:
            response += """• Context will NOT be automatically optimized
• You'll need to manually use /optimize-context when needed
• Token usage may be higher but you have full control
• Slash commands will work normally but without auto-optimization"""

        response += f"\n\n💡 Use /toggle-auto-optimize {not enabled} to switch back anytime."

        return CallToolResult(
            content=[TextContent(type="text", text=response)]
        )


async def main():
    """Run the MCP server"""

    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Create and run server
    oos_server = OOSContextEngineeringServer()

    # Run stdio server
    async with stdio_server() as streams:
        await oos_server.server.run(
            streams[0], streams[1],
            InitializationOptions(
                server_name="oos-context-engineering",
                server_version="1.0.0",
                capabilities={}
            )
        )


if __name__ == "__main__":
    asyncio.run(main())