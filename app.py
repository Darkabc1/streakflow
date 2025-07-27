from flask import Flask, render_template_string, request, jsonify
from pymongo import MongoClient
from datetime import datetime
import os

app = Flask(__name__)

# Connect to MongoDB Atlas (replace with your real connection string)
MONGO_URI = os.getenv("MONGO_URI", "your_mongodb_uri_here")
client = MongoClient(MONGO_URI)
db = client["streakflow"]
collection = db["habits"]

# Embedded HTML + JS (modern, mobile portrait layout)
UI_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>StreakFlow Tracker</title>
  <style>
    body {
      margin: 0;
      font-family: 'Segoe UI', sans-serif;
      background: #0f0f0f;
      color: #fff;
      padding: 20px;
    }
    h1 {
      font-size: 2rem;
      text-align: center;
      margin-top: 1rem;
    }
    .streak-box {
      background: #1a1a1a;
      padding: 15px;
      border-radius: 15px;
      margin: 20px 0;
      text-align: center;
    }
    .btn {
      background: #00e676;
      color: black;
      border: none;
      padding: 12px 20px;
      border-radius: 10px;
      font-size: 1rem;
      cursor: pointer;
    }
    .btn:hover {
      background: #00c853;
    }
    canvas {
      background: #1f1f1f;
      border-radius: 10px;
      width: 100%;
      height: 200px;
      margin-top: 30px;
    }
  </style>
</head>
<body>
  <h1>StreakFlow</h1>
  <div class="streak-box">
    <p id="streakCount">Streak: 0 days</p>
    <button class="btn" onclick="recordEntry()">Add Entry</button>
  </div>

  <canvas id="progressChart"></canvas>
  <canvas id="moodChart"></canvas>

  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script>
    async function recordEntry() {
      const response = await fetch('/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ mood: Math.floor(Math.random() * 5) + 1 })
      });
      const data = await response.json();
      document.getElementById('streakCount').innerText = "Streak: " + data.streak + " days";
      drawCharts(data.history);
    }

    function drawCharts(history) {
      const labels = history.map(h => new Date(h.date).toLocaleDateString());
      const moods = history.map(h => h.mood || 3);

      const ctx1 = document.getElementById('progressChart').getContext('2d');
      const ctx2 = document.getElementById('moodChart').getContext('2d');

      new Chart(ctx1, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [{
            label: 'Daily Entries',
            data: history.map((_, i) => i + 1),
            borderColor: '#00e676',
            backgroundColor: 'rgba(0, 230, 118, 0.2)',
            fill: true,
          }]
        }
      });

      new Chart(ctx2, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            label: 'Mood Level',
            data: moods,
            backgroundColor: '#2979ff'
          }]
        }
      });
    }

    // Load data on startup
    window.onload = async () => {
      const res = await fetch('/data');
      const data = await res.json();
      document.getElementById('streakCount').innerText = "Streak: " + data.streak + " days";
      drawCharts(data.history);
    };
  </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(UI_HTML)

@app.route('/add', methods=['POST'])
def add_entry():
    data = request.get_json()
    entry = {
        "date": datetime.utcnow(),
        "mood": data.get("mood", 3)
    }
    collection.insert_one(entry)

    history = list(collection.find().sort("date", 1))
    streak = calculate_streak(history)
    return jsonify({"streak": streak, "history": serialize(history)})

@app.route('/data')
def get_data():
    history = list(collection.find().sort("date", 1))
    streak = calculate_streak(history)
    return jsonify({"streak": streak, "history": serialize(history)})

def serialize(entries):
    return [{"date": e["date"].isoformat(), "mood": e.get("mood", 3)} for e in entries]

def calculate_streak(entries):
    if not entries:
        return 0
    entries.sort(key=lambda x: x["date"])
    streak = 1
    for i in range(len(entries) - 1, 0, -1):
        delta = (entries[i]["date"] - entries[i-1]["date"]).days
        if delta == 1:
            streak += 1
        else:
            break
    return streak

if __name__ == '__main__':
    app.run(debug=True)
