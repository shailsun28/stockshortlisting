import subprocess

# Define the path to the scripts
script_path = '/Users/shail/Documents/Trading/My-Code/'

# Run web_hourly_to_db.py
web_hourly_script = f"{script_path}web_hourly_to_db.py"
onetimedb_script = f"{script_path}onetimedb_hrly_shortlist.py"

try:
    # Run the first script
    subprocess.run(['python3', web_hourly_script], check=True)
    print(f"Successfully ran {web_hourly_script}")

    # Run the second script after the first completes
    subprocess.run(['python3', onetimedb_script], check=True)
    print(f"Successfully ran {onetimedb_script}")

except subprocess.CalledProcessError as e:
    print(f"An error occurred while running the scripts: {e}")
