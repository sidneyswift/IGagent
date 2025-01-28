# Instagram Auto Poster

This Python application automatically posts images from a local folder to Instagram with AI-generated captions.

## Features
- Automatically posts one image per day at 12:00 PM
- Generates engaging captions using OpenAI's GPT-3.5
- Keeps track of posted images to avoid duplicates
- Supports JPG, JPEG, and PNG image formats

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the project root and add your credentials:
```
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password
OPENAI_API_KEY=your_openai_api_key
```

3. Place your images in the `images` folder.

## Usage

Run the application:
```bash
python instagram_poster.py
```

The app will:
- Post one image immediately when started
- Schedule future posts for 12:00 PM daily
- Keep track of posted images in `posted_images.txt`

## Notes
- Make sure your Instagram account has 2FA disabled
- Images should be in JPG, JPEG, or PNG format
- Keep the script running to maintain the posting schedule
- Monitor the console output for any posting errors 