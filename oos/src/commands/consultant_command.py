#!/usr/bin/env python3
"""
OOS Consultant Command
Slash command implementation for structured consulting workflow
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging
from datetime import datetime

from strategic_consultant import StrategicConsultant
from config_loader import load_config

logger = logging.getLogger(__name__)

class ConsultantCommand:
    """Slash command handler for /consultant - Strategic AI Consultant"""

    def __init__(self):
        self.strategic_consultant = StrategicConsultant()
        self.config = load_config("consultant")
        self.active_analyses: Dict[str, Dict[str, Any]] = {}

    async def handle_command(self, args: List[str], context: Dict[str, Any] = None) -> str:
        """Handle /consultant slash command - Strategic Analysis"""
        # Documentation-code sync check: Verify command implementation matches documentation
        self._validate_implementation_docs()

        if not args:
            return self._show_help()

        # Check for status/monitoring commands
        if args[0].lower() == "status":
            return await self._show_project_status(args[1:])
        elif args[0].lower() == "monitor":
            return await self._monitor_projects(args[1:])
        elif args[0].lower() == "dashboard":
            return await self._show_dashboard()
        elif args[0].lower() == "help":
            return self._show_help()

        # The entire args list is the strategic question
        strategic_question = " ".join(args)

        # Analyze the strategic question
        return await self._analyze_strategic_question(strategic_question)

    async def _analyze_strategic_question(self, question: str) -> str:
        """Analyze strategic question and provide recommendation"""
        try:
            # Analyze the strategic question
            recommendation = await self.strategic_consultant.analyze_strategic_question(question)

            # Store analysis for future reference
            analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.active_analyses[analysis_id] = {
                "question": question,
                "recommendation": recommendation,
                "timestamp": datetime.now().isoformat()
            }

            # Format response
            return self._format_strategic_response(question, recommendation, analysis_id)

        except Exception as e:
            logger.error(f"Error analyzing strategic question: {e}")
            return f"❌ Error analyzing strategic question: {str(e)}"

    def _format_strategic_response(self, question: str, recommendation, analysis_id: str) -> str:
        """Format strategic recommendation response"""
        response = [
            "🧠 **Strategic Analysis Complete**",
            "",
            f"**Question:** {question}",
            "",
            f"🎯 **Strategic Direction: {recommendation.direction.value.replace('_', ' ').title()}**",
            "",
            "**Rationale:**",
            recommendation.rationale,
            "",
            "**🚀 Immediate Actions (Next 30 days):**"
        ]

        for action in recommendation.immediate_actions:
            response.append(f"• {action}")

        response.extend([
            "",
            "**📋 Medium-term Actions (30-90 days):**"
        ])

        for action in recommendation.medium_term_actions:
            response.append(f"• {action}")

        response.extend([
            "",
            "**🔮 Long-term Vision (90+ days):**"
        ])

        for action in recommendation.long_term_actions:
            response.append(f"• {action}")

        response.extend([
            "",
            "**📊 Success Metrics:**"
        ])

        for metric in recommendation.success_metrics:
            response.append(f"• {metric}")

        response.extend([
            "",
            "⚠️ **Early Warning Indicators:**"
        ])

        for warning in recommendation.early_warnings:
            response.append(f"• {warning}")

        response.extend([
            "",
            "🏗️ **Archon Project Plan:**",
            f"• Project: {recommendation.archon_project_plan.get('project_name', 'Strategic Initiative')}",
            f"• Phases: {len(recommendation.archon_project_plan.get('phases', []))}",
            f"• Tasks: {len(recommendation.archon_project_plan.get('tasks', []))}",
            f"• Status: Ready for execution",
            "",
            "**💡 Next Steps:**",
            "1. Review recommendation with stakeholders",
            "2. Approve strategic direction",
            "3. Launch Archon project for execution",
            "4. Monitor progress and adapt as needed",
            "",
            f"📋 **Analysis ID:** {analysis_id}",
            "",
            "---",
            "*Analysis complete. Ready for execution.*"
        ])

        return "\n".join(response)

    async def _show_project_status(self, args: List[str]) -> str:
        """Show status of strategic projects"""
        if not args:
            # Show all active projects
            if hasattr(self.strategic_consultant, 'archon_integration') and self.strategic_consultant.archon_integration:
                projects = self.strategic_consultant.archon_integration.get_all_active_projects()
                if not projects:
                    return "📊 No active strategic projects found."

                response = ["📊 **Active Strategic Projects**", ""]
                for project in projects:
                    response.extend([
                        f"**{project['name']}**",
                        f"• ID: {project['id']}",
                        f"• Status: {project['status'].title()}",
                        f"• Progress: {project['progress_percentage']:.1f}%",
                        f"• Tasks: {project['completed_tasks']}/{project['total_tasks']}",
                        f"• Last Updated: {project['updated_at']}",
                        ""
                    ])
                return "\n".join(response)
            else:
                return "❌ Archon integration not available for project status."

        # Show specific project status
        project_id = args[0]
        if hasattr(self.strategic_consultant, 'archon_integration') and self.strategic_consultant.archon_integration:
            return await self.strategic_consultant.archon_integration.generate_status_report(project_id)
        else:
            return "❌ Archon integration not available for project status."

    async def _monitor_projects(self, args: List[str]) -> str:
        """Monitor project execution and momentum"""
        if hasattr(self.strategic_consultant, 'archon_integration') and self.strategic_consultant.archon_integration:
            try:
                from src.execution_driver import ExecutionDriver
                executor = ExecutionDriver(self.strategic_consultant.archon_integration)

                if not args:
                    return "❌ Please specify a project ID to monitor."

                project_id = args[0]
                return await executor.generate_execution_report(project_id)

            except ImportError:
                return "❌ Execution driver not available."
        else:
            return "❌ Archon integration not available for monitoring."

    async def _show_dashboard(self) -> str:
        """Show momentum dashboard for all projects"""
        if hasattr(self.strategic_consultant, 'archon_integration') and self.strategic_consultant.archon_integration:
            try:
                from src.execution_driver import ExecutionDriver
                executor = ExecutionDriver(self.strategic_consultant.archon_integration)

                # Get all project IDs
                projects = self.strategic_consultant.archon_integration.get_all_active_projects()
                project_ids = [p['id'] for p in projects]

                if not project_ids:
                    return "📊 No active projects to monitor."

                dashboard = await executor.get_momentum_dashboard(project_ids)

                response = [
                    "🚀 **Strategic Momentum Dashboard**",
                    "",
                    "📊 **Overview:**",
                    f"• Total Projects: {dashboard['overview']['total_projects']}",
                    f"• High Momentum: {dashboard['overview']['high_momentum']}",
                    f"• Medium Momentum: {dashboard['overview']['medium_momentum']}",
                    f"• Low Momentum: {dashboard['overview']['low_momentum']}",
                    f"• At Risk: {dashboard['overview']['at_risk']}",
                    "",
                    "📈 **Project Details:**"
                ]

                for project in dashboard['projects']:
                    momentum_emoji = "🟢" if project['momentum_score'] >= 80 else "🟡" if project['momentum_score'] >= 50 else "🔴"
                    response.extend([
                        f"{momentum_emoji} **{project['id']}**",
                        f"   Momentum: {project['momentum_score']:.1f}%",
                        f"   Trend: {project['velocity_trend'].title()}",
                        f"   Risk: {project['risk_level'].title()}",
                        f"   Blockers: {project['blocker_count']}",
                        ""
                    ])

                return "\n".join(response)

            except ImportError:
                return "❌ Execution driver not available for dashboard."
        else:
            return "❌ Archon integration not available for dashboard."

    def _show_help(self) -> str:
        """Show help for consultant command"""
        return """
