from tiktok_collections import getCollectionData, getCollectionItems, getFavorites
from tiktok import getTiktokData
from download import downloadCollectionVideos
import asyncio

async def main():
  config = getTiktokData()

  # Get collections
  collections = getCollectionData(config)
  collectionData = { "collections": collections }
  collectionItems = getCollectionItems(config, collectionData)

  # Get all video IDs from collections
  collectedIds = set()
  for collection in collectionItems["collections"]:
    collectedIds.update(item['id'] for item in collection.get('itemList', []))
  print(f"Total unique videos found in collections: {len(collectedIds)}")
  
  # Get favorites and filter out already collected ones
  favorites = getFavorites(config)
  uncategorized = [
    item 
    for item in favorites 
    if item['id'] not in collectedIds
  ]

  # Create a "Favorites" pseudo-collection
  uncategorizedFavorites = {
    "collections": [{
      "name": "Uncategorized",
      "itemList": uncategorized
    }]
  }

# Download collections & favorites
  await downloadCollectionVideos(collectionItems, config)
  await downloadCollectionVideos(uncategorizedFavorites, config)

if __name__ == "__main__":
  asyncio.run(main())