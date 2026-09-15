from flask import Flask, request, jsonify, render_template, session
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

# Session secret key
app.secret_key = os.getenv(
    "SECRET_KEY",
    "dev-secret-key"
)


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME", "lifeflow"),
    "port": int(os.getenv("DB_PORT", "3306"))
}


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():

    try:

        connection = mysql.connector.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
            port=DB_CONFIG["port"]
        )

        return connection

    except Error as e:

        print("MySQL Connection Error:", e)

        return None


# =========================================================
# HELPER: CHECK LOGIN
# =========================================================

def is_logged_in():

    return "user_id" in session


# =========================================================
# HELPER: CHECK ADMIN
# =========================================================

def is_admin():

    return (
        "user_id" in session
        and session.get("user_role") == "admin"
    )


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    return render_template("index.html")


# =========================================================
# TEST FLASK + MYSQL
# =========================================================

@app.route("/test")
def test():

    connection = get_db_connection()

    if connection:

        connection.close()

        return "LifeFlow Flask + MySQL Connected Successfully! ✅"

    return "MySQL Connection Failed ❌", 500


# =========================================================
# REGISTER USER ACCOUNT
# =========================================================

@app.route("/api/register", methods=["POST"])
def register_user():

    data = request.get_json()

    if not data:

        return jsonify({
            "success": False,
            "message": "Invalid request data."
        }), 400

    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", "")).strip()

    if not name or not email or not password:

        return jsonify({
            "success": False,
            "message": "Name, email and password are required."
        }), 400

    if len(password) < 6:

        return jsonify({
            "success": False,
            "message": "Password must contain at least 6 characters."
        }), 400

    connection = get_db_connection()

    if not connection:

        return jsonify({
            "success": False,
            "message": "Database connection failed."
        }), 500

    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT id
            FROM users
            WHERE email = %s
        """, (email,))

        existing_user = cursor.fetchone()

        if existing_user:

            return jsonify({
                "success": False,
                "message": "An account with this email already exists."
            }), 409

        hashed_password = generate_password_hash(password)

        cursor.execute("""
            INSERT INTO users
            (
                name,
                email,
                password
            )
            VALUES
            (
                %s,
                %s,
                %s
            )
        """, (
            name,
            email,
            hashed_password
        ))

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Account registered successfully! 🎉"
        }), 201

    except Error as e:

        connection.rollback()

        print("Register Error:", e)

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:

        cursor.close()
        connection.close()


# =========================================================
# LOGIN USER
# =========================================================

@app.route("/api/login", methods=["POST"])
def login_user():

    data = request.get_json()

    if not data:

        return jsonify({
            "success": False,
            "message": "Invalid request data."
        }), 400

    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", "")).strip()

    if not email or not password:

        return jsonify({
            "success": False,
            "message": "Email and password are required."
        }), 400

    connection = get_db_connection()

    if not connection:

        return jsonify({
            "success": False,
            "message": "Database connection failed."
        }), 500

    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                id,
                name,
                email,
                password,
                role
            FROM users
            WHERE email = %s
        """, (email,))

        user = cursor.fetchone()

        if not user:

            return jsonify({
                "success": False,
                "message": "Invalid email or password."
            }), 401

        password_valid = check_password_hash(
            user["password"],
            password
        )

        if not password_valid:

            return jsonify({
                "success": False,
                "message": "Invalid email or password."
            }), 401

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]
        session["user_role"] = user["role"]

        return jsonify({

            "success": True,

            "message": "Login successful! Welcome to LifeFlow ❤️",

            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"]
            }

        })

    except Error as e:

        print("Login Error:", e)

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:

        cursor.close()
        connection.close()


# =========================================================
# LOGOUT
# =========================================================

@app.route("/api/logout", methods=["POST"])
def logout_user():

    session.clear()

    return jsonify({
        "success": True,
        "message": "Logged out successfully."
    })


# =========================================================
# CURRENT LOGGED-IN USER
# =========================================================

