import os
import glob
import ollama

WORKSPACE_PATH = r"C:\Users\Pierre\.openclaw\workspace"
MODEL_NAME = "gemma4:26b"

def run_warmup():
    print("[WARMUP] Loading system context and workspace MD files...")
    md_files = glob.glob(os.path.join(WORKSPACE_PATH, "*.md")) + glob.glob(os.path.join(WORKSPACE_PATH, "Julie-Core", "*.md"))
    
    context_text = "SYSTEM CONTEXT INIT:\n"
    for file_path in md_files:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                filename = os.path.basename(file_path)
                context_text += f"\n--- DOCUMENT: {filename} ---\n{content[:2000]}\n"
        except Exception as e:
            print(f"[WARMUP WARNING] Could not read {file_path}: {e}")

    # Warm up Ollama context window
    try:
        print("[WARMUP] Warming up Ollama context buffer...")
        ollama.chat(model=MODEL_NAME, messages=[
            {"role": "system", "content": "You are Julie, an executive AI assistant. Process and acknowledge the following workspace context."},
            {"role": "user", "content": context_text[:8000]},
            {"role": "assistant", "content": "Context loaded and acknowledged. Standing by for user voice commands."}
        ])
        print("[WARMUP COMPLETE] Model memory pre-warmed successfully.")
    except Exception as e:
        print(f"[WARMUP ERROR] Failed to warm up Ollama model: {e}")

if __name__ == "__main__":
    run_warmup()
