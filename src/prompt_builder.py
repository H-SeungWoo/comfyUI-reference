import json
import sys
from pathlib import Path


def load_shot_spec(file_path: str) -> dict:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"ShotSpec file not found: {file_path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_image_prompt(spec: dict) -> str:
    character = spec["character"]
    environment = spec["environment"]
    composition = spec["composition"]
    lighting = spec["lighting"]
    mood = spec["mood"]

    blocks = []

    # Subject / Character
    blocks.append(f"Subject: {character['subject']}.")
    blocks.append(f"Action: {character['action']}.")
    blocks.append(f"Orientation: {character['facing']}.")

    # Environment
    environment_parts = [
        environment["location"],
        environment["time"]
    ]

    if "weather" in environment:
        environment_parts.append(environment["weather"])

    blocks.append("Environment: " + ", ".join(environment_parts) + ".")

    # Composition
    composition_parts = [
        composition["shot_size"],
        composition["camera_view"],
        f"subject positioned {composition['subject_position']}",
        composition["perspective"]
    ]

    if "vanishing_point" in composition:
        composition_parts.append(
            f"{composition['vanishing_point']} vanishing point"
        )

    if composition.get("leading_lines"):
        composition_parts.append("strong leading lines")

    blocks.append("Composition: " + ", ".join(composition_parts) + ".")

    # Environment details
    if environment.get("details"):
        blocks.append(
            "Environment details: "
            + ", ".join(environment["details"])
            + "."
        )

    # Lighting
    lighting_parts = [lighting["type"]]

    if lighting.get("details"):
        lighting_parts.extend(lighting["details"])

    blocks.append("Lighting: " + ", ".join(lighting_parts) + ".")

    # Mood
    blocks.append("Mood: " + ", ".join(mood) + ".")

    return " ".join(blocks)

def build_video_prompt(spec: dict) -> str:
    motion = spec["motion"]

    speed_map = {
        "very_slow": "very slow movement",
        "slow": "slow movement",
        "moderate": "moderate movement",
        "fast": "fast movement"
    }

    stability_map = {
        "low": "allow noticeable scene movement",
        "medium": "maintain moderate scene stability",
        "high": "maintain high scene stability"
    }

    composition_map = {
        "low": "composition may change naturally",
        "medium": "mostly preserve the original composition",
        "high": "preserve the original composition"
    }

    parts = [
        motion["subject_motion"],
        motion["camera_motion"],
        speed_map[motion["speed"]],
        stability_map[motion["scene_stability"]],
        composition_map[motion["composition_preservation"]]
    ]

    return ", ".join(parts)


def main():
    if len(sys.argv) != 2:
        print("Usage:")
        print("python src/prompt_builder.py specs/<shot_spec>.json")
        sys.exit(1)

    spec_path = sys.argv[1]

    try:
        spec = load_shot_spec(spec_path)

        image_prompt = build_image_prompt(spec)
        video_prompt = build_video_prompt(spec)

        print(f"\nSHOT ID: {spec['shot_id']}")

        print("\n[IMAGE PROMPT]")
        print(image_prompt)

        print("\n[VIDEO PROMPT]")
        print(video_prompt)

    except (FileNotFoundError, json.JSONDecodeError, KeyError) as error:
        print(f"\nError: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()