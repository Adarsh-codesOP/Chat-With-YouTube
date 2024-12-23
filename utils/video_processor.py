from youtube_transcript_api import YouTubeTranscriptApi
import os
from config.config import Config
import json
import re

class VideoProcessor:
    def __init__(self):
        # Create transcripts directory if it doesn't exist
        os.makedirs(Config.TRANSCRIPT_STORAGE, exist_ok=True)

    def get_video_id(self, url):
        """Extract video ID from YouTube URL."""
        try:
            # Pattern to match YouTube video IDs
            patterns = [
                r'(?:v=|\/)([\w-]{11})(?:\?|&|\/|$)',  # Standard YouTube URLs
                r'(?:youtu\.be\/)([\w-]{11})(?:\?|&|$)',  # Shortened YouTube URLs
                r'^([\w-]{11})$'  # Direct video ID
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            
            return None
            
        except Exception as e:
            print(f"Error extracting video ID: {e}")
            return None

    def get_transcript(self, video_url):
        """Get transcript for a YouTube video."""
        try:
            video_id = self.get_video_id(video_url)
            if not video_id:
                raise ValueError("Could not extract valid video ID")

            transcript_path = os.path.join(Config.TRANSCRIPT_STORAGE, f"{video_id}.json")

            # Check if transcript already exists
            if os.path.exists(transcript_path):
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    return json.load(f)['text']

            # Get transcript from YouTube
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            full_text = ' '.join([entry['text'] for entry in transcript])

            # Save transcript
            with open(transcript_path, 'w', encoding='utf-8') as f:
                json.dump({'video_id': video_id, 'text': full_text}, f)

            return full_text

        except Exception as e:
            print(f"Error processing video {video_url}: {e}")
            return None

    def clean_filename(self, filename):
        """Remove invalid characters from filename."""
        return "".join(c for c in filename if c.isalnum() or c in ('-', '_')).rstrip()