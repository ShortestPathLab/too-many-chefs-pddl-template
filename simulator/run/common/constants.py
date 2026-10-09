VISUAL_STEP_INTERVAL_MS = int(
    1000 / 8 * 5
)  # 8 frames per second, use 5 frames per step.

PLAY_CONTROLS = {
    "title": "Controls",
    "items": [
        {"key": "Arrows", "action": "Turn + move"},
        {"key": "Enter", "action": "Interact"},
        {"key": "Space", "action": "Pick up / place / combine"},
        {"key": ".", "action": "Wait a step"},
    ],
}

AGENT_CONTROLS = {
    "title": "Controls",
    "items": [
        {"key": "Space", "action": "Start / stop"},
    ],
}

REPLAY_CONTROLS = {
    "title": "Controls",
    "items": [
        {"key": "Space", "action": "Play / pause"},
        {"key": "Right", "action": "Step forward"},
        {"key": "Left", "action": "Step back"},
    ],
}

LIVE_CONTROLS = {
    "title": "Controls",
    "items": [
        {"key": "Space", "action": "Pause / follow"},
    ],
}
