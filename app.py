from flask import Flask, request, jsonify, render_template_string
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
import requests
import json

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
            timeout=10
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

def fetch_google_sheets_data():
    """Fetch data from Google Sheets for calculations"""
    if not GOOGLE_SCRIPT_URL:
        return []
    
    try:
        # Add a query parameter to indicate we want to fetch data
        fetch_url = f"{GOOGLE_SCRIPT_URL}?action=fetch"
        response = requests.get(fetch_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('data', [])
        else:
            print(f"Failed to fetch Google Sheets data: HTTP {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching Google Sheets data: {str(e)}")
        return []

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>StreakFlow - Modern Mood Tracker</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.min.js"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%);
      color: #ffffff;
      min-height: 100vh;
      padding: 20px;
      overflow-x: hidden;
    }

    .container {
      max-width: 1200px;
      margin: 0 auto;
      display: grid;
      gap: 24px;
      grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
    }

    .header {
      grid-column: 1 / -1;
      text-align: center;
      margin-bottom: 20px;
    }

    .header h1 {
      font-size: 3rem;
      font-weight: 800;
      background: linear-gradient(135deg, #00d4ff, #00ff88, #ff6b6b);
      background-clip: text;
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 10px;
      text-shadow: 0 0 30px rgba(0, 255, 136, 0.3);
    }

    .header p {
      color: #a0a0a0;
      font-size: 1.1rem;
      font-weight: 300;
    }

    .glass-card {
      background: rgba(255, 255, 255, 0.05);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 24px;
      padding: 32px;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
      transition: all 0.3s ease;
      position: relative;
      overflow: hidden;
    }

    .glass-card::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 1px;
      background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
    }

    .glass-card:hover {
      transform: translateY(-5px);
      box-shadow: 0 30px 60px rgba(0, 255, 136, 0.2);
      border-color: rgba(0, 255, 136, 0.3);
    }

    .form-card {
      background: linear-gradient(135deg, rgba(0, 212, 255, 0.1), rgba(0, 255, 136, 0.1));
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }

    .stat-item {
      text-align: center;
      padding: 20px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 16px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      transition: all 0.3s ease;
    }

    .stat-item:hover {
      background: rgba(255, 255, 255, 0.1);
      transform: scale(1.05);
    }

    .stat-value {
      font-size: 2rem;
      font-weight: 700;
      color: #00ff88;
      display: block;
      margin-bottom: 4px;
    }

    .stat-label {
      font-size: 0.9rem;
      color: #a0a0a0;
      text-transform: uppercase;
      letter-spacing: 1px;
    }

    .form-group {
      margin-bottom: 24px;
    }

    .form-group label {
      display: block;
      margin-bottom: 8px;
      font-weight: 600;
      color: #ffffff;
      font-size: 0.95rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .form-control {
      width: 100%;
      padding: 16px 20px;
      font-size: 16px;
      border: 2px solid rgba(255, 255, 255, 0.1);
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.05);
      color: #ffffff;
      transition: all 0.3s ease;
      font-family: inherit;
    }

    .form-control:focus {
      outline: none;
      border-color: #00ff88;
      background: rgba(255, 255, 255, 0.1);
      box-shadow: 0 0 20px rgba(0, 255, 136, 0.2);
    }

    .btn-primary {
      width: 100%;
      padding: 18px;
      font-size: 1.1rem;
      font-weight: 600;
      border: none;
      border-radius: 12px;
      background: linear-gradient(135deg, #00d4ff, #00ff88);
      color: #000;
      cursor: pointer;
      transition: all 0.3s ease;
      text-transform: uppercase;
      letter-spacing: 1px;
      position: relative;
      overflow: hidden;
    }

    .btn-primary::before {
      content: '';
      position: absolute;
      top: 0;
      left: -100%;
      width: 100%;
      height: 100%;
      background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
      transition: left 0.5s;
    }

    .btn-primary:hover::before {
      left: 100%;
    }

    .btn-primary:hover {
      transform: translateY(-2px);
      box-shadow: 0 10px 30px rgba(0, 255, 136, 0.4);
    }

    .chart-container {
      background: rgba(255, 255, 255, 0.02);
      border-radius: 16px;
      padding: 24px;
      margin-bottom: 20px;
      border: 1px solid rgba(255, 255, 255, 0.05);
      position: relative;
    }

    .chart-title {
      font-size: 1.3rem;
      font-weight: 600;
      margin-bottom: 20px;
      color: #ffffff;
      text-align: center;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
    }

    .chart-title i {
      color: #00ff88;
    }

    canvas {
      max-height: 300px !important;
    }

    .mood-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
      gap: 12px;
      margin-top: 20px;
    }

    .mood-item {
      text-align: center;
      padding: 16px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 12px;
      border: 1px solid rgba(255, 255, 255, 0.1);
    }

    .mood-emoji {
      font-size: 2rem;
      display: block;
      margin-bottom: 8px;
    }

    .mood-count {
      font-size: 1.2rem;
      font-weight: 600;
      color: #00ff88;
    }

    .mood-percentage {
      font-size: 0.8rem;
      color: #a0a0a0;
    }

    .success-popup {
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%) scale(0);
      background: linear-gradient(135deg, #00ff88, #00d4ff);
      color: #000;
      padding: 24px 32px;
      border-radius: 16px;
      font-weight: 600;
      z-index: 10000;
      transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
      box-shadow: 0 20px 40px rgba(0, 255, 136, 0.3);
    }

    .success-popup.show {
      transform: translate(-50%, -50%) scale(1);
    }

    .recent-entries {
      max-height: 300px;
      overflow-y: auto;
      scrollbar-width: thin;
      scrollbar-color: #00ff88 transparent;
    }

    .recent-entries::-webkit-scrollbar {
      width: 6px;
    }

    .recent-entries::-webkit-scrollbar-track {
      background: transparent;
    }

    .recent-entries::-webkit-scrollbar-thumb {
      background: #00ff88;
      border-radius: 3px;
    }

    .entry-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      margin-bottom: 8px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 12px;
      border-left: 4px solid #00ff88;
      transition: all 0.3s ease;
    }

    .entry-item:hover {
      background: rgba(255, 255, 255, 0.1);
      transform: translateX(4px);
    }

    .entry-date {
      font-weight: 600;
      color: #ffffff;
    }

    .entry-mood {
      font-size: 1.5rem;
    }

    .insights-card {
      background: linear-gradient(135deg, rgba(255, 107, 107, 0.1), rgba(255, 165, 0, 0.1));
    }

    .insight-item {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 16px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 12px;
      margin-bottom: 12px;
    }

    .insight-icon {
      width: 40px;
      height: 40px;
      background: linear-gradient(135deg, #ff6b6b, #ffa500);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.2rem;
    }

    @media (max-width: 768px) {
      .container {
        grid-template-columns: 1fr;
        padding: 10px;
      }
      
      .header h1 {
        font-size: 2rem;
      }
      
      .glass-card {
        padding: 20px;
      }
      
      .stats-grid {
        grid-template-columns: repeat(2, 1fr);
      }
    }

    .loading {
      display: inline-block;
      width: 20px;
      height: 20px;
      border: 3px solid rgba(255, 255, 255, 0.3);
      border-radius: 50%;
      border-top-color: #00ff88;
      animation: spin 1s ease-in-out infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .trend-indicator {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 0.9rem;
      padding: 4px 8px;
      border-radius: 6px;
      font-weight: 600;
    }

    .trend-up {
      background: rgba(0, 255, 136, 0.2);
      color: #00ff88;
    }

    .trend-down {
      background: rgba(255, 107, 107, 0.2);
      color: #ff6b6b;
    }

    .trend-neutral {
      background: rgba(255, 221, 0, 0.2);
      color: #ffdd00;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1><i class="fas fa-chart-line"></i> StreakFlow</h1>
      <p>Track your daily mood with beautiful insights and analytics</p>
    </div>

    <!-- Entry Form -->
    <div class="glass-card form-card">
      <div class="chart-title">
        <i class="fas fa-plus-circle"></i>
        Add Today's Entry
      </div>
      <form id="entryForm">
        <div class="form-group">
          <label for="date"><i class="fas fa-calendar"></i> Date</label>
          <input type="date" id="date" class="form-control" required />
        </div>
        
        <div class="form-group">
          <label for="mood"><i class="fas fa-smile"></i> How are you feeling?</label>
          <select id="mood" class="form-control" required>
            <option value="">Select your mood</option>
            <option value="happy">😊 Happy & Energetic</option>
            <option value="neutral">😐 Neutral & Calm</option>
            <option value="sad">😞 Sad & Low</option>
          </select>
        </div>
        
        <button type="submit" class="btn-primary">
          <span id="submitText">Submit Entry</span>
          <span id="submitLoading" class="loading" style="display: none;"></span>
        </button>
      </form>
    </div>

    <!-- Statistics -->
    <div class="glass-card">
      <div class="chart-title">
        <i class="fas fa-chart-bar"></i>
        Your Statistics
      </div>
      <div class="stats-grid">
        <div class="stat-item">
          <span class="stat-value" id="streakCount">0</span>
          <span class="stat-label">Current Streak</span>
        </div>
        <div class="stat-item">
          <span class="stat-value" id="totalEntries">0</span>
          <span class="stat-label">Total Entries</span>
        </div>
        <div class="stat-item">
          <span class="stat-value" id="happyDays">0</span>
          <span class="stat-label">Happy Days</span>
        </div>
        <div class="stat-item">
          <span class="stat-value" id="avgMood">-</span>
          <span class="stat-label">Mood Trend</span>
        </div>
      </div>
    </div>

    <!-- Progress Chart -->
    <div class="glass-card">
      <div class="chart-title">
        <i class="fas fa-line-chart"></i>
        30-Day Progress
      </div>
      <div class="chart-container">
        <canvas id="progressChart"></canvas>
      </div>
    </div>

    <!-- Mood Distribution -->
    <div class="glass-card">
      <div class="chart-title">
        <i class="fas fa-pie-chart"></i>
        Mood Distribution
      </div>
      <div class="chart-container">
        <canvas id="moodChart"></canvas>
      </div>
      <div class="mood-grid">
        <div class="mood-item">
          <span class="mood-emoji">😊</span>
          <div class="mood-count" id="happyCount">0</div>
          <div class="mood-percentage" id="happyPercent">0%</div>
        </div>
        <div class="mood-item">
          <span class="mood-emoji">😐</span>
          <div class="mood-count" id="neutralCount">0</div>
          <div class="mood-percentage" id="neutralPercent">0%</div>
        </div>
        <div class="mood-item">
          <span class="mood-emoji">😞</span>
          <div class="mood-count" id="sadCount">0</div>
          <div class="mood-percentage" id="sadPercent">0%</div>
        </div>
      </div>
    </div>

    <!-- Recent Entries -->
    <div class="glass-card">
      <div class="chart-title">
        <i class="fas fa-history"></i>
        Recent Entries
      </div>
      <div class="recent-entries" id="recentEntries">
        <!-- Entries will be populated here -->
      </div>
    </div>

    <!-- Insights -->
    <div class="glass-card insights-card">
      <div class="chart-title">
        <i class="fas fa-lightbulb"></i>
        Insights & Tips
      </div>
      <div id="insightsContainer">
        <!-- Insights will be populated here -->
      </div>
    </div>
  </div>

  <div class="success-popup" id="popup">
    <i class="fas fa-check-circle"></i> Entry submitted successfully!
  </div>

  <script>
    // Set today's date as default
    document.getElementById('date').valueAsDate = new Date();
    
    let progressChart = null;
    let moodChart = null;

    const moodEmojis = {
      happy: '😊',
      neutral: '😐', 
      sad: '😞'
    };

    const moodColors = {
      happy: '#00ff88',
      neutral: '#ffdd00',
      sad: '#ff6b6b'
    };

    function generateInsights(data) {
      const insights = [];
      const { logs, streak } = data;
      
      if (streak >= 7) {
        insights.push({
          icon: 'fas fa-fire',
          text: `Amazing! You've maintained a ${streak}-day streak. Keep up the excellent work!`,
          type: 'success'
        });
      }

      const recentMoods = logs.slice(-7);
      const happyCount = recentMoods.filter(entry => entry.mood === 'happy').length;
      
      if (happyCount >= 5) {
        insights.push({
          icon: 'fas fa-sun',
          text: `You've been feeling great lately! ${happyCount} happy days in the last week.`,
          type: 'positive'
        });
      } else if (happyCount <= 2) {
        insights.push({
          icon: 'fas fa-heart',
          text: 'Remember to take care of yourself. Consider activities that bring you joy.',
          type: 'care'
        });
      }

      if (logs.length >= 30) {
        const last30Days = logs.slice(-30);
        const moodCounts = { happy: 0, neutral: 0, sad: 0 };
        last30Days.forEach(entry => moodCounts[entry.mood]++);
        
        const dominantMood = Object.keys(moodCounts).reduce((a, b) => 
          moodCounts[a] > moodCounts[b] ? a : b
        );
        
        insights.push({
          icon: 'fas fa-chart-pie',
          text: `Over the last 30 days, your most common mood has been ${dominantMood}. ${moodEmojis[dominantMood]}`,
          type: 'analysis'
        });
      }

      return insights;
    }

    function renderInsights(insights) {
      const container = document.getElementById('insightsContainer');
      
      if (insights.length === 0) {
        container.innerHTML = '<div class="insight-item"><div class="insight-icon"><i class="fas fa-info"></i></div><div>Keep tracking to unlock personalized insights!</div></div>';
        return;
      }

      container.innerHTML = insights.map(insight => `
        <div class="insight-item">
          <div class="insight-icon">
            <i class="${insight.icon}"></i>
          </div>
          <div>${insight.text}</div>
        </div>
      `).join('');
    }

    function renderRecentEntries(logs) {
      const container = document.getElementById('recentEntries');
      const recentLogs = logs.slice(-10).reverse();
      
      if (recentLogs.length === 0) {
        container.innerHTML = '<div style="text-align: center; color: #a0a0a0; padding: 20px;">No entries yet. Start tracking your mood!</div>';
        return;
      }

      container.innerHTML = recentLogs.map(entry => `
        <div class="entry-item">
          <div class="entry-date">${new Date(entry.date).toLocaleDateString('en-US', { 
            weekday: 'short', 
            month: 'short', 
            day: 'numeric' 
          })}</div>
          <div class="entry-mood">${moodEmojis[entry.mood]}</div>
        </div>
      `).join('');
    }

    function calculateMoodTrend(logs) {
      if (logs.length < 7) return 'neutral';
      
      const recent = logs.slice(-7);
      const earlier = logs.slice(-14, -7);
      
      if (earlier.length === 0) return 'neutral';
      
      const moodValues = { sad: 1, neutral: 2, happy: 3 };
      
      const recentAvg = recent.reduce((sum, entry) => sum + moodValues[entry.mood], 0) / recent.length;
      const earlierAvg = earlier.reduce((sum, entry) => sum + moodValues[entry.mood], 0) / earlier.length;
      
      if (recentAvg > earlierAvg + 0.2) return 'up';
      if (recentAvg < earlierAvg - 0.2) return 'down';
      return 'neutral';
    }

    async function updateUI() {
      try {
        const response = await fetch('/data');
        const data = await response.json();
        
        // Update statistics
        document.getElementById("streakCount").textContent = data.streak;
        document.getElementById("totalEntries").textContent = data.logs.length;
        
        const moodCounts = { happy: 0, neutral: 0, sad: 0 };
        data.logs.forEach(entry => moodCounts[entry.mood]++);
        
        document.getElementById("happyDays").textContent = moodCounts.happy;
        
        // Calculate and display mood trend
        const trend = calculateMoodTrend(data.logs);
        const trendElement = document.getElementById("avgMood");
        trendElement.innerHTML = `<span class="trend-indicator trend-${trend}">
          <i class="fas fa-${trend === 'up' ? 'arrow-up' : trend === 'down' ? 'arrow-down' : 'minus'}"></i>
          ${trend === 'up' ? 'Improving' : trend === 'down' ? 'Declining' : 'Stable'}
        </span>`;

        // Update mood distribution
        const total = data.logs.length;
        if (total > 0) {
          document.getElementById("happyCount").textContent = moodCounts.happy;
          document.getElementById("neutralCount").textContent = moodCounts.neutral;
          document.getElementById("sadCount").textContent = moodCounts.sad;
          
          document.getElementById("happyPercent").textContent = `${Math.round((moodCounts.happy / total) * 100)}%`;
          document.getElementById("neutralPercent").textContent = `${Math.round((moodCounts.neutral / total) * 100)}%`;
          document.getElementById("sadPercent").textContent = `${Math.round((moodCounts.sad / total) * 100)}%`;
        }

        // Destroy existing charts
        if (progressChart) progressChart.destroy();
        if (moodChart) moodChart.destroy();

        // Create progress chart
        const last30Days = data.logs.slice(-30);
        const progressCtx = document.getElementById("progressChart").getContext('2d');
        
        progressChart = new Chart(progressCtx, {
          type: "line",
          data: {
            labels: last30Days.map(entry => new Date(entry.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })),
            datasets: [{
              label: "Mood Score",
              data: last30Days.map(entry => ({ sad: 1, neutral: 2, happy: 3 })[entry.mood]),
              borderColor: "#00ff88",
              backgroundColor: "rgba(0,255,136,0.1)",
              tension: 0.4,
              fill: true,
              pointBackgroundColor: last30Days.map(entry => moodColors[entry.mood]),
              pointBorderColor: "#ffffff",
              pointBorderWidth: 2,
              pointRadius: 6,
              pointHoverRadius: 8
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false },
              tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                titleColor: '#ffffff',
                bodyColor: '#ffffff',
                borderColor: '#00ff88',
                borderWidth: 1,
                callbacks: {
                  label: function(context) {
                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                    const percentage = Math.round((context.parsed / total) * 100);
                    return `${context.label}: ${context.parsed} (${percentage}%)`;
                  }
                }
              }
            }
          }
        });

        // Render recent entries and insights
        renderRecentEntries(data.logs);
        renderInsights(generateInsights(data));

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

      // Show loading state
      const submitText = document.getElementById("submitText");
      const submitLoading = document.getElementById("submitLoading");
      submitText.style.display = "none";
      submitLoading.style.display = "inline-block";

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
        const popup = document.getElementById("popup");
        popup.classList.add("show");
        setTimeout(() => {
          popup.classList.remove("show");
        }, 3000);
        
        // Reset form
        document.getElementById("mood").value = "";
        
        // Update UI
        await updateUI();
        
      } catch (error) {
        console.error('Error submitting entry:', error);
        alert('Error submitting entry. Please try again.');
      } finally {
        // Hide loading state
        submitText.style.display = "inline";
        submitLoading.style.display = "none";
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
    entries.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d'), reverse=True)
    
    if len(entries) == 1:
        return 1
    
    streak = 1
    current_date = datetime.strptime(entries[0]['date'], '%Y-%m-%d')
    
    for i in range(1, len(entries)):
        previous_date = datetime.strptime(entries[i]['date'], '%Y-%m-%d')
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

        # Convert date string to datetime for MongoDB
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        # Check for duplicate entry for the same date in MongoDB
        existing_entry = collection.find_one({"date": date_obj})
        if existing_entry:
            return jsonify({"message": "Entry already exists for this date"}), 200

        # Insert new entry to MongoDB
        collection.insert_one({"date": date_obj, "mood": mood})
        mongodb_msg = "Entry saved to MongoDB"

        # Send to Google Sheets
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
        # Try to fetch data from Google Sheets first
        sheets_data = fetch_google_sheets_data()
        
        if sheets_data:
            # Use Google Sheets data for calculations
            entries = []
            for row in sheets_data:
                if len(row) >= 2:  # Ensure we have at least date and mood
                    try:
                        # Assuming Google Sheets data format: [date, mood, ...]
                        date_str = row[0]
                        mood_str = row[1]
                        
                        # Validate date format
                        datetime.strptime(date_str, "%Y-%m-%d")
                        
                        entries.append({
                            "date": date_str,
                            "mood": mood_str
                        })
                    except (ValueError, IndexError):
                        continue  # Skip invalid entries
            
            # Calculate streak using Google Sheets data
            streak = calculate_streak(entries)
            
            return jsonify({"logs": entries, "streak": streak})
        
        else:
            # Fallback to MongoDB data if Google Sheets is not available
            entries = list(collection.find({}, {"_id": 0}).sort("date", 1))
            
            # Convert datetime objects to strings for JSON serialization
            for entry in entries:
                entry["date"] = entry["date"].strftime("%Y-%m-%d")
            
            # Calculate streak using MongoDB data
            streak = calculate_streak(entries)
            
            return jsonify({"logs": entries, "streak": streak})
    
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"})

if __name__ == "__main__":
    app.run(debug=True): 'rgba(0, 0, 0, 0.8)',
                titleColor: '#ffffff',
                bodyColor: '#ffffff',
                borderColor: '#00ff88',
                borderWidth: 1,
                callbacks: {
                  label: function(context) {
                    const moodNames = { 1: 'Sad', 2: 'Neutral', 3: 'Happy' };
                    return `Mood: ${moodNames[context.parsed.y]}`;
                  }
                }
              }
            },
            scales: {
              x: {
                ticks: { color: '#a0a0a0', maxTicksLimit: 8 },
                grid: { color: 'rgba(255, 255, 255, 0.1)' }
              },
              y: {
                min: 0.5,
                max: 3.5,
                ticks: { 
                  color: '#a0a0a0',
                  callback: function(value) {
                    const labels = { 1: '😞', 2: '😐', 3: '😊' };
                    return labels[value] || '';
                  }
                },
                grid: { color: 'rgba(255, 255, 255, 0.1)' }
              }
            },
            elements: {
              point: {
                hoverBorderWidth: 3
              }
            }
          }
        });

        // Create mood distribution chart
        const moodCtx = document.getElementById("moodChart").getContext('2d');
        moodChart = new Chart(moodCtx, {
          type: "doughnut",
          data: {
            labels: ["😊 Happy", "😐 Neutral", "😞 Sad"],
            datasets: [{
              data: [moodCounts.happy, moodCounts.neutral, moodCounts.sad],
              backgroundColor: ["#00ff88", "#ffdd00", "#ff6b6b"],
              borderWidth: 0,
              cutout: '60%'
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                position: 'bottom',
                labels: {
                  color: '#ffffff',
                  padding: 20,
                  usePointStyle: true,
                  font: { size: 14 }
                }
              },
tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                titleColor: '#ffffff',
                bodyColor: '#ffffff',
                borderColor: '#00ff88',
                borderWidth: 1,
                callbacks: {
                  label: function(context) {
                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                    const percentage = Math.round((context.parsed / total) * 100);
                    return `${context.label}: ${context.parsed} (${percentage}%)`;
                  }
                }
              }
            }
          }
        });

        // Render recent entries and insights
        renderRecentEntries(data.logs);
        renderInsights(generateInsights(data));

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

      // Show loading state
      const submitText = document.getElementById("submitText");
      const submitLoading = document.getElementById("submitLoading");
      submitText.style.display = "none";
      submitLoading.style.display = "inline-block";

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
        const popup = document.getElementById("popup");
        popup.classList.add("show");
        setTimeout(() => {
          popup.classList.remove("show");
        }, 3000);
        
        // Reset form
        document.getElementById("mood").value = "";
        
        // Update UI
        await updateUI();
        
      } catch (error) {
        console.error('Error submitting entry:', error);
        alert('Error submitting entry. Please try again.');
      } finally {
        // Hide loading state
        submitText.style.display = "inline";
        submitLoading.style.display = "none";
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
    entries.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d'), reverse=True)
    
    if len(entries) == 1:
        return 1
    
    streak = 1
    current_date = datetime.strptime(entries[0]['date'], '%Y-%m-%d')
    
    for i in range(1, len(entries)):
        previous_date = datetime.strptime(entries[i]['date'], '%Y-%m-%d')
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

        # Convert date string to datetime for MongoDB
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        # Check for duplicate entry for the same date in MongoDB
        existing_entry = collection.find_one({"date": date_obj})
        if existing_entry:
            return jsonify({"message": "Entry already exists for this date"}), 200

        # Insert new entry to MongoDB
        collection.insert_one({"date": date_obj, "mood": mood})
        mongodb_msg = "Entry saved to MongoDB"

        # Send to Google Sheets
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
        # Try to fetch data from Google Sheets first
        sheets_data = fetch_google_sheets_data()
        
        if sheets_data:
            # Use Google Sheets data for calculations
            entries = []
            for row in sheets_data:
                if len(row) >= 2:  # Ensure we have at least date and mood
                    try:
                        # Assuming Google Sheets data format: [date, mood, ...]
                        date_str = row[0]
                        mood_str = row[1]
                        
                        # Validate date format
                        datetime.strptime(date_str, "%Y-%m-%d")
                        
                        entries.append({
                            "date": date_str,
                            "mood": mood_str
                        })
                    except (ValueError, IndexError):
                        continue  # Skip invalid entries
            
            # Calculate streak using Google Sheets data
            streak = calculate_streak(entries)
            
            return jsonify({"logs": entries, "streak": streak})
        
        else:
            # Fallback to MongoDB data if Google Sheets is not available
            entries = list(collection.find({}, {"_id": 0}).sort("date", 1))
            
            # Convert datetime objects to strings for JSON serialization
            for entry in entries:
                entry["date"] = entry["date"].strftime("%Y-%m-%d")
            
            # Calculate streak using MongoDB data
            streak = calculate_streak(entries)
            
            return jsonify({"logs": entries, "streak": streak})
    
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"})

if __name__ == "__main__":
    app.run(debug=True)
