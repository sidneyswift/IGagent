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
import time

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
        
        # Set consistent device settings
        self._set_device_settings()
            
        # Try to load existing session first
        if not self._load_session():
            # If no session exists, perform fresh login
            self._perform_fresh_login()
            # Save the session for future use
            self._save_session()

    def _set_device_settings(self):
        """Set consistent device settings to avoid suspicious activity flags."""
        # Use consistent device settings
        self.instagram.set_device({
            "app_version": "269.0.0.18.75",
            "android_version": 26,
            "android_release": "8.0.0",
            "dpi": "480dpi",
            "resolution": "1080x1920",
            "manufacturer": "Samsung",
            "device": "SM-G973F",
            "model": "Galaxy S10",
            "cpu": "exynos",
            "version_code": "314665256"
        })
        
        # Set additional client settings
        self.instagram.set_user_agent("Instagram 269.0.0.18.75 Android (26/8.0.0; 480dpi; 1080x1920; Samsung; SM-G973F; Galaxy S10; exynos; en_US; 314665256)")
        self.instagram.set_country("US")
        self.instagram.set_country_code(1)  # US country code
        self.instagram.set_locale("en_US")
        
        # Set request timeout
        self.instagram.request_timeout = 30
        
        # If running in GitHub Actions, use proxy if provided
        if os.getenv('GITHUB_ACTIONS') == 'true' and os.getenv('PROXY_URL'):
            proxy_url = os.getenv('PROXY_URL')
            self.instagram.set_proxy(proxy_url)
            logging.info("Running in GitHub Actions - Proxy configured")

    def _load_session(self):
        """Try to load existing session."""
        try:
            if self.session_file.exists():
                logging.info("Loading existing session...")
                settings = json.loads(self.session_file.read_text())
                self.instagram.set_settings(settings)
                
                # Verify the session is still valid
                try:
                    self.instagram.get_timeline_feed()
                    logging.info("Session loaded successfully!")
                    return True
                except Exception as e:
                    logging.warning(f"Stored session is invalid: {str(e)}")
                    return False
        except Exception as e:
            logging.warning(f"Error loading session: {str(e)}")
            return False
        return False

    def _save_session(self):
        """Save current session for future use."""
        try:
            logging.info("Saving session...")
            settings = self.instagram.get_settings()
            self.session_file.write_text(json.dumps(settings))
            logging.info("Session saved successfully!")
        except Exception as e:
            logging.error(f"Error saving session: {str(e)}")

    def _perform_fresh_login(self):
        """Perform a fresh login."""
        try:
            logging.info("Attempting login...")
            
            # Small delay before login
            time.sleep(2)
            
            username = os.getenv('INSTAGRAM_USERNAME')
            password = os.getenv('INSTAGRAM_PASSWORD')
            
            print("\nAttempting to log in to Instagram...")
            
            # First try to login without 2FA
            try:
                # If running in GitHub Actions, use pre-saved session
                if os.getenv('GITHUB_ACTIONS') == 'true':
                    if os.getenv('INSTAGRAM_SESSION_DATA'):
                        logging.info("Running in GitHub Actions - Using provided session data")
                        session_data = json.loads(os.getenv('INSTAGRAM_SESSION_DATA'))
                        self.instagram.set_settings(session_data)
                        self.instagram.get_timeline_feed()  # Verify session
                        print("Login successful using session data!")
                        return
                    else:
                        raise Exception("No session data provided for GitHub Actions")
                
                # Normal login flow for local development
                self.instagram.login(username, password)
                print("Login successful!")
            except Exception as e:
                if any(phrase in str(e).lower() for phrase in ["two_factor", "2fa", "verification"]):
                    print("\n" + "="*50)
                    print("TWO FACTOR AUTHENTICATION REQUIRED")
                    print("="*50)
                    verification_code = input("Enter the 2FA code from your phone: ").strip()
                    print("="*50)
                    
                    # Try login with 2FA
                    self.instagram.login(username, password, verification_code=verification_code)
                    print("2FA Login successful!")
                    
                    if os.getenv('SAVE_SESSION') == 'true':
                        # Save session data for GitHub Actions
                        settings = self.instagram.get_settings()
                        print("\nCopy this session data to your GitHub repository secrets as INSTAGRAM_SESSION_DATA:")
                        print("="*50)
                        print(json.dumps(settings))
                        print("="*50)
                elif "challenge_required" in str(e).lower():
                    print("\n" + "="*50)
                    print("INSTAGRAM SECURITY CHECK REQUIRED")
                    print("="*50)
                    print("1. Please log in to Instagram through the app")
                    print("2. Complete any security checks")
                    print("3. Try running this script again")
                    print("="*50 + "\n")
                    raise
                else:
                    print(f"\nLogin failed: {str(e)}")
                    raise
            
            # Verify the connection
            self.instagram.get_timeline_feed()
            logging.info("Login successful!")
            
            # Save the session immediately after successful login
            self._save_session()
            print("Session saved - you won't need to enter 2FA next time!")
            
        except Exception as e:
            logging.error(f"Login failed: {str(e)}")
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

    def convert_to_jpeg(self, image_path):
        """Convert image to JPEG format."""
        try:
            logging.info(f"Converting {image_path} to JPEG...")
            with Image.open(image_path) as img:
                # Create a temporary file with .jpg extension
                temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                
                # Convert to RGB if necessary and save as JPEG
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                img.save(temp_file.name, 'JPEG')
                logging.info(f"Image converted successfully: {temp_file.name}")
                return temp_file.name
                
        except Exception as e:
            logging.error(f"Error converting image: {e}")
            raise

    def generate_caption(self, image_path):
        """Generate a caption for the image using GPT-4."""
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                "Content-Type": "application/json"
            }
            
            # Extract the base filename without extension
            image_name = Path(image_path).stem
            # Replace underscores with spaces and remove any random strings
            prompt = image_name.split('_')[:-1]  # Remove the last part which is usually random
            prompt = ' '.join(prompt)
            
            data = {
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a creative Instagram caption writer. Write short, engaging captions that are casual and fun."
                    },
                    {
                        "role": "user",
                        "content": f"Write a short, fun caption for an Instagram post. The image is about: {prompt}"
                    }
                ],
                "max_tokens": 100
            }
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            caption = response.json()['choices'][0]['message']['content'].strip()
            logging.info(f"Generated caption: {caption}")
            return caption
            
        except Exception as e:
            logging.error(f"Error generating caption: {e}")
            return "whatever"

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
        
        # Debug environment in GitHub Actions
        if os.getenv('GITHUB_ACTIONS') == 'true':
            logging.info("Running in GitHub Actions environment")
            logging.info(f"Username: {os.getenv('INSTAGRAM_USERNAME')}")
            logging.info("OpenAI API Key exists: " + str(bool(os.getenv('OPENAI_API_KEY'))))
            logging.info("Session data exists: " + str(bool(os.getenv('INSTAGRAM_SESSION_DATA'))))
            
            # List available files
            logging.info("Available files:")
            for file in os.listdir('.'):
                logging.info(f"- {file}")
        
        poster = InstagramPoster()
        poster.post_image()
        logging.info("Posting complete!")
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        if os.getenv('GITHUB_ACTIONS') == 'true':
            logging.error("Full error details:", exc_info=True)
        raise

if __name__ == "__main__":
    main() 