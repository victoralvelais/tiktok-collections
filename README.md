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

## Usage
Run the main script to capture your TikTok session data and fetch collections:
```$ python main.py```

This will:
- Open a browser window to log in on first run
- Capture necessary cookies & data to access your collections (i.e. username)
- Fetch a list of all your collections
- Fetch all items within each collection
- Save collective metadata to a JSON file named `collection_data_[username].json`
- Save videos & slideshow photos to their collections folder under `[username]-tiktok-collection`
- Save a metadata file in the collections containing details for the collection (name, description, etc.) and each entry
- Metadata information includes data about the video, author, music, and statistics (likes, shares, etc.)

## Note
Automatic cookie fetching & using your personal browser for sessions is planned, but not a priority.