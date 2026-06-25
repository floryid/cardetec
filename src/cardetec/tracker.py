from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import json
import os
from math import hypot
import urllib.request


@dataclass(slots=True)
class Detection:
    box: tuple[int, int, int, int]
    confidence: float
    class_id: int
    label: str

    @property
    def center(self) -> tuple[int, int]:
        x1, y1, x2, y2 = self.box
        return ((x1 + x2) // 2, (y1 + y2) // 2)


# #region debug-point shared:tracker-debug
def _debug_report(hypothesis_id: str, location: str, msg: str, data: dict | None = None, run_id: str = "pre-fix") -> None:
    data = data or {}
    url = "http://127.0.0.1:7777/event"
    session_id = "camera-speed-realtime"
    try:
        with open(".dbg/camera-speed-realtime.env", encoding="utf-8") as env_file:
            for line in env_file:
                line = line.strip()
                if line.startswith("DEBUG_SERVER_URL="):
                    url = line.split("=", 1)[1]
                elif line.startswith("DEBUG_SESSION_ID="):
                    session_id = line.split("=", 1)[1]
    except OSError:
        pass
    payload = {
        "sessionId": session_id,
        "runId": os.getenv("CARDETEC_DEBUG_RUN_ID", run_id),
        "hypothesisId": hypothesis_id,
        "location": location,
        "msg": f"[DEBUG] {msg}",
        "data": data,
    }
    try:
        urllib.request.urlopen(
            urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            ),
            timeout=0.25,
        ).read()
    except Exception:
        pass


# #endregion


@dataclass(slots=True)
class Track:
    track_id: int
    box: tuple[int, int, int, int]
    label: str
    confidence: float
    center: tuple[int, int]
    previous_center: tuple[int, int] | None = None
    hits: int = 1
    missing_frames: int = 0
    trail: deque[tuple[int, int]] = field(default_factory=deque)

    @property
    def is_confirmed(self) -> bool:
        return self.hits >= 1


class CentroidTracker:
    def __init__(
        self,
        max_distance: float = 90.0,
        max_missing_frames: int = 30,
        min_confirmed_hits: int = 3,
        trail_size: int = 24,
    ) -> None:
        self.max_distance = max_distance
        self.max_missing_frames = max_missing_frames
        self.min_confirmed_hits = min_confirmed_hits
        self.trail_size = trail_size
        self._next_track_id = 1
        self._tracks: dict[int, Track] = {}

    def update(self, detections: list[Detection]) -> list[Track]:
        unmatched_track_ids = set(self._tracks.keys())
        unmatched_detection_indices = set(range(len(detections)))
        pairs: list[tuple[float, int, int]] = []

        for track_id, track in self._tracks.items():
            for detection_index, detection in enumerate(detections):
                if detection.label != track.label:
                    continue
                distance = hypot(detection.center[0] - track.center[0], detection.center[1] - track.center[1])
                pairs.append((distance, track_id, detection_index))

        pairs.sort(key=lambda item: item[0])
        for distance, track_id, detection_index in pairs:
            if distance > self.max_distance:
                continue
            if track_id not in unmatched_track_ids or detection_index not in unmatched_detection_indices:
                continue
            self._apply_match(track_id, detections[detection_index])
            unmatched_track_ids.remove(track_id)
            unmatched_detection_indices.remove(detection_index)

        for detection_index in unmatched_detection_indices:
            self._create_track(detections[detection_index])

        for track_id in list(unmatched_track_ids):
            track = self._tracks[track_id]
            track.missing_frames += 1
            if track.missing_frames > self.max_missing_frames:
                # #region debug-point B:tracker-dropped-track
                _debug_report(
                    "B",
                    "tracker.py:update",
                    "Track dihapus karena terlalu lama hilang",
                    {
                        "track_id": track_id,
                        "label": track.label,
                        "hits": track.hits,
                        "missing_frames": track.missing_frames,
                    },
                )
                # #endregion
                del self._tracks[track_id]

        confirmed_tracks = [
            track
            for track in self._tracks.values()
            if track.hits >= self.min_confirmed_hits and track.missing_frames == 0
        ]
        if detections or confirmed_tracks:
            # #region debug-point B:tracker-frame-summary
            _debug_report(
                "B",
                "tracker.py:update",
                "Ringkasan tracker per frame",
                {
                    "detections": len(detections),
                    "total_tracks": len(self._tracks),
                    "confirmed_tracks": len(confirmed_tracks),
                    "min_confirmed_hits": self.min_confirmed_hits,
                },
            )
            # #endregion
        return confirmed_tracks

    def _apply_match(self, track_id: int, detection: Detection) -> None:
        track = self._tracks[track_id]
        previous_center = track.center
        track.previous_center = track.center
        track.center = detection.center
        track.box = detection.box
        track.confidence = detection.confidence
        track.label = detection.label
        track.hits += 1
        track.missing_frames = 0
        track.trail.append(track.center)
        if len(track.trail) > self.trail_size:
            track.trail.popleft()
        # #region debug-point B:tracker-match
        _debug_report(
            "B",
            "tracker.py:_apply_match",
            "Detection dipasangkan ke track yang ada",
            {
                "track_id": track_id,
                "label": detection.label,
                "previous_center": previous_center,
                "current_center": detection.center,
                "hits": track.hits,
                "confidence": round(detection.confidence, 4),
            },
        )
        # #endregion

    def _create_track(self, detection: Detection) -> None:
        track = Track(
            track_id=self._next_track_id,
            box=detection.box,
            label=detection.label,
            confidence=detection.confidence,
            center=detection.center,
            trail=deque([detection.center], maxlen=self.trail_size),
        )
        self._tracks[self._next_track_id] = track
        # #region debug-point B:tracker-create
        _debug_report(
            "B",
            "tracker.py:_create_track",
            "Track baru dibuat dari detection",
            {
                "track_id": self._next_track_id,
                "label": detection.label,
                "center": detection.center,
                "confidence": round(detection.confidence, 4),
            },
        )
        # #endregion
        self._next_track_id += 1

    def all_tracks(self) -> list[Track]:
        return list(self._tracks.values())
