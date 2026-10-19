import os
import asyncio
import pytest

# Configure headless offscreen rendering for Qt runner
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QBoxLayout, QLabel
from PySide6.QtCore import Qt
from oppo_control.commands import TouchGesture
from oppo_control.gui import MainWindow, changed_gestures, apply_gesture_changes
from oppo_control.devices import EncoBuds3ProProfile, OnePlusNordBuds3Profile

@pytest.fixture(scope="session")
def q_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_gui_profile_capabilities(q_app):
    """Verify that MainWindow dynamically shows/hides widgets based on profile capabilities."""
    window = MainWindow(auto_connect=False)
    
    try:
        # 1. Enco Buds3 Pro: supports_anc is False
        window._on_profile_detected(EncoBuds3ProProfile)
        assert window.anc_card.isHidden() is True
        assert window.vol_card.isHidden() is False
        
        # 2. OnePlus Nord Buds 3: supports_anc is True
        window._on_profile_detected(OnePlusNordBuds3Profile)
        assert window.anc_card.isHidden() is False
        assert window.vol_card.isHidden() is False
    finally:
        # Clean shutdown of worker thread to avoid "Destroyed while thread is still running" Segfault
        window.worker.stop()
        window.worker.wait()


def test_game_mode_checkbox_forwards_its_actual_checked_state():
    """PySide emits an int for stateChanged, not a Qt.CheckState enum."""
    class MockWidget:
        def setEnabled(self, val):
            pass
        def setText(self, val):
            pass
        def setStyleSheet(self, val):
            pass

    class Worker:
        def __init__(self):
            self.values = []

        def toggle_game_mode(self, enabled):
            self.values.append(enabled)

    class Window:
        is_connected = True
        worker = Worker()
        status_lbl = MockWidget()
        game_mode_cb = MockWidget()

    window = Window()
    MainWindow._on_game_mode_ui_changed(window, Qt.Checked.value)
    MainWindow._on_game_mode_ui_changed(window, Qt.Unchecked.value)

    assert window.worker.values == [True, False]


def test_gui_non_optimistic_state_machine_success(q_app):
    """Verify that GUI controls follow 'Applying...' -> 'Connected' state transitions on success."""
    window = MainWindow(auto_connect=False)
    window.is_connected = True
    
    try:
        # 1. Trigger EQ change: state goes to 'Applying...' and control is disabled
        window._on_eq_ui_changed(1)
        assert window.status_lbl.text() == "Applying..."
        assert window.eq_dropdown.isEnabled() is False
        
        # 2. Worker emits success preset index: state reverts to 'Connected' and control re-enables
        window._on_eq_received(1)
        assert window.status_lbl.text() == "Connected"
        assert window.eq_dropdown.isEnabled() is True
        assert window._confirmed_eq == 1
    finally:
        window.worker.stop()
        window.worker.wait()


def test_gui_non_optimistic_state_machine_failure_rollback(q_app):
    """Verify that GUI controls roll back to last confirmed values and re-enable on write failure."""
    window = MainWindow(auto_connect=False)
    window.is_connected = True
    
    try:
        # Confirm initial state
        window._on_eq_received(0) # confirmed preset index is 0
        
        # Trigger change to 2
        window._on_eq_ui_changed(2)
        assert window.eq_dropdown.isEnabled() is False
        
        # Worker fails and emits error: rollback to confirmed preset index 0
        window._on_worker_error("Connection timeout")
        assert window.status_lbl.text() == "Apply Failed"
        assert window.eq_dropdown.currentIndex() == 0
        assert window.eq_dropdown.isEnabled() is True
    finally:
        window.worker.stop()
        window.worker.wait()


def test_gui_trace_mode_default_synchronization(q_app):
    """Verify default trace mode check state propagates safely to worker and transport."""
    window = MainWindow(auto_connect=False)
    try:
        # Check defaults
        assert window.trace_cb.isChecked() is True
        # Verify worker state is synchronized
        assert window.worker.trace_mode is True
    finally:
        window.worker.stop()
        window.worker.wait()


def test_gui_silhouette_paint_rendering(q_app):
    """Verify SilhouetteWidget renders Left, Right, and Case variants without raising exceptions."""
    from oppo_control.gui import SilhouetteWidget
    left = SilhouetteWidget("left")
    right = SilhouetteWidget("right")
    case = SilhouetteWidget("case")
    
    # Force updates and verify state fields
    left.update_state(True, 85, True)
    assert left.is_connected is True
    assert left.battery_level == 85
    assert left.is_charging is True
    
    # Trigger repaint to verify paintEvent logic
    left.repaint()
    right.repaint()
    case.repaint()


def _gesture():
    return TouchGesture(earbud_id=1, action_type=1, trigger_id=1, function_id=0x01)


def test_changed_gestures_returns_only_edited_records():
    """Apply must not rewrite the full 24-record matrix for one edit."""
    baseline = [
        TouchGesture(1, 1, 1, 0x01),
        TouchGesture(1, 1, 2, 0x05),
    ]
    edited = [
        TouchGesture(1, 1, 1, 0x00),
        TouchGesture(1, 1, 2, 0x05),
    ]
    assert changed_gestures(edited, baseline) == [edited[0]]


def test_gui_apply_gestures_noop_when_unchanged(q_app):
    """An unchanged matrix must not touch the hardware or disable Apply."""
    window = MainWindow(auto_connect=False)
    try:
        window.is_connected = True
        window._gestures = [_gesture()]
        window._gesture_baseline = [_gesture()]
        calls = []
        window.worker.save_gestures = lambda gestures: calls.append(gestures)

        window._on_apply_gestures()

        assert calls == []
        assert window.status_lbl.text() == "No changes"
        assert window.btn_apply_gestures.isEnabled() is True
    finally:
        window.worker.stop()
        window.worker.wait()


