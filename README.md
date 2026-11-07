# WasteWise AI

WasteWise AI is a Team Spark hackathon project. It helps a college canteen see which meals are wasted, remember what happened on past days, and ask a simple AI assistant for a next-day prep suggestion.

## Files

| File | Role |
| --- | --- |
| `app.py` | Streamlit dashboard |
| `data_manager.py` | Loads canteen rows from CSV |
| `analytics.py` | Waste totals, percentage, and breakdowns |
| `hindsight_memory.py` | Hindsight memory: retain, recall, reflect |
| `check_hindsight.py` | Command-line test of the Hindsight connection and the three operations |
| `ai_agent.py` | Groq assistant (next) |
| `data/sample_data.csv` | Example breakfast, lunch, and snack records |

## Sample data

Each row is one item at one meal. Portions wasted are `portions_prepared - portions_served`. `cost_per_portion` is in rupees. `waste_kg` is the estimated leftover weight.

## Setup (when you are ready)

1. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and add your own keys. Do not commit `.env`.

3. Start the dashboard:

   ```bash
   streamlit run app.py
   ```

The dashboard reads the sample file and shows waste totals.

The AI Food Advisor page has three tabs that use Hindsight Cloud: Retain (save canteen records), Recall (search them) and Reflect (get insights from them). It needs `HINDSIGHT_API_KEY` in `.env`. To test it from the terminal first, run `python check_hindsight.py`. Groq is not connected yet.
