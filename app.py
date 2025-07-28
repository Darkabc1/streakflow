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
  <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
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
    h2 { color: #00ffe1; margin-bottom: 10px; }
    h3 { color: #ffffff; margin-bottom: 10px; }
    .card {
      background: #1e1e1e;
      border-radius: 15px;
      padding: 20px;
      margin: 10px;
      width: 90%;
      max-width: 400px;
      box-shadow: 0 0 10px #00ffe1;
    }
    label {
      color: #ffffff;
      font-weight: bold;
    }
    input, select {
      width: 100%;
      margin-top: 5px;
      margin-bottom: 10px;
      font-size: 16px;
      padding: 8px;
      border: 1px solid #333;
      border-radius: 5px;
      background-color: #2a2a2a;
      color: #ffffff;
      box-sizing: border-box;
    }
    button {
      width: 100%;
      background-color: #00ffe1;
      border: none;
      padding: 12px;
      color: #000;
      font-weight: bold;
      cursor: pointer;
      border-radius: 8px;
      font-size: 16px;
      margin-top: 10px;
    }
    button:hover {
      background-color: #00d4b8;
    }
    .popup {
      position: fixed;
      top: 20%;
      left: 50%;
      transform: translate(-50%, -50%);
      background-color: #00ffe1;
      color: #000;
      padding: 20px;
      border-radius: 10px;
      z-index: 9999;
      display: none;
      font-weight: bold;
    }
    .chart-container {
      width: 100%;
      max-width: 400px;
      margin: 20px 0;
      background: #1e1e1e;
      border-radius: 10px;
      padding: 15px;
    }
    canvas {
      width: 100% !important;
      height: 200px !important;
    }
  </style>
</head>
<body>
    <h2>🗓️ Daily Mood Tracker</h2>
    
    <div class="card">
      <form id="entryForm">
        <label for="date">Date:</label>
        <input type="date" id="date" required />
        
        <label for="mood">Mood:</label>
        <select id="mood" required>
          <option value="">Select your mood</option>
          <option value="happy">😊 Happy</option>
          <option value="neutral">😐 Neutral</option>
          <option value="sad">😞 Sad</option>
        </select>
        
        <button type="submit">Submit Entry</button>
      </form>
    </div>
    
    <div class="popup" id="popup">✔️ Entry Submitted Successfully!</div>

    <h3>Current Streak: <span id="streakCount">0</span> days</h3>
    
    <div class="chart-container">
      <h4 style="color: #00ffe1; text-align: center; margin-top: 0;">Progress Chart</h4>
      <canvas id="progressChart"></canvas>
    </div>
    
    <div class="chart-container">
      <h4 style="color: #00ffe1; text-align: center; margin-top: 0;">Mood Distribution</h4>
      <canvas id="moodChart"></canvas>
    </div>

    <script>
      // Set today's date as default
      document.getElementById('date').valueAsDate = new Date();
      
      let progressChart = null;
      let moodChart = null;

      async function updateUI() {
        try {
          const response = await fetch('/data');
          const data = await response.json();
          
          document.getElementById("streakCount").textContent = data.streak;

          const dates = data.logs.map((e) => e.date);
          const moods = data.logs.map((e) => e.mood);

          const moodCounts = { happy: 0, neutral: 0, sad: 0 };
          moods.forEach((m) => moodCounts[m]++);

          // Destroy existing charts
          if (progressChart) {
            progressChart.destroy();
          }
          if (moodChart) {
            moodChart.destroy();
          }

          // Create progress chart
          const progressCtx = document.getElementById("progressChart").getContext('2d');
          progressChart = new Chart(progressCtx, {
            type: "line",
            data: {
              labels: dates.slice(-7), // Show last 7 days
              datasets: [{
                label: "Daily Entries",
                data: dates.slice(-7).map((_, i) => i + 1),
                borderColor: "#00ffe1",
                backgroundColor: "rgba(0,255,225,0.2)",
                tension: 0.4,
                fill: true
              }]
            },
            options: { 
              responsive: true,
              maintainAspectRatio: false,
              plugins: { 
                legend: { 
                  display: true,
                  labels: {
                    color: '#ffffff'
                  }
                } 
              },
              scales: {
                x: {
                  ticks: { color: '#ffffff' },
                  grid: { color: '#333' }
                },
                y: {
                  ticks: { color: '#ffffff' },
                  grid: { color: '#333' }
                }
              }
            }
          });

          // Create mood chart
          const moodCtx = document.getElementById("moodChart").getContext('2d');
          moodChart = new Chart(moodCtx, {
            type: "doughnut",
            data: {
              labels: ["😊 Happy", "😐 Neutral", "😞 Sad"],
              datasets: [{
                label: "Mood Count",
                data: [moodCounts.happy, moodCounts.neutral, moodCounts.sad],
                backgroundColor: ["#00ff88", "#ffdd00", "#ff4444"]
              }]
            },
            options: { 
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: {
                  labels: {
                    color: '#ffffff'
                  }
                }
              }
            }
          });
        } catch (error) {
          console.error('Error updating UI:', error);
        }
      }

      document.getElementById("entryForm").addEventListener("submit", async function (e) {
        e.preventDefault();
        
        const date = document.getElementById("date").value;
        const mood = document.getElementById("mood").value;
        
        if (!date || !mood) {
          alert('Please fill in all fields');
          return;
        }

        try {
          const response = await fetch('/submit', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ date, mood })
          });

          const result = await response.json();
          
          // Show success popup
          document.getElementById("popup").style.display = "block";
          setTimeout(() => {
            document.getElementById("popup").style.display = "none";
          }, 2000);
          
          // Reset form
          document.getElementById("mood").value = "";
          
          // Update charts
          updateUI();
          
        } catch (error) {
          console.error('Error submitting entry:', error);
          alert('Error submitting entry. Please try again.');
        }
      });

      // Initialize UI on page load
      updateUI();
    </script>
  </body>
