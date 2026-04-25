# AGENTS.md

## Project-Specific Context

### Running the Project

```bash
# Install dependencies (uses special PyPI indices for PyTorch CUDA)
uv sync

# Run the main entry point
webot

# Run tests (prefix t_ in test/ directory)
pytest test/t_*.py
```

### Key Facts

- **Python**: >=3.12 (required)
- **Build**: hatchling (not setuptools)
- **Package**: `src/webot/` with `skills/` subpackage
- **Entry point**: `webot.main:main`
- **Test discovery**: Files named `t_*.py` in `test/`

### Dependencies

- PyTorch uses CUDA 11.8 index: `https://download.pytorch.org/whl/cu118`
- PaddleOCR: `uv pip install "paddleocr[all]"` + GPU version from paddlepaddle.org.cn

### Windows-Specific

- `pyautogui.FAILSAFE` is enabled by default (move mouse to corner to abort)
- Window management uses `pygetwindow`
- Screenshots via `pyscreeze`

### Skills (src/webot/skills/)

- `click_skill.py`: click_ui_element
- `input_skill.py`: find_and_input_text, clear_text_field
- `window_skill.py`: resize_window, center_window, activate_window, maximize_window
- `scroll_skill.py`: scroll_repeatedly
- `wait_skill.py`: wait_for_user_focus

---

## Coding Guidelines

Adapted from CLAUDE.md - prioritizing caution over speed.

### Think Before Coding

- State assumptions explicitly. Ask if uncertain.
- Present multiple interpretations instead of picking silently.
- Push back if a simpler approach exists.

### Simplicity First

- No features beyond what was asked.
- No abstractions for single-use code.
- If you write 200 lines and it could be 50, rewrite it.

### Surgical Changes

- Touch only what you must.
- Match existing style, even if you'd do it differently.
- Clean up only your own messes (unused imports/variables from YOUR changes).

### Goal-Driven

- Define verifiable success criteria before implementing.
- For multi-step tasks, state a brief plan.