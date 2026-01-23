
import os

updates = {
    "QDRANT_URL": "https://690e02e9-740a-47e8-bc03-a9fea7a1692f.us-east4-0.gcp.cloud.qdrant.io",
    "QDRANT_API_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.q2iGWOQYfzml4VOCkLPDXH6MhQds63nVlR7qD59tYoI"
}

path = ".env"
new_lines = []
processed_keys = set()

if os.path.exists(path):
    with open(path, "r") as f:
        lines = f.readlines()
        
    for line in lines:
        key = line.split("=")[0].strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}\n")
            processed_keys.add(key)
        else:
            new_lines.append(line)
else:
    print(".env file not found!")
    exit(1)

# Append missing keys
for key, val in updates.items():
    if key not in processed_keys:
        new_lines.append(f"{key}={val}\n")

with open(path, "w") as f:
    f.writelines(new_lines)

print("✅ .env Updated Successfully with Cloud Credentials")
