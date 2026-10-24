import sys
from pathlib import Path
lines = Path(sys.argv[1]).read_text(encoding='utf-8').splitlines()
start, end = int(sys.argv[2]), int(sys.argv[3])
for index in range(start - 1, min(end, len(lines))):
    print(str(index + 1) + ': ' + lines[index])
