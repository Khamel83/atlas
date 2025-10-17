#!/usr/bin/env python3
"""
Source Analyzer for Atlas

This module implements content discovery capabilities for Atlas, automatically
finding related repositories, code examples, and technical resources.
"""

import re
import requests
from typing import List, Dict, Any, Optional
from collections import defaultdict
from urllib.parse import urlparse
import json

class SourceAnalyzer:
    """Content discovery and source analysis system"""

    def __init__(self):
        """Initialize the source analyzer"""
        self.github_patterns = [
            r'https?://github\.com/([^/]+)/([^/]+)',
            r'https?://www\.github\.com/([^/]+)/([^/]+)',
            r'github\.com/([^/]+)/([^/]+)'
        ]

        self.documentation_patterns = [
            r'https?://docs\.python\.org',
            r'https?://reactjs\.org',
            r'https?://developer\.mozilla\.org',
            r'https?://docs\.nodejs\.org',
            r'https?://kubernetes\.io/docs',
            r'https?://docs\.docker\.com',
            r'https?://angular\.io/docs',
            r'https?://vuejs\.org/v2/guide',
            r'https?://expressjs\.com',
            r'https?://flask\.pocoo\.org/docs',
            r'https?://django\.documentation',
            r'https?://docs\.mongodb\.com',
            r'https?://redis\.io/documentation',
            r'https?://postgresql\.org/docs',
            r'https?://docs\.aws\.amazon\.com',
            r'https?://cloud\.google\.com/docs',
            r'https?://docs\.microsoft\.com',
            r'https?://developer\.android\.com',
            r'https?://developer\.apple\.com/documentation',
            r'https?://getbootstrap\.com/docs'
        ]

        self.technical_resource_patterns = [
            r'https?://stackoverflow\.com/questions',
            r'https?://medium\.com',
            r'https?://towardsdatascience\.com',
            r'https?://dev\.to',
            r'https?://hashcat\.net/wiki',
            r'https?://owasp\.org',
            r'https?://cve\.mitre\.org',
            r'https?://nvd\.nist\.gov',
            r'https?://security\.googleblog\.com',
            r'https?://krebsonsecurity\.com'
        ]

    def analyze_content(self, content: str) -> Dict[str, Any]:
        """
        Analyze content for related sources and technical resources

        Args:
            content (str): Content to analyze

        Returns:
            Dict[str, Any]: Analysis results
        """
        print("Analyzing content for related sources...")

        # Detect GitHub repositories
        github_repos = self._detect_github_repos(content)

        # Detect documentation links
        documentation_links = self._detect_documentation_links(content)

        # Detect technical resources
        technical_resources = self._detect_technical_resources(content)

        # Extract code examples
        code_examples = self._extract_code_examples(content)

        # Extract technical terms
        technical_terms = self._extract_technical_terms(content)

        # Find related repositories
        related_repos = self._find_related_repositories(technical_terms)

        # Find related tutorials
        related_tutorials = self._find_related_tutorials(technical_terms)

        # Find related articles
        related_articles = self._find_related_articles(technical_terms)

        # Build analysis results
        analysis = {
            'github_repos': github_repos,
            'documentation_links': documentation_links,
            'technical_resources': technical_resources,
            'code_examples': code_examples,
            'technical_terms': technical_terms,
            'related_repositories': related_repos,
            'related_tutorials': related_tutorials,
            'related_articles': related_articles,
            'analysis_timestamp': '2023-05-01T12:00:00Z'  # In a real implementation, this would be current time
        }

        print(f"Analysis complete: Found {len(github_repos)} repos, "
              f"{len(documentation_links)} docs, "
              f"{len(technical_resources)} resources")

        return analysis

    def _detect_github_repos(self, content: str) -> List[Dict[str, Any]]:
        """
        Detect GitHub repository URLs in content

        Args:
            content (str): Content to analyze

        Returns:
            List[Dict[str, Any]]: Detected GitHub repositories
        """
        repos = []

        for pattern in self.github_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match) >= 2:
                    owner, repo = match[0], match[1]
                    # Clean repo name (remove trailing characters)
                    repo = re.split(r'[/?#]', repo)[0]

                    repo_info = {
                        'url': f"https://github.com/{owner}/{repo}",
                        'owner': owner,
                        'name': repo,
                        'full_name': f"{owner}/{repo}"
                    }

                    # Avoid duplicates
                    if repo_info not in repos:
                        repos.append(repo_info)

        return repos

    def _detect_documentation_links(self, content: str) -> List[Dict[str, Any]]:
        """
        Detect documentation links in content

        Args:
            content (str): Content to analyze

        Returns:
            List[Dict[str, Any]]: Detected documentation links
        """
        links = []

        for pattern in self.documentation_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Extract full URL
                url_match = re.search(r'(https?://[^"\'>\s]+)', content[content.find(match):])
                if url_match:
                    url = url_match.group(1)
                    links.append({
                        'url': url,
                        'type': 'documentation',
                        'domain': urlparse(url).netloc
                    })

        return links

    def _detect_technical_resources(self, content: str) -> List[Dict[str, Any]]:
        """
        Detect technical resources in content

        Args:
            content (str): Content to analyze

        Returns:
            List[Dict[str, Any]]: Detected technical resources
        """
        resources = []

        for pattern in self.technical_resource_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Extract full URL
                url_match = re.search(r'(https?://[^"\'>\s]+)', content[content.find(match):])
                if url_match:
                    url = url_match.group(1)
                    resources.append({
                        'url': url,
                        'type': 'technical_resource',
                        'domain': urlparse(url).netloc
                    })

        return resources

    def _extract_code_examples(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract code examples from content

        Args:
            content (str): Content to analyze

        Returns:
            List[Dict[str, Any]]: Extracted code examples
        """
        examples = []

        # Look for code blocks in markdown-style content
        # Pattern for fenced code blocks: ```language\n...\n```
        fenced_pattern = r'```([a-zA-Z]*)\n(.*?)\n```'
        matches = re.findall(fenced_pattern, content, re.DOTALL)

        for language, code in matches:
            examples.append({
                'content': code.strip(),
                'language': language or self._detect_language(code),
                'type': 'fenced_code_block'
            })

        # Look for inline code (single backticks)
        inline_pattern = r'`([^`\n]+)`'
        inline_matches = re.findall(inline_pattern, content)

        for code in inline_matches:
            if self._looks_like_api_reference(code):
                examples.append({
                    'content': code,
                    'language': self._detect_language(code),
                    'type': 'inline_code'
                })

        return examples

    def _extract_technical_terms(self, content: str) -> List[str]:
        """
        Extract technical terms from content

        Args:
            content (str): Content to analyze

        Returns:
            List[str]: Extracted technical terms
        """
        # Simple technical term extraction (in a real implementation, use NLP)
        content_lower = content.lower()

        # Common technical terms
        technical_terms = [
            'python', 'javascript', 'java', 'go', 'rust', 'c++', 'c#',
            'react', 'vue', 'angular', 'django', 'flask', 'express',
            'docker', 'kubernetes', 'aws', 'gcp', 'azure',
            'postgresql', 'mongodb', 'redis', 'mysql',
            'tensorflow', 'pytorch', 'scikit-learn', 'machine learning',
            'api', 'database', 'framework', 'library', 'package',
            'algorithm', 'data structure', 'authentication', 'security',
            'encryption', 'hashing', 'cryptography', 'ssl', 'tls',
            'http', 'https', 'rest', 'graphql', 'websocket',
            'git', 'github', 'ci/cd', 'devops', 'agile',
            'oop', 'functional programming', 'design patterns',
            'testing', 'unit testing', 'integration testing', 'tdd',
            'microservices', 'serverless', 'cloud computing',
            'big data', 'data science', 'artificial intelligence',
            'natural language processing', 'computer vision',
            'blockchain', 'cryptocurrency', 'smart contracts',
            'iot', 'internet of things', 'embedded systems',
            'mobile development', 'web development', 'frontend', 'backend',
            'fullstack', 'responsive design', 'ux/ui',
            'cybersecurity', 'penetration testing', 'vulnerability assessment',
            'compliance', 'gdpr', 'hipaa', 'sox',
            'performance optimization', 'scalability', 'reliability',
            'monitoring', 'logging', 'observability',
            'debugging', 'profiling', 'troubleshooting'
        ]

        # Find terms in content
        found_terms = []
        for term in technical_terms:
            if term in content_lower:
                found_terms.append(term)

        return list(set(found_terms))  # Remove duplicates

    def _find_related_repositories(self, technical_terms: List[str]) -> List[Dict[str, Any]]:
        """
        Find related repositories based on technical terms

        Args:
            technical_terms (List[str]): Technical terms to search for

        Returns:
            List[Dict[str, Any]]: Related repositories
        """
        # In a real implementation, this would query GitHub API or similar
        # For now, we'll return placeholder results

        repos = []

        # Map technical terms to popular repositories
        term_to_repo = {
            'python': [
                {'owner': 'python', 'name': 'cpython', 'description': 'The Python programming language'},
                {'owner': 'psf', 'name': 'requests', 'description': 'Python HTTP Requests for Humans'},
                {'owner': 'numpy', 'name': 'numpy', 'description': 'Fundamental package for scientific computing with Python'}
            ],
            'javascript': [
                {'owner': 'nodejs', 'name': 'node', 'description': 'Node.js JavaScript runtime'},
                {'owner': 'jquery', 'name': 'jquery', 'description': 'jQuery JavaScript Library'},
                {'owner': 'axios', 'name': 'axios', 'description': 'Promise based HTTP client for the browser and node.js'}
            ],
            'react': [
                {'owner': 'facebook', 'name': 'react', 'description': 'A declarative, efficient, and flexible JavaScript library for building user interfaces'},
                {'owner': 'reduxjs', 'name': 'redux', 'description': 'Predictable state container for JavaScript apps'},
                {'owner': 'react-navigation', 'name': 'react-navigation', 'description': 'Routing and navigation for your React Native apps'}
            ],
            'docker': [
                {'owner': 'docker', 'name': 'docker-ce', 'description': 'Docker CE'},
                {'owner': 'docker', 'name': 'compose', 'description': 'Define and run multi-container applications with Docker'},
                {'owner': 'docker', 'name': 'docker-py', 'description': 'A Python library for the Docker Engine API'}
            ],
            'kubernetes': [
                {'owner': 'kubernetes', 'name': 'kubernetes', 'description': 'Production-Grade Container Scheduling and Management'},
                {'owner': 'helm', 'name': 'helm', 'description': 'The Kubernetes Package Manager'},
                {'owner': 'kubernetes-sigs', 'name': 'kustomize', 'description': 'Customization of kubernetes YAML configurations'}
            ]
        }

        # Find repositories for each technical term
        for term in technical_terms:
            if term in term_to_repo:
                repos.extend(term_to_repo[term])

        # Remove duplicates
        seen = set()
        unique_repos = []
        for repo in repos:
            repo_key = f"{repo['owner']}/{repo['name']}"
            if repo_key not in seen:
                seen.add(repo_key)
                unique_repos.append(repo)

        return unique_repos[:10]  # Limit to top 10

    def _find_related_tutorials(self, technical_terms: List[str]) -> List[Dict[str, Any]]:
        """
        Find related tutorials based on technical terms

        Args:
            technical_terms (List[str]): Technical terms to search for

        Returns:
            List[Dict[str, Any]]: Related tutorials
        """
        # In a real implementation, this would query tutorial sites or APIs
        # For now, we'll return placeholder results

        tutorials = []

        # Map technical terms to popular tutorials
        term_to_tutorial = {
            'python': [
                {'title': 'Python Tutorial for Beginners', 'url': 'https://example.com/python-tutorial', 'level': 'beginner'},
                {'title': 'Intermediate Python Programming', 'url': 'https://example.com/intermediate-python', 'level': 'intermediate'},
                {'title': 'Advanced Python Techniques', 'url': 'https://example.com/advanced-python', 'level': 'advanced'}
            ],
            'javascript': [
                {'title': 'JavaScript Fundamentals', 'url': 'https://example.com/js-fundamentals', 'level': 'beginner'},
                {'title': 'Modern JavaScript ES6+', 'url': 'https://example.com/modern-js', 'level': 'intermediate'},
                {'title': 'JavaScript Design Patterns', 'url': 'https://example.com/js-patterns', 'level': 'advanced'}
            ],
            'react': [
                {'title': 'React Basics Tutorial', 'url': 'https://example.com/react-basics', 'level': 'beginner'},
                {'title': 'React Hooks Deep Dive', 'url': 'https://example.com/react-hooks', 'level': 'intermediate'},
                {'title': 'Advanced React Patterns', 'url': 'https://example.com/advanced-react', 'level': 'advanced'}
            ],
            'docker': [
                {'title': 'Docker for Beginners', 'url': 'https://example.com/docker-beginners', 'level': 'beginner'},
                {'title': 'Docker Compose Tutorial', 'url': 'https://example.com/docker-compose', 'level': 'intermediate'},
                {'title': 'Docker Swarm and Kubernetes', 'url': 'https://example.com/docker-swarm-k8s', 'level': 'advanced'}
            ],
            'kubernetes': [
                {'title': 'Kubernetes Fundamentals', 'url': 'https://example.com/k8s-fundamentals', 'level': 'beginner'},
                {'title': 'Kubernetes Helm Charts', 'url': 'https://example.com/k8s-helm', 'level': 'intermediate'},
                {'title': 'Kubernetes Operators', 'url': 'https://example.com/k8s-operators', 'level': 'advanced'}
            ]
        }

        # Find tutorials for each technical term
        for term in technical_terms:
            if term in term_to_tutorial:
                tutorials.extend(term_to_tutorial[term])

        # Remove duplicates
        seen = set()
        unique_tutorials = []
        for tutorial in tutorials:
            tutorial_key = tutorial['url']
            if tutorial_key not in seen:
                seen.add(tutorial_key)
                unique_tutorials.append(tutorial)

        return unique_tutorials[:10]  # Limit to top 10

    def _find_related_articles(self, technical_terms: List[str]) -> List[Dict[str, Any]]:
        """
        Find related articles based on technical terms

        Args:
            technical_terms (List[str]): Technical terms to search for

        Returns:
            List[Dict[str, Any]]: Related articles
        """
        # In a real implementation, this would query article databases or APIs
        # For now, we'll return placeholder results

        articles = []

        # Map technical terms to popular articles
        term_to_article = {
            'python': [
                {'title': 'Why Python is Great for Data Science', 'url': 'https://example.com/python-data-science', 'source': 'TechBlog'},
                {'title': 'Python vs Other Programming Languages', 'url': 'https://example.com/python-comparison', 'source': 'DevNews'},
                {'title': 'The Future of Python Development', 'url': 'https://example.com/python-future', 'source': 'FutureTech'}
            ],
            'javascript': [
                {'title': 'The Rise of JavaScript Frameworks', 'url': 'https://example.com/js-frameworks', 'source': 'WebDevToday'},
                {'title': 'JavaScript Performance Optimization', 'url': 'https://example.com/js-performance', 'source': 'PerformanceWeekly'},
                {'title': 'JavaScript in 2023: Trends and Predictions', 'url': 'https://example.com/js-2023', 'source': 'TrendReport'}
            ],
            'react': [
                {'title': 'React 18: What\'s New and Exciting', 'url': 'https://example.com/react-18', 'source': 'ReactBlog'},
                {'title': 'State Management in Modern React Apps', 'url': 'https://example.com/react-state', 'source': 'StateManagementDigest'},
                {'title': 'React vs Vue: A Comprehensive Comparison', 'url': 'https://example.com/react-vue', 'source': 'FrameworkWars'}
            ],
            'docker': [
                {'title': 'Containerization Best Practices', 'url': 'https://example.com/container-best-practices', 'source': 'DevOpsPro'},
                {'title': 'Docker Security: What You Need to Know', 'url': 'https://example.com/docker-security', 'source': 'SecurityToday'},
                {'title': 'Microservices with Docker: A Practical Guide', 'url': 'https://example.com/docker-microservices', 'source': 'MicroservicesMag'}
            ],
            'kubernetes': [
                {'title': 'Kubernetes: The Container Orchestrator', 'url': 'https://example.com/k8s-orchestrator', 'source': 'CloudNativeNews'},
                {'title': 'Kubernetes Networking Explained', 'url': 'https://example.com/k8s-networking', 'source': 'NetworkingPro'},
                {'title': 'Kubernetes in Production: Lessons Learned', 'url': 'https://example.com/k8s-production', 'source': 'ProductionStories'}
            ]
        }

        # Find articles for each technical term
        for term in technical_terms:
            if term in term_to_article:
                articles.extend(term_to_article[term])

        # Remove duplicates
        seen = set()
        unique_articles = []
        for article in articles:
            article_key = article['url']
            if article_key not in seen:
                seen.add(article_key)
                unique_articles.append(article)

        return unique_articles[:10]  # Limit to top 10

    def _detect_language(self, code: str) -> str:
        """
        Detect programming language from code snippet

        Args:
            code (str): Code snippet

        Returns:
            str: Detected language
        """
        # Simple language detection based on keywords
        if re.search(r'\b(def|import|from|class)\s', code):
            return 'python'
        elif re.search(r'\b(function|var|let|const|=>)\s', code):
            return 'javascript'
        elif re.search(r'\b(public|private|class|interface)\s', code):
            return 'java'
        elif re.search(r'\b(func|package|import)\s', code):
            return 'go'
        elif re.search(r'\b(fn|let|mut)\s', code):
            return 'rust'
        else:
            return 'unknown'

    def _looks_like_api_reference(self, text: str) -> bool:
        """
        Check if text looks like an API reference

        Args:
            text (str): Text to check

        Returns:
            bool: True if looks like API reference
        """
        # Simple heuristics for API references
        api_patterns = [
            r'^[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)',  # Function signatures
            r'^function\s+[a-zA-Z_][a-zA-Z0-9_]*',  # JavaScript functions
            r'^def\s+[a-zA-Z_][a-zA-Z0-9_]*',  # Python functions
            r'^public\s+[a-zA-Z_][a-zA-Z0-9_]*',  # Java/C# methods
            r'^[A-Z][a-zA-Z0-9]*\.[a-zA-Z_][a-zA-Z0-9_]*'  # Static method calls
        ]

        return any(re.match(pattern, text.strip()) for pattern in api_patterns)

    def get_analysis_stats(self) -> Dict[str, Any]:
        """
        Get source analysis statistics

        Returns:
            Dict[str, Any]: Analysis statistics
        """
        return {
            'total_documents_analyzed': len(self.documents),
            'total_github_repos_found': sum(len(doc.get('github_repos', [])) for doc in self.documents),
            'total_documentation_links_found': sum(len(doc.get('documentation_links', [])) for doc in self.documents),
            'total_technical_resources_found': sum(len(doc.get('technical_resources', [])) for doc in self.documents),
            'total_code_examples_found': sum(len(doc.get('code_examples', [])) for doc in self.documents),
            'total_related_repositories_found': sum(len(doc.get('related_repositories', [])) for doc in self.documents),
            'total_related_tutorials_found': sum(len(doc.get('related_tutorials', [])) for doc in self.documents),
            'total_related_articles_found': sum(len(doc.get('related_articles', [])) for doc in self.documents)
        }

def main():
    """Example usage of SourceAnalyzer"""
    # Create analyzer
    analyzer = SourceAnalyzer()

    # Sample content
    content = """
    Check out these great repositories:
    - https://github.com/python/cpython for the Python interpreter
    - https://github.com/facebook/react for the React library
    - https://github.com/tensorflow/tensorflow for machine learning

    Also see the official documentation:
    - https://docs.python.org/3/ for Python documentation
    - https://reactjs.org/docs/getting-started.html for React documentation

    And these technical resources:
    - https://stackoverflow.com/questions/12345678 for Python questions
    - https://medium.com/@user/python-tutorial for tutorials

    Here's a Python code example:
    ```python
    def hello_world():
        print("Hello, World!")
        return True
    ```

    And a JavaScript example:
    ```javascript
    function helloWorld() {
        console.log("Hello, World!");
        return true;
    }
    ```

    Dependencies in requirements.txt:
    requests==2.25.1
    beautifulsoup4==4.9.3
    flask==2.0.1

    Dependencies in package.json:
    "express": "^4.17.1",
    "lodash": "^4.17.21"
    """

    # Analyze content
    print("Analyzing content for related sources...")
    analysis = analyzer.analyze_content(content)

    # Display results
    print(f"\nAnalysis Results:")
    print(f"  GitHub Repos: {len(analysis['github_repos'])}")
    print(f"  Documentation Links: {len(analysis['documentation_links'])}")
    print(f"  Technical Resources: {len(analysis['technical_resources'])}")
    print(f"  Code Examples: {len(analysis['code_examples'])}")
    print(f"  Technical Terms: {len(analysis['technical_terms'])}")
    print(f"  Related Repositories: {len(analysis['related_repositories'])}")
    print(f"  Related Tutorials: {len(analysis['related_tutorials'])}")
    print(f"  Related Articles: {len(analysis['related_articles'])}")

    # Display GitHub repos
    if analysis['github_repos']:
        print(f"\nGitHub Repositories Found:")
        for repo in analysis['github_repos'][:3]:
            print(f"  - {repo['full_name']}: {repo['url']}")

    # Display documentation links
    if analysis['documentation_links']:
        print(f"\nDocumentation Links Found:")
        for link in analysis['documentation_links'][:3]:
            print(f"  - {link['domain']}: {link['url']}")

    # Display technical resources
    if analysis['technical_resources']:
        print(f"\nTechnical Resources Found:")
        for resource in analysis['technical_resources'][:3]:
            print(f"  - {resource['domain']}: {resource['url']}")

    # Display code examples
    if analysis['code_examples']:
        print(f"\nCode Examples Found:")
        for example in analysis['code_examples'][:2]:
            print(f"  - {example['language']}: {example['content'][:50]}...")

    # Display technical terms
    if analysis['technical_terms']:
        print(f"\nTechnical Terms Found:")
        print(f"  - {', '.join(analysis['technical_terms'][:10])}")

    # Display related repositories
    if analysis['related_repositories']:
        print(f"\nRelated Repositories Found:")
        for repo in analysis['related_repositories'][:3]:
            print(f"  - {repo['owner']}/{repo['name']}: {repo['description']}")

    # Display related tutorials
    if analysis['related_tutorials']:
        print(f"\nRelated Tutorials Found:")
        for tutorial in analysis['related_tutorials'][:3]:
            print(f"  - {tutorial['title']} ({tutorial['level']}): {tutorial['url']}")

    # Display related articles
    if analysis['related_articles']:
        print(f"\nRelated Articles Found:")
        for article in analysis['related_articles'][:3]:
            print(f"  - {article['title']} [{article['source']}]: {article['url']}")

    # Get analysis stats
    stats = analyzer.get_analysis_stats()
    print(f"\nAnalysis Statistics:")
    print(f"  Total Documents Analyzed: {stats['total_documents_analyzed']}")
    print(f"  GitHub Repos Found: {stats['total_github_repos_found']}")
    print(f"  Documentation Links Found: {stats['total_documentation_links_found']}")
    print(f"  Technical Resources Found: {stats['total_technical_resources_found']}")
    print(f"  Code Examples Found: {stats['total_code_examples_found']}")
    print(f"  Related Repositories Found: {stats['total_related_repositories_found']}")
    print(f"  Related Tutorials Found: {stats['total_related_tutorials_found']}")
    print(f"  Related Articles Found: {stats['total_related_articles_found']}")

if __name__ == "__main__":
    main()