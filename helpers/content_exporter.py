#!/usr/bin/env python3
"""
Content Export System - Task 3.3 Enhanced User Experience Features

Provides comprehensive content export capabilities for Atlas content in multiple formats
including PDF, Markdown, JSON, HTML, and CSV. Supports bulk operations and filtering.

Key Features:
- Multi-format export (PDF, MD, HTML, JSON, CSV)
- Bulk export with filtering capabilities
- Metadata preservation and custom formatting
- Performance optimized for large content sets
- User preferences and customization options
"""

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging

try:
    import markdown
    from weasyprint import HTML, CSS
    ADVANCED_EXPORT_AVAILABLE = True
except ImportError:
    ADVANCED_EXPORT_AVAILABLE = False
    markdown = None
    HTML = None

from helpers.simple_database import SimpleDatabase
from helpers.config import load_config
from helpers.utils import log_info, log_error


class ExportFormat(Enum):
    """Supported export formats."""
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    CSV = "csv"
    TXT = "txt"


@dataclass
class ExportOptions:
    """Configuration options for content export."""
    format: ExportFormat
    output_path: Optional[str] = None
    include_metadata: bool = True
    include_content: bool = True
    content_type_filter: Optional[str] = None
    date_filter_after: Optional[str] = None
    date_filter_before: Optional[str] = None
    max_items: Optional[int] = None
    custom_template: Optional[str] = None
    compression: bool = False


@dataclass
class ExportResult:
    """Result information from export operation."""
    success: bool
    output_path: str
    items_exported: int
    format: ExportFormat
    file_size_bytes: int
    processing_time_ms: float
    errors: List[str]


