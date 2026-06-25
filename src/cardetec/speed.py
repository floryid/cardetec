from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import urllib.request


Point = tuple[int, int]


# #region debug-point shared:speed-debug
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


def _side_of_line(point: Point, start: Point, end: Point) -> float:
    return (end[0] - start[0]) * (point[1] - start[1]) - (end[1] - start[1]) * (point[0] - start[0])


def crossed_line(previous: Point, current: Point, start: Point, end: Point) -> bool:
    prev_side = _side_of_line(previous, start, end)
    curr_side = _side_of_line(current, start, end)
    return prev_side == 0 or curr_side == 0 or (prev_side < 0 < curr_side) or (curr_side < 0 < prev_side)


@dataclass(slots=True)
class SpeedEvent:
    track_id: int
    label: str
    direction: str
    speed_kmh: float
    elapsed_seconds: float
    frame_index: int


@dataclass(slots=True)
class TrackSpeedState:
    first_line_name: str | None = None
    first_cross_time: float | None = None
    first_cross_frame: int | None = None
    first_cross_position: Point | None = None
    speed_kmh: float | None = None
    direction: str | None = None
    reported: bool = False
    crossed_lines: set[str] = field(default_factory=set)


class SpeedEstimator:
    def __init__(
        self,
        line_a_start: Point,
        line_a_end: Point,
        line_b_start: Point,
        line_b_end: Point,
        real_distance_meters: float,
        min_speed_kmh: float = 1.0,
        max_speed_kmh: float = 220.0,
    ) -> None:
        self.line_a_start = line_a_start
        self.line_a_end = line_a_end
        self.line_b_start = line_b_start
        self.line_b_end = line_b_end
        self.real_distance_meters = real_distance_meters
        self.min_speed_kmh = min_speed_kmh
        self.max_speed_kmh = max_speed_kmh
        self._states: dict[int, TrackSpeedState] = {}

    def get_state(self, track_id: int) -> TrackSpeedState:
        return self._states.setdefault(track_id, TrackSpeedState())

    def update(
        self,
        track_id: int,
        label: str,
        previous_center: Point | None,
        current_center: Point,
        timestamp_sec: float,
        frame_index: int,
    ) -> SpeedEvent | None:
        if previous_center is None:
            # #region debug-point B:speed-no-previous-center
            _debug_report(
                "B",
                "speed.py:update",
                "Track belum punya previous_center, update kecepatan dilewati",
                {"track_id": track_id, "label": label, "frame_index": frame_index, "current_center": current_center},
            )
            # #endregion
            return None

        state = self.get_state(track_id)
        crossed_a = crossed_line(previous_center, current_center, self.line_a_start, self.line_a_end)
        crossed_b = crossed_line(previous_center, current_center, self.line_b_start, self.line_b_end)

        if crossed_a or crossed_b:
            # #region debug-point C:speed-crossing-detected
            _debug_report(
                "C",
                "speed.py:update",
                "Track melintasi salah satu garis ukur",
                {
                    "track_id": track_id,
                    "label": label,
                    "frame_index": frame_index,
                    "timestamp_sec": round(timestamp_sec, 4),
                    "previous_center": previous_center,
                    "current_center": current_center,
                    "crossed_a": crossed_a,
                    "crossed_b": crossed_b,
                    "first_line_name": state.first_line_name,
                    "reported": state.reported,
                },
            )
            # #endregion

        if crossed_a:
            event = self._handle_crossing(
                state=state,
                current_line="A",
                other_line="B",
                label=label,
                track_id=track_id,
                timestamp_sec=timestamp_sec,
                frame_index=frame_index,
                current_center=current_center,
            )
            if event is not None:
                return event

        if crossed_b:
            event = self._handle_crossing(
                state=state,
                current_line="B",
                other_line="A",
                label=label,
                track_id=track_id,
                timestamp_sec=timestamp_sec,
                frame_index=frame_index,
                current_center=current_center,
            )
            if event is not None:
                return event

        return None

    def _handle_crossing(
        self,
        *,
        state: TrackSpeedState,
        current_line: str,
        other_line: str,
        label: str,
        track_id: int,
        timestamp_sec: float,
        frame_index: int,
        current_center: Point,
    ) -> SpeedEvent | None:
        if current_line in state.crossed_lines:
            # #region debug-point C:speed-duplicate-crossing
            _debug_report(
                "C",
                "speed.py:_handle_crossing",
                "Crossing garis yang sama diabaikan",
                {"track_id": track_id, "line": current_line, "crossed_lines": sorted(state.crossed_lines)},
            )
            # #endregion
            return None

        state.crossed_lines.add(current_line)
        if state.first_line_name is None:
            state.first_line_name = current_line
            state.first_cross_time = timestamp_sec
            state.first_cross_frame = frame_index
            state.first_cross_position = current_center
            # #region debug-point C:speed-first-line-recorded
            _debug_report(
                "C",
                "speed.py:_handle_crossing",
                "Garis pertama terekam untuk track",
                {
                    "track_id": track_id,
                    "line": current_line,
                    "timestamp_sec": round(timestamp_sec, 4),
                    "frame_index": frame_index,
                    "current_center": current_center,
                },
            )
            # #endregion
            return None

        if state.reported or state.first_line_name != other_line or state.first_cross_time is None:
            # #region debug-point B:speed-invalid-second-cross
            _debug_report(
                "B",
                "speed.py:_handle_crossing",
                "Crossing kedua tidak valid untuk menghasilkan event",
                {
                    "track_id": track_id,
                    "current_line": current_line,
                    "other_line": other_line,
                    "first_line_name": state.first_line_name,
                    "reported": state.reported,
                    "has_first_cross_time": state.first_cross_time is not None,
                },
            )
            # #endregion
            return None

        elapsed = timestamp_sec - state.first_cross_time
        if elapsed <= 0:
            # #region debug-point A:speed-nonpositive-elapsed
            _debug_report(
                "A",
                "speed.py:_handle_crossing",
                "Delta waktu crossing tidak valid",
                {
                    "track_id": track_id,
                    "elapsed_seconds": round(elapsed, 6),
                    "timestamp_sec": round(timestamp_sec, 6),
                    "first_cross_time": round(state.first_cross_time, 6),
                },
            )
            # #endregion
            return None

        speed_kmh = (self.real_distance_meters / elapsed) * 3.6
        if not (self.min_speed_kmh <= speed_kmh <= self.max_speed_kmh):
            state.reported = True
            # #region debug-point A:speed-out-of-range
            _debug_report(
                "A",
                "speed.py:_handle_crossing",
                "Kecepatan hasil crossing keluar dari rentang valid",
                {
                    "track_id": track_id,
                    "speed_kmh": round(speed_kmh, 3),
                    "elapsed_seconds": round(elapsed, 6),
                    "min_speed_kmh": self.min_speed_kmh,
                    "max_speed_kmh": self.max_speed_kmh,
                },
            )
            # #endregion
            return None

        direction = f"{state.first_line_name}->{current_line}"
        state.speed_kmh = speed_kmh
        state.direction = direction
        state.reported = True
        # #region debug-point E:speed-event-created
        _debug_report(
            "E",
            "speed.py:_handle_crossing",
            "Event kecepatan berhasil dibuat",
            {
                "track_id": track_id,
                "label": label,
                "direction": direction,
                "speed_kmh": round(speed_kmh, 3),
                "elapsed_seconds": round(elapsed, 6),
                "frame_index": frame_index,
            },
        )
        # #endregion
        return SpeedEvent(
            track_id=track_id,
            label=label,
            direction=direction,
            speed_kmh=speed_kmh,
            elapsed_seconds=elapsed,
            frame_index=frame_index,
        )
