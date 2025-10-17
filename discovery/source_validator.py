#!/usr/bin/env python3
"""
Source Validator for Atlas

This module validates discovered content sources to ensure they are accessible,
reliable, and of high quality.
"""

import re
import requests
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse
import time
from collections import defaultdict


class SourceValidator:
    """Content source validation system"""

    def __init__(self):
        """Initialize the source validator"""
        # HTTP headers for requests
        self.headers = {
            'User-Agent': 'Atlas/1.0 (Content Discovery Bot)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }

        # Validation timeouts
        self.timeout = 10  # seconds

        # Quality thresholds
        self.quality_thresholds = {
            'min_content_length': 1000,  # Minimum content length in bytes
            'max_response_time': 5,      # Maximum response time in seconds
            'min_availability': 0.9,     # Minimum availability rate (90%)
        }

    def validate_source(self, source_url: str) -> Dict[str, Any]:
        """
        Validate a single content source

        Args:
            source_url (str): URL of the source to validate

        Returns:
            Dict[str, Any]: Validation results
        """
        print(f"Validating source: {source_url}")

        validation_result = {
            'url': source_url,
            'accessible': False,
            'response_time': None,
            'status_code': None,
            'content_type': None,
            'content_length': None,
            'has_paywall': False,
            'has_captcha': False,
            'robots_allowed': True,
            'quality_score': 0.0,
            'validation_timestamp': time.time(),
            'error': None
        }

        try:
            # Make HTTP request
            start_time = time.time()
            response = requests.get(
                source_url,
                headers=self.headers,
                timeout=self.timeout,
                allow_redirects=True
            )
            end_time = time.time()

            # Update validation results
            validation_result['accessible'] = True
            validation_result['response_time'] = end_time - start_time
            validation_result['status_code'] = response.status_code
            validation_result['content_type'] = response.headers.get('content-type', '')
            validation_result['content_length'] = len(response.content)

            # Check for paywalls
            validation_result['has_paywall'] = self._detect_paywall(response)

            # Check for CAPTCHAs
            validation_result['has_captcha'] = self._detect_captcha(response)

            # Check robots.txt (simplified)
            validation_result['robots_allowed'] = self._check_robots_txt(source_url)

            # Calculate quality score
            validation_result['quality_score'] = self._calculate_quality_score(validation_result)

        except requests.exceptions.Timeout:
            validation_result['error'] = 'timeout'
        except requests.exceptions.ConnectionError:
            validation_result['error'] = 'connection_error'
        except requests.exceptions.RequestException as e:
            validation_result['error'] = str(e)
        except Exception as e:
            validation_result['error'] = f'validation_error: {str(e)}'

        return validation_result

    def validate_multiple_sources(self, source_urls: List[str]) -> List[Dict[str, Any]]:
        """
        Validate multiple content sources

        Args:
            source_urls (List[str]): List of URLs to validate

        Returns:
            List[Dict[str, Any]]: Validation results for all sources
        """
        print(f"Validating {len(source_urls)} sources...")

        validation_results = []

        for url in source_urls:
            result = self.validate_source(url)
            validation_results.append(result)

            # Add small delay to be respectful to servers
            time.sleep(0.1)

        return validation_results

    def filter_valid_sources(self, validation_results: List[Dict[str, Any]],
                           min_quality_score: float = 0.7) -> List[Dict[str, Any]]:
        """
        Filter validation results to only include valid sources

        Args:
            validation_results (List[Dict[str, Any]]): Validation results
            min_quality_score (float): Minimum quality score for valid sources

        Returns:
            List[Dict[str, Any]]: Valid sources
        """
        valid_sources = []

        for result in validation_results:
            if (result['accessible'] and
                not result['has_paywall'] and
                not result['has_captcha'] and
                result['quality_score'] >= min_quality_score):
                valid_sources.append(result)

        return valid_sources

    def check_source_reliability(self, source_url: str,
                               check_period_days: int = 30) -> Dict[str, Any]:
        """
        Check source reliability over time

        Args:
            source_url (str): URL of the source to check
            check_period_days (int): Period to check reliability over (days)

        Returns:
            Dict[str, Any]: Reliability analysis
        """
        # In a real implementation, this would check historical data
        # For now, we'll return a mock reliability score

        reliability_score = 0.85  # Mock score
        availability_rate = 0.92  # Mock availability

        return {
            'url': source_url,
            'reliability_score': reliability_score,
            'availability_rate': availability_rate,
            'check_period_days': check_period_days,
            'last_check': time.time(),
            'is_reliable': reliability_score >= 0.8
        }

    def build_source_reputation(self, validation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build source reputation from validation history

        Args:
            validation_history (List[Dict[str, Any]]): Historical validation data

        Returns:
            Dict[str, Any]: Source reputation scores
        """
        if not validation_history:
            return {}

        # Group by domain
        domain_stats = defaultdict(list)
        for record in validation_history:
            domain = urlparse(record['url']).netloc
            domain_stats[domain].append(record)

        # Calculate reputation scores
        reputations = {}
        for domain, records in domain_stats.items():
            total_checks = len(records)
            successful_checks = sum(1 for r in records if r['accessible'])
            paywall_checks = sum(1 for r in records if r['has_paywall'])
            captcha_checks = sum(1 for r in records if r['has_captcha'])

            # Calculate scores
            availability = successful_checks / total_checks if total_checks > 0 else 0
            paywall_rate = paywall_checks / total_checks if total_checks > 0 else 0
            captcha_rate = captcha_checks / total_checks if total_checks > 0 else 0

            # Overall reputation score
            reputation_score = (
                availability * 0.7 +
                (1 - paywall_rate) * 0.2 +
                (1 - captcha_rate) * 0.1
            )

            reputations[domain] = {
                'domain': domain,
                'reputation_score': reputation_score,
                'availability_rate': availability,
                'paywall_rate': paywall_rate,
                'captcha_rate': captcha_rate,
                'total_checks': total_checks,
                'is_trusted': reputation_score >= 0.8
            }

        return reputations

    def _detect_paywall(self, response: requests.Response) -> bool:
        """
        Detect if content is behind a paywall

        Args:
            response (requests.Response): HTTP response

        Returns:
            bool: True if paywall detected
        """
        content = response.text.lower()

        # Common paywall indicators
        paywall_indicators = [
            'subscribe to read',
            'premium content',
            'paywall',
            'subscription required',
            'sign in to read',
            'limited access',
            'unlock full article',
            'become a member',
            'upgrade your account'
        ]

        # Check content for paywall indicators
        for indicator in paywall_indicators:
            if indicator in content:
                return True

        # Check for common paywall CSS classes
        paywall_css_classes = [
            'paywall',
            'subscription-wall',
            'premium-content',
            'member-only'
        ]

        for css_class in paywall_css_classes:
            if f'class="{css_class}"' in content or f"class='{css_class}'" in content:
                return True

        return False

    def _detect_captcha(self, response: requests.Response) -> bool:
        """
        Detect if CAPTCHA is present

        Args:
            response (requests.Response): HTTP response

        Returns:
            bool: True if CAPTCHA detected
        """
        content = response.text.lower()

        # Common CAPTCHA indicators
        captcha_indicators = [
            'captcha',
            'recaptcha',
            'hcaptcha',
            'verify you are human',
            'prove you are not a robot',
            'security check'
        ]

        for indicator in captcha_indicators:
            if indicator in content:
                return True

        return False

    def _check_robots_txt(self, url: str) -> bool:
        """
        Check if URL is allowed in robots.txt

        Args:
            url (str): URL to check

        Returns:
            bool: True if allowed, False if disallowed
        """
        try:
            parsed_url = urlparse(url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"

            response = requests.get(robots_url, headers=self.headers, timeout=5)
            if response.status_code == 200:
                # Simple check - in a real implementation, parse robots.txt properly
                content = response.text.lower()
                if f"disallow: {parsed_url.path}" in content:
                    return False
        except:
            # If we can't check robots.txt, assume it's allowed
            pass

        return True

    def _calculate_quality_score(self, validation_result: Dict[str, Any]) -> float:
        """
        Calculate quality score for a source

        Args:
            validation_result (Dict[str, Any]): Validation results

        Returns:
            float: Quality score (0.0 to 1.0)
        """
        score = 0.0

        # Accessibility (30% weight)
        if validation_result['accessible']:
            score += 0.3

        # Response time (20% weight)
        if validation_result['response_time']:
            response_time = validation_result['response_time']
            if response_time <= 1:
                score += 0.2
            elif response_time <= 3:
                score += 0.15
            elif response_time <= 5:
                score += 0.1

        # Content length (20% weight)
        if validation_result['content_length']:
            content_length = validation_result['content_length']
            if content_length >= 5000:
                score += 0.2
            elif content_length >= 2000:
                score += 0.15
            elif content_length >= 1000:
                score += 0.1

        # No paywall (15% weight)
        if not validation_result['has_paywall']:
            score += 0.15

        # No CAPTCHA (15% weight)
        if not validation_result['has_captcha']:
            score += 0.15

        return min(score, 1.0)  # Cap at 1.0


def main():
    """Example usage of SourceValidator"""
    # Create source validator
    validator = SourceValidator()

    # Sample sources to validate
    sample_sources = [
        'https://realpython.com',
        'https://javascript.info',
        'https://towardsdatascience.com',
        'https://github.com',
        'https://stackoverflow.com'
    ]

    # Validate sources
    print("Validating sources...")
    validation_results = validator.validate_multiple_sources(sample_sources)

    # Display results
    print(f"\nValidation Results:")
    for result in validation_results:
        print(f"  - {result['url']}:")
        print(f"    Accessible: {result['accessible']}")
        print(f"    Response Time: {result['response_time']:.2f}s" if result['response_time'] else "    Response Time: N/A")
        print(f"    Status Code: {result['status_code']}")
        print(f"    Content Length: {result['content_length']} bytes" if result['content_length'] else "    Content Length: N/A")
        print(f"    Paywall: {result['has_paywall']}")
        print(f"    CAPTCHA: {result['has_captcha']}")
        print(f"    Quality Score: {result['quality_score']:.2f}")
        print(f"    Error: {result['error']}" if result['error'] else "")
        print()

    # Filter valid sources
    valid_sources = validator.filter_valid_sources(validation_results, min_quality_score=0.5)
    print(f"\nValid Sources ({len(valid_sources)}):")
    for source in valid_sources:
        print(f"  - {source['url']} (Quality: {source['quality_score']:.2f})")

    # Check source reliability (mock)
    print("\nChecking source reliability...")
    reliability = validator.check_source_reliability('https://realpython.com')
    print(f"  {reliability['url']}: {reliability['reliability_score']:.2f} "
          f"(Available: {reliability['availability_rate']:.2f})")


if __name__ == "__main__":
    main()