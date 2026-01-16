Pentagon Pizza Theory – Automated Activity Analysis

Overview

This project is a Python-based automation and analysis tool designed to monitor pizza restaurants located around the Pentagon area and detect abnormal activity spikes using Google Maps data.
The goal is to automate the collection and analysis of location-based activity signals and compare them against a baseline of normal density, inspired by the well-known Pentagon Pizza Theory.

The system replaces manual monitoring by programmatically collecting data, preprocessing it, and identifying unusual increases in activity.

⸻

Key Features
	•	Automated data collection from Google Maps using Playwright
	•	Baseline calculation for normal activity density
	•	Detection of abnormal activity spikes exceeding expected thresholds
	•	Clean, structured outputs for further analysis or monitoring
	•	Designed as an extensible automation pipeline (alerts, dashboards, messaging can be added)

⸻

Project Structure

Pentagon-Pizza-Theory/
│
├── main2.py        # Main automation and analysis script
├── notlar.txt      # Notes / observations (optional)
├── README.md       # Project documentation
├── .gitignore      # Excludes sensitive and environment-specific files

Important: Browser profiles, virtual environments, and sensitive files are intentionally excluded for security reasons.

⸻

Requirements
	•	Python 3.9+
	•	Playwright
	•	Chromium browser (installed via Playwright)

Install dependencies:

pip install playwright
playwright install


⸻

Browser Profile (Important)

This project uses a persistent Playwright browser profile to access Google Maps reliably.

⚠️ Security Note

The browser profile directory (pw_profile) may contain:
	•	Cookies
	•	Session data
	•	Browsing history

For this reason, it is not included in the repository and should never be shared publicly.

How to set up your own profile
	1.	Create a local directory named pw_profile in the project root:

mkdir pw_profile

	2.	The profile will be automatically populated when the script is executed.
	3.	Each user must generate and use their own local browser profile.

⸻

Usage

Run the main script:

python main2.py

The program will:
	1.	Open Google Maps using a persistent browser session
	2.	Collect activity-related data for pizza restaurants around the Pentagon
	3.	Compute a baseline of normal activity density
	4.	Detect and flag abnormal spikes that exceed expected levels

⸻

Use Case

This project demonstrates:
	•	Process automation
	•	Data collection and preprocessing
	•	Baseline-driven anomaly detection
	•	Hypothesis-driven analysis (Pentagon Pizza Theory)

It is suitable as a portfolio project showcasing automation, data analysis, and applied problem-solving skills.

⸻

Future Improvements
	•	Real-time alerts (Telegram, email, Slack)
	•	Historical data storage (CSV / database)
	•	Visualization dashboards
	•	Advanced statistical or ML-based anomaly detection

⸻

Disclaimer

This project is for educational and analytical purposes only. It does not make any real-world claims and should not be used for decision-making beyond experimental analysis.

⸻

Author

Developed as a personal automation and data analysis project.
