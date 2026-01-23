
import os

path = ".env"

if os.path.exists(path):
    with open(path, "rb") as f:
        content = f.read()
    
    # Check for null bytes (UTF-16 indicator often)
    if b'\x00' in content:
        print("⚠️ Detected Null bytes (Encoding Issue). Cleaning...")
        # Decode ignoring errors or try specific encodings
        try:
            # Try decoding as utf-16 if it looks like it
            decoded = content.decode('utf-16')
        except:
            # Fallback: Just strip null bytes and decode utf-8
            decoded = content.replace(b'\x00', b'').decode('utf-8', errors='ignore')
            
        # Re-write as clean UTF-8
        with open(path, "w", encoding="utf-8") as f:
            f.write(decoded)
        print("✅ .env Cleaned and Saved as UTF-8")
    else:
        print("ℹ️ .env seems valid (No null bytes).")
else:
    print("❌ .env not found")