</html>
"""

def calculate_streak(entries):
    if not entries:
        return 0
    
    # Sort entries by date (newest first)
    entries.sort(key=lambda x: x['date'], reverse=True)
    
    if len(entries) == 1:
        return 1
    
    streak = 1
    current_date = entries[0]['date']
    
    for i in range(1, len(entries)):
        previous_date = entries[i]['date']
        diff = (current_date - previous_date).days
        
        if diff == 1:
            streak += 1
            current_date = previous_date
        elif diff == 0:
            # Same date, skip
            continue
        else:
            # Gap in streak
            break
    
    return streak

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/submit", methods=["POST"])
def submit_entry():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        mood = data.get("mood")
        date_str = data.get("date")

        if not mood or not date_str:
            return jsonify({"error": "Missing mood or date"}), 400

        # Convert date string to datetime
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        # Check for duplicate entry for the same date
        existing_entry = collection.find_one({"date": date_obj})
        if existing_entry:
            return jsonify({"message": "Entry already exists for this date"}), 200

        # Insert new entry
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
                'message': f'{mongodb_msg}. Google Sheets: {sheets_result.get("message", "Not configured")}'
            }), 201

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/data")
def data():
    try:
        entries = list(collection.find({}, {"_id": 0}).sort("date", 1))
        
        # Convert datetime objects to strings for JSON serialization
        for entry in entries:
            entry["date"] = entry["date"].strftime("%Y-%m-%d")
        
        # Calculate streak using datetime objects
        datetime_entries = [
            {"date": datetime.strptime(e["date"], "%Y-%m-%d")} for e in entries
        ]
        streak = calculate_streak(datetime_entries)
        
        return jsonify({"logs": entries, "streak": streak})
    
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"})

if __name__ == "__main__":
    app.run(debug=True)
