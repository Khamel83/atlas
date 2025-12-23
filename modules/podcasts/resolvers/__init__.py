# Transcript resolvers package

from .youtube_transcript import YouTubeTranscriptResolver
from .network_transcripts import NetworkTranscriptResolver
from .rss_link import RSSLinkResolver
from .generic_html import GenericHTMLResolver
from .podscripts import PodscriptsResolver


def get_all_resolvers():
    """Return instances of all available transcript resolvers."""
    return [
        RSSLinkResolver(),
        GenericHTMLResolver(),
        NetworkTranscriptResolver(),
        PodscriptsResolver(),
        YouTubeTranscriptResolver(),
    ]


__all__ = [
    'YouTubeTranscriptResolver',
    'NetworkTranscriptResolver',
    'RSSLinkResolver',
    'GenericHTMLResolver',
    'PodscriptsResolver',
    'get_all_resolvers',
]