@app.route("/api/me", methods=["GET"])
def current_user():

    if not is_logged_in():

        return jsonify({
            "success": False,
            "logged_in": False
        })

    return jsonify({

        "success": True,

        "logged_in": True,

        "user": {
            "id": session.get("user_id"),
            "name": session.get("user_name"),
            "email": session.get("user_email"),
            "role": session.get("user_role")
        }

    })


# =========================================================
# BLOOD STOCK
# =========================================================

@app.route("/api/blood-stock", methods=["GET"])
def get_blood_stock():

    connection = get_db_connection()

    if not connection:

        return jsonify({
            "success": False,
            "message": "Database connection failed."
        }), 500

    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                id,
                blood_group,
                units,
                updated_at
            FROM blood_stock
            ORDER BY id
        """)

        stock = cursor.fetchall()

        return jsonify({
            "success": True,
            "stock": stock
        })

    except Error as e:

        print("Blood Stock Error:", e)

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:

        cursor.close()
        connection.close()


# =========================================================
# DONOR REGISTRATION
# =========================================================

@app.route("/api/donor", methods=["POST"])
def register_donor():

    if not is_logged_in():

        return jsonify({
            "success": False,
            "message": "Please login or register before donating blood."
        }), 401

    data = request.get_json()

    if not data:

        return jsonify({
            "success": False,
            "message": "Invalid request data."
        }), 400

    # Supports both "name" and "full_name"
    name = str(
        data.get("full_name", data.get("name", ""))
    ).strip()

    age = data.get("age")

    gender = str(
        data.get("gender", "")
    ).strip()

    blood_group = str(
        data.get("blood_group", "")
    ).strip()

    phone = str(
        data.get("phone", "")
    ).strip()

    city = str(
        data.get("city", "")
    ).strip()

    if not name or not blood_group:

        return jsonify({
            "success": False,
            "message": "Name and blood group are required."
        }), 400

    try:

        age = int(age)

    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "message": "Age must be a valid number."
        }), 400

    if age < 18:

        return jsonify({
            "success": False,
            "message": "Donor must be at least 18 years old."
        }), 400

    valid_blood_groups = [
        "A+",
        "A-",
        "B+",
        "B-",
        "O+",
        "O-",
        "AB+",
        "AB-"
    ]

    if blood_group not in valid_blood_groups:

        return jsonify({
            "success": False,
            "message": "Invalid blood group."
        }), 400

    valid_genders = [
        "Male",
        "Female",
        "Other"
    ]

    if gender not in valid_genders:

        return jsonify({
            "success": False,
            "message": "Invalid gender."
        }), 400

    connection = get_db_connection()

    if not connection:

        return jsonify({
            "success": False,
            "message": "Database connection failed."
        }), 500

    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO donors
            (
                full_name,
                age,
                gender,
                blood_group,
                phone,
                city,
                user_id
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
        """, (
            name,
            age,
            gender,
            blood_group,
            phone,
            city,
            session["user_id"]
        ))

        connection.commit()

        donor_id = cursor.lastrowid

        return jsonify({

            "success": True,

            "message":
                "Donor registered successfully ❤️",

            "donor_id":
                donor_id

        })

    except Error as e:

        connection.rollback()

        print("Donor Registration Error:", e)

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:

        cursor.close()
        connection.close()


# =========================================================
# BLOOD REQUEST
# =========================================================

