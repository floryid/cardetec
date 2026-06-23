from cardetec.speed import SpeedEstimator, crossed_line


def test_crossed_line_when_point_moves_across_segment() -> None:
    assert crossed_line((10, 10), (10, 30), (0, 20), (100, 20)) is True


def test_speed_estimator_creates_event_after_crossing_two_lines() -> None:
    estimator = SpeedEstimator(
        line_a_start=(0, 20),
        line_a_end=(100, 20),
        line_b_start=(0, 40),
        line_b_end=(100, 40),
        real_distance_meters=10.0,
    )

    assert estimator.update(1, "car", None, (10, 10), 0.0, 1) is None
    assert estimator.update(1, "car", (10, 10), (10, 30), 1.0, 2) is None

    event = estimator.update(1, "car", (10, 30), (10, 50), 2.0, 3)

    assert event is not None
    assert event.track_id == 1
    assert event.direction == "A->B"
    assert round(event.speed_kmh, 2) == 36.0
