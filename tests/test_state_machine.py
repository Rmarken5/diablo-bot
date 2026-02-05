"""Tests for the bot state machine."""

import time
from src.state_machine import (
    BotState,
    BotStateMachine,
    StateTransitionError,
    VALID_TRANSITIONS,
)
from src.utils.logger import setup_logger, get_logger


def test_initial_state():
    """Test that state machine starts in IDLE state."""
    log = get_logger()
    log.info("Testing initial state...")

    sm = BotStateMachine()
    assert sm.state == BotState.IDLE
    assert sm.previous_state is None
    assert not sm.is_running

    log.info("PASSED: initial state")
    return True


def test_valid_transition():
    """Test valid state transitions work."""
    log = get_logger()
    log.info("Testing valid transitions...")

    sm = BotStateMachine()

    # IDLE -> STARTING is valid
    assert sm.can_transition_to(BotState.STARTING)
    sm.transition_to(BotState.STARTING)
    assert sm.state == BotState.STARTING
    assert sm.previous_state == BotState.IDLE

    # STARTING -> IN_TOWN is valid
    assert sm.can_transition_to(BotState.IN_TOWN)
    sm.transition_to(BotState.IN_TOWN)
    assert sm.state == BotState.IN_TOWN

    log.info("PASSED: valid transitions")
    return True


def test_invalid_transition():
    """Test that invalid transitions raise error."""
    log = get_logger()
    log.info("Testing invalid transitions...")

    sm = BotStateMachine()

    # IDLE -> IN_TOWN is not valid (must go through STARTING)
    assert not sm.can_transition_to(BotState.IN_TOWN)

    try:
        sm.transition_to(BotState.IN_TOWN)
        assert False, "Should have raised StateTransitionError"
    except StateTransitionError as e:
        assert "Cannot transition" in str(e)

    # State should be unchanged
    assert sm.state == BotState.IDLE

    log.info("PASSED: invalid transitions")
    return True


def test_forced_transition():
    """Test that forced transitions bypass validation."""
    log = get_logger()
    log.info("Testing forced transitions...")

    sm = BotStateMachine()

    # Force an invalid transition
    sm.transition_to(BotState.IN_TOWN, force=True)
    assert sm.state == BotState.IN_TOWN

    log.info("PASSED: forced transitions")
    return True


def test_transition_to_same_state():
    """Test transitioning to current state is no-op."""
    log = get_logger()
    log.info("Testing same-state transition...")

    sm = BotStateMachine()
    sm.transition_to(BotState.STARTING, force=True)

    # Transition to same state should return True but not change previous
    result = sm.transition_to(BotState.STARTING)
    assert result is True
    assert sm.state == BotState.STARTING
    # previous_state should still be from actual transition
    assert sm.previous_state == BotState.IDLE

    log.info("PASSED: same-state transition")
    return True


def test_state_handlers():
    """Test that state handlers are called."""
    log = get_logger()
    log.info("Testing state handlers...")

    sm = BotStateMachine()
    call_log = []

    def starting_handler():
        call_log.append("starting_tick")

    def starting_entry(prev, new):
        call_log.append(f"starting_entry:{prev.name}->{new.name}")

    def starting_exit(old, new):
        call_log.append(f"starting_exit:{old.name}->{new.name}")

    sm.register_handler(
        BotState.STARTING,
        handler=starting_handler,
        on_entry=starting_entry,
        on_exit=starting_exit,
    )

    # Transition to STARTING
    sm.transition_to(BotState.STARTING, force=True)
    assert "starting_entry:IDLE->STARTING" in call_log

    # Update should call handler
    sm.update()
    assert "starting_tick" in call_log

    # Transition away should call exit
    sm.transition_to(BotState.IN_TOWN, force=True)
    assert "starting_exit:STARTING->IN_TOWN" in call_log

    log.info("PASSED: state handlers")
    return True


def test_state_duration():
    """Test state duration tracking."""
    log = get_logger()
    log.info("Testing state duration...")

    sm = BotStateMachine()
    sm.transition_to(BotState.STARTING, force=True)

    # Should have been in state for ~0 seconds
    assert sm.state_duration < 0.1

    # Wait a bit
    time.sleep(0.15)
    assert sm.state_duration >= 0.1

    # Transition resets duration
    sm.transition_to(BotState.IN_TOWN, force=True)
    assert sm.state_duration < 0.1

    log.info("PASSED: state duration")
    return True


def test_start_stop():
    """Test starting and stopping the state machine."""
    log = get_logger()
    log.info("Testing start/stop...")

    sm = BotStateMachine(tick_rate=0.05)
    tick_count = [0]

    def starting_handler():
        tick_count[0] += 1
        if tick_count[0] >= 3:
            sm.transition_to(BotState.IN_TOWN, force=True)

    sm.register_handler(BotState.STARTING, handler=starting_handler)

    # Start
    sm.start()
    assert sm.is_running

    # Wait for some ticks
    time.sleep(0.3)

    # Stop
    sm.stop()
    assert not sm.is_running
    assert sm.state == BotState.IDLE
    assert tick_count[0] >= 3

    log.info(f"Handler called {tick_count[0]} times")
    log.info("PASSED: start/stop")
    return True


