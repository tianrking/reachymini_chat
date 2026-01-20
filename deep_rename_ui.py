import os

def deep_rename(target_dir):
    print(f"🚀 Starting deep rename in: {target_dir}")
    replacements = {
        "Pipecat Playground": "Seeed Studio",
        "Pipecat": "Seeed Studio"
    }
    
    for root, dirs, files in os.walk(target_dir):
        for filename in files:
            if filename.endswith((".js", ".html", ".css", ".json")):
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    new_content = content
                    for old, new in replacements.items():
                        # Using exact replacement first
                        new_content = new_content.replace(old, new)
                    
                    if new_content != content:
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        print(f"✅ Updated: {filepath}")
                except Exception as e:
                    print(f"❌ Error processing {filepath}: {e}")

if __name__ == "__main__":
    ui_path = "/home/w0x7ce/Downloads/ddeevv/pipecat/reachymini_chat/custom_ui"
    deep_rename(ui_path)
