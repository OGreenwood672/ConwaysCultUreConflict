"""
Culture file watcher - monitors culture.md files and extracts attributes via Ollama.
"""

import csv
import json
import time
import requests
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"  # Change to your preferred model

ATTRIBUTES = ["Aggression", "Resources", "Commerce", "Resilience", "Adaptability"]

OUTPUT_DIR = Path(__file__).parent / "your-mum" / "public" / "culture_data"
HISTORY_DIR = OUTPUT_DIR / "history"

# Track update counts per culture for CSV saving
update_counts = {}


def extract_attributes_from_culture(content: str) -> dict:
    """Send culture content to Ollama and extract attribute values."""

    prompt = f"""Analyze this culture document and rate the following attributes from 0 to 100.
Base your ratings on the content - what behaviors, norms, and conditions are described.

Culture Document:
{content}

Rate these 5 attributes (0-100):
1. Aggression - How aggressive/warlike is this culture? (conflicts, rivalries, threats)
2. Resources - How abundant are their resources? (food, materials, wealth)
3. Commerce - How developed is their trade/economy? (trade routes, currency, markets)
4. Resilience - How resilient are they to hardship? (shelter, survival skills, preparedness)
5. Adaptability - How adaptable/flexible is the culture? (learning, changing norms, innovation)

Respond ONLY with valid JSON in this exact format, no other text:
{{"Aggression": <number>, "Resources": <number>, "Commerce": <number>, "Resilience": <number>, "Adaptability": <number>}}"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3},
            },
            timeout=60,
        )
        response.raise_for_status()

        result = response.json()
        text = result.get("response", "").strip()

        # Try to extract JSON from response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            json_str = text[start:end]
            attributes = json.loads(json_str)

            # Validate and clamp values
            validated = {}
            for attr in ATTRIBUTES:
                val = attributes.get(attr, 50)
                validated[attr] = max(0, min(100, int(val)))

            return validated

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Ollama: {e}")
    except json.JSONDecodeError:
        print(f"Error parsing Ollama response")
    except Exception as e:
        print(f"Unexpected error: {e}")

    # Return default values on error
    return {attr: 50 for attr in ATTRIBUTES}


def save_history_to_csv(culture_name: str, attributes: dict, timestamp: float):
    """Append culture attributes to historical CSV file."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    csv_file = HISTORY_DIR / f"{culture_name}.csv"
    file_exists = csv_file.exists()

    with open(csv_file, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            # Write header for new file
            writer.writerow(["timestamp"] + ATTRIBUTES)
        # Write data row
        row = [timestamp] + [attributes[attr] for attr in ATTRIBUTES]
        writer.writerow(row)

    print(f"  -> Saved to history CSV (every 5 updates)")


def save_culture_data(culture_name: str, attributes: dict):
    """Save culture attributes to JSON file for frontend."""
    global update_counts

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = time.time()
    data = {"culture": culture_name, "attributes": attributes, "timestamp": timestamp}

    # Save individual culture file
    culture_file = OUTPUT_DIR / f"{culture_name}.json"
    with open(culture_file, "w") as f:
        json.dump(data, f, indent=2)

    # Update combined cultures file
    all_cultures = {}
    for json_file in OUTPUT_DIR.glob("*.json"):
        if json_file.name != "all_cultures.json":
            try:
                with open(json_file) as f:
                    culture_data = json.load(f)
                    all_cultures[culture_data["culture"]] = culture_data
            except:
                pass

    with open(OUTPUT_DIR / "all_cultures.json", "w") as f:
        json.dump(all_cultures, f, indent=2)

    print(f"Saved {culture_name} attributes: {attributes}")

    # Track updates and save to CSV every 5 updates
    if culture_name not in update_counts:
        update_counts[culture_name] = 0
    update_counts[culture_name] += 1

    if update_counts[culture_name] % 5 == 0:
        save_history_to_csv(culture_name, attributes, timestamp)


def process_culture_file(file_path: str):
    """Process a single culture file."""
    path = Path(file_path)

    # Extract culture name from path (e.g., world/cultures/alpha/culture.md -> alpha)
    culture_name = path.parent.name

    print(f"Processing culture: {culture_name}")

    try:
        with open(path, "r") as f:
            content = f.read()

        attributes = extract_attributes_from_culture(content)
        save_culture_data(culture_name, attributes)

    except Exception as e:
        print(f"Error processing {file_path}: {e}")


class CultureFileHandler(FileSystemEventHandler):
    """Handler for culture file changes."""

    def __init__(self):
        self.last_modified = {}

    def on_modified(self, event):
        if event.is_directory:
            return

        if event.src_path.endswith("culture.md"):
            # Debounce - ignore if modified within last 2 seconds
            now = time.time()
            last = self.last_modified.get(event.src_path, 0)
            if now - last < 2:
                return
            self.last_modified[event.src_path] = now

            print(f"\nDetected change in: {event.src_path}")
            process_culture_file(event.src_path)

    def on_created(self, event):
        if event.is_directory:
            return

        if event.src_path.endswith("culture.md"):
            print(f"\nNew culture file: {event.src_path}")
            process_culture_file(event.src_path)


def main():
    """Main entry point."""
    base_path = Path(__file__).parent / "world" / "cultures"

    print(f"Culture Watcher Starting...")
    print(f"Watching: {base_path}")
    print(f"Ollama URL: {OLLAMA_URL}")
    print(f"Model: {OLLAMA_MODEL}")
    print("-" * 50)

    # Process all existing culture files on startup
    existing_files = list(base_path.glob("*/culture.md"))
    print(f"Found {len(existing_files)} existing culture files")

    for culture_file in existing_files:
        process_culture_file(str(culture_file))

    print("-" * 50)
    print("Watching for changes... (Ctrl+C to stop)")

    # Set up file watcher
    event_handler = CultureFileHandler()
    observer = Observer()
    observer.schedule(event_handler, str(base_path), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        observer.stop()

    observer.join()


if __name__ == "__main__":
    main()
