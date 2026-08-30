"""CSV seeds are committed and intentionally not regenerated during app runtime."""
from pathlib import Path
import pandas as pd

def main():
    for path in Path("data").glob("*.csv"):
        print(path, len(pd.read_csv(path)), "rows")

if __name__ == "__main__": main()

