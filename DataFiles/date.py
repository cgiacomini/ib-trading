import csv
import sys
from datetime import datetime
import pytz

def convert_dates_to_timestamps(input_file):
    reader = csv.reader(open(input_file, 'r'))
    writer = csv.writer(sys.stdout)

    # Read and write the header
    header = next(reader)
    writer.writerow(header)

    # Process each row
    for row in reader:
        if row and row[0]:
            # Parse the datetime with timezone
            dt = datetime.fromisoformat(row[0])
            timestamp = int(dt.timestamp())
            row[0] = str(timestamp)
        writer.writerow(row)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python convert_dates_to_timestamps.py <input_file.csv>")
        sys.exit(1)

    convert_dates_to_timestamps(sys.argv[1])

