#!/usr/bin/env python3
"""
Visualization Generator - Create charts and visualizations for analytics
Generates various chart types for content analytics and insights.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from helpers.utils import log_info, log_error


class VisualizationGenerator:
    """
    Generate visualizations for Atlas analytics.

    Creates various chart types:
    - Content distribution pie charts
    - Timeline charts for consumption patterns
    - Trend lines for content types
    - Heatmaps for activity patterns
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize VisualizationGenerator with configuration."""
        self.config = config or {}
        self.output_dir = Path(self.config.get('visualization_output', 'dashboard/static/charts'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Chart configuration
        self.chart_width = self.config.get('chart_width', 800)
        self.chart_height = self.config.get('chart_height', 400)
        self.color_palette = self.config.get('color_palette', [
            '#2196F3', '#4CAF50', '#FF9800', '#F44336',
            '#9C27B0', '#00BCD4', '#FFEB3B', '#795548'
        ])

    def generate_content_distribution_chart(self, distribution_data: List[Dict]) -> str:
        """Generate pie chart for content type distribution."""
        try:
            if not distribution_data:
                return self._create_empty_chart("No content data available")

            # Prepare data
            labels = [item['type'] for item in distribution_data]
            values = [item['count'] for item in distribution_data]
            colors = self.color_palette[:len(labels)]

            # Generate SVG pie chart
            svg_content = self._create_pie_chart_svg(labels, values, colors, "Content Distribution")

            # Save to file
            filename = "content_distribution.svg"
            filepath = self.output_dir / filename
            with open(filepath, 'w') as f:
                f.write(svg_content)

            log_info(f"Generated content distribution chart: {filename}")
            return str(filepath)

        except Exception as e:
            log_error(f"Error generating content distribution chart: {str(e)}")
            return self._create_error_chart(str(e))

    def generate_timeline_chart(self, timeline_data: List[Dict], title: str = "Activity Timeline") -> str:
        """Generate timeline chart for activity patterns."""
        try:
            if not timeline_data:
                return self._create_empty_chart("No timeline data available")

            # Prepare data
            dates = [item['date'] for item in timeline_data]
            values = [item['events'] for item in timeline_data]

            # Generate SVG line chart
            svg_content = self._create_line_chart_svg(dates, values, title)

            # Save to file
            filename = "activity_timeline.svg"
            filepath = self.output_dir / filename
            with open(filepath, 'w') as f:
                f.write(svg_content)

            log_info(f"Generated timeline chart: {filename}")
            return str(filepath)

        except Exception as e:
            log_error(f"Error generating timeline chart: {str(e)}")
            return self._create_error_chart(str(e))

    def generate_trend_chart(self, trends_data: Dict[str, List[Dict]], title: str = "Content Trends") -> str:
        """Generate multi-line chart for content type trends."""
        try:
            if not trends_data:
                return self._create_empty_chart("No trend data available")

            # Generate SVG multi-line chart
            svg_content = self._create_multi_line_chart_svg(trends_data, title)

            # Save to file
            filename = "content_trends.svg"
            filepath = self.output_dir / filename
            with open(filepath, 'w') as f:
                f.write(svg_content)

            log_info(f"Generated trend chart: {filename}")
            return str(filepath)

        except Exception as e:
            log_error(f"Error generating trend chart: {str(e)}")
            return self._create_error_chart(str(e))

    def generate_bar_chart(self, data: List[Dict], x_key: str, y_key: str, title: str) -> str:
        """Generate bar chart for categorical data."""
        try:
            if not data:
                return self._create_empty_chart("No data available")

            # Prepare data
            labels = [str(item[x_key]) for item in data]
            values = [float(item[y_key]) for item in data]

            # Generate SVG bar chart
            svg_content = self._create_bar_chart_svg(labels, values, title)

            # Save to file
            filename = f"bar_chart_{title.lower().replace(' ', '_')}.svg"
            filepath = self.output_dir / filename
            with open(filepath, 'w') as f:
                f.write(svg_content)

            log_info(f"Generated bar chart: {filename}")
            return str(filepath)

        except Exception as e:
            log_error(f"Error generating bar chart: {str(e)}")
            return self._create_error_chart(str(e))

    def _create_pie_chart_svg(self, labels: List[str], values: List[float], colors: List[str], title: str) -> str:
        """Create SVG pie chart."""
        width, height = self.chart_width, self.chart_height
        radius = min(width, height) // 3
        center_x, center_y = width // 2, height // 2

        total = sum(values)
        if total == 0:
            return self._create_empty_chart("No data to display")

        svg_parts = [
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            f'<title>{title}</title>',
            f'<text x="{width//2}" y="30" text-anchor="middle" font-size="18" font-weight="bold">{title}</text>'
        ]

        # Draw pie slices
        start_angle = 0
        for i, (label, value) in enumerate(zip(labels, values)):
            angle = (value / total) * 360
            end_angle = start_angle + angle

            # Calculate arc path
            large_arc = 1 if angle > 180 else 0
            start_x = center_x + radius * self._cos_deg(start_angle)
            start_y = center_y + radius * self._sin_deg(start_angle)
            end_x = center_x + radius * self._cos_deg(end_angle)
            end_y = center_y + radius * self._sin_deg(end_angle)

            color = colors[i % len(colors)]

            path = f'M {center_x} {center_y} L {start_x} {start_y} A {radius} {radius} 0 {large_arc} 1 {end_x} {end_y} Z'
            svg_parts.append(f'<path d="{path}" fill="{color}" stroke="white" stroke-width="2"/>')

            # Add label
            label_angle = start_angle + angle / 2
            label_radius = radius * 0.7
            label_x = center_x + label_radius * self._cos_deg(label_angle)
            label_y = center_y + label_radius * self._sin_deg(label_angle)

            percentage = (value / total) * 100
            if percentage > 5:  # Only show label if slice is large enough
                svg_parts.append(f'<text x="{label_x}" y="{label_y}" text-anchor="middle" font-size="12" fill="white">{percentage:.1f}%</text>')

            start_angle = end_angle

        # Add legend
        legend_y = height - 100
        for i, (label, value) in enumerate(zip(labels, values)):
            legend_x = 50 + (i % 4) * 180
            legend_row = legend_y + (i // 4) * 20
            color = colors[i % len(colors)]

            svg_parts.append(f'<rect x="{legend_x}" y="{legend_row}" width="15" height="15" fill="{color}"/>')
            svg_parts.append(f'<text x="{legend_x + 20}" y="{legend_row + 12}" font-size="12">{label} ({value})</text>')

        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)

    def _create_line_chart_svg(self, dates: List[str], values: List[float], title: str) -> str:
        """Create SVG line chart."""
        width, height = self.chart_width, self.chart_height
        margin = 60
        chart_width = width - 2 * margin
        chart_height = height - 2 * margin

        if not values or max(values) == 0:
            return self._create_empty_chart("No data to display")

        svg_parts = [
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            f'<title>{title}</title>',
            f'<text x="{width//2}" y="30" text-anchor="middle" font-size="18" font-weight="bold">{title}</text>'
        ]

        # Draw axes
        svg_parts.append(f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height-margin}" stroke="black" stroke-width="2"/>')
        svg_parts.append(f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="black" stroke-width="2"/>')

        # Calculate scales
        max_value = max(values)
        x_scale = chart_width / max(len(values) - 1, 1)
        y_scale = chart_height / max_value if max_value > 0 else 1

        # Draw line
        points = []
        for i, value in enumerate(values):
            x = margin + i * x_scale
            y = height - margin - value * y_scale
            points.append(f"{x},{y}")

            # Draw point
            svg_parts.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{self.color_palette[0]}"/>')

        # Draw line connecting points
        if len(points) > 1:
            path = f'M {" L ".join(points)}'
            svg_parts.append(f'<path d="{path}" stroke="{self.color_palette[0]}" stroke-width="2" fill="none"/>')

        # Add axis labels
        for i, date in enumerate(dates[::max(len(dates)//5, 1)]):
            x = margin + i * x_scale * max(len(dates)//5, 1)
            svg_parts.append(f'<text x="{x}" y="{height-20}" text-anchor="middle" font-size="10">{date}</text>')

        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)

    def _create_bar_chart_svg(self, labels: List[str], values: List[float], title: str) -> str:
        """Create SVG bar chart."""
        width, height = self.chart_width, self.chart_height
        margin = 60
        chart_width = width - 2 * margin
        chart_height = height - 2 * margin

        if not values or max(values) == 0:
            return self._create_empty_chart("No data to display")

        svg_parts = [
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            f'<title>{title}</title>',
            f'<text x="{width//2}" y="30" text-anchor="middle" font-size="18" font-weight="bold">{title}</text>'
        ]

        # Draw axes
        svg_parts.append(f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height-margin}" stroke="black" stroke-width="2"/>')
        svg_parts.append(f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="black" stroke-width="2"/>')

        # Calculate scales
        max_value = max(values)
        bar_width = chart_width / len(values) * 0.8
        spacing = chart_width / len(values) * 0.2
        y_scale = chart_height / max_value if max_value > 0 else 1

        # Draw bars
        for i, (label, value) in enumerate(zip(labels, values)):
            x = margin + i * (bar_width + spacing) + spacing / 2
            bar_height = value * y_scale
            y = height - margin - bar_height

            color = self.color_palette[i % len(self.color_palette)]
            svg_parts.append(f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" fill="{color}"/>')

            # Add value label on top of bar
            label_x = x + bar_width / 2
            label_y = y - 5
            svg_parts.append(f'<text x="{label_x}" y="{label_y}" text-anchor="middle" font-size="12">{value}</text>')

            # Add category label at bottom
            bottom_label_y = height - margin + 20
            # Truncate long labels
            display_label = label[:10] + "..." if len(label) > 10 else label
            svg_parts.append(f'<text x="{label_x}" y="{bottom_label_y}" text-anchor="middle" font-size="10">{display_label}</text>')

        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)

    def _create_multi_line_chart_svg(self, trends_data: Dict[str, List[Dict]], title: str) -> str:
        """Create SVG multi-line chart."""
        width, height = self.chart_width, self.chart_height
        margin = 60
        chart_width = width - 2 * margin
        chart_height = height - 2 * margin

        if not trends_data:
            return self._create_empty_chart("No trend data available")

        svg_parts = [
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            f'<title>{title}</title>',
            f'<text x="{width//2}" y="30" text-anchor="middle" font-size="18" font-weight="bold">{title}</text>'
        ]

        # Draw axes
        svg_parts.append(f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height-margin}" stroke="black" stroke-width="2"/>')
        svg_parts.append(f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="black" stroke-width="2"/>')

        # Find max values for scaling
        all_values = []
        max_points = 0
        for content_type, data in trends_data.items():
            values = [point['count'] for point in data]
            all_values.extend(values)
            max_points = max(max_points, len(values))

        if not all_values or max(all_values) == 0:
            return self._create_empty_chart("No data to display")

        max_value = max(all_values)
        x_scale = chart_width / max(max_points - 1, 1)
        y_scale = chart_height / max_value

        # Draw lines for each content type
        color_index = 0
        for content_type, data in trends_data.items():
            if not data:
                continue

            color = self.color_palette[color_index % len(self.color_palette)]
            points = []

            for i, point in enumerate(data):
                x = margin + i * x_scale
                y = height - margin - point['count'] * y_scale
                points.append(f"{x},{y}")

                # Draw point
                svg_parts.append(f'<circle cx="{x}" cy="{y}" r="3" fill="{color}"/>')

            # Draw line
            if len(points) > 1:
                path = f'M {" L ".join(points)}'
                svg_parts.append(f'<path d="{path}" stroke="{color}" stroke-width="2" fill="none"/>')

            color_index += 1

        # Add legend
        legend_y = height - 40
        legend_x = margin
        color_index = 0
        for content_type in trends_data.keys():
            color = self.color_palette[color_index % len(self.color_palette)]
            svg_parts.append(f'<rect x="{legend_x}" y="{legend_y}" width="15" height="15" fill="{color}"/>')
            svg_parts.append(f'<text x="{legend_x + 20}" y="{legend_y + 12}" font-size="12">{content_type}</text>')
            legend_x += len(content_type) * 8 + 50
            color_index += 1

        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)

    def _create_empty_chart(self, message: str) -> str:
        """Create empty chart with message."""
        width, height = self.chart_width, self.chart_height
        return f'''<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
            <rect width="{width}" height="{height}" fill="#f5f5f5" stroke="#ddd"/>
            <text x="{width//2}" y="{height//2}" text-anchor="middle" font-size="16" fill="#666">{message}</text>
        </svg>'''

    def _create_error_chart(self, error: str) -> str:
        """Create error chart."""
        width, height = self.chart_width, self.chart_height
        return f'''<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
            <rect width="{width}" height="{height}" fill="#ffebee" stroke="#f44336"/>
            <text x="{width//2}" y="{height//2}" text-anchor="middle" font-size="14" fill="#f44336">Error: {error}</text>
        </svg>'''

    def _cos_deg(self, degrees: float) -> float:
        """Cosine in degrees."""
        import math
        return math.cos(math.radians(degrees))

    def _sin_deg(self, degrees: float) -> float:
        """Sine in degrees."""
        import math
        return math.sin(math.radians(degrees))

    def export_all_charts(self, insights: Dict[str, Any]) -> List[str]:
        """Export all charts for given insights."""
        charts = []

        try:
            # Content distribution chart
            distribution = insights.get('content_distribution', {}).get('distribution', [])
            if distribution:
                chart_path = self.generate_content_distribution_chart(distribution)
                charts.append(chart_path)

            # Timeline chart
            patterns = insights.get('consumption_patterns', {})
            daily_activity = patterns.get('daily_activity', [])
            if daily_activity:
                chart_path = self.generate_timeline_chart(daily_activity)
                charts.append(chart_path)

            # Trends chart
            trends = insights.get('trends', {}).get('weekly_trends', {})
            if trends:
                chart_path = self.generate_trend_chart(trends)
                charts.append(chart_path)

            log_info(f"Exported {len(charts)} charts")
            return charts

        except Exception as e:
            log_error(f"Error exporting charts: {str(e)}")
            return charts


def generate_all_visualizations(insights: Dict[str, Any], config: Dict[str, Any] = None) -> List[str]:
    """Convenience function to generate all visualizations."""
    generator = VisualizationGenerator(config)
    return generator.export_all_charts(insights)