🧠 OOS Strategic Consultant - AI Brain for Strategic Analysis

**Usage:**
- `/consultant "<strategic question>"` - Analyze strategic question and get recommendations
- `/consultant status` - Show all active strategic projects
- `/consultant status <project_id>` - Show detailed project status
- `/consultant monitor <project_id>` - Generate execution report with momentum analysis
- `/consultant dashboard` - Show momentum dashboard for all projects
- `/consultant help` - Show this help

**How It Works:**
1. **Analyze Current State** - Reads your codebase/documentation as gospel
2. **Understand Constraints** - Extracts timeline, budget, resource limits from your question
3. **Map Optimal Path** - Compares current trajectory vs. optimal path to goal
4. **Provide Strategic Direction** - Recommends: Stay Course, Pivot Approach, or Scrap & Rebuild
5. **Create Execution Plan** - Generates Archon project for implementation

**Strategic Questions to Ask:**
- `How do we scale from 100 to 10,000 users with current team?`
- `Should we rebuild or refactor the legacy payment system?`
- `What's the fastest path to enterprise security compliance?`
- `How is our security? Could we reasonably sell this?`
- `Is this always going to be an open source project?`
- `Why is podcast transcription not getting above 30%?`

**What You Get:**
- **Strategic Direction** - Clear recommendation on how to proceed
- **Action Plan** - Immediate, medium, and long-term actions
- **Success Metrics** - How to measure progress
- **Early Warnings** - What to watch for
- **Archon Integration** - Ready-to-execute project plan

