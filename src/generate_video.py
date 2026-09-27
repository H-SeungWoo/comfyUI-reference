import json
import random
import shutil
import sys
import time
from pathlib import Path

import requests

from prompt_builder import load_shot_spec, build_video_prompt


COMFYUI_BASE_URL = "http://127.0.0.1:8188"
WORKFLOW_PATH = Path("workflows/wan_i2v_workflow_api.json")
COMFYUI_INPUT_DIR = Path("../input")

# Wan API workflow에서 확인한 node id
REFERENCE_IMAGE_NODE_ID = "52"
VIDEO_PROMPT_NODE_ID = "6"
SAVE_VIDEO_NODE_ID = "56"
FRAMES_NODE_ID = "50"
FPS_NODE_ID = "55"
SEED_NODE_ID = "3"

DEFAULT_FRAMES = 49
DEFAULT_FPS = 16


def load_json(path: str) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_workflow(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Workflow file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def stage_reference_for_comfy(selected_reference_path: str) -> str:
    source_path = Path(selected_reference_path)

    if not source_path.exists():
        raise FileNotFoundError(f"Selected reference not found: {selected_reference_path}")

    if not COMFYUI_INPUT_DIR.exists():
        raise FileNotFoundError(f"ComfyUI input directory not found: {COMFYUI_INPUT_DIR}")

    destination_path = COMFYUI_INPUT_DIR / source_path.name
    shutil.copy2(source_path, destination_path)

    return source_path.name

def prepare_video_workflow(
    workflow: dict,
    video_prompt: str,
    reference_path: str,
    shot_id: str,
    frames: int,
    fps: int
) -> tuple[dict, int]:
    workflow_copy = json.loads(json.dumps(workflow))
    seed = random.randint(1, 2**31 - 1)

    # 1. Selected Reference 주입
    workflow_copy[REFERENCE_IMAGE_NODE_ID]["inputs"]["image"] = reference_path

    # 2. Video Prompt 주입
    workflow_copy[VIDEO_PROMPT_NODE_ID]["inputs"]["text"] = video_prompt

    # 3. Frames(length) 주입
    workflow_copy[FRAMES_NODE_ID]["inputs"]["length"] = frames

    # 4. FPS 주입
    workflow_copy[FPS_NODE_ID]["inputs"]["frame_rate"] = fps

    # 5. Seed 주입
    workflow_copy[SEED_NODE_ID]["inputs"]["seed"] = seed

    # 6. Save Video prefix 주입
    # 노드에 따라 key 이름이 다를 수 있으므로 "filename_prefix"를 먼저 가정
    if "filename_prefix" in workflow_copy[SAVE_VIDEO_NODE_ID]["inputs"]:
        workflow_copy[SAVE_VIDEO_NODE_ID]["inputs"]["filename_prefix"] = f"videos/{shot_id}"
    elif "output_path" in workflow_copy[SAVE_VIDEO_NODE_ID]["inputs"]:
        workflow_copy[SAVE_VIDEO_NODE_ID]["inputs"]["output_path"] = f"videos/{shot_id}"
    elif "filename" in workflow_copy[SAVE_VIDEO_NODE_ID]["inputs"]:
        workflow_copy[SAVE_VIDEO_NODE_ID]["inputs"]["filename"] = f"{shot_id}.mp4"

    return workflow_copy, seed


def queue_prompt(workflow: dict) -> str:
    response = requests.post(
        f"{COMFYUI_BASE_URL}/prompt",
        json={"prompt": workflow},
        timeout=30
    )

    if not response.ok:
        print("\n[COMFYUI ERROR]")
        print(response.text)

    response.raise_for_status()

    data = response.json()
    return data["prompt_id"]


def wait_for_completion(prompt_id: str, timeout_sec: int = 1200) -> dict:
    start_time = time.time()

    while time.time() - start_time < timeout_sec:
        response = requests.get(f"{COMFYUI_BASE_URL}/history/{prompt_id}", timeout=30)
        response.raise_for_status()
        data = response.json()

        if prompt_id in data:
            return data[prompt_id]

        time.sleep(2)

    raise TimeoutError(f"Timed out waiting for prompt_id={prompt_id}")


def main():
    if len(sys.argv) != 3:
        print("Usage:")
        print("python src/generate_video.py specs/<shot_spec>.json selections/<selection>.json")
        sys.exit(1)

    spec_path = sys.argv[1]
    selection_path = sys.argv[2]

    try:
        # 1. ShotSpec 읽기
        spec = load_shot_spec(spec_path)

        # 2. Video Prompt 생성
        video_prompt = build_video_prompt(spec)

        # 3. Selection 읽기
        selection = load_json(selection_path)

        shot_id = spec["shot_id"]
        selected_reference_path = selection["selected_reference"]
        reference_path_for_comfy = stage_reference_for_comfy(selected_reference_path)
        # shot_id 일치 체크
        if selection["shot_id"] != shot_id:
            raise ValueError(
                f"Shot ID mismatch: spec={shot_id}, selection={selection['shot_id']}"
            )

        # 4. Workflow 로드
        workflow = load_workflow(WORKFLOW_PATH)

        # 5. Workflow 준비
        prepared_workflow, seed = prepare_video_workflow(
            workflow=workflow,
            video_prompt=video_prompt,
            reference_path=reference_path_for_comfy,
            shot_id=shot_id,
            frames=DEFAULT_FRAMES,
            fps=DEFAULT_FPS
        )

        print(f"\nSHOT ID: {shot_id}")
        print(f"REFERENCE: {reference_path_for_comfy}")
        print(f"SEED: {seed}")
        print(f"FRAMES: {DEFAULT_FRAMES}")
        print(f"FPS: {DEFAULT_FPS}")

        print("\n[VIDEO PROMPT]")
        print(video_prompt)

        print("\nSending Wan I2V workflow to ComfyUI...")
        prompt_id = queue_prompt(prepared_workflow)
        print(f"Prompt queued successfully. prompt_id = {prompt_id}")

        print("Waiting for video generation completion...")
        result = wait_for_completion(prompt_id)

        print("\nVideo generation completed.")
        print("[HISTORY RESULT]")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as error:
        print(f"\nError: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()