def test_gui_gesture_rows_distinguish_basic_and_custom(q_app):
    """The 24-record matrix has two tables; rows must say which one they are."""
    window = MainWindow(auto_connect=False)
    try:
        window._on_gestures_received([
            TouchGesture(1, 1, 1, 0x01),
            TouchGesture(1, 6, 1, 0x00),
        ])
        labels = []
        for i in range(window.scroll_layout.count()):
            widget = window.scroll_layout.itemAt(i).widget()
            if widget:
                labels.extend(label.text() for label in widget.findChildren(QLabel))
        assert "Left · Basic · Single Tap" in labels
        assert "Left · Custom · Single Tap" in labels
    finally:
        window.worker.stop()
        window.worker.wait()


class _FakeGestureDevice:
    def __init__(self, matrix, accept=True):
        self.matrix = [_copy_gesture(g) for g in matrix]
        self.accept = accept
        self.writes = []

    async def set_gestures(self, gestures):
        self.writes.append(list(gestures))
        if not self.accept:
            return
        for change in gestures:
            for i, current in enumerate(self.matrix):
                if _key(current) == _key(change):
                    self.matrix[i] = _copy_gesture(change)

    async def get_gestures(self):
        return [_copy_gesture(g) for g in self.matrix]


class _FailingGestureDevice(_FakeGestureDevice):
    async def set_gestures(self, gestures):
        self.writes.append(list(gestures))
        raise RuntimeError("transport closed")


def _key(g):
    return (g.earbud_id, g.action_type, g.trigger_id)


def _copy_gesture(g):
    return TouchGesture(g.earbud_id, g.action_type, g.trigger_id, g.function_id)


def test_apply_gesture_changes_verifies_accepted_and_ignored_writes():
    """The helper must report a silent no-op instead of claiming success."""
    baseline = [TouchGesture(1, 1, 1, 0x01), TouchGesture(1, 1, 2, 0x05)]
    changed = TouchGesture(1, 1, 1, 0x00)

    accepted = _FakeGestureDevice(baseline, accept=True)
    updated, rejected, failures = asyncio.run(
        apply_gesture_changes(accepted, [changed])
    )
    assert accepted.writes == [[changed]]
    assert failures == []
    assert rejected == []
    assert updated[0].function_id == 0x00

    ignored = _FakeGestureDevice(baseline, accept=False)
    updated, rejected, failures = asyncio.run(
        apply_gesture_changes(ignored, [changed])
    )
    assert ignored.writes == [[changed]]
    assert failures == []
    assert rejected == [changed]
    assert updated[0].function_id == 0x01


def test_apply_gesture_changes_reports_transport_failure():
    baseline = [TouchGesture(1, 1, 1, 0x01)]
    changed = TouchGesture(1, 1, 1, 0x00)
    failed = _FailingGestureDevice(baseline)

    updated, rejected, failures = asyncio.run(
        apply_gesture_changes(failed, [changed])
    )

    assert len(failures) == 1
    assert failures[0][0] == changed
    assert "transport closed" in failures[0][1]
    assert rejected == [changed]
    assert updated[0].function_id == 0x01


def test_gui_apply_gestures_reenables_after_success(q_app):
    """Apply must return to Connected and be reusable after a successful write."""
    window = MainWindow(auto_connect=False)
    try:
        window.is_connected = True
        window._gestures = [_gesture()]
        window.worker.save_gestures = lambda gestures: window._on_gestures_received(gestures)

        window._on_apply_gestures()

        assert window.status_lbl.text() == "Connected"
        assert window.btn_apply_gestures.isEnabled() is True
    finally:
        window.worker.stop()
        window.worker.wait()


def test_gui_apply_gestures_reenables_after_failure(q_app):
    """A failed gesture write must not leave the Apply button stuck disabled."""
    window = MainWindow(auto_connect=False)
    try:
        window.is_connected = True
        window._gestures = [_gesture()]
        window.worker.save_gestures = lambda gestures: None

        window._on_apply_gestures()
        assert window.btn_apply_gestures.isEnabled() is False

        window._on_worker_error("write failed")
        assert window.status_lbl.text() == "Apply Failed"
        assert window.btn_apply_gestures.isEnabled() is True
    finally:
        window.worker.stop()
        window.worker.wait()


def test_gui_dashboard_stretch_resets_when_stacked(q_app):
    """Width stretches from the fullscreen layout must not leak into stacked modes."""
    window = MainWindow(auto_connect=False)
    try:
        window.width = lambda: 1300
        window._apply_layout_mode()
        assert window._dash_body.direction() == QBoxLayout.LeftToRight
        assert (window._dash_body.stretch(0), window._dash_body.stretch(1)) == (3, 2)

        window.width = lambda: 900
        window._apply_layout_mode()
        assert window._dash_body.direction() == QBoxLayout.TopToBottom
        assert (window._dash_body.stretch(0), window._dash_body.stretch(1)) == (0, 0)
    finally:
        window.worker.stop()
        window.worker.wait()


def test_gui_anc_buttons_send_protocol_modes(q_app):
    """UI captions must map to the protocol modes, not to button label text."""
    window = MainWindow(auto_connect=False)
    try:
        window.is_connected = True
        seen = []
        window.worker.set_anc_mode = seen.append

        window._on_anc_changed(window.btn_anc, True)
        window._on_anc_changed(window.btn_anc_off, True)
        window._on_anc_changed(window.btn_transparency, True)

        assert seen == ["on", "off", "transparency"]
    finally:
        window.worker.stop()
        window.worker.wait()
