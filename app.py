from flask import Flask, request, jsonify, render_template_string
from pymongo import MongoClient
from datetime import datetime
import os

app = Flask(__name__)

# Connect to MongoDB (replace with your own URI or use environment variable)
MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["streakflow"]
collection = db["entries"]

HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>StreakFlow - Habit Tracker</title>
  <style>
    body {
      font-family: "Segoe UI", sans-serif;
      margin: 0;
      padding: 20px;
      background: #0e0e10;
      color: white;
    }
    h1 {
      text-align: center;
      color: #00ffd5;
    }
    .counter {
      text-align: center;
      font-size: 2.5em;
      margin: 30px 0;
    }
    form {
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    input[type="text"],
    select {
      padding: 10px;
      margin: 10px;
      border-radius: 8px;
      border: none;
      width: 80%;
    }
    button {
      background: #00ffd5;
      border: none;
      color: black;
      padding: 10px 20px;
      font-weight: bold;
      border-radius: 8px;
      cursor: pointer;
      margin-top: 10px;
    }
    .success-popup {
      display: none;
      position: fixed;
      top: 30%;
      left: 50%;
      transform: translate(-50%, -50%);
      background-color: #1f1f22;
      color: #00ffd5;
      padding: 20px 30px;
      border-radius: 12px;
      box-shadow: 0 0 20px #00ffd5;
      font-size: 1.2em;
    }
    .charts {
      margin-top: 40px;
      padding: 10px;
    }
    canvas {
      width: 100%;
      max-height: 250px;
      margin-top: 20px;
    }
  </style>
</head>
<body>
  <h1>StreakFlow</h1>
  <div class="counter">Current Streak: <span id="streak">0</span></div>
  <form id="entryForm">
    <input type="text" id="note" placeholder="What triggered it?" required />
    <select id="mood">
      <option value="😌">Calm</option>
      <option value="😐">Neutral</option>
      <option value="😖">Stressed</option>
      <option value="🔥">Urge</option>
    </select>
    <button type="submit">Log Entry</button>
  </form>
  <div class="success-popup" id="successPopup">✔️ Entry Saved!</div>

  <div class="charts">
    <canvas id="progressChart"></canvas>
    <canvas id="moodChart"></canvas>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script>
    const form = document.getElementById("entryForm");
    const popup = document.getElementById("successPopup");
    const streakDisplay = document.getElementById("streak");

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const note = document.getElementById("note").value;
      const mood = document.getElementById("mood").value;

      const res = await fetch("/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note, mood })
      });
      const data = await res.json();
      if (data.success) {
        popup.style.display = "block";
        setTimeout(() => popup.style.display = "none", 2000);
        document.getElementById("note").value = "";
        updateCounter();
      }
    });

    async function updateCounter() {
      const res = await fetch("/streak");
      const data = await res.json();
      streakDisplay.textContent = data.count;
    }

    updateCounter();
  </script>
</body>
</html>
'''

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json()
    note = data.get("note")
    mood = data.get("mood")
    timestamp = datetime.now()
    collection.insert_one({"note": note, "mood": mood, "timestamp": timestamp})
    return jsonify(success=True)

@app.route("/streak")
def get_streak():
    count = collection.count_documents({})
    return jsonify(count=count)

if __name__ == "__main__":
    app.run(debug=True)
