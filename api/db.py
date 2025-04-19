from pymongo import MongoClient
import mysql.connector

# MongoDB Configuration
mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["ChangeDetectionDB"]
image_collection = mongo_db["Images"]

# MySQL Configuration
mysql_conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Vvhm@1234",
    database="UserDB"
)
mysql_cursor = mysql_conn.cursor()
