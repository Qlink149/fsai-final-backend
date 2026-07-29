from pymongo import MongoClient

from qlink_chatbot.utils.env_load import mongo_uri

client = MongoClient(mongo_uri)
db = client["paac_fsai"]
