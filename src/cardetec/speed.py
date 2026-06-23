from __future__ import annotations

from dataclasses import dataclass, field


Point = tuple[int, int]


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
            return None

        state = self.get_state(track_id)
        crossed_a = crossed_line(previous_center, current_center, self.line_a_start, self.line_a_end)
        crossed_b = crossed_line(previous_center, current_center, self.line_b_start, self.line_b_end)

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
            return None

        state.crossed_lines.add(current_line)
        if state.first_line_name is None:
            state.first_line_name = current_line
            state.first_cross_time = timestamp_sec
            state.first_cross_frame = frame_index
            state.first_cross_position = current_center
            return None

        if state.reported or state.first_line_name != other_line or state.first_cross_time is None:
            return None

        elapsed = timestamp_sec - state.first_cross_time
        if elapsed <= 0:
            return None

        speed_kmh = (self.real_distance_meters / elapsed) * 3.6
        if not (self.min_speed_kmh <= speed_kmh <= self.max_speed_kmh):
            state.reported = True
            return None

        direction = f"{state.first_line_name}->{current_line}"
        state.speed_kmh = speed_kmh
        state.direction = direction
        state.reported = True
        return SpeedEvent(
            track_id=track_id,
            label=label,
            direction=direction,
            speed_kmh=speed_kmh,
            elapsed_seconds=elapsed,
            frame_index=frame_index,
        )