class ContentExporter:
    """Advanced content export system with multiple format support."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize content exporter with configuration.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or load_config()
        self.db = SimpleDatabase()
        self.export_dir = Path(self.config.get('export_directory', 'exports'))
        self.export_dir.mkdir(exist_ok=True)

        # Set up logging
        self.log_path = os.path.join(self.config.get('log_directory', 'logs'), 'content_export.log')
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def export_content(self, options: ExportOptions) -> ExportResult:
        """Export content based on provided options.

        Args:
            options: Export configuration options

        Returns:
            ExportResult with operation details and status

        Raises:
            ValueError: If invalid options provided
            IOError: If export operation fails
        """
        start_time = datetime.now()
        errors = []

        try:
            # Validate options
            self._validate_options(options)

            # Get filtered content
            content_items = self._get_filtered_content(options)

            if not content_items:
                return ExportResult(
                    success=False,
                    output_path="",
                    items_exported=0,
                    format=options.format,
                    file_size_bytes=0,
                    processing_time_ms=0,
                    errors=["No content items matched the specified filters"]
                )

            # Generate output filename if not provided
            output_path = options.output_path or self._generate_output_filename(options)

            # Perform export based on format
            if options.format == ExportFormat.JSON:
                self._export_json(content_items, output_path, options)
            elif options.format == ExportFormat.MARKDOWN:
                self._export_markdown(content_items, output_path, options)
            elif options.format == ExportFormat.HTML:
                self._export_html(content_items, output_path, options)
            elif options.format == ExportFormat.PDF:
                self._export_pdf(content_items, output_path, options)
            elif options.format == ExportFormat.CSV:
                self._export_csv(content_items, output_path, options)
            elif options.format == ExportFormat.TXT:
                self._export_txt(content_items, output_path, options)
            else:
                raise ValueError(f"Unsupported export format: {options.format}")

            # Get file size
            file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            log_info(self.log_path, f"Successfully exported {len(content_items)} items to {output_path}")

            return ExportResult(
                success=True,
                output_path=output_path,
                items_exported=len(content_items),
                format=options.format,
                file_size_bytes=file_size,
                processing_time_ms=processing_time,
                errors=errors
            )

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            error_msg = f"Export failed: {str(e)}"
            log_error(self.log_path, error_msg)
            errors.append(error_msg)

            return ExportResult(
                success=False,
                output_path=options.output_path or "",
                items_exported=0,
                format=options.format,
                file_size_bytes=0,
                processing_time_ms=processing_time,
                errors=errors
            )

    def _validate_options(self, options: ExportOptions) -> None:
        """Validate export options."""
        if options.format == ExportFormat.PDF and not ADVANCED_EXPORT_AVAILABLE:
            raise ValueError("PDF export requires weasyprint and markdown libraries")

        if options.max_items is not None and options.max_items <= 0:
            raise ValueError("max_items must be positive")

    def _get_filtered_content(self, options: ExportOptions) -> List[Dict[str, Any]]:
        """Get content items filtered by options."""
        all_content = self.db.get_all_content()

        filtered_content = []
        for item in all_content:
            # Filter by content type
            if options.content_type_filter and item.get('content_type') != options.content_type_filter:
                continue

            # Filter by date range
            if options.date_filter_after:
                if item.get('created_at', '') < options.date_filter_after:
                    continue

            if options.date_filter_before:
                if item.get('created_at', '') > options.date_filter_before:
                    continue

            filtered_content.append(item)

            # Apply max items limit
            if options.max_items and len(filtered_content) >= options.max_items:
                break

        return filtered_content

    def _generate_output_filename(self, options: ExportOptions) -> str:
        """Generate output filename based on options."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filter_desc = ""

        if options.content_type_filter:
            filter_desc += f"_{options.content_type_filter}"
        if options.max_items:
            filter_desc += f"_top{options.max_items}"

        filename = f"atlas_content_{timestamp}{filter_desc}.{options.format.value}"
        return str(self.export_dir / filename)

    def _export_json(self, content_items: List[Dict[str, Any]], output_path: str, options: ExportOptions) -> None:
        """Export content as JSON."""
        export_data = {
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'total_items': len(content_items),
                'format': options.format.value,
                'filters_applied': {
                    'content_type': options.content_type_filter,
                    'date_after': options.date_filter_after,
                    'date_before': options.date_filter_before,
                    'max_items': options.max_items
                }
            },
            'content': []
        }

        for item in content_items:
            export_item = {}

            if options.include_metadata:
                export_item['metadata'] = {
                    'id': item.get('id'),
                    'title': item.get('title'),
                    'url': item.get('url'),
                    'content_type': item.get('content_type'),
                    'created_at': item.get('created_at'),
                    'updated_at': item.get('updated_at')
                }

            if options.include_content:
                export_item['content'] = item.get('content', '')

            export_data['content'].append(export_item)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

    def _export_markdown(self, content_items: List[Dict[str, Any]], output_path: str, options: ExportOptions) -> None:
        """Export content as Markdown."""
        with open(output_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write(f"# Atlas Content Export\n\n")
            f.write(f"**Export Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Total Items:** {len(content_items)}\n\n")
            f.write("---\n\n")

            # Write content items
            for i, item in enumerate(content_items, 1):
                if options.include_metadata:
                    f.write(f"## {i}. {item.get('title', 'Untitled')}\n\n")
                    f.write(f"- **Type:** {item.get('content_type', 'Unknown')}\n")
                    f.write(f"- **URL:** {item.get('url', 'N/A')}\n")
                    f.write(f"- **Created:** {item.get('created_at', 'Unknown')}\n\n")

                if options.include_content and item.get('content'):
                    f.write("### Content\n\n")
                    f.write(f"{item.get('content')}\n\n")

                f.write("---\n\n")

    def _export_html(self, content_items: List[Dict[str, Any]], output_path: str, options: ExportOptions) -> None:
        """Export content as HTML."""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Atlas Content Export</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ border-bottom: 2px solid #333; padding-bottom: 20px; }}
                .item {{ margin: 30px 0; padding: 20px; border-left: 4px solid #007acc; }}
                .metadata {{ color: #666; font-size: 0.9em; }}
                .content {{ margin-top: 15px; line-height: 1.6; }}
                pre {{ background: #f5f5f5; padding: 10px; overflow-x: auto; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Atlas Content Export</h1>
                <p><strong>Export Date:</strong> {export_date}</p>
                <p><strong>Total Items:</strong> {total_items}</p>
            </div>
        """.format(
            export_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_items=len(content_items)
        )

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_template)

            for i, item in enumerate(content_items, 1):
                f.write('<div class="item">')

                if options.include_metadata:
                    f.write(f'<h2>{i}. {item.get("title", "Untitled")}</h2>')
                    f.write('<div class="metadata">')
                    f.write(f'<p><strong>Type:</strong> {item.get("content_type", "Unknown")}</p>')
                    f.write(f'<p><strong>URL:</strong> <a href="{item.get("url", "#")}">{item.get("url", "N/A")}</a></p>')
                    f.write(f'<p><strong>Created:</strong> {item.get("created_at", "Unknown")}</p>')
                    f.write('</div>')

                if options.include_content and item.get('content'):
                    f.write('<div class="content">')
                    content = item.get('content', '').replace('<', '&lt;').replace('>', '&gt;')
                    f.write(f'<pre>{content}</pre>')
                    f.write('</div>')

                f.write('</div>')

            f.write('</body></html>')

    def _export_pdf(self, content_items: List[Dict[str, Any]], output_path: str, options: ExportOptions) -> None:
        """Export content as PDF."""
        if not ADVANCED_EXPORT_AVAILABLE:
            raise ValueError("PDF export requires weasyprint and markdown libraries")

        # Create HTML first
        temp_html = output_path.replace('.pdf', '_temp.html')
        self._export_html(content_items, temp_html, options)

        # Convert to PDF
        HTML(filename=temp_html).write_pdf(output_path)

        # Clean up temp file
        try:
            os.remove(temp_html)
        except:
            pass

    def _export_csv(self, content_items: List[Dict[str, Any]], output_path: str, options: ExportOptions) -> None:
        """Export content as CSV."""
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            if not content_items:
                return

            # Determine columns based on options
            columns = []
            if options.include_metadata:
                columns.extend(['id', 'title', 'url', 'content_type', 'created_at', 'updated_at'])
            if options.include_content:
                columns.append('content')

            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()

            for item in content_items:
                row = {}
                if options.include_metadata:
                    row.update({
                        'id': item.get('id'),
                        'title': item.get('title'),
                        'url': item.get('url'),
                        'content_type': item.get('content_type'),
                        'created_at': item.get('created_at'),
                        'updated_at': item.get('updated_at')
                    })
                if options.include_content:
                    row['content'] = item.get('content', '')

                writer.writerow(row)

    def _export_txt(self, content_items: List[Dict[str, Any]], output_path: str, options: ExportOptions) -> None:
        """Export content as plain text."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Atlas Content Export - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Items: {len(content_items)}\n")
            f.write("=" * 60 + "\n\n")

            for i, item in enumerate(content_items, 1):
                if options.include_metadata:
                    f.write(f"[{i}] {item.get('title', 'Untitled')}\n")
                    f.write(f"Type: {item.get('content_type', 'Unknown')}\n")
                    f.write(f"URL: {item.get('url', 'N/A')}\n")
                    f.write(f"Created: {item.get('created_at', 'Unknown')}\n")
                    f.write("-" * 40 + "\n")

                if options.include_content and item.get('content'):
                    f.write(f"{item.get('content')}\n")

                f.write("\n" + "=" * 60 + "\n\n")


def export_content_cli():
    """Command-line interface for content export."""
    import argparse

    parser = argparse.ArgumentParser(description='Export Atlas content in various formats')
    parser.add_argument('--format', choices=[f.value for f in ExportFormat], required=True,
                      help='Export format')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--type', help='Filter by content type')
    parser.add_argument('--after', help='Filter content created after date (YYYY-MM-DD)')
    parser.add_argument('--before', help='Filter content created before date (YYYY-MM-DD)')
    parser.add_argument('--limit', type=int, help='Maximum number of items to export')
    parser.add_argument('--no-metadata', action='store_true', help='Exclude metadata')
    parser.add_argument('--no-content', action='store_true', help='Exclude content text')

    args = parser.parse_args()

    # Create export options
    options = ExportOptions(
        format=ExportFormat(args.format),
        output_path=args.output,
        include_metadata=not args.no_metadata,
        include_content=not args.no_content,
        content_type_filter=args.type,
        date_filter_after=args.after,
        date_filter_before=args.before,
        max_items=args.limit
    )

    # Perform export
    exporter = ContentExporter()
    result = exporter.export_content(options)

    if result.success:
        print(f"✅ Successfully exported {result.items_exported} items to {result.output_path}")
        print(f"📁 File size: {result.file_size_bytes:,} bytes")
        print(f"⏱️ Processing time: {result.processing_time_ms:.1f}ms")
    else:
        print("❌ Export failed:")
        for error in result.errors:
            print(f"   - {error}")


if __name__ == "__main__":
    export_content_cli()