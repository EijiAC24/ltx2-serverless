"""
LTX-2 Video Generator GUI
Local GUI for generating videos with Runpod Serverless
"""

import os
import base64
import time
import requests
import gradio as gr
from datetime import datetime

# Config
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY", "")
RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID", "j01yykel5de361")
RUNPOD_ENDPOINT = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}"

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "videos")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def check_health():
    """Check endpoint health"""
    try:
        response = requests.get(
            f"{RUNPOD_ENDPOINT}/health",
            headers={"Authorization": f"Bearer {RUNPOD_API_KEY}"},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            workers = data.get("workers", {})
            return f"Ready ({workers.get('ready', 0)} workers)"
        return "Not responding"
    except Exception as e:
        return f"Error: {e}"


def submit_job(prompt, duration, width, height, steps, seed, image_base64=None, image_strength=1.0):
    """Submit generation job (T2V or I2V)"""
    payload = {
        "input": {
            "prompt": prompt,
            "duration": duration,
            "width": width,
            "height": height,
            "steps": steps,
        }
    }

    if seed and seed > 0:
        payload["input"]["seed"] = seed

    # I2V: 画像パラメータ
    if image_base64:
        payload["input"]["image_base64"] = image_base64
        payload["input"]["image_strength"] = image_strength

    response = requests.post(
        f"{RUNPOD_ENDPOINT}/run",
        headers={
            "Authorization": f"Bearer {RUNPOD_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )

    response.raise_for_status()
    return response.json()["id"]


def get_status(job_id):
    """Get job status"""
    response = requests.get(
        f"{RUNPOD_ENDPOINT}/status/{job_id}",
        headers={"Authorization": f"Bearer {RUNPOD_API_KEY}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def generate_video(prompt, duration, width, height, steps, seed, input_image, image_strength, progress=gr.Progress()):
    """Main generation function (T2V or I2V)"""

    if not prompt.strip():
        return None, "Error: Prompt is required", None

    # I2V: 画像をBase64エンコード
    image_base64 = None
    if input_image is not None:
        import base64
        with open(input_image, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")

    mode = "I2V" if image_base64 else "T2V"

    # Validate resolution
    if width % 64 != 0 or height % 64 != 0:
        return None, f"Error: Resolution {width}x{height} must be divisible by 64", None

    try:
        # Submit job
        progress(0.1, desc=f"Submitting {mode} job...")
        job_id = submit_job(prompt, duration, width, height, steps, seed if seed else None, image_base64, image_strength)

        # Poll for completion
        start_time = time.time()
        max_time = 600  # 10 minutes

        while time.time() - start_time < max_time:
            status = get_status(job_id)
            state = status.get("status")

            elapsed = int(time.time() - start_time)
            progress_pct = min(0.1 + (elapsed / max_time) * 0.8, 0.9)

            if state == "COMPLETED":
                progress(0.95, desc="Downloading video...")

                output = status.get("output", {})
                video_b64 = output.get("video_base64")

                if not video_b64:
                    return None, "Error: No video in response", None

                # Decode and save
                video_bytes = base64.b64decode(video_b64)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"ltx2_{timestamp}.mp4"
                filepath = os.path.join(OUTPUT_DIR, filename)

                with open(filepath, "wb") as f:
                    f.write(video_bytes)

                # Calculate cost
                exec_time = status.get("executionTime", 0) / 1000
                cost = exec_time * 0.00106

                info = f"""Generation complete! ({mode})

Mode: {mode}
Duration: {output.get('duration')}s
Resolution: {output.get('resolution')}
Frames: {output.get('frames')}
Generation time: {exec_time:.1f}s
Cost: ${cost:.4f}

Saved to: {filepath}"""

                progress(1.0, desc="Done!")
                return filepath, info, filepath

            elif state == "FAILED":
                error = status.get("error", "Unknown error")
                return None, f"Error: {error}", None

            elif state in ("IN_QUEUE", "IN_PROGRESS"):
                progress(progress_pct, desc=f"{state}... ({elapsed}s)")
                time.sleep(5)
            else:
                progress(progress_pct, desc=f"Status: {state}")
                time.sleep(5)

        return None, "Error: Timeout (10 minutes)", None

    except Exception as e:
        return None, f"Error: {str(e)}", None


# Preset resolutions
RESOLUTIONS = {
    "Reel/TikTok (576x1024)": (576, 1024),
    "Reel HD (1088x1920)": (1088, 1920),
    "YouTube (1280x768)": (1280, 768),
    "Square (1024x1024)": (1024, 1024),
    "Custom": (576, 1024),
}


def update_resolution(preset):
    """Update width/height from preset"""
    if preset in RESOLUTIONS:
        w, h = RESOLUTIONS[preset]
        return w, h
    return 576, 1024


# Build UI
with gr.Blocks(title="LTX-2 Video Generator", theme=gr.themes.Soft()) as app:
    gr.Markdown("# LTX-2 Video Generator")
    gr.Markdown("Generate AI videos using LTX-2 on Runpod Serverless (T2V & I2V supported)")

    with gr.Row():
        with gr.Column(scale=2):
            prompt = gr.Textbox(
                label="Prompt",
                placeholder="A cat walking in a garden, cinematic lighting, shallow depth of field...",
                lines=5,
            )

            with gr.Row():
                resolution_preset = gr.Dropdown(
                    choices=list(RESOLUTIONS.keys()),
                    value="Reel/TikTok (576x1024)",
                    label="Resolution Preset",
                )

            with gr.Row():
                width = gr.Number(value=576, label="Width", precision=0)
                height = gr.Number(value=1024, label="Height", precision=0)

            with gr.Row():
                duration = gr.Slider(1, 15, value=15, step=1, label="Duration (seconds)")
                steps = gr.Slider(8, 30, value=20, step=1, label="Steps")

            seed = gr.Number(value=0, label="Seed (0 = random)", precision=0)

            # I2V: Image-to-Video section
            with gr.Accordion("🖼️ Image-to-Video (I2V)", open=False):
                gr.Markdown("Upload an image to animate it. Leave empty for Text-to-Video (T2V).")
                input_image = gr.Image(
                    label="Input Image (optional)",
                    type="filepath",
                    height=200,
                )
                image_strength = gr.Slider(
                    0.1, 1.0, value=1.0, step=0.1,
                    label="Image Strength (1.0 = strong conditioning)"
                )

            with gr.Row():
                generate_btn = gr.Button("Generate Video", variant="primary", size="lg")
                health_btn = gr.Button("Check Status")

        with gr.Column(scale=2):
            video_output = gr.Video(label="Generated Video")
            info_output = gr.Textbox(label="Info", lines=10)
            download_output = gr.File(label="Download")

    # Examples
    gr.Examples(
        examples=[
            ["Close-up of an orange tabby cat sitting on a modern kitchen counter in warm morning sunlight. The cat stares directly into camera with an intense judgmental expression and speaks in a deadpan British accent, 'I know what you did last night.' The cat slowly blinks with smug satisfaction. Shallow depth of field, cinematic lighting, comedic tone.", 15, 576, 1024, 20, 0],
            ["A golden retriever puppy playing with a red ball in a sunny backyard. The puppy runs excitedly, tail wagging. Natural lighting, handheld camera feel, joyful atmosphere.", 15, 576, 1024, 20, 0],
            ["Old monochrome documentary film footage from the 1920s with heavy film grain and flickering. A young man in vintage clothing sits at a wooden desk, writing with a fountain pen. Authentic vintage film aesthetic, sepia tones.", 15, 1280, 768, 20, 0],
        ],
        inputs=[prompt, duration, width, height, steps, seed],
    )

    # Tips
    with gr.Accordion("Prompt Tips", open=False):
        gr.Markdown("""
### Good prompts include:
- **Shot setup**: Camera angle (close-up, medium shot, wide shot)
- **Scene**: Lighting, atmosphere, environment
- **Action**: Use present tense, keep to 1-2 actions
- **Character**: Appearance, clothing, expression
- **Camera work**: Pan, zoom, handheld, etc.

### For dialogue:
```
speaking in British accent, "Hello there!"
speaking in enthusiastic English, "This is amazing!"
```

### Avoid:
- "no text", "no subtitles" (causes text to appear)
- Specific location names (Tokyo, NYC)
- Negative prompts
- Complex physics (jumping, juggling)

### Image-to-Video (I2V) Tips:
- Describe the **motion/action** you want, not the image content
- The model already sees the image, so focus on what should happen
- Good: "The cat slowly turns its head and blinks"
- Bad: "A cat sitting on a table" (redundant with image)
        """)

    # Event handlers
    resolution_preset.change(
        fn=update_resolution,
        inputs=[resolution_preset],
        outputs=[width, height],
    )

    generate_btn.click(
        fn=generate_video,
        inputs=[prompt, duration, width, height, steps, seed, input_image, image_strength],
        outputs=[video_output, info_output, download_output],
    )

    health_btn.click(
        fn=check_health,
        outputs=[info_output],
    )


if __name__ == "__main__":
    print("Starting LTX-2 Video Generator GUI...")
    print(f"Output directory: {OUTPUT_DIR}")
    app.launch(
        server_name="0.0.0.0",
        inbrowser=True,
    )
