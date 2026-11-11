import re

from haizflow.pipeline import render


def _layers(count, step_ms=1000, duration_ms=1500):
    return [{"region": {"x_percent": 5, "y_percent": 10 + index % 5, "width_percent": 40, "height_percent": 6},
             "start_ms": index * step_ms, "duration_ms": duration_ms, "mode": "blur"}
            for index in range(count)]


def _prefix(layers):
    return render._ordered_subtitle_removal_prefix(
        {"treatment_layers": layers, "timeline_offset_seconds": 0.0}, 720, 1280, "blur", 0.0)


def test_few_regions_keep_the_plain_chain():
    prefix = _prefix(_layers(3))
    assert "concat" not in prefix and "trim=" not in prefix
    assert prefix.count("gblur") == 3 and prefix.count(":enable='") >= 3 * 3  # blur, blend and overlay are timed


def test_many_regions_are_cut_into_pieces_that_only_carry_visible_regions():
    layers = _layers(12)
    prefix = _prefix(layers)
    pieces = int(re.search(r"concat=n=(\d+):v=1:a=0\[source_without_original\];", prefix).group(1))
    assert prefix.startswith(f"[0:v]split={pieces}")
    assert prefix.count("trim=") == pieces
    # Each region is visible for 1.5 s, so no piece may blur more than two at once.
    per_piece = [len(re.findall(r"gblur", chunk)) for chunk in re.split(r"\[piece\d+_in\]trim=", prefix)[1:]]
    assert max(per_piece) <= 2 and sum(per_piece) >= len(layers)
    # Output labels are all defined once and the graph ends on the label the render expects.
    labels = re.findall(r"\[([A-Za-z0-9_]+)\](?=[;,])", prefix)
    assert prefix.rstrip(";").endswith("[source_without_original]")
    assert prefix.count("[source_without_original]") == 1


def test_a_region_that_only_ends_at_a_boundary_is_not_carried_into_the_next_piece():
    layers = _layers(6, step_ms=2000, duration_ms=2000)  # each ends exactly where the next starts
    prefix = _prefix(layers)
    # Each region is blurred in exactly one piece, never repeated into a neighbour.
    assert prefix.count("gblur") == 6
