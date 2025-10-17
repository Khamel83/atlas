#!/usr/bin/env python3
"""
Strategic Consultant - AI Consultant Brain
Analyzes current state, maps optimal paths, drives execution through Archon
"""

import asyncio
import json
import yaml
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class StrategicDirection(Enum):
    STAY_COURSE = "stay_course"  # Current trajectory is optimal
    PIVOT_APPROACH = "pivot_approach"  # Modify current path
    SCRAP_AND_REBUILD = "scrap_and_rebuild"  # New direction needed

@dataclass
class CurrentState:
    """Analysis of current project state"""
    project_structure: Dict[str, Any]
    tech_stack: List[str]
    documentation_quality: float  # 0-1 score
    code_quality_metrics: Dict[str, float]
    team_capacity: Dict[str, Any]
    current_roadmap: Optional[Dict[str, Any]]
    constraints: Dict[str, Any]
    risks: List[str]
    opportunities: List[str]

@dataclass
class DesiredFuture:
    """Defined future state and goals"""
    primary_objective: str
    success_metrics: List[str]
    timeline_constraints: Dict[str, str]
    budget_constraints: Dict[str, Any]
    quality_requirements: List[str]
    strategic_priorities: List[str]

@dataclass
class PathAnalysis:
    """Analysis of current vs optimal path"""
    current_trajectory: Dict[str, Any]
    optimal_path: Dict[str, Any]
    gap_analysis: List[str]
    recommendations: List[str]
    estimated_timeline: Dict[str, str]
    resource_requirements: Dict[str, Any]
    risk_assessment: List[Dict[str, Any]]
    strategic_direction: StrategicDirection

@dataclass
class ConsultantRecommendation:
    """Final strategic recommendation"""
    direction: StrategicDirection
    rationale: str
    immediate_actions: List[str]
    medium_term_actions: List[str]
    long_term_actions: List[str]
    success_metrics: List[str]
    early_warnings: List[str]
    archon_project_plan: Dict[str, Any]

