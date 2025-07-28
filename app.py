from flask import Flask, request, jsonify, render_template_string
from pymongo import MongoClient
from datetime import datetime
import os
import requests


app = Flask(__name__)

# Replace with your actual MongoDB URI
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://<username>:<password>@<cluster>.mongodb.net/<dbname>?retryWrites=true&w=majority")

if not MONGO_URI:
    raise ValueError("MONGO_URI is not set. Please set it as an environment variable.")

GOOGLE_SCRIPT_URL = os.getenv("GOOGLE_SCRIPT_URL")
if not GOOGLE_SCRIPT_URL:
    print("Warning: GOOGLE_SCRIPT_URL is not set. Data will only be saved to MongoDB.")


client = MongoClient(MONGO_URI)
db = client["streakflow"]
collection = db["entries"]

def send_to_google_sheets(data):
    if not GOOGLE_SCRIPT_URL:
        return {"status": "skipped", "message": "Google Script URL not configured"}
    
    try:
        response = requests.post(
            GOOGLE_SCRIPT_URL,
            json=data,
            timeout=10  # Set a timeout to prevent hanging
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "status": "error",
                "message": f"Google Sheets API error: HTTP {response.status_code}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to send data to Google Sheets: {str(e)}"
        }

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>StreakFlow</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
  <style>
    body {
      margin: 0;
      font-family: 'Segoe UI', sans-serif;
      background-color: #0e0e0e;
      color: #ffffff;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 20px;
    }
    h1 { color: #00ffe1; margin-bottom: 10px; }
    .card {
      background: #1e1e1e;
      border-radius: 15px;
      padding: 20px;
      margin: 10px;
      width: 90%;
      max-width: 400px;
      box-shadow: 0 0 10px #00ffe1;
    }
    label, input, select, button {
      width: 100%;
      margin-top: 10px;
      font-size: 16px;
    }
    button {
      background-color: #00ffe1;
      border: none;
      padding: 10px;
      color: #000;
      font-weight: bold;
      cursor: pointer;
      border-radius: 8px;
    }
    .popup {
      position: fixed;
      top: 10%;
      left: 50%;
      transform: translate(-50%, -50%);
      background-color: #00ffe1;
      color: #000;
      padding: 20px;
      border-radius: 10px;
      z-index: 9999;
      display: none;
    }
    canvas {
      width: 100% !important;
      max-width: 400px;
    }
  </style>
</head>
<body>
    <h2>🗓️ Daily Mood Tracker</h2>
    <form id="entryForm">
      <label>Date:</label><br />
      <input type="date" id="date" required /><br /><br />
      <label>Mood:</label><br />
      <select id="mood" required>
        <option value="happy">😊 Happy</option>
        <option value="neutral">😐 Neutral</option>
        <option value="sad">😞 Sad</option>
      </select><br /><br />
      <button type="submit">Submit</button>
    </form>
    <div class="popup" id="popup">✔️ Entry Submitted</div>

    <h3>Current Streak: <span id="streakCount">0</span> days</h3>
    <canvas id="progressChart" width="300" height="200"></canvas>
    <canvas id="moodChart" width="300" height="200"></canvas>

    <script>
      async function updateUI() {
        google.script.run.withSuccessHandler(function (data) {
          document.getElementById("streakCount").textContent = data.streak;

          const dates = data.logs.map((e) => e.date);
          const moods = data.logs.map((e) => e.mood);

          const moodCounts = { happy: 0, neutral: 0, sad: 0 };
          moods.forEach((m) => moodCounts[m]++);

          new Chart(document.getElementById("progressChart"), {
            type: "line",
            data: {
              labels: dates,
              datasets: [{
                label: "Progress",
                data: dates.map((_, i) => i + 1),
                borderColor: "#00ffe1",
                backgroundColor: "rgba(0,255,225,0.2)",
                tension: 0.4
              }]
            },
            options: { responsive: true, plugins: { legend: { display: false } } }
          });

          new Chart(document.getElementById("moodChart"), {
            type: "bar",
            data: {
              labels: ["😊", "😐", "😞"],
              datasets: [{
                label: "Mood Count",
                data: [moodCounts.happy, moodCounts.neutral, moodCounts.sad],
                backgroundColor: ["#0f0", "#ff0", "#f00"]
              }]
            },
            options: { responsive: true }
          });
        }).getData();
      }

      document.getElementById("entryForm").addEventListener("submit", function (e) {
        e.preventDefault();
        const date = document.getElementById("date").value;
        const mood = document.getElementById("mood").value;
        google.script.run.withSuccessHandler(() => {
          document.getElementById("popup").style.display = "block";
          setTimeout(() => {
            document.getElementById("popup").style.display = "none";
          }, 2000);
          updateUI();
        }).submitData({ date, mood });
      });

      updateUI();
    </script>
  </body>
</html>
"""

def calculate_streak(entries):
    if not entries:
        return 0
    entries.sort(key=lambda x: x['date'], reverse=True)
    streak = 1
    for i in range(1, len(entries)):
        diff = (entries[i-1]['date'] - entries[i]['date']).days
        if diff == 1:
            streak += 1
        elif diff == 0:
            continue
        else:
            break
    return streak

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/submit", methods=["POST"])
def submit_entry():
    data = request.get_json()
    mood = data.get("mood")
    date_str = data.get("date")

    # Convert date string to datetime
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400

    # Avoid duplicate entry for the same date
    if collection.find_one({"date": date_obj}):
        return jsonify({"message": "Already submitted for today"}), 200

    collection.insert_one({"date": date_obj, "mood": mood})
    mongodb_msg = "Entry saved to MongoDB"

    # Optional: Send to Google Sheets
    sheets_data = {
        "type": "mydata",
        "date": date_str,
        "mood": mood
    }
    sheets_result = send_to_google_sheets(sheets_data)

    if sheets_result.get("status") == "success":
        d2_value = sheets_result.get("d2Value", "N/A")
        return jsonify({
            'message': f'{mongodb_msg} and Google Sheets. D2 Value: {d2_value}'
        }), 201
    else:
        return jsonify({
            'message': f'{mongodb_msg}. Google Sheets error: {sheets_result.get("message", "Unknown error")}'
        }), 201



@app.route("/data")
def data():
    entries = list(collection.find({}, {"_id": 0}))
    for entry in entries:
        entry["date"] = entry["date"].strftime("%Y-%m-%d")
    streak = calculate_streak([
        {"date": datetime.strptime(e["date"], "%Y-%m-%d")} for e in entries
    ])
    return jsonify({"logs": entries, "streak": streak})

if __name__ == "__main__":
    app.run(debug=True)
