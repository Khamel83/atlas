#!/usr/bin/env python3
"""
GitHub Repository Detector for Atlas

This module detects GitHub URLs in content and extracts repository metadata
to enhance Atlas content with code examples and technical resources.
"""

import re
import logging
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import json
from datetime import datetime

class GitHubDetector:
    """Detects GitHub repositories in content and extracts metadata"""

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize the GitHub detector

        Args:
            github_token (str, optional): GitHub personal access token for API access
        """
        self.github_token = github_token
        self.session = requests.Session()
        if github_token:
            self.session.headers.update({'Authorization': f'token {github_token}'})

        # GitHub URL patterns
        self.github_patterns = [
            r'https?://github\.com/([^/]+)/([^/]+)(?:\.git)?',
            r'https?://www\.github\.com/([^/]+)/([^/]+)(?:\.git)?',
            r'github\.com/([^/]+)/([^/]+)(?:\.git)?'
        ]

    def detect_github_urls(self, content: str) -> List[str]:
        """
        Build GitHub URL pattern detection in transcripts/articles

        Args:
            content (str): Text content to search for GitHub URLs

        Returns:
            List[str]: List of detected GitHub URLs
        """
        detected_urls = []

        # Search for GitHub URLs using patterns
        for pattern in self.github_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match) >= 2:
                    owner, repo = match[0], match[1]
                    # Clean repo name (remove trailing slashes, query params, etc.)
                    repo = re.split(r'[/?#]', repo)[0]
                    url = f"https://github.com/{owner}/{repo}"
                    if url not in detected_urls:
                        detected_urls.append(url)

        return detected_urls

    def extract_repository_metadata(self, github_urls: List[str]) -> List[Dict[str, Any]]:
        """
        Extract repository information (stars, forks, language, description)

        Args:
            github_urls (List[str]): List of GitHub repository URLs

        Returns:
            List[Dict[str, Any]]: List of repository metadata
        """
        repositories = []

        for url in github_urls:
            try:
                # Parse URL to get owner and repo
                parsed = urlparse(url)
                path_parts = parsed.path.strip('/').split('/')
                if len(path_parts) >= 2:
                    owner, repo = path_parts[0], path_parts[1]
                    metadata = self._fetch_repo_metadata(owner, repo)
                    if metadata:
                        repositories.append(metadata)
            except Exception as e:
                logging.warning(f"Failed to extract metadata from {url}: {e}")

        return repositories

    def _fetch_repo_metadata(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """
        Fetch metadata for a specific repository using GitHub API

        Args:
            owner (str): Repository owner
            repo (str): Repository name

        Returns:
            Dict[str, Any]: Repository metadata or None if failed
        """
        try:
            # GitHub API endpoint for repository
            api_url = f"https://api.github.com/repos/{owner}/{repo}"

            # Make request
            response = self.session.get(api_url)
            response.raise_for_status()

            data = response.json()

            # Extract key metadata
            metadata = {
                'id': data.get('id'),
                'name': data.get('name'),
                'full_name': data.get('full_name'),
                'owner': data.get('owner', {}).get('login'),
                'description': data.get('description', ''),
                'url': data.get('html_url'),
                'clone_url': data.get('clone_url'),
                'homepage': data.get('homepage', ''),
                'language': data.get('language'),
                'languages_url': data.get('languages_url'),
                'stars': data.get('stargazers_count', 0),
                'forks': data.get('forks_count', 0),
                'watchers': data.get('watchers_count', 0),
                'size': data.get('size', 0),
                'default_branch': data.get('default_branch', 'main'),
                'open_issues': data.get('open_issues_count', 0),
                'created_at': data.get('created_at'),
                'updated_at': data.get('updated_at'),
                'pushed_at': data.get('pushed_at'),
                'topics': data.get('topics', []),
                'readme_url': f"https://api.github.com/repos/{owner}/{repo}/readme",
                'contents_url': f"https://api.github.com/repos/{owner}/{repo}/contents",
                'atlas_metadata': {
                    'processed_at': datetime.now().isoformat(),
                    'source': 'github_detector'
                }
            }

            return metadata

        except requests.exceptions.RequestException as e:
            logging.warning(f"Failed to fetch metadata for {owner}/{repo}: {e}")
            return None
        except Exception as e:
            logging.warning(f"Error processing metadata for {owner}/{repo}: {e}")
            return None

    def parse_readme_files(self, repositories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse README files for project summaries

        Args:
            repositories (List[Dict[str, Any]]): List of repository metadata

        Returns:
            List[Dict[str, Any]]: Repositories with README content
        """
        for repo in repositories:
            try:
                owner = repo.get('owner')
                name = repo.get('name')
                if owner and name:
                    readme_content = self._fetch_readme_content(owner, name)
                    repo['readme_content'] = readme_content
                    repo['readme_summary'] = self._extract_readme_summary(readme_content)
            except Exception as e:
                logging.warning(f"Failed to parse README for {repo.get('full_name', 'unknown')}: {e}")

        return repositories

    def _fetch_readme_content(self, owner: str, repo: str) -> str:
        """
        Fetch README content for a repository

        Args:
            owner (str): Repository owner
            repo (str): Repository name

        Returns:
            str: README content or empty string
        """
        try:
            # GitHub API endpoint for README
            api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"

            # Make request
            response = self.session.get(api_url)
            response.raise_for_status()

            data = response.json()

            # Decode content (GitHub API returns base64 encoded content)
            import base64
            content = base64.b64decode(data['content']).decode('utf-8')
            return content

        except Exception as e:
            logging.warning(f"Failed to fetch README for {owner}/{repo}: {e}")
            return ""

    def _extract_readme_summary(self, readme_content: str) -> str:
        """
        Extract a summary from README content

        Args:
            readme_content (str): README content

        Returns:
            str: Extracted summary
        """
        if not readme_content:
            return ""

        # Simple extraction: get first paragraph or section
        lines = readme_content.strip().split('\n')

        # Find first non-empty line that looks like a title or description
        summary = ""
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if line and not line.startswith('#') and len(line) > 20:
                summary = line[:200] + "..." if len(line) > 200 else line
                break

        return summary

    def identify_code_examples(self, repositories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify code examples and key files

        Args:
            repositories (List[Dict[str, Any]]): List of repository metadata

        Returns:
            List[Dict[str, Any]]: Repositories with code examples
        """
        for repo in repositories:
            try:
                owner = repo.get('owner')
                name = repo.get('name')
                if owner and name:
                    key_files = self._find_key_files(owner, name)
                    repo['key_files'] = key_files
                    repo['code_examples'] = self._extract_code_examples(key_files)
            except Exception as e:
                logging.warning(f"Failed to identify code examples for {repo.get('full_name', 'unknown')}: {e}")

        return repositories

    def _find_key_files(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """
        Find key files in a repository

        Args:
            owner (str): Repository owner
            repo (str): Repository name

        Returns:
            List[Dict[str, Any]]: List of key files
        """
        try:
            # GitHub API endpoint for repository contents
            api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"

            # Make request
            response = self.session.get(api_url)
            response.raise_for_status()

            data = response.json()

            # Identify key files (common important files)
            key_files = []
            important_files = [
                'README.md', 'README', 'main.py', 'app.py', 'index.js', 'package.json',
                'requirements.txt', 'Dockerfile', 'docker-compose.yml', 'Makefile',
                'setup.py', 'pyproject.toml', 'Cargo.toml', 'pom.xml'
            ]

            for item in data:
                if item.get('type') == 'file' and item.get('name') in important_files:
                    key_files.append({
                        'name': item['name'],
                        'path': item['path'],
                        'url': item['html_url'],
                        'download_url': item['download_url']
                    })

            return key_files

        except Exception as e:
            logging.warning(f"Failed to find key files for {owner}/{repo}: {e}")
            return []

    def _extract_code_examples(self, key_files: List[Dict[str, Any]]) -> List[str]:
        """
        Extract code examples from key files

        Args:
            key_files (List[Dict[str, Any]]): List of key files

        Returns:
            List[str]: List of code examples
        """
        examples = []

        # In a real implementation, this would download and parse key files
        # to extract actual code examples
        for file in key_files:
            examples.append(f"Code example from {file['name']} would be extracted here.")

        return examples

    def track_repository_activity(self, repositories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Track repository activity and update patterns

        Args:
            repositories (List[Dict[str, Any]]): List of repository metadata

        Returns:
            List[Dict[str, Any]]: Repositories with activity data
        """
        for repo in repositories:
            try:
                # Calculate activity metrics
                created_at = repo.get('created_at')
                updated_at = repo.get('updated_at')
                pushed_at = repo.get('pushed_at')

                if created_at and updated_at:
                    # Convert ISO strings to datetime objects
                    from dateutil import parser
                    created_dt = parser.parse(created_at)
                    updated_dt = parser.parse(updated_at)

                    # Calculate activity metrics
                    age_days = (datetime.now(created_dt.tzinfo) - created_dt).days
                    days_since_update = (datetime.now(updated_dt.tzinfo) - updated_dt).days

                    repo['activity_metrics'] = {
                        'age_days': age_days,
                        'days_since_update': days_since_update,
                        'updates_per_year': (updated_dt - created_dt).days / max(age_days, 1) * 365,
                        'is_active': days_since_update < 90  # Active if updated in last 90 days
                    }
            except Exception as e:
                logging.warning(f"Failed to track activity for {repo.get('full_name', 'unknown')}: {e}")

        return repositories

    def create_relationship_mapping(self, repositories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create GitHub relationship mapping

        Args:
            repositories (List[Dict[str, Any]]): List of repository metadata

        Returns:
            Dict[str, Any]: Relationship mapping data
        """
        mapping = {
            'repositories': len(repositories),
            'languages': {},
            'topics': {},
            'owners': {},
            'relationships': []
        }

        for repo in repositories:
            # Language distribution
            language = repo.get('language')
            if language:
                mapping['languages'][language] = mapping['languages'].get(language, 0) + 1

            # Topic distribution
            topics = repo.get('topics', [])
            for topic in topics:
                mapping['topics'][topic] = mapping['topics'].get(topic, 0) + 1

            # Owner distribution
            owner = repo.get('owner')
            if owner:
                mapping['owners'][owner] = mapping['owners'].get(owner, 0) + 1

            # Create relationships
            mapping['relationships'].append({
                'repository': repo.get('full_name'),
                'language': language,
                'topics': topics,
                'stars': repo.get('stars', 0),
                'forks': repo.get('forks', 0)
            })

        return mapping

def main():
    """Example usage of GitHubDetector"""
    # Example usage
    detector = GitHubDetector()

    # Sample content with GitHub URLs
    sample_content = """
    Check out these great repositories:
    - https://github.com/python/cpython for the Python interpreter
    - https://github.com/facebook/react for the React library
    - https://github.com/tensorflow/tensorflow for machine learning
    Also see https://www.github.com/kubernetes/kubernetes for container orchestration.
    """

    # Detect GitHub URLs
    urls = detector.detect_github_urls(sample_content)
    print(f"Detected {len(urls)} GitHub URLs:")
    for url in urls:
        print(f"  - {url}")

    # Extract repository metadata
    repositories = detector.extract_repository_metadata(urls)
    print(f"\nExtracted metadata for {len(repositories)} repositories:")
    for repo in repositories:
        print(f"  - {repo.get('full_name', 'Unknown')}: {repo.get('description', 'No description')}")

    # Parse README files
    repositories = detector.parse_readme_files(repositories)

    # Identify code examples
    repositories = detector.identify_code_examples(repositories)

    # Track repository activity
    repositories = detector.track_repository_activity(repositories)

    # Create relationship mapping
    mapping = detector.create_relationship_mapping(repositories)
    print(f"\nCreated relationship mapping with {mapping['repositories']} repositories")

    print("GitHub detection demo completed successfully!")

if __name__ == "__main__":
    main()