class StrategicConsultant:
    """
    AI Consultant Brain - Analyzes, plans, and drives execution
    """

    def __init__(self):
        self.project_root = Path.cwd()
        self.config = self._load_config()

        # Initialize Archon integration
        try:
            from src.archon_integration import ArchonIntegration
            self.archon_integration = ArchonIntegration()
        except ImportError:
            logger.warning("Archon integration not available")
            self.archon_integration = None

    def _load_config(self) -> Dict[str, Any]:
        """Load consultant configuration"""
        try:
            with open("config/consultant.yaml", "r") as f:
                return yaml.safe_load(f)
        except:
            # Default config
            return {
                "analysis": {
                    "max_file_size": 1000000,  # 1MB
                    "documentation_threshold": 0.7,
                    "code_quality_threshold": 0.6
                },
                "planning": {
                    "default_timeline": "90 days",
                    "buffer_percentage": 0.2
                },
                "archon": {
                    "auto_create_projects": True,
                    "update_frequency": "daily"
                }
            }

    async def analyze_strategic_question(self, question: str) -> ConsultantRecommendation:
        """
        Main entry point - analyze strategic question and provide recommendation
        """
        logger.info(f"Analyzing strategic question: {question}")

        # Parse question to understand objective and constraints
        desired_future = self._parse_strategic_question(question)

        # Analyze current state
        current_state = await self._analyze_current_state()

        # Map optimal path
        path_analysis = self._map_optimal_path(current_state, desired_future)

        # Generate recommendation
        recommendation = self._generate_recommendation(path_analysis, current_state, desired_future)

        # Create Archon project plan
        recommendation.archon_project_plan = await self._create_archon_plan(recommendation, desired_future.primary_objective)

        logger.info(f"Strategic analysis complete. Direction: {recommendation.direction.value}")
        return recommendation

    def _parse_strategic_question(self, question: str) -> DesiredFuture:
        """Parse strategic question to extract objectives and constraints"""
        # Extract key information patterns
        scaling_pattern = r"scale from (\d+) to (\d+)"
        timeline_pattern = r"by (Q[1-4]| \d+ weeks| \d+ months)"
        budget_pattern = r"(\$?\d+[kKmM]|budget \$?\d+)"

        desired_future = DesiredFuture(
            primary_objective=question,
            success_metrics=self._extract_success_metrics(question),
            timeline_constraints=self._extract_timeline_constraints(question),
            budget_constraints=self._extract_budget_constraints(question),
            quality_requirements=["Production-ready", "Maintainable", "Scalable"],
            strategic_priorities=self._extract_strategic_priorities(question)
        )

        return desired_future

    async def _analyze_current_state(self) -> CurrentState:
        """Analyze current project state using documentation as gospel"""
        logger.info("Analyzing current project state")

        # Analyze project structure
        project_structure = self._analyze_project_structure()

        # Identify tech stack
        tech_stack = self._identify_tech_stack()

        # Assess documentation quality
        documentation_quality = self._assess_documentation()

        # Code quality metrics
        code_quality = self._analyze_code_quality()

        # Team capacity (from documentation)
        team_capacity = self._extract_team_capacity()

        # Current roadmap
        current_roadmap = self._extract_current_roadmap()

        # Constraints and risks
        constraints = self._identify_constraints()
        risks = self._identify_risks()
        opportunities = self._identify_opportunities()

        return CurrentState(
            project_structure=project_structure,
            tech_stack=tech_stack,
            documentation_quality=documentation_quality,
            code_quality_metrics=code_quality,
            team_capacity=team_capacity,
            current_roadmap=current_roadmap,
            constraints=constraints,
            risks=risks,
            opportunities=opportunities
        )

    def _analyze_project_structure(self) -> Dict[str, Any]:
        """Analyze project directory structure"""
        structure = {
            "directories": [],
            "key_files": [],
            "total_files": 0,
            "languages": [],
            "frameworks": []
        }

        for item in self.project_root.rglob("*"):
            if item.is_dir():
                if not item.name.startswith('.'):
                    structure["directories"].append(str(item.relative_to(self.project_root)))
            elif item.is_file():
                structure["total_files"] += 1
                rel_path = str(item.relative_to(self.project_root))
                if item.suffix in ['.py', '.js', '.ts', '.java', '.go', '.rs']:
                    structure["key_files"].append(rel_path)
                    if item.suffix not in structure["languages"]:
                        structure["languages"].append(item.suffix)

        return structure

    def _identify_tech_stack(self) -> List[str]:
        """Identify technology stack from files"""
        tech_stack = []

        # Check for package files
        package_files = {
            "requirements.txt": "Python",
            "package.json": "Node.js",
            "pom.xml": "Java",
            "go.mod": "Go",
            "Cargo.toml": "Rust"
        }

        for file, tech in package_files.items():
            if (self.project_root / file).exists():
                tech_stack.append(tech)

        # Check for frameworks
        if any((self.project_root / "src").rglob("*.js")):
            tech_stack.append("JavaScript")
        if any((self.project_root / "src").rglob("*.py")):
            tech_stack.append("Python")

        return tech_stack

    def _assess_documentation(self) -> float:
        """Assess documentation quality (0-1)"""
        doc_files = ["README.md", "README", "docs/", "documentation/"]
        score = 0.0

        for doc in doc_files:
            doc_path = self.project_root / doc
            if doc_path.exists():
                if doc_path.is_file():
                    content = doc_path.read_text()
                    if len(content) > 500:  # Substantial content
                        score += 0.3
                elif doc_path.is_dir():
                    files = list(doc_path.rglob("*.md"))
                    if len(files) > 3:
                        score += 0.4

        return min(score, 1.0)

    def _analyze_code_quality(self) -> Dict[str, float]:
        """Analyze code quality metrics"""
        metrics = {
            "test_coverage": 0.0,
            "complexity_score": 0.0,
            "duplication_rate": 0.0,
            "maintainability_index": 0.0
        }

        # Look for test files
        test_files = list(self.project_root.rglob("*test*.py")) + list(self.project_root.rglob("test_*.py"))
        total_py_files = list(self.project_root.rglob("*.py"))
        if total_py_files:
            metrics["test_coverage"] = len(test_files) / len(total_py_files)

        # Simple heuristics for other metrics
        metrics["maintainability_index"] = 0.7  # Default assumption

        return metrics

    def _extract_team_capacity(self) -> Dict[str, Any]:
        """Extract team capacity from documentation"""
        capacity = {
            "team_size": "Unknown",
            "skill_areas": [],
            "availability": "Unknown"
        }

        # Look for team info in README or docs
        readme_path = self.project_root / "README.md"
        if readme_path.exists():
            content = readme_path.read_text()
            if "team" in content.lower():
                capacity["team_size"] = "Documented"

        return capacity

    def _extract_current_roadmap(self) -> Optional[Dict[str, Any]]:
        """Extract current roadmap from documentation"""
        roadmap_files = ["ROADMAP.md", "roadmap.md", "PLANNING.md"]
        for file in roadmap_files:
            roadmap_path = self.project_root / file
            if roadmap_path.exists():
                return {"source": file, "exists": True}
        return None

    def _identify_constraints(self) -> Dict[str, Any]:
        """Identify project constraints"""
        return {
            "budget": "Documented in question",
            "timeline": "Documented in question",
            "resources": "Current team capacity",
            "technical": "Current tech stack"
        }

    def _identify_risks(self) -> List[str]:
        """Identify project risks"""
        risks = []
        if self._assess_documentation() < 0.5:
            risks.append("Limited documentation")
        if len(self._identify_tech_stack()) < 2:
            risks.append("Single technology dependency")
        return risks

    def _identify_opportunities(self) -> List[str]:
        """Identify improvement opportunities"""
        opportunities = []
        if self._assess_documentation() < 0.8:
            opportunities.append("Improve documentation")
        tech_stack = self._identify_tech_stack()
        if len(tech_stack) > 3:
            opportunities.append("Consolidate technology stack")
        return opportunities

    def _extract_success_metrics(self, question: str) -> List[str]:
        """Extract success metrics from question"""
        metrics = []
        if "scale" in question.lower():
            metrics.append("User growth rate")
            metrics.append("System performance")
        if "security" in question.lower():
            metrics.append("Security compliance score")
            metrics.append("Vulnerability resolution rate")
        return metrics or ["Objective achievement rate"]

    def _extract_timeline_constraints(self, question: str) -> Dict[str, str]:
        """Extract timeline constraints from question"""
        import re
        timeline_match = re.search(r"by (Q[1-4]| \d+ weeks| \d+ months)", question)
        if timeline_match:
            return {"deadline": timeline_match.group(1)}
        return {"deadline": "Not specified"}

    def _extract_budget_constraints(self, question: str) -> Dict[str, Any]:
        """Extract budget constraints from question"""
        import re
        budget_match = re.search(r"\$?(\d+)[kK]", question)
        if budget_match:
            return {"budget": f"${budget_match.group(1)}k"}
        return {"budget": "Not specified"}

    def _extract_strategic_priorities(self, question: str) -> List[str]:
        """Extract strategic priorities from question"""
        priorities = []
        if "scale" in question.lower():
            priorities.append("Scalability")
        if "security" in question.lower():
            priorities.append("Security")
        if "performance" in question.lower():
            priorities.append("Performance")
        return priorities or ["Efficiency", "Quality"]

    def _map_optimal_path(self, current: CurrentState, desired: DesiredFuture) -> PathAnalysis:
        """Map optimal path from current to desired state"""
        logger.info("Mapping optimal path")

        # Analyze current trajectory
        current_trajectory = {
            "pace": "Current development velocity",
            "direction": "Based on existing roadmap",
            "timeline": "Current pace to goal",
            "resource_usage": "Current allocation"
        }

        # Calculate gaps
        gaps = self._calculate_gaps(current, desired)

        # Design optimal path
        optimal_path = {
            "phases": self._design_phases(current, desired),
            "resource_allocation": self._optimize_resources(current, desired),
            "timeline": self._calculate_optimal_timeline(current, desired),
            "key_milestones": self._identify_key_milestones(desired)
        }

        # Generate recommendations
        recommendations = self._generate_recommendations(current, desired, gaps)

        # Determine strategic direction
        direction = self._determine_strategic_direction(current, desired, gaps)

        # Risk assessment
        risks = self._assess_path_risks(optimal_path, current)

        return PathAnalysis(
            current_trajectory=current_trajectory,
            optimal_path=optimal_path,
            gap_analysis=gaps,
            recommendations=recommendations,
            estimated_timeline=self._estimate_timeline(optimal_path),
            resource_requirements=optimal_path["resource_allocation"],
            risk_assessment=risks,
            strategic_direction=direction
        )

    def _calculate_gaps(self, current: CurrentState, desired: DesiredFuture) -> List[str]:
        """Calculate gaps between current and desired state"""
        gaps = []

        # Documentation gap
        if current.documentation_quality < 0.7:
            gaps.append("Documentation below threshold for scaling")

        # Tech stack gaps
        if "scaling" in desired.primary_objective.lower():
            if not any(tech in current.tech_stack for tech in ["Go", "Rust", "Java"]):
                gaps.append("Current tech stack may not scale efficiently")

        # Process gaps
        if not current.current_roadmap:
            gaps.append("No clear current roadmap defined")

        return gaps

    def _design_phases(self, current: CurrentState, desired: DesiredFuture) -> List[Dict[str, Any]]:
        """Design implementation phases"""
        phases = [
            {
                "name": "Foundation",
                "duration": "30 days",
                "focus": "Stabilize current system, improve documentation",
                "deliverables": ["Documentation overhaul", "Code quality improvements"]
            }
        ]

        if "scale" in desired.primary_objective.lower():
            phases.append({
                "name": "Scaling Preparation",
                "duration": "60 days",
                "focus": "Architecture for scale",
                "deliverables": ["Microservices architecture", "Performance optimization"]
            })

        phases.append({
            "name": "Execution",
            "duration": "90 days",
            "focus": "Achieve primary objective",
            "deliverables": [desired.primary_objective]
        })

        return phases

    def _optimize_resources(self, current: CurrentState, desired: DesiredFuture) -> Dict[str, Any]:
        """Optimize resource allocation"""
        return {
            "team_allocation": "Full team on strategic initiatives",
            "budget_allocation": "80% strategic, 20% maintenance",
            "tooling_investment": "Automation and monitoring tools"
        }

    def _calculate_optimal_timeline(self, current: CurrentState, desired: DesiredFuture) -> Dict[str, str]:
        """Calculate optimal timeline"""
        return {
            "total_duration": "6 months",
            "foundation_phase": "1 month",
            "execution_phase": "4 months",
            "optimization_phase": "1 month"
        }

    def _identify_key_milestones(self, desired: DesiredFuture) -> List[str]:
        """Identify key milestones"""
        from datetime import timedelta
        now = datetime.now()
        future_date = now + timedelta(days=60)  # 2 months

        return [
            f"Foundation complete: {now.strftime('%Y-%m-%d')}",
            f"Architecture validated: {future_date.strftime('%Y-%m-%d')}",
            f"Objective achieved: {desired.timeline_constraints.get('deadline', 'Q4')}"
        ]

    def _generate_recommendations(self, current: CurrentState, desired: DesiredFuture, gaps: List[str]) -> List[str]:
        """Generate strategic recommendations"""
        recommendations = []

        # Always recommend documentation improvements
        if current.documentation_quality < 0.8:
            recommendations.append("Immediately improve documentation quality")

        # Tech stack recommendations
        if "scale" in desired.primary_objective.lower():
            recommendations.append("Evaluate tech stack for scaling requirements")

        # Process recommendations
        recommendations.append("Implement clear project management methodology")
        recommendations.append("Establish regular progress monitoring")

        return recommendations

    def _determine_strategic_direction(self, current: CurrentState, desired: DesiredFuture, gaps: List[str]) -> StrategicDirection:
        """Determine strategic direction"""
        # If current state is close to desired, stay course
        if len(gaps) <= 2 and current.documentation_quality > 0.7:
            return StrategicDirection.STAY_COURSE

        # If major gaps exist but foundation is solid, pivot
        elif current.documentation_quality > 0.5:
            return StrategicDirection.PIVOT_APPROACH

        # If foundation is weak, rebuild
        else:
            return StrategicDirection.SCRAP_AND_REBUILD

    def _assess_path_risks(self, optimal_path: Dict[str, Any], current: CurrentState) -> List[Dict[str, Any]]:
        """Assess risks in optimal path"""
        risks = [
            {"risk": "Timeline slippage", "probability": "Medium", "mitigation": "Buffer planning"},
            {"risk": "Resource constraints", "probability": "Medium", "mitigation": "Cross-training team"},
            {"risk": "Technical complexity", "probability": "Low", "mitigation": "Early prototyping"}
        ]
        return risks

    def _estimate_timeline(self, optimal_path: Dict[str, Any]) -> Dict[str, str]:
        """Estimate implementation timeline"""
        return {
            "foundation": "30 days",
            "core_implementation": "90 days",
            "optimization": "30 days",
            "total": "150 days (5 months)"
        }

    def _generate_recommendation(self, path_analysis: PathAnalysis, current: CurrentState, desired: DesiredFuture) -> ConsultantRecommendation:
        """Generate final strategic recommendation"""
        direction = path_analysis.strategic_direction

        # Rationale based on direction
        rationale_map = {
            StrategicDirection.STAY_COURSE: "Current trajectory is sound. Focus on execution excellence and minor optimizations.",
            StrategicDirection.PIVOT_APPROACH: "Strong foundation exists but strategic adjustments needed to optimize path to objectives.",
            StrategicDirection.SCRAP_AND_REBUILD: "Current approach has fundamental issues. New direction required for success."
        }

        # Action recommendations by timeframe
        immediate_actions = self._generate_immediate_actions(direction, path_analysis)
        medium_term_actions = self._generate_medium_term_actions(direction, path_analysis)
        long_term_actions = self._generate_long_term_actions(direction, desired)

        # Success metrics
        success_metrics = desired.success_metrics + ["Plan execution rate", "Budget adherence"]

        # Early warnings
        early_warnings = self._generate_early_warnings(direction, path_analysis)

        return ConsultantRecommendation(
            direction=direction,
            rationale=rationale_map[direction],
            immediate_actions=immediate_actions,
            medium_term_actions=medium_term_actions,
            long_term_actions=long_term_actions,
            success_metrics=success_metrics,
            early_warnings=early_warnings,
            archon_project_plan={}  # Will be populated in _create_archon_plan
        )

    def _generate_immediate_actions(self, direction: StrategicDirection, path_analysis: PathAnalysis) -> List[str]:
        """Generate immediate action items"""
        actions = [
            "Document current state assessment",
            "Align stakeholders on strategic direction",
            "Establish project governance"
        ]

        if direction == StrategicDirection.SCRAP_AND_REBUILD:
            actions.extend([
                "Begin system architecture redesign",
                "Plan migration strategy"
            ])

        return actions

    def _generate_medium_term_actions(self, direction: StrategicDirection, path_analysis: PathAnalysis) -> List[str]:
        """Generate medium-term action items"""
        return [
            "Execute core implementation phases",
            "Monitor progress against milestones",
            "Adjust based on learnings"
        ]

    def _generate_long_term_actions(self, direction: StrategicDirection, desired: DesiredFuture) -> List[str]:
        """Generate long-term action items"""
        return [
            f"Achieve primary objective: {desired.primary_objective}",
            "Establish sustainable operations",
            "Plan next strategic cycle"
        ]

    def _generate_early_warnings(self, direction: StrategicDirection, path_analysis: PathAnalysis) -> List[str]:
        """Generate early warning indicators"""
        warnings = [
            "Documentation quality below 70%",
            "Key milestones delayed by >2 weeks",
            "Budget variance >15%"
        ]

        if direction == StrategicDirection.SCRAP_AND_REBUILD:
            warnings.append("Legacy system degradation")

        return warnings

    async def _create_archon_plan(self, recommendation: ConsultantRecommendation, question: str = None) -> Dict[str, Any]:
        """Create Archon project plan for execution"""
        if self.archon_integration:
            try:
                # Create actual project in Archon
                archon_project = await self.archon_integration.create_strategic_project(
                    recommendation,
                    question or "Strategic Initiative"
                )

                return {
                    "project_name": archon_project.name,
                    "project_id": archon_project.id,
                    "phases": len(archon_project.phases),
                    "tasks": len(archon_project.tasks),
                    "milestones": len(archon_project.milestones),
                    "status": "created_in_archon",
                    "archon_connected": True,
                    "created_at": archon_project.created_at
                }
            except Exception as e:
                logger.error(f"Failed to create Archon project: {e}")

        # Fallback to plan structure
        return {
            "project_name": f"Strategic Initiative: {recommendation.direction.value}",
            "phases": self._plan_archon_phases(recommendation),
            "tasks": self._plan_archon_tasks(recommendation),
            "milestones": self._plan_archon_milestones(recommendation),
            "status": "ready_for_creation",
            "archon_connected": False
        }

    def _plan_archon_phases(self, recommendation: ConsultantRecommendation) -> List[Dict[str, Any]]:
        """Plan Archon project phases"""
        return [
            {
                "name": "Strategic Alignment",
                "duration": "2 weeks",
                "objectives": recommendation.immediate_actions[:3]
            },
            {
                "name": "Foundation Building",
                "duration": "4 weeks",
                "objectives": recommendation.immediate_actions[3:] + recommendation.medium_term_actions[:2]
            },
            {
                "name": "Strategic Execution",
                "duration": "12 weeks",
                "objectives": recommendation.medium_term_actions[2:] + recommendation.long_term_actions
            }
        ]

    def _plan_archon_tasks(self, recommendation: ConsultantRecommendation) -> List[Dict[str, Any]]:
        """Plan detailed Archon tasks"""
        tasks = []
        all_actions = recommendation.immediate_actions + recommendation.medium_term_actions + recommendation.long_term_actions

        for i, action in enumerate(all_actions):
            tasks.append({
                "name": action,
                "priority": "high" if i < 3 else "medium",
                "estimated_effort": "1 week",
                "dependencies": [] if i == 0 else [f"task_{i}"]
            })

        return tasks

    def _plan_archon_milestones(self, recommendation: ConsultantRecommendation) -> List[Dict[str, Any]]:
        """Plan Archon milestones"""
        from datetime import timedelta
        now = datetime.now()

        return [
            {
                "name": "Strategic Direction Set",
                "date": (now + timedelta(days=14)).strftime('%Y-%m-%d'),
                "criteria": ["Stakeholder alignment", "Project plan approved"]
            },
            {
                "name": "Foundation Complete",
                "date": (now + timedelta(days=60)).strftime('%Y-%m-%d'),
                "criteria": ["Core systems stable", "Documentation current"]
            },
            {
                "name": "Strategic Objectives Achieved",
                "date": (now + timedelta(days=150)).strftime('%Y-%m-%d'),
                "criteria": recommendation.success_metrics
            }
        ]