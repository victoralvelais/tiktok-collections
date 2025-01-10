# tiktok-collections
A Python utility for backing up your TikTok collections. It captures collection metadata and will eventually support downloading the videos themselves as mp4 files.

## Installation
```
$ git clone https://github.com/victoralvelais/tiktok-collections.git
$ cd tiktok-collections
$ python -m playwright install
$ pip install -r requirements.txt
```

If you get permission errors, try using `sudo` or using a virtual environment.

## Configuration
You can create a `credentials.json` file with the following structure to automate the login inputs:
```
{
  "username": "your_email",
  "password": "your_password"
}
```
Note: You'll still have to manually solve TikTok's captcha, but it can save you some grief if you use it often.

## Usage
Run the main script to capture your TikTok session data and fetch collections:
```$ python main.py```

This will:
- Open a browser window where you'll need to log in (if no valid session exists)
- Capture necessary cookies and app context data
- Fetch a list of all your collections
- Fetch all items within each collection
- Save everything to a JSON file named `collection_data_[username].json`

## Output
The tool generates a JSON file containing:
- List of all your collections
- Collection metadata (name, description, etc.)
- Details for each video in the collections including:
  - Video metadata (duration, dimensions, etc.)
  - Author information
  - Music details
  - Statistics (likes, shares, etc.)

## Note
Video downloading functionality is planned for future updates.