from flask import Flask, request, jsonify, render_template_string
from pymongo import MongoClient
from datetime import datetime
import os

app = Flask(__name__)

# Replace with your actual MongoDB URI
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://<username>:<password>@<cluster>.mongodb.net/<dbname>?retryWrites=true&w=majority")
client = MongoClient(MONGO_URI)
db = client["streakflow"]
collection = db["entries"]

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
  <h1>StreakFlow</h1>
  <div class="card">
    <form id="entryForm">
      <label>Date:</label>
      <input type="date" id="date" required><br>
      <label>Mood:</label>
      <select id="mood">
        <option value="happy">😊 Happy</option>
        <option value="neutral">😐 Neutral</option>
        <option value="sad">😞 Sad</option>
      </select><br>
      <button type="submit">Log Entry</button>
    </form>
  </div>

  <div class="card">
    <h2>Current Streak: <span id="streakCount">0</span> days</h2>
  </div>

  <div class="card">
    <canvas id="progressChart"></canvas>
  </div>

  <div class="card">
    <canvas id="moodChart"></canvas>
  </div>

  <div class="popup" id="popup">✅ Entry logged successfully!</div>

  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script>
    async function updateUI() {
      const res = await fetch("/data");
      const data = await res.json();
      document.getElementById("streakCount").textContent = data.streak;

      const dates = data.logs.map(e => e.date);
      const moods = data.logs.map(e => e.mood);

      new Chart(document.getElementById("progressChart"), {
        type: 'line',
        data: {
          labels: dates,
          datasets: [{
            label: 'Activity Log',
            data: dates.map((_, i) => i + 1),
            borderColor: '#00ffe1',
            backgroundColor: 'rgba(0,255,225,0.2)',
            tension: 0.4
          }]
        },
        options: { responsive: true, plugins: { legend: { display: false } } }
      });

      const moodCounts = { happy: 0, neutral: 0, sad: 0 };
      moods.forEach(m => moodCounts[m]++);
      new Chart(document.getElementById("moodChart"), {
        type: 'bar',
        data: {
          labels: ["😊", "😐", "😞"],
          datasets: [{
            label: "Mood Count",
            data: [moodCounts.happy, moodCounts.neutral, moodCounts.sad],
            backgroundColor: ['#0f0', '#ff0', '#f00']
          }]
        },
        options: { responsive: true }
      });
    }

    document.getElementById("entryForm").addEventListener("submit", async function(e) {
      e.preventDefault();
      const date = document.getElementById("date").value;
      const mood = document.getElementById("mood").value;

      const res = await fetch("/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date, mood })
      });

      if (res.ok) {
        document.getElementById("popup").style.display = "block";
        setTimeout(() => {
          document.getElementById("popup").style.display = "none";
        }, 2000);
        updateUI();
      }
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
    return jsonify({"message": "Entry submitted successfully!"})

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
