
import os

key_line = "LLAMA_CLOUD_API_KEY=\"llx-iUjiJF7ryVdyiKlIYwjCQiWuhnraE6El6rE27hS5YVXidOkX\""
path = ".env"

with open(path, "r") as f:
    lines = f.readlines()

key_found = False
new_lines = []
for line in lines:
    if line.startswith("LLAMA_CLOUD_API_KEY="):
        new_lines.append(key_line + "\n")
        key_found = True
    else:
        new_lines.append(line)

if not key_found:
    if new_lines and not new_lines[-1].endswith('\n'):
        new_lines[-1] += "\n"
    new_lines.append(key_line + "\n")

with open(path, "w") as f:
    f.writelines(new_lines)

print("Updated .env with LLAMA_CLOUD_API_KEY")
