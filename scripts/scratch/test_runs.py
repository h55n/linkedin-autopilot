import urllib.request
import json

def fetch_runs():
    req = urllib.request.Request("https://api.github.com/repos/h55n/linkedin-autopilot/actions/runs?per_page=10")
    req.add_header("Accept", "application/vnd.github.v3+json")
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        for r in data.get("workflow_runs", []):
            print(f"{r['name']}: {r['status']} - {r['conclusion']} (ID: {r['id']})")

if __name__ == "__main__":
    fetch_runs()