def test_synchronous_run():
    """Test synchronous execution for testing."""
    log = get_logger()
    log.info("Testing synchronous run...")

    sm = BotStateMachine()
    tick_count = [0]
    transitions = []

    def starting_handler():
        tick_count[0] += 1
        if tick_count[0] == 2:
            sm.transition_to(BotState.IN_TOWN, force=True)

    def town_handler():
        tick_count[0] += 1
        if tick_count[0] == 4:
            sm.transition_to(BotState.STOPPING, force=True)

    def track_entry(prev, new):
        transitions.append(f"{prev.name}->{new.name}")

    sm.register_handler(BotState.STARTING, starting_handler, on_entry=track_entry)
    sm.register_handler(BotState.IN_TOWN, town_handler, on_entry=track_entry)

    # Run synchronously
    sm.run_synchronously(max_ticks=10)

    assert tick_count[0] >= 4
    assert "IDLE->STARTING" in transitions
    assert "STARTING->IN_TOWN" in transitions

    log.info(f"Transitions: {transitions}")
    log.info("PASSED: synchronous run")
    return True


def test_error_state_on_exception():
    """Test that exceptions in handlers cause ERROR state."""
    log = get_logger()
    log.info("Testing error handling...")

    sm = BotStateMachine()
    error_triggered = [False]

    def bad_handler():
        raise ValueError("Intentional test error")

    def error_entry(prev, new):
        error_triggered[0] = True

    sm.register_handler(BotState.STARTING, bad_handler)
    sm.register_handler(BotState.ERROR, lambda: None, on_entry=error_entry)

    sm.transition_to(BotState.STARTING, force=True)
    sm.update()  # Should trigger error

    assert error_triggered[0], "Should have transitioned to ERROR"
    assert sm.state == BotState.ERROR

    log.info("PASSED: error handling")
    return True


def test_wait_for_state():
    """Test waiting for a specific state."""
    log = get_logger()
    log.info("Testing wait_for_state...")

    sm = BotStateMachine(tick_rate=0.05)
    tick_count = [0]

    def starting_handler():
        tick_count[0] += 1
        if tick_count[0] >= 5:
            sm.transition_to(BotState.IN_TOWN, force=True)

    sm.register_handler(BotState.STARTING, starting_handler)
    sm.start()

    # Wait for IN_TOWN
    reached = sm.wait_for_state(BotState.IN_TOWN, timeout=2.0)
    assert reached, "Should have reached IN_TOWN"
    assert sm.state == BotState.IN_TOWN

    sm.stop()

    log.info("PASSED: wait_for_state")
    return True


def test_all_states_have_transitions():
    """Verify all states have defined transitions."""
    log = get_logger()
    log.info("Testing transition completeness...")

    for state in BotState:
        assert state in VALID_TRANSITIONS, f"Missing transitions for {state.name}"
        transitions = VALID_TRANSITIONS[state]
        assert len(transitions) > 0, f"No transitions from {state.name}"

    log.info(f"All {len(BotState)} states have transitions defined")
    log.info("PASSED: transition completeness")
    return True


def test_stopping_always_reachable():
    """Verify STOPPING can be reached from any state."""
    log = get_logger()
    log.info("Testing STOPPING reachability...")

    for state in BotState:
        if state == BotState.STOPPING:
            continue
        transitions = VALID_TRANSITIONS.get(state, set())
        assert BotState.STOPPING in transitions, (
            f"STOPPING not reachable from {state.name}"
        )

    log.info("PASSED: STOPPING reachability")
    return True


def run_all_tests():
    """Run all state machine tests."""
    setup_logger(level="INFO")
    log = get_logger()

    log.info("=" * 50)
    log.info("State Machine Tests")
    log.info("=" * 50)

    tests = [
        ("Initial State", test_initial_state),
        ("Valid Transitions", test_valid_transition),
        ("Invalid Transitions", test_invalid_transition),
        ("Forced Transitions", test_forced_transition),
        ("Same-State Transition", test_transition_to_same_state),
        ("State Handlers", test_state_handlers),
        ("State Duration", test_state_duration),
        ("Start/Stop", test_start_stop),
        ("Synchronous Run", test_synchronous_run),
        ("Error Handling", test_error_state_on_exception),
        ("Wait For State", test_wait_for_state),
        ("Transition Completeness", test_all_states_have_transitions),
        ("STOPPING Reachability", test_stopping_always_reachable),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            log.info(f"\n--- {name} ---")
            result = test_func()
            if result:
                passed += 1
            else:
                log.error(f"FAILED: {name}")
                failed += 1
        except Exception as e:
            log.error(f"FAILED: {name} - {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    log.info("\n" + "=" * 50)
    log.info(f"Results: {passed} passed, {failed} failed")
    log.info("=" * 50)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
