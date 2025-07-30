import csv
import sys
from datetime import datetime

def convert_timestamps(input_file):
    reader = csv.reader(open(input_file, 'r'))
    writer = csv.writer(sys.stdout)

    # Read and write the header
    header = next(reader)
    writer.writerow(header)

    # Process each row
    for row in reader:
        if row and row[0].isdigit():
            timestamp = int(row[0])
            row[0] = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        writer.writerow(row)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python convert_timestamps.py <input_file.csv>")
        sys.exit(1)

    convert_timestamps(sys.argv[1])