@app.route("/api/request-blood", methods=["POST"])
def request_blood():

    if not is_logged_in():

        return jsonify({
            "success": False,
            "message": "Please login or register before requesting blood."
        }), 401

    data = request.get_json()

    if not data:

        return jsonify({
            "success": False,
            "message": "Invalid request data."
        }), 400

    patient_name = str(
        data.get("patient_name", "")
    ).strip()

    hospital_name = str(
        data.get("hospital_name", "")
    ).strip()

    blood_group = str(
        data.get("blood_group", "")
    ).strip()

    units = data.get("units")

    location = str(
        data.get("location", "")
    ).strip()

    priority = str(
        data.get("priority", "Normal")
    ).strip()

    if (
        not patient_name
        or not hospital_name
        or not blood_group
        or units is None
        or not location
    ):

        return jsonify({
            "success": False,
            "message":
                "Please fill all required blood request fields."
        }), 400

    try:

        units = int(units)

    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "message": "Units must be a number."
        }), 400

    if units <= 0:

        return jsonify({
            "success": False,
            "message": "Units must be greater than 0."
        }), 400

    valid_blood_groups = [
        "A+",
        "A-",
        "B+",
        "B-",
        "O+",
        "O-",
        "AB+",
        "AB-"
    ]

    if blood_group not in valid_blood_groups:

        return jsonify({
            "success": False,
            "message": "Invalid blood group."
        }), 400

    if priority == "High":

        priority = "Urgent"

    valid_priorities = [
        "Normal",
        "Urgent",
        "Emergency"
    ]

    if priority not in valid_priorities:

        priority = "Normal"

    connection = get_db_connection()

    if not connection:

        return jsonify({
            "success": False,
            "message": "Database connection failed."
        }), 500

    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO blood_requests
            (
                patient_name,
                hospital_name,
                blood_group,
                units,
                location,
                priority,
                user_id
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
        """, (
            patient_name,
            hospital_name,
            blood_group,
            units,
            location,
            priority,
            session["user_id"]
        ))

        connection.commit()

        request_id = cursor.lastrowid

        return jsonify({

            "success": True,

            "message":
                "Blood request submitted successfully 🩸",

            "request_id":
                request_id

        })

    except Error as e:

        connection.rollback()

        print("Blood Request Error:", e)

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:

        cursor.close()
        connection.close()


# =========================================================
# GET ALL BLOOD REQUESTS
# =========================================================

@app.route("/api/requests", methods=["GET"])
def get_requests():

    connection = get_db_connection()

    if not connection:

        return jsonify({
            "success": False,
            "message": "Database connection failed."
        }), 500

    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                br.id,
                br.user_id,
                u.name AS requester_name,
                u.email AS requester_email,
                br.patient_name,
                br.hospital_name,
                br.blood_group,
                br.units,
                br.location,
                br.priority,
                br.status,
                br.created_at

            FROM blood_requests br

            LEFT JOIN users u
                ON br.user_id = u.id

            ORDER BY br.id DESC
        """)

        requests = cursor.fetchall()

        return jsonify({
            "success": True,
            "requests": requests
        })

    except Error as e:

        print("Get Requests Error:", e)

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:

        cursor.close()
        connection.close()


# =========================================================
# ADMIN STATISTICS
# =========================================================

