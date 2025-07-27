from flask import Flask, render_template_string, request, jsonify
from pymongo import MongoClient
from datetime import datetime
import os

app = Flask(__name__)

# MongoDB connection (replace with your MongoDB Atlas URI or use .env)
MONGO_URI = os.getenv("MONGO_URI", "your_mongodb_uri_here")
client = MongoClient(MONGO_URI)
db = client["streakflow"]
collection = db["entries"]

# ---------------- HTML Template ----------------
TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>StreakFlow</title>
  <style>
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      margin: 0;
      padding: 1rem;
      background-color: #0f0f0f;
      color: #f5f5f5;
    }

    h1, h2 {
      text-align: center;
    }

    .card {
      background-color: #1a1a1a;
      padding: 1rem;
      border-radius: 12px;
      margin-bottom: 1rem;
      box-shadow: 0 0 8px rgba(255, 255, 255, 0.05);
    }

    .stat {
      display: flex;
      justify-content: space-between;
      font-size: 1.2rem;
    }

    .btn {
      display: inline-block;
      width: 48%;
      padding: 1rem;
      margin-top: 0.5rem;
      font-size: 1rem;
      border: none;
      border-radius: 8px;
      cursor: pointer;
    }

    .btn-clean {
      background-color: #28a745;
      color: white;
    }

    .btn-relapsed {
      background-color: #e07b39;
      color: white;
    }

    select, textarea {
      width: 100%;
      padding: 0.6rem;
      border-radius: 6px;
      border: none;
      margin-top: 0.5rem;
      background: #2c2c2c;
      color: white;
    }

    canvas {
      width: 100% !important;
      max-height: 200px;
    }
  </style>
</head>
<body>
  <h1>StreakFlow</h1>

  <div class="card stat">
    <div>
      <strong>Current Streak:</strong>
      <span id="currentStreak">0</span>
    </div>
    <div>
      <strong>Longest Streak:</strong>
      <span id="longestStreak">0</span>
    </div>
  </div>

  <div class="card">
    <h2>Log Entry</h2>
    <button class="btn btn-clean" onclick="logEntry('clean')">Stayed Clean</button>
    <button class="btn btn-relapsed" onclick="logEntry('relapse')">Relapsed</button>

    <label>Trigger</label>
    <select id="trigger">
      <option>Boredom</option>
      <option>Stress</option>
      <option>Loneliness</option>
      <option>Habit</option>
    </select>

    <label>Mood</label>
    <select id="mood">
      <option>Positive</option>
      <option>Neutral</option>
      <option>Negative</option>
    </select>

    <label>Notes</label>
    <textarea id="notes" rows="3"></textarea>
  </div>

  <div class="card">
    <h2>Progress Chart</h2>
    <canvas id="streakChart"></canvas>
  </div>

  <div class="card">
    <h2>Mood Chart</h2>
    <canvas id="moodChart"></canvas>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script>
    let history = [];

    async function fetchData() {
      const res = await fetch('/data');
      const data = await res.json();
      history = data.history;
      document.getElementById('currentStreak').innerText = data.current_streak;
      document.getElementById('longestStreak').innerText = data.longest_streak;
      updateCharts();
    }

    async function logEntry(type) {
      const entry = {
        type: type,
        trigger: document.getElementById('trigger').value,
        mood: document.getElementById('mood').value,
        notes: document.getElementById('notes').value
      };
      await fetch('/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(entry)
      });
      fetchData();
    }

    function updateCharts() {
      const labels = history.slice(-7).map(e => new Date(e.date).toLocaleDateString());
      const streakData = history.slice(-7).map((e, i) => i + 1);
      const moodData = history.slice(-7).map(e => e.mood === 'Positive' ? 2 : e.mood === 'Neutral' ? 1 : 0);

      streakChart.data.labels = labels;
      streakChart.data.datasets[0].data = streakData;
      streakChart.update();

      moodChart.data.labels = labels;
      moodChart.data.datasets[0].data = moodData;
      moodChart.update();
    }

    const streakChart = new Chart(document.getElementById('streakChart'), {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Streak Days',
          backgroundColor: '#007bff',
          borderColor: '#007bff',
          data: [],
          fill: false
        }]
      },
      options: { responsive: true, scales: { y: { beginAtZero: true } } }
    });

    const moodChart = new Chart(document.getElementById('moodChart'), {
      type: 'bar',
      data: {
        labels: [],
        datasets: [{
          label: 'Mood Level',
          backgroundColor: '#17a2b8',
          data: []
        }]
      },
      options: { responsive: true, scales: { y: { beginAtZero: true, max: 2 } } }
    });

    fetchData();
  </script>
</body>
</html>
"""

# ---------------- API Routes ----------------

@app.route('/')
def index():
    return render_template_string(TEMPLATE)

@app.route('/add', methods=['POST'])
def add_entry():
    data = request.get_json()
    entry = {
        "date": datetime.utcnow(),
        "type": data.get("type"),
        "trigger": data.get("trigger"),
        "mood": data.get("mood"),
        "notes": data.get("notes")
    }
    collection.insert_one(entry)
    return jsonify({"status": "ok"})

@app.route('/data')
def get_data():
    history = list(collection.find().sort("date", 1))
    current_streak, longest_streak = calculate_streaks(history)
    return jsonify({
        "history": [serialize(e) for e in history],
        "current_streak": current_streak,
        "longest_streak": longest_streak
    })

def serialize(entry):
    return {
        "date": entry["date"].isoformat(),
        "type": entry.get("type"),
        "trigger": entry.get("trigger"),
        "mood": entry.get("mood"),
        "notes": entry.get("notes")
    }

def calculate_streaks(entries):
    streak = 0
    max_streak = 0
    last_date = None

    for entry in sorted(entries, key=lambda x: x["date"]):
        if entry["type"] == "clean":
            if last_date:
                delta = (entry["date"].date() - last_date).days
                if delta == 1:
                    streak += 1
                elif delta == 0:
                    continue
                else:
                    streak = 1
            else:
                streak = 1
            max_streak = max(max_streak, streak)
            last_date = entry["date"].date()
        elif entry["type"] == "relapse":
            streak = 0
            last_date = None

    return streak, max_streak

# ---------------- Run App ----------------

if __name__ == '__main__':
    app.run(debug=True)
