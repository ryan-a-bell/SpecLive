"""Deterministic transcript perturbations for stress-testing the methodology.

Each transform takes a transcript dict and returns a *new* transcript dict, so a
clean case can be re-scored under noise to measure degradation. Wire these into
``run.py`` (a ``--perturb`` flag) once the clean baseline is trusted; kept here
as the scaffolded stress suite so the transforms live next to the harness.

Transforms are intentionally simple and label-preserving where possible — a
perturbation that moves text also invalidates gold ``turn_index`` evidence, so
those (e.g. reordering) should only be scored on recovery, not traceability.
"""

from __future__ import annotations

import copy
import re

_HOMOPHONES = {
    "their": "there", "shall": "shell", "to": "too", "week": "weak",
    "cloud": "clowd", "edge": "edje", "would": "wood",
}


def _map_turns(transcript: dict, fn) -> dict:
    out = copy.deepcopy(transcript)
    for turn in out["turns"]:
        turn["text"] = fn(turn["text"])
    return out


def stt_noise(transcript: dict) -> dict:
    """Simulate ASR errors: homophone swaps + dropped articles."""

    def _noise(text: str) -> str:
        words = text.split()
        out = []
        for i, w in enumerate(words):
            low = re.sub(r"[^a-z]", "", w.lower())
            if low in _HOMOPHONES and i % 2 == 0:
                out.append(_HOMOPHONES[low])
            elif low in {"a", "an", "the"} and i % 3 == 0:
                continue  # dropped word
            else:
                out.append(w)
        return " ".join(out)

    return _map_turns(transcript, _noise)


def speaker_swap(transcript: dict) -> dict:
    """Flip customer/facilitator labels — attacks any 'customer-only' rule."""
    out = copy.deepcopy(transcript)
    flip = {"customer": "facilitator", "facilitator": "customer"}
    for turn in out["turns"]:
        turn["speaker"] = flip.get(turn["speaker"], turn["speaker"])
    return out


def distractor_padding(transcript: dict) -> dict:
    """Insert off-topic chit-chat turns that should yield no artifacts."""
    out = copy.deepcopy(transcript)
    filler = [
        {"speaker": "facilitator", "text": "How was the drive in this morning?"},
        {"speaker": "customer", "text": "Traffic was fine, thanks. Good coffee here."},
    ]
    out["turns"] = filler + out["turns"] + filler
    return out


TRANSFORMS = {
    "stt_noise": stt_noise,
    "speaker_swap": speaker_swap,
    "distractor_padding": distractor_padding,
}
