import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
import random

# Load environment variables
load_dotenv()

def test_caption_generation(image_path):
    """Test generating a caption for a single image."""
    try:
        print(f"\nGenerating caption for: {image_path}")
        
        # Create a prompt describing the image
        image_name = image_path.stem  # Get filename without extension
        image_description = image_name.replace('_', ' ')  # Convert filename to readable text
        
        print("Generating caption...")
        
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
        
        # Make the API call
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Parse the response
        result = response.json()
        caption = result['choices'][0]['message']['content'].strip()
        print(f"\nGenerated caption: {caption}")
        return caption
        
    except Exception as e:
        print(f"Error: {e}")
        print(f"Error type: {type(e)}")
        print(f"Error details: {str(e)}")
        if isinstance(e, requests.exceptions.HTTPError):
            print(f"Response content: {e.response.content}")
        return None

if __name__ == "__main__":
    # List all images
    images_dir = Path('images')
    all_images = list(images_dir.glob('*'))
    
    # Print available images
    print("\nAvailable images:")
    for i, img in enumerate(all_images):
        print(f"{i}: {img.name}")
    
    # Get user input
    try:
        choice = int(input("\nEnter the number of the image to test (or press Enter for random): ").strip() or "-1")
        if choice >= 0:
            test_image = all_images[choice]
        else:
            test_image = random.choice(all_images)
        test_caption_generation(test_image)
    except (ValueError, IndexError):
        print("Invalid input, using random image...")
        test_image = random.choice(all_images)
        test_caption_generation(test_image) 