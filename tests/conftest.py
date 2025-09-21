# tests/conftest.py
import sys
import types

# Mock playsound so tests don't fail in CI
sys.modules["playsound"] = types.SimpleNamespace(playsound=lambda *a, **k: None)
