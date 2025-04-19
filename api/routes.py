from flask import Blueprint, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import mysql.connector
from werkzeug.utils import secure_filename
import os
import jwt
import datetime
from models.unet import run_unet
from functools import wraps

# Create blueprint
api_blueprint = Blueprint("api", __name__)
CORS(api_blueprint, origins=["*"])  # Allow all origins (not recommended for production)
 # Enable CORS

# MongoDB Setup
mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["ChangeDetectionDB"]
image_collection = mongo_db["Images"]

# MySQL Setup
mysql_conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Vvhm@1234",
    database="UserDB"
)
mysql_cursor = mysql_conn.cursor()

# File upload setup
UPLOAD_FOLDER = os.path.join("static", "inputs")
RESULT_FOLDER = os.path.join("static", "results")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "tif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# JWT Token Decorator
def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        if "x-access-token" in request.headers:
            token = request.headers["x-access-token"]

        if not token:
            return jsonify({"error": "Token is missing"}), 403

        try:
            data = jwt.decode(token, "secretkey", algorithms=["HS256"])
            current_user = data["email"]
        except Exception as e:
            return jsonify({"error": "Token is invalid"}), 403

        return f(current_user, *args, **kwargs)

    return decorated_function

# 1. Upload Endpoint
@api_blueprint.route("/upload", methods=["POST"])
@token_required
def upload_image(current_user):
    if "file1" not in request.files or "file2" not in request.files:
        return jsonify({"error": "Both images required"}), 400

    file1 = request.files["file1"]
    file2 = request.files["file2"]

    if file1 and file2 and allowed_file(file1.filename) and allowed_file(file2.filename):
        filename1 = secure_filename(file1.filename)
        filename2 = secure_filename(file2.filename)

        file1_path = os.path.join(UPLOAD_FOLDER, filename1)
        file2_path = os.path.join(UPLOAD_FOLDER, filename2)

        file1.save(file1_path)
        file2.save(file2_path)

        result_filename = "result_" + filename1
        result_path = os.path.join(RESULT_FOLDER, result_filename)

        run_unet(file1_path, file2_path, result_path)

        # Save metadata in MongoDB
        image_data = {
            "user": current_user,
            "original_image1": f"inputs/{filename1}",
            "original_image2": f"inputs/{filename2}",
            "result_image": f"results/{result_filename}",
            "status": "processed"
        }
        image_collection.insert_one(image_data)

        return jsonify({
            "message": "Images uploaded and processed successfully",
            "result": f"results/{result_filename}"
        }), 200

    return jsonify({"error": "Invalid file format"}), 400

# 2. Get Results Endpoint
@api_blueprint.route("/get_results", methods=["GET"])
@token_required
def get_results(current_user):
    results = list(image_collection.find({"user": current_user}, {"_id": 0}))
    return jsonify(results), 200

# 3. Register User Endpoint
@api_blueprint.route("/register", methods=["POST"])
def register_user():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    # Check if email already exists
    query = "SELECT * FROM Users WHERE email = %s"
    mysql_cursor.execute(query, (email,))
    user = mysql_cursor.fetchone()
    if user:
        return jsonify({"error": "Email already registered"}), 400

    query = "INSERT INTO Users (name, email, password) VALUES (%s, %s, %s)"
    values = (name, email, password)
    mysql_cursor.execute(query, values)
    mysql_conn.commit()

    return jsonify({"message": "User registered successfully"}), 201

# 4. Login Endpoint
@api_blueprint.route("/login", methods=["POST"])
def login_user():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    # Authenticate the user
    query = "SELECT * FROM Users WHERE email = %s AND password = %s"
    mysql_cursor.execute(query, (email, password))
    user = mysql_cursor.fetchone()

    if user:
        token = jwt.encode(
            {"email": email, "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)},
            "secretkey",
            algorithm="HS256"
        )
        return jsonify({"message": "Login successful", "token": token}), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401
