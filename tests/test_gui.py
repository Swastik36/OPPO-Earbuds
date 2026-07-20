import os
import pytest

# Configure headless offscreen rendering for Qt runner
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from oppo_control.gui import MainWindow
from oppo_control.devices import EncoBuds3ProProfile, OnePlusNordBuds3Profile

@pytest.fixture(scope="session")
def q_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_gui_profile_capabilities(q_app):
    """Verify that MainWindow dynamically shows/hides widgets based on profile capabilities."""
    window = MainWindow()
    
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
    window = MainWindow()
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
    window = MainWindow()
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
    window = MainWindow()
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
