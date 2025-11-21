#!/usr/bin/env python3
"""
Atlas Dashboard - Personal Analytics and Insights Dashboard
Provides web-based analytics and insights for personal content consumption.
"""

__version__ = "1.0.0"
__author__ = "Atlas Project"

from helpers.analytics_engine import AnalyticsEngine
from .dashboard_server import DashboardServer
from .visualization_generator import VisualizationGenerator

__all__ = [
    "AnalyticsEngine",
    "DashboardServer",
    "VisualizationGenerator"
]