@app.route("/api/admin/stats", methods=["GET"])
def admin_stats():

    if not is_admin():

        return jsonify({
            "success": False,
            "message": "Admin access required."
        }), 403

    connection = get_db_connection()

    if not connection:

        return jsonify({
            "success": False,
            "message": "Database connection failed."
        }), 500

    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT COUNT(*) AS total_donors
            FROM donors
        """)

        donor_result = cursor.fetchone()

        total_donors = int(
            donor_result["total_donors"]
        )

        cursor.execute("""
            SELECT
                COALESCE(SUM(units), 0) AS total_units
            FROM blood_stock
        """)

        stock_result = cursor.fetchone()

        total_units = int(
            stock_result["total_units"]
        )

        cursor.execute("""
            SELECT COUNT(*) AS total_requests
            FROM blood_requests
        """)

        request_result = cursor.fetchone()

        total_requests = int(
            request_result["total_requests"]
        )

        cursor.execute("""
            SELECT COUNT(*) AS pending_requests
            FROM blood_requests
            WHERE status = 'Pending'
        """)

        pending_result = cursor.fetchone()

        pending_requests = int(
            pending_result["pending_requests"]
        )

        cursor.execute("""
            SELECT COUNT(*) AS approved_requests
            FROM blood_requests
            WHERE status = 'Approved'
        """)

        approved_result = cursor.fetchone()

        approved_requests = int(
            approved_result["approved_requests"]
        )

        cursor.execute("""
            SELECT COUNT(*) AS rejected_requests
            FROM blood_requests
            WHERE status = 'Rejected'
        """)

        rejected_result = cursor.fetchone()

        rejected_requests = int(
            rejected_result["rejected_requests"]
        )

        return jsonify({

            "success": True,

            "total_donors":
                total_donors,

            "total_units":
                total_units,

            "total_requests":
                total_requests,

            "pending_requests":
                pending_requests,

            "approved_requests":
                approved_requests,

            "rejected_requests":
                rejected_requests

        })

    except Error as e:

        print("Admin Stats Error:", e)

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:

        cursor.close()
        connection.close()


# =========================================================
# ADMIN APPROVE BLOOD REQUEST
# =========================================================

@app.route(
    "/api/admin/request/<int:request_id>/approve",
    methods=["PUT"]
)
def approve_request(request_id):

    if not is_admin():

        return jsonify({
            "success": False,
            "message": "Admin access required."
        }), 403

    connection = get_db_connection()

    if not connection:

        return jsonify({
            "success": False,
            "message": "Database connection failed."
        }), 500

    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                id,
                blood_group,
                units,
                status

            FROM blood_requests

            WHERE id = %s

            FOR UPDATE
        """, (request_id,))

        req = cursor.fetchone()

        if not req:

            connection.rollback()

            return jsonify({
                "success": False,
                "message": "Blood request not found."
            }), 404

        if req["status"] != "Pending":

            connection.rollback()

            return jsonify({
                "success": False,
                "message":
                    "This request has already been processed."
            }), 400

        blood_group = req["blood_group"]

        requested_units = int(
            req["units"]
        )

        cursor.execute("""
            SELECT
                units

            FROM blood_stock

            WHERE blood_group = %s

            FOR UPDATE
        """, (blood_group,))

        stock = cursor.fetchone()

        if not stock:

            connection.rollback()

            return jsonify({
                "success": False,
                "message":
                    "Blood group not found in stock."
            }), 404

        available_units = int(
            stock["units"]
        )

        if available_units < requested_units:

            connection.rollback()

            return jsonify({
                "success": False,
                "message":
                    f"Insufficient {blood_group} blood stock. "
                    f"Available: {available_units} units, "
                    f"Required: {requested_units} units."
            }), 400

        cursor.execute("""
            UPDATE blood_stock

            SET units = units - %s

            WHERE blood_group = %s
        """, (
            requested_units,
            blood_group
        ))

        cursor.execute("""
            UPDATE blood_requests

            SET status = 'Approved'

            WHERE id = %s
        """, (request_id,))

        connection.commit()

        return jsonify({

            "success": True,

            "message":
                f"Request #{request_id} approved successfully. "
                f"{requested_units} units of {blood_group} "
                f"deducted from stock."

        })

    except Error as e:

        connection.rollback()

        print("Approve Request Error:", e)

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:

        cursor.close()
        connection.close()


# =========================================================
# ADMIN REJECT BLOOD REQUEST
# =========================================================

@app.route(
    "/api/admin/request/<int:request_id>/reject",
    methods=["PUT"]
)
def reject_request(request_id):

    if not is_admin():

        return jsonify({
            "success": False,
            "message": "Admin access required."
        }), 403

    connection = get_db_connection()

    if not connection:

        return jsonify({
            "success": False,
            "message": "Database connection failed."
        }), 500

    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                id,
                status

            FROM blood_requests

            WHERE id = %s

            FOR UPDATE
        """, (request_id,))

        req = cursor.fetchone()

        if not req:

            connection.rollback()

            return jsonify({
                "success": False,
                "message": "Blood request not found."
            }), 404

        if req["status"] != "Pending":

            connection.rollback()

            return jsonify({
                "success": False,
                "message":
                    "This request has already been processed."
            }), 400

        cursor.execute("""
            UPDATE blood_requests

            SET status = 'Rejected'

            WHERE id = %s
        """, (request_id,))

        connection.commit()

        return jsonify({

            "success": True,

            "message":
                f"Request #{request_id} rejected successfully."

        })

    except Error as e:

        connection.rollback()

        print("Reject Request Error:", e)

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:

        cursor.close()
        connection.close()


# =========================================================
# RUN FLASK SERVER
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
