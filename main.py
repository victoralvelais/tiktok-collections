from tiktok_collections import getCollectionData, getCollectionItems
from tiktok import getTiktokData

def main():
  config = getTiktokData()
  collections = getCollectionData(config)
  collectionData = { "collections": collections }
  collectionItems = getCollectionItems(config, collectionData)
  print(f"collectionItems {collectionItems['collections']}")
  return collectionItems

if __name__ == "__main__":
  main()