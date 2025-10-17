"""
Integration layer to add Smart Dispatcher to existing Atlas content processing
"""

from helpers.smart_dispatcher import SmartDispatcher
import logging

logger = logging.getLogger(__name__)

class ContentDispatcherIntegration:
    def __init__(self, config=None):
        self.dispatcher = SmartDispatcher(config)

    def process_with_dispatch(self, content_type: str, url: str, metadata: dict, content: str = None):
        """
        Enhanced content processing with smart dispatching
        Integrates with existing ArticleManager, ContentPipeline, etc.
        """
        logger.info(f"Dispatching {content_type}: {url}")

        # Let smart dispatcher decide
        dispatch_result = self.dispatcher.dispatch_content(content_type, url, metadata, content)

        logger.info(f"Dispatch decision: {dispatch_result['action']} - {dispatch_result['reason']}")

        return dispatch_result

    def integrate_with_article_manager(self, article_manager):
        """Add dispatch logic to ArticleManager"""
        original_process = article_manager.process_article

        def enhanced_process_article(url, **kwargs):
            # Get article metadata first
            try:
                # Try to get basic metadata without full processing
                basic_metadata = article_manager._get_article_metadata(url)

                # Decide if we should dispatch
                dispatch_result = self.process_with_dispatch('article', url, basic_metadata)

                if dispatch_result['action'] == 'process_local':
                    # Process normally with ArticleManager
                    return original_process(url, **kwargs)
                else:
                    # Return dispatch result - job queued
                    return {
                        'success': True,
                        'dispatched': True,
                        'job_id': dispatch_result.get('job_id'),
                        'reason': dispatch_result['reason']
                    }

            except Exception as e:
                logger.error(f"Dispatch integration error: {e}")
                # Fallback to normal processing
                return original_process(url, **kwargs)

        article_manager.process_article = enhanced_process_article
        return article_manager

    def integrate_with_youtube_processor(self, youtube_processor):
        """Add dispatch logic to YouTube processor"""
        original_process = youtube_processor.process_video

        def enhanced_process_video(url, **kwargs):
            try:
                # Get YouTube metadata
                metadata = youtube_processor._get_video_metadata(url)

                # Dispatch decision
                dispatch_result = self.process_with_dispatch('youtube', url, metadata)

                if dispatch_result['action'] == 'offload':
                    # Job queued for Mac Mini
                    logger.info(f"YouTube video queued for Mac Mini: {dispatch_result['job_id']}")
                    return {
                        'success': True,
                        'dispatched': True,
                        'job_id': dispatch_result.get('job_id'),
                        'content_id': dispatch_result.get('content_id'),
                        'reason': dispatch_result['reason']
                    }
                else:
                    # Process locally (transcripts available, short video, etc.)
                    return original_process(url, **kwargs)

            except Exception as e:
                logger.error(f"YouTube dispatch error: {e}")
                return original_process(url, **kwargs)

        youtube_processor.process_video = enhanced_process_video
        return youtube_processor

    def integrate_with_podcast_processor(self, podcast_processor):
        """Add dispatch logic to podcast processor"""
        original_process = podcast_processor.process_episode

        def enhanced_process_episode(episode_data, **kwargs):
            try:
                url = episode_data.get('audio_url', episode_data.get('url'))
                metadata = {
                    'title': episode_data.get('title', ''),
                    'duration_seconds': episode_data.get('duration', 0),
                    'file_size_bytes': episode_data.get('file_size', 0),
                    'description': episode_data.get('description', ''),
                    'podcast_title': episode_data.get('podcast_title', ''),
                    'episode_data': episode_data
                }

                dispatch_result = self.process_with_dispatch('podcast', url, metadata)

                if dispatch_result['action'] == 'offload':
                    logger.info(f"Podcast episode queued for Mac Mini: {dispatch_result['job_id']}")
                    return {
                        'success': True,
                        'dispatched': True,
                        'job_id': dispatch_result.get('job_id'),
                        'content_id': dispatch_result.get('content_id'),
                        'reason': dispatch_result['reason']
                    }
                else:
                    # Process locally (transcript available, short episode, etc.)
                    return original_process(episode_data, **kwargs)

            except Exception as e:
                logger.error(f"Podcast dispatch error: {e}")
                return original_process(episode_data, **kwargs)

        podcast_processor.process_episode = enhanced_process_episode
        return podcast_processor


# Convenience function for easy integration
def enhance_processors_with_dispatch(processors_dict, config=None):
    """
    Enhance multiple processors with dispatch logic

    Usage:
        processors = {
            'article_manager': article_manager,
            'youtube_processor': youtube_processor,
            'podcast_processor': podcast_processor
        }
        enhanced = enhance_processors_with_dispatch(processors)
    """
    integration = ContentDispatcherIntegration(config)

    enhanced = {}

    if 'article_manager' in processors_dict:
        enhanced['article_manager'] = integration.integrate_with_article_manager(
            processors_dict['article_manager']
        )

    if 'youtube_processor' in processors_dict:
        enhanced['youtube_processor'] = integration.integrate_with_youtube_processor(
            processors_dict['youtube_processor']
        )

    if 'podcast_processor' in processors_dict:
        enhanced['podcast_processor'] = integration.integrate_with_podcast_processor(
            processors_dict['podcast_processor']
        )

    # Return both enhanced and original for flexibility
    return {
        'enhanced': enhanced,
        'original': processors_dict,
        'dispatcher': integration.dispatcher
    }