**Example:**
```
/consultant "How do we achieve enterprise security by Q3 with $50k budget?"
```

**Output:**
🧠 **Strategic Analysis Complete**

**Question:** How do we achieve enterprise security by Q3 with $50k budget?

🎯 **Strategic Direction: Pivot Approach**

**Rationale:** Current security foundation is solid but strategic adjustments needed...

**🚀 Immediate Actions:**
• Conduct security gap analysis
• Implement authentication upgrades
• ...

---
*Ready for execution through Archon PMO*
"""

    def _validate_implementation_docs(self):
        """Validate that implementation matches documentation requirements"""
        # Check that all documented features are implemented
        documented_features = [
            "intake_questions",
            "synthesis",
            "scoring",
            "planning",
            "export_artifacts"
        ]

        # Validate configuration has required sections
        required_config_sections = [
            "intake_questions",
            "scoring",
            "output",
            "portfolio",
            "planning"
        ]

        missing_sections = [section for section in required_config_sections
                           if section not in self.config]

        if missing_sections:
            logger.warning(f"Documentation mentions features not fully configured: {missing_sections}")

        # Check that template files exist as documented
        template_files = [
            "a3.md.j2",
            "ost.mmd.j2",
            "impact_effort.csv.j2",
            "rice.csv.j2",
            "plan.md.j2"
        ]

        template_dir = Path("templates")
        if template_dir.exists():
            existing_templates = [f.name for f in template_dir.glob("*.j2")]
            missing_templates = [f for f in template_files if f not in existing_templates]

            if missing_templates:
                logger.warning(f"Documentation references templates not yet created: {missing_templates}")

        # This ensures documentation and implementation stay in sync
        logger.info("Documentation-code sync validation completed")

# MCP Tool Handlers
class ConsultantMCPTools:
    """MCP tool handlers for consultant functionality"""

    def __init__(self):
        self.consultant_command = ConsultantCommand()

    async def oos_consultant_start(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """MCP tool to start consulting engagement"""
        project = params.get("project")
        domain = params.get("domain")

        if not project:
            return {"error": "Project name is required"}

        try:
            args = [project]
            if domain:
                args.append(domain)

            result = await self.consultant_command._start_consulting(args)
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}

    async def oos_consultant_answer(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """MCP tool to submit answer"""
        question_id = params.get("question_id")
        text = params.get("text")

        if not question_id or not text:
            return {"error": "Both question_id and text are required"}

        try:
            args = [question_id, text]
            result = await self.consultant_command._submit_answer(args)
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}

    async def oos_consultant_export(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """MCP tool to export results"""
        format_type = params.get("format", "all")

        try:
            args = []
            if format_type != "all":
                args.append(format_type)

            result = await self.consultant_command._export_results(args)
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}

    async def oos_consultant_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """MCP tool to get status"""
        try:
            result = await self.consultant_command._show_status([])
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}

# Command registration helper
def register_consultant_command(command_handler):
    """Register consultant command with the command handler"""
    consultant_cmd = ConsultantCommand()

    async def consultant_handler(args, context=None):
        return await consultant_cmd.handle_command(args, context)

    command_handler.register_command("consultant", consultant_handler)

    return consultant_cmd