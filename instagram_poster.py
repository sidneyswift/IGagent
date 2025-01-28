import os
import json
import random
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from instagrapi import Client
from PIL import Image
import tempfile
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()

class InstagramPoster:
    def __init__(self):
        # Initialize Instagram client
        self.instagram = Client()
        self.session_file = Path('instagram_session.json')
        
        # Set up images directory
        self.images_dir = Path('images')
        self.posted_images_file = Path('posted_images.txt')
        
        # Create posted images file if it doesn't exist
        if not self.posted_images_file.exists():
            self.posted_images_file.touch()
            
        # Login to Instagram
        self._perform_fresh_login()

    def _perform_fresh_login(self):
        """Perform a fresh login."""
        try:
            logging.info("Logging into Instagram...")
            self.instagram.login(
                os.getenv('INSTAGRAM_USERNAME'),
                os.getenv('INSTAGRAM_PASSWORD')
            )
            logging.info("Login successful!")
        except Exception as e:
            if "Two-factor authentication required" in str(e):
                logging.error("2FA is enabled - this won't work in automated environment!")
                raise
            logging.error(f"Login failed: {e}")
            raise

    def get_posted_images(self):
        """Get list of already posted images."""
        with open(self.posted_images_file, 'r') as f:
            return set(f.read().splitlines())

    def mark_image_as_posted(self, image_path):
        """Mark an image as posted."""
        with open(self.posted_images_file, 'a') as f:
            f.write(f"{image_path}\n")

    def get_random_unposted_image(self):
        """Get a random image that hasn't been posted yet."""
        posted_images = self.get_posted_images()
        available_images = [
            img for img in self.images_dir.glob('*')
            if img.suffix.lower() in {'.jpg', '.jpeg', '.png'}
            and str(img) not in posted_images
        ]
        
        if not available_images:
            raise Exception("No unposted images available!")
            
        return random.choice(available_images)

    def generate_caption(self, image_path):
        """Generate a caption for the image."""
        try:
            logging.info(f"Generating caption for: {image_path}")
            
            # Create a prompt describing the image
            image_name = image_path.stem  # Get filename without extension
            image_description = image_name.replace('_', ' ')  # Convert filename to readable text
            
            # API endpoint
            url = "https://api.openai.com/v1/chat/completions"
            
            # Request headers
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"
            }
            
            # Request data
            data = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "you write extremely deadpan, dry captions. think gen z nihilism meets ironic detachment. lowercase only. max 4 words. no hashtags. no punctuation. no enthusiasm."
                    },
                    {
                        "role": "user",
                        "content": f"write a deadpan caption for {image_description}. max 4 words. lowercase only. be ironic or detached. think exhausted vibes."
                    }
                ],
                "temperature": 1.0,
                "max_tokens": 10
            }
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            caption = response.json()['choices'][0]['message']['content'].strip()
            logging.info(f"Generated caption: {caption}")
            return caption
            
        except Exception as e:
            logging.error(f"Error generating caption: {e}")
            return "whatever"

    def convert_to_jpeg(self, image_path):
        """Convert image to JPEG format with smart cropping."""
        try:
            logging.info(f"Converting {image_path} to JPEG...")
            temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
            temp_path = temp_file.name
            temp_file.close()

            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save as JPEG
                img.save(temp_path, 'JPEG', quality=95)
            
            logging.info(f"Image converted successfully: {temp_path}")
            return temp_path
        except Exception as e:
            logging.error(f"Error converting image: {e}")
            raise

    def post_image(self):
        """Post a single image to Instagram."""
        temp_path = None
        try:
            # Get random unposted image
            image_path = self.get_random_unposted_image()
            logging.info(f"Selected image to post: {image_path}")
            
            # Convert image to JPEG if needed
            if image_path.suffix.lower() == '.png':
                temp_path = self.convert_to_jpeg(image_path)
                upload_path = temp_path
            else:
                upload_path = str(image_path)
            
            # Generate caption
            caption = self.generate_caption(image_path)
            
            # Upload to Instagram
            logging.info("Uploading to Instagram...")
            self.instagram.photo_upload(
                upload_path,
                caption=caption
            )
            
            # Mark image as posted
            self.mark_image_as_posted(str(image_path))
            
            logging.info(f"Successfully posted {image_path} at {datetime.now()}")
            
        except Exception as e:
            logging.error(f"Error posting image: {e}")
            raise
        finally:
            # Clean up temporary file if it exists
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logging.error(f"Error cleaning up temporary file: {e}")

def main():
    try:
        logging.info("Starting Instagram Auto Poster...")
        poster = InstagramPoster()
        poster.post_image()
        logging.info("Posting complete!")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main() 