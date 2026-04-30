import pandas as pd
import json

try:
    # Read the file from inside the container (assuming it was copied to the backend folder)
    df = pd.read_excel('/app/maharashtra_comprehensive_real_estate_dataset.xlsx', nrows=5)
    info = {
        "columns": list(df.columns),
        "shape": str(df.shape),
        "head": df.to_dict(orient="records")
    }
    with open("/app/data/excel_info.json", "w") as f:
        json.dump(info, f, indent=2, default=str)
    print("✅ Successfully analyzed! You can now ask me to check the results.")
except Exception as e:
    print("Error:", str(e))
