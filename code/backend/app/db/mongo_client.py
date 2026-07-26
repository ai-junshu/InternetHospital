"""MongoDB 客户端（技术架构第5章：治疗记录/评估原始 JSON）。

脚手架阶段使用 pymongo 同步客户端占位；生产建议在异步环境中替换为 motor。
"""
from pymongo import MongoClient
from pymongo.database import Database

from app.core.config import settings

mongo_client: MongoClient = MongoClient(settings.mongo_uri)
mongo_db: Database = mongo_client.get_default_database()
