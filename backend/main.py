from flask import Flask, request, jsonify,send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
import pymongo
import certifi
import smtplib
from email.message import EmailMessage
from bson import ObjectId
from datetime import datetime
import time
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os 
import sys
import bcrypt
from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware
from werkzeug.utils import secure_filename 

app = Flask(__name__)

app = Flask(__name__)
CORS(app)

app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

MONGO_URI = "mongodb+srv://ddarn3681:eyl349H2RkqaraZb@cluster0.ezhvpef.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    client = pymongo.MongoClient(MONGO_URI, tls=True, tlsCAFile=certifi.where())
    db = client.get_database("event_db")
    collection = db["registrations"]
    hall_collections = {
        "Seminar Hall 1": db["seminar_hall_1"],
        "Seminar Hall 2": db["seminar_hall_2"],
        "Seminar Hall 3": db["seminar_hall_3"]
    }
    print("✅ MongoDB connected successfully!")
except Exception as e:
    print("❌ MongoDB connection failed:", e)



COORDINATOR_EMAIL = "coordinator@example.com"  # Replace with actual coordinator email
APPROVED_EMAILS = ["ajaiks2005@gmail.com", "tm07hariharan2122@gmail.com", "ajaisha2021@gmail.com"]

users = {
    "kncet@principal": {"password": bcrypt.hashpw("principal@123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), "role": "principal"},
    "hod.it@kncet": {"password": bcrypt.hashpw("hodit@123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), "role": "hod", "department": "IT"},
    "hod.cse@kncet": {"password": bcrypt.hashpw("hodcse@123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), "role": "hod", "department": "CSE"},
    "hod.ece@kncet": {"password": bcrypt.hashpw("hodece@123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), "role": "hod", "department": "ECE"},
    "hod.eee@kncet": {"password": bcrypt.hashpw("hodeee@123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), "role": "hod", "department": "EEE"},
    "hod.civil@kncet": {"password": bcrypt.hashpw("hodcivil@123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), "role": "hod", "department": "Civil"},
    "hod.bme@kncet": {"password": bcrypt.hashpw("hodbme@123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), "role": "hod", "department": "BME"},
    "hod.agri@kncet": {"password": bcrypt.hashpw("hodagri@123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), "role": "hod", "department": "Agri"},
    "hod.ads@kncet": {"password": bcrypt.hashpw("hodads@123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), "role": "hod", "department": "ADS"},
    "hod.mech@kncet": {"password": bcrypt.hashpw("hodmech@123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), "role": "hod", "department": "Mech"},
}

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user_id = data.get("id")
    password = data.get("password")

    user = users.get(user_id)
    
    if user and bcrypt.checkpw(password.encode('utf-8'), user["password"].encode('utf-8')):
        response = {"message": "Login successful", "user": user_id, "role": user["role"]}
        if user["role"] == "hod":
            response["department"] = user["department"]
        return jsonify(response), 200
    else:
        return jsonify({"message": "Invalid credentials"}), 401


@app.route("/approved_bookings", methods=["GET"])
def get_approved_bookings():
    try:
        approved_bookings = {}
        current_time = datetime.now()

        for hall_name, collection in hall_collections.items():
            bookings = list(collection.find({"status": "approved"}))

            for booking in bookings:
                booking["_id"] = str(booking["_id"]) 

                print(f"Checking booking: {booking}")

                if "Date" not in booking or "TimeTo" not in booking:
                    print(f"Skipping booking due to missing Date or TimeTo: {booking}")
                    continue

                try:
                    booking_date = datetime.strptime(booking["Date"], "%Y-%m-%d")
                    end_time = datetime.strptime(booking["TimeTo"], "%H:%M")
                    booking_end_datetime = datetime.combine(booking_date.date(), end_time.time())

                    if booking_end_datetime < current_time:
                        collection.update_one(
                            {"_id": ObjectId(booking["_id"])},
                            {"$set": {"status": "Completed"}}
                        )
                        booking["status"] = "Completed"
                        print(f"✅ Status updated to 'Completed' for booking: {booking}")

                except ValueError as e:
                    print(f"❌ Error parsing date/time: {e}")

            approved_bookings[hall_name] = bookings

        return jsonify(approved_bookings)

    except Exception as e:
        print(f"🔥 Server error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/cancel_booking/<booking_id>", methods=["PUT"])
def cancel_booking(booking_id):
    try:
        if not ObjectId.is_valid(booking_id):
            return jsonify({"error": "Invalid booking ID"}), 400

        data = request.json 
        cancel_reason = data.get("cancel_reason", "")

        if not cancel_reason:
            return jsonify({"error": "Cancellation reason is required"}), 400

        for hall_name, collection in hall_collections.items():
            booking = collection.find_one({"_id": ObjectId(booking_id)})
            if booking:
                result = collection.update_one(
                    {"_id": ObjectId(booking_id)},
                    {"$set": {"status": "Cancelled", "cancel_reason": cancel_reason}}
                )

                if result.modified_count == 1:
                    return jsonify({"message": f"Booking in {hall_name} cancelled successfully"})

                return jsonify({"error": "Failed to update booking status"}), 500

        return jsonify({"error": "Booking not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/canceled_bookings", methods=["GET"])
def get_canceled_bookings():
    try:
        canceled_bookings = {}

        for hall_name, collection in hall_collections.items():
            bookings = list(collection.find({"status": "Cancelled"}))

            for booking in bookings:
                booking["_id"] = str(booking["_id"])

            canceled_bookings[hall_name] = bookings  

        return jsonify(canceled_bookings)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def update_completed_bookings():
    current_time = datetime.now()
    for hall_name, collection in hall_collections.items():
        bookings = list(collection.find({"status": "approved"}))
        for booking in bookings:
            booking_date_str = booking.get("Date")
            time_to_str = booking.get("TimeTo")
            if not booking_date_str or not time_to_str:
                continue
            try:
                booking_date = datetime.strptime(booking_date_str, "%Y-%m-%d")
                time_to = datetime.strptime(time_to_str, "%H:%M").time()
                booking_end_datetime = datetime.combine(booking_date.date(), time_to)
                if booking_end_datetime <= current_time:
                    collection.update_one(
                        {"_id": booking["_id"]},
                        {"$set": {"status": "Completed", "completedAt": current_time}}
                    )
                    print(f"✅ Booking {booking['_id']} marked Completed")
            except Exception as e:
                print(f"❌ Error parsing booking datetime: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(update_completed_bookings, "interval", minutes=1)
scheduler.start()


def send_completed_booking_email(selected_hall, booking):
    """Send email to coordinator to upload extra details after booking completion."""
    try:
        coordinator_email = booking.get("CoordinatorEmail")
        if not coordinator_email:
            return

        subject = f"Seminar Hall Booking Completed - {selected_hall}"
        email_body = f"""
        <h2>Your seminar hall booking has been completed.</h2>
        <p><strong>Coordinator Name:</strong> {booking.get("CoordinatorName", "N/A")}</p>
        <p><strong>Department:</strong> {booking.get("Department", "N/A")}</p>
        <p><strong>Event Name:</strong> {booking.get("EventName", "N/A")}</p>
        <p><strong>Seminar Hall:</strong> {selected_hall}</p>
        <p><strong>Date:</strong> {booking.get("Date", "N/A")}</p>
        <p><strong>Time:</strong> {booking.get("TimeFrom", "N/A")} - {booking.get("TimeTo", "N/A")}</p>
        <p><strong>Action Required:</strong> Please upload photos, geotag, and event document within 1 day to complete the record.</p>
        <p>Upload Link: <a href="http://your-frontend-url.com/upload_details">Click here to upload</a></p>
        """

        send_email(coordinator_email, subject, email_body)
        print(f"📧 Email sent to coordinator: {coordinator_email}")

    except Exception as e:
        print(f"❌ Error sending completion email: {e}")



        
@app.route("/completed_bookings", methods=["GET"])
def get_completed_bookings():
    try:
        completed_bookings = {}
        for hall_name, collection in hall_collections.items():
            bookings = list(collection.find({"status": "Completed"}))
            for booking in bookings:
                booking["_id"] = str(booking["_id"])
            completed_bookings[hall_name] = bookings
        return jsonify(completed_bookings)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

app.config["UPLOAD_FOLDER"] = os.path.join(os.getcwd(), "uploads")


@app.route("/get_completed", methods=["GET"])
def get_completed():
    completed = list(collection.find({"status": "Total Completed"}))  
    for item in completed:
        item["_id"] = str(item["_id"])
    return jsonify(completed)

@app.route("/upload_details", methods=["POST"])
def upload_details():
    try:
        booking_id = request.form.get("bookingId")
        hall_name = request.form.get("hallName")
        extra_details = request.form.get("extraDetails")

        photo_file = request.files.get("photo")
        geotag_file = request.files.get("geotagPhoto")
        event_doc_file = request.files.get("eventDoc")

        # Debug log
        print("---- DEBUG /upload_details ----")
        print("bookingId received:", booking_id)
        print("hall_name:", hall_name)
        print("extra_details:", extra_details)
        print("files:", request.files.keys())
        print("hall_collections keys:", list(hall_collections.keys()))
        print("------------------------------")

        # ✅ Validation checks
        if not booking_id:
            return jsonify({"success": False, "message": "Booking ID missing"}), 400
        if not hall_name:
            return jsonify({"success": False, "message": "Hall name missing"}), 400
        if not extra_details:
            return jsonify({"success": False, "message": "Extra details missing"}), 400
        if not photo_file:
            return jsonify({"success": False, "message": "Photo file missing"}), 400
        if not geotag_file:
            return jsonify({"success": False, "message": "Geotag photo missing"}), 400
        if not event_doc_file:
            return jsonify({"success": False, "message": "Event doc missing"}), 400

        # ✅ Check hall collection exists
        if hall_name not in hall_collections:
            return jsonify({"success": False, "message": f"Invalid seminar hall: {hall_name}"}), 400

        collection = hall_collections[hall_name]
        if collection is None:
            return jsonify({"success": False, "message": "No DB collection linked for this hall"}), 400

        # ✅ Save uploaded files
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

        photo_filename = secure_filename(photo_file.filename)
        geotag_filename = secure_filename(geotag_file.filename)
        doc_filename = secure_filename(event_doc_file.filename)

        photo_path = os.path.join(app.config["UPLOAD_FOLDER"], photo_filename)
        geotag_path = os.path.join(app.config["UPLOAD_FOLDER"], geotag_filename)
        doc_path = os.path.join(app.config["UPLOAD_FOLDER"], doc_filename)

        photo_file.save(photo_path)
        geotag_file.save(geotag_path)
        event_doc_file.save(doc_path)

        # ✅ Generate accessible URLs
        server_url = request.host_url.rstrip("/")  # e.g. http://localhost:5000
        photo_url = f"{server_url}/uploads/{photo_filename}"
        geotag_url = f"{server_url}/uploads/{geotag_filename}"
        doc_url = f"{server_url}/uploads/{doc_filename}"

        # ✅ Validate bookingId is a valid ObjectId
        try:
            booking_object_id = ObjectId(booking_id)
        except Exception as e:
            return jsonify({"success": False, "message": "Invalid booking ID", "error": str(e)}), 400

        # ✅ Update booking in DB
        update_result = collection.update_one(
            {"_id": booking_object_id},
            {"$set": {
                "status": "Total Completed",
                "extraDetails": extra_details,
                "photo": photo_url,
                "geotagPhoto": geotag_url,
                "eventDoc": doc_url
            }}
        )

        if update_result.modified_count == 0:
            return jsonify({"success": False, "message": "Booking not found or update failed"}), 500

        return jsonify({
            "success": True,
            "message": "Details uploaded and status updated successfully!",
            "photo": photo_url,
            "geotagPhoto": geotag_url,
            "eventDoc": doc_url
        })

    except Exception as e:
        print("ERROR in /upload_details:", str(e))
        return jsonify({"success": False, "error": str(e)}), 500


# ✅ Serve uploaded files
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/total_completed_bookings", methods=["GET"])
def get_total_completed_bookings():
    try:
        total_completed_bookings = {}

        for hall_name, collection in hall_collections.items():
            bookings = list(collection.find({"status": "Total Completed"}))

            for booking in bookings:
                booking["_id"] = str(booking["_id"])

                # Ensure all media paths (2 images + 1 PDF) are correctly formatted
                if "imagePath1" in booking and booking["imagePath1"]:
                    booking["imagePath1"] = f"http://all-6.onrender.com/uploads/{booking['imagePath1']}"
                else:
                    booking["imagePath1"] = None

                if "imagePath2" in booking and booking["imagePath2"]:
                    booking["imagePath2"] = f"http://all-6.onrender.com/uploads/{booking['imagePath2']}"
                else:
                    booking["imagePath2"] = None

                if "pdfPath" in booking and booking["pdfPath"]:
                    booking["pdfPath"] = f"http://all-6.onrender.com/uploads/{booking['pdfPath']}"
                else:
                    booking["pdfPath"] = None

            total_completed_bookings[hall_name] = bookings

        return jsonify(total_completed_bookings), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


    
@app.route("/bookings", methods=["GET"])
def get_all_bookings():
    try:
        all_bookings = {}
        for hall, collection in hall_collections.items():
            bookings = list(collection.find({}, {"_id": 1, "CoordinatorName": 1, "EventName": 1, "Date": 1, "TimeFrom": 1, "TimeTo": 1, "status": 1}))
            for booking in bookings:
                booking["_id"] = str(booking["_id"]) 
            all_bookings[hall] = bookings

        return jsonify(all_bookings), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
@app.route("/update_booking_status", methods=["POST"])
def update_booking_status():
    try:
        data = request.json
        selected_hall = data.get("SelectedSeminarHall")
        coordinator_email = data.get("CoordinatorEmail")
        status = data.get("status")

        if status not in ["approved", "declined"]:
            return jsonify({"error": "Invalid status update"}), 400

        booking = hall_collections[selected_hall].find_one(
            {"CoordinatorEmail": coordinator_email, "status": "pending"}
        )

        if not booking:
            return jsonify({"error": "Booking not found or already processed"}), 404

        hall_collections[selected_hall].update_one(
            {"CoordinatorEmail": coordinator_email, "status": "pending"},
            {"$set": {"status": status}}
        )

        subject = f"Seminar Hall Booking {status.capitalize()} - {selected_hall}"
        email_body = f"""
        <h2>Your seminar hall booking has been {status}.</h2>
        <p><strong>Coordinator Name:</strong> {booking["CoordinatorName"]}</p>
        <p><strong>Department:</strong> {booking["Department"]}</p>
        <p><strong>Event Name:</strong> {booking["EventName"]}</p>
        <p><strong>Total Participants:</strong> {booking["TotalParticipants"]}</p>
        <p><strong>Seminar Hall:</strong> {selected_hall}</p>
        <p><strong>Date:</strong> {booking["Date"]}</p>
        <p><strong>Time:</strong> {booking["TimeFrom"]} - {booking["TimeTo"]}</p>
        <p><strong>Coordinator Email:</strong> {booking["CoordinatorEmail"]}</p>
        <p><strong>Coordinator Phone:</strong> {booking["CoordinatorPhone"]}</p>
        <p><strong>Organized By:</strong> {booking["OrganizedBy"]}</p>
        """

        if status == "approved":
            recipients = [coordinator_email, "yuthikam2005@gmail.com", "sahanamagesh72@gmail.com", "darav4852@gmail.com"]
        else: 
            recipients = [coordinator_email]

        for recipient in recipients:
            send_email(recipient, subject, email_body)

        return jsonify({"success": True, "message": f"Booking {status} and email sent!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/pending_bookings", methods=["GET"])
def get_pending_bookings():
    try:
        pending_bookings = {}
        for hall_name, collection in hall_collections.items():
            pending_bookings[hall_name] = list(collection.find({"status": "pending"}, {"_id": 0}))

        return jsonify(pending_bookings)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/bookings/<hall_name>", methods=["GET"])
def get_hall_bookings(hall_name):
    try:
        if hall_name not in hall_collections:
            return jsonify({"error": "Invalid seminar hall"}), 400

        bookings = list(hall_collections[hall_name].find({}, {"_id": 1, "CoordinatorName": 1, "EventName": 1, "Date": 1, "TimeFrom": 1, "TimeTo": 1, "status": 1}))
        for booking in bookings:
            booking["_id"] = str(booking["_id"])

        return jsonify(bookings), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


pending_bookings = {}

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "ajaiks2005@gmail.com" 
EMAIL_PASSWORD = "pvxp uuvb fsap xqbb"  

def send_email(to_email, subject, body):
    try:
        msg = EmailMessage()
        msg.set_content(body, subtype="html")  
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = to_email

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Error sending email: {e}")

@app.route("/check_availability", methods=["POST"])
def check_availability():
    try:
        data = request.json
        selected_hall = data.get("SelectedSeminarHall")
        date = data.get("Date")
        time_from = data.get("TimeFrom")
        time_to = data.get("TimeTo")

        if not selected_hall or not date or not time_from or not time_to:
            return jsonify({"available": False, "message": "Invalid input"}), 400

        existing_booking = hall_collections[selected_hall].find_one({
            "Date": date,
            "$or": [
                {"TimeFrom": {"$lte": time_to}, "TimeTo": {"$gte": time_from}}
            ],
            "status": {"$in": ["pending", "approved"]}
        })

        if existing_booking:
            return jsonify({"available": False, "message": "Slot already booked!"}), 200

        return jsonify({"available": True}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/book", methods=["POST"])
def book_seminar():
    try:
        data = request.json
        selected_hall = data.get("SelectedSeminarHall")

        if not selected_hall or selected_hall not in hall_collections:
            return jsonify({"error": "Invalid seminar hall selection"}), 400
        
        data["status"] = "pending"
        booking_id = hall_collections[selected_hall].insert_one(data).inserted_id

        login_link = "https://seminar-hall-b828d.web.app/"

        products_html = ""
        if "products" in data and isinstance(data["products"], list):
            products_html += "<ul>"
            for product in data["products"]:
                product_name = product.get("name", "Unknown Product")
                product_quantity = product.get("quantity", 0)
                products_html += f"<li>{product_name} - {product_quantity}</li>"
            products_html += "</ul>"
        else:
            products_html = "<p>No products selected</p>"

        admin_email_body = f'''
        <h2>New Seminar Hall Booking Request</h2>
        <p><strong>Coordinator Name:</strong> {data["CoordinatorName"]}</p>
        <p><strong>Department:</strong> {data["Department"]}</p>
        <p><strong>Event Name:</strong> {data["EventName"]}</p>
        <p><strong>Total Participants:</strong> {data["TotalParticipants"]}</p>
        <p><strong>Seminar Hall:</strong> {selected_hall}</p>
        <p><strong>Date:</strong> {data["Date"]}</p>
        <p><strong>Time:</strong> {data["TimeFrom"]} - {data["TimeTo"]}</p>
        <p><strong>Coordinator Email:</strong> {data["CoordinatorEmail"]}</p>
        <p><strong>Coordinator Phone:</strong> {data["CoordinatorPhone"]}</p>
        <p><strong>Organized By:</strong> {data["OrganizedBy"]}</p>
        <p><strong>Products Requested:</strong></p>
        {products_html}
        <p>Please log in, approve, or decline:</p>
        <a href="{login_link}" style="padding:10px; background-color:blue; color:white; text-decoration:none; display:block; margin-bottom:10px;">Login</a>
        '''

        send_email("ajaisha2021@gmail.com", "Seminar Hall Booking Approval", admin_email_body)

        return jsonify({
            "success": True,
            "message": f"Booking request for {selected_hall} stored and approval email sent!",
            "booking_id": str(booking_id)
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/image", methods=["POST"])
def image():
    try:
        image = request.files["image"]
        image.save("image.jpg")
        return "Image uploaded successfully!", 200
    except Exception as e:
        return str(e), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Default to 5000 if no environment variable
    app.run(debug=True, host="0.0.0.0", port=port)


