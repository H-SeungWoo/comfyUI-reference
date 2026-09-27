import json
import random
import sys
import time
from pathlib import Path

import requests

from prompt_builder import load_shot_spec, build_image_prompt


COMFYUI_BASE_URL = "http://127.0.0.1:8188"
WORKFLOW_PATH = Path("workflows/reference_image_workflow_api.json")

POSITIVE_NODE_ID = "2"
NEGATIVE_NODE_ID = "3"
KSAMPLER_NODE_ID = "5"
SAVE_IMAGE_NODE_ID = "7"

NUM_CANDIDATES = 3


def load_workflow(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Workflow file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def prepare_workflow(
    workflow: dict,
    image_prompt: str,
    shot_id: str,
    candidate_index: int
) -> tuple[dict, int]:
    workflow_copy = json.loads(json.dumps(workflow))
    seed = random.randint(1, 2**31 - 1)

    # Positive Prompt
    workflow_copy[POSITIVE_NODE_ID]["inputs"]["text"] = image_prompt

    # Negative Prompt
    workflow_copy[NEGATIVE_NODE_ID]["inputs"]["text"] = (
        "blurry, low quality, distorted anatomy, bad hands, extra fingers, "
        "deformed face, duplicate subject, cropped, text, watermark"
    )

    # Seed
    workflow_copy[KSAMPLER_NODE_ID]["inputs"]["seed"] = seed

    # Save path / prefix
    workflow_copy[SAVE_IMAGE_NODE_ID]["inputs"]["filename_prefix"] = (
        f"references/{shot_id}/candidate_{candidate_index:02d}"
    )

    return workflow_copy, seed


def queue_prompt(workflow: dict) -> str:
    response = requests.post(
        f"{COMFYUI_BASE_URL}/prompt",
        json={"prompt": workflow},
        timeout=30
    )
    response.raise_for_status()
    data = response.json()
    return data["prompt_id"]


def wait_for_completion(prompt_id: str, timeout_sec: int = 180) -> dict:
    start_time = time.time()

    while time.time() - start_time < timeout_sec:
        response = requests.get(f"{COMFYUI_BASE_URL}/history/{prompt_id}", timeout=30)
        response.raise_for_status()
        data = response.json()

        if prompt_id in data:
            return data[prompt_id]

        time.sleep(1)

    raise TimeoutError(f"Timed out waiting for prompt_id={prompt_id}")


def main():
    if len(sys.argv) != 2:
        print("Usage:")
        print("python src/generate.py specs/<shot_spec>.json")
        sys.exit(1)

    spec_path = sys.argv[1]

    try:
        spec = load_shot_spec(spec_path)
        image_prompt = build_image_prompt(spec)
        workflow = load_workflow(WORKFLOW_PATH)

        print(f"\nSHOT ID: {spec['shot_id']}")
        print("\n[IMAGE PROMPT]")
        print(image_prompt)

        results = []

        for candidate_index in range(1, NUM_CANDIDATES + 1):
            print(f"\n--- Generating candidate {candidate_index}/{NUM_CANDIDATES} ---")

            prepared_workflow, seed = prepare_workflow(
                workflow,
                image_prompt,
                spec["shot_id"],
                candidate_index
            )

            print(f"SEED: {seed}")
            print("Sending workflow to ComfyUI...")

            prompt_id = queue_prompt(prepared_workflow)
            print(f"Prompt queued successfully. prompt_id = {prompt_id}")

            print("Waiting for completion...")
            result = wait_for_completion(prompt_id)

            print(f"Candidate {candidate_index} completed.")
            results.append({
                "candidate_index": candidate_index,
                "seed": seed,
                "prompt_id": prompt_id,
                "history": result
            })

        print("\nAll candidates completed.")
        print("\n[SUMMARY]")
        print(json.dumps(results, indent=2, ensure_ascii=False))

    except Exception as error:
        print(f"\nError: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()