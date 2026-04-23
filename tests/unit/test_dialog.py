"""Tests for Dialog component."""

import pytest

from pyxflow.components import Dialog, Button, Span
from pyxflow.core.state_tree import StateTree
from pyxflow.core.state_node import Feature


class TestDialog:
    """Test Dialog component."""

    @pytest.fixture
    def tree(self):
        return StateTree()

    def test_create_dialog(self):
        """Dialog can be created."""
        dialog = Dialog()
        assert dialog.is_opened() is False
        assert dialog.is_modal() is True
        assert dialog.is_draggable() is False
        assert dialog.is_resizable() is False

    def test_dialog_tag(self):
        """Dialog has correct tag."""
        dialog = Dialog()
        assert dialog._tag == "vaadin-dialog"

    def test_open_close(self, tree):
        """open() and close() work correctly."""
        dialog = Dialog()
        dialog._attach(tree)

        dialog.open()
        assert dialog.is_opened() is True

        dialog.close()
        assert dialog.is_opened() is False

    def test_set_opened(self, tree):
        """set_opened works correctly."""
        dialog = Dialog()
        dialog._attach(tree)

        dialog.set_opened(True)
        assert dialog.is_opened() is True

        dialog.set_opened(False)
        assert dialog.is_opened() is False

    def test_set_modal(self, tree):
        """set_modal sets modeless property (inverted)."""
        dialog = Dialog()
        dialog._attach(tree)

        dialog.set_modal(False)
        assert dialog.is_modal() is False

        dialog.set_modal(True)
        assert dialog.is_modal() is True

    def test_set_draggable(self, tree):
        """set_draggable works correctly."""
        dialog = Dialog()
        dialog._attach(tree)

        dialog.set_draggable(True)
        assert dialog.is_draggable() is True

        dialog.set_draggable(False)
        assert dialog.is_draggable() is False

    def test_set_resizable(self, tree):
        """set_resizable works correctly."""
        dialog = Dialog()
        dialog._attach(tree)

        dialog.set_resizable(True)
        assert dialog.is_resizable() is True

        dialog.set_resizable(False)
        assert dialog.is_resizable() is False

    def test_set_header_title(self, tree):
        """set_header_title works correctly."""
        dialog = Dialog()
        dialog._attach(tree)

        dialog.set_header_title("My Dialog")
        assert dialog.get_header_title() == "My Dialog"

    def test_header_title_in_constructor(self, tree):
        """Header title can be set before attach."""
        dialog = Dialog()
        dialog.set_header_title("Test Title")
        dialog._attach(tree)

        assert dialog.get_header_title() == "Test Title"

    def test_set_width_height(self, tree):
        """set_width and set_height use element properties (not CSS vars)."""
        dialog = Dialog()
        dialog._attach(tree)

        dialog.set_width("400px")
        dialog.set_height("300px")

        props = dialog.element.node._features[1]
        assert props["width"] == "400px"
        assert props["height"] == "300px"
        assert dialog.get_width() == "400px"
        assert dialog.get_height() == "300px"

    def test_set_width_height_before_attach(self, tree):
        """Width/height set before attach are applied on attach."""
        dialog = Dialog()
        dialog.set_width("500px")
        dialog.set_height("400px")
        dialog._attach(tree)

        props = dialog.element.node._features[1]
        assert props["width"] == "500px"
        assert props["height"] == "400px"

    def test_set_min_max_dimensions(self, tree):
        """Min/max width/height use execute_js on overlay."""
        dialog = Dialog()
        dialog._attach(tree)

        dialog.set_min_width("200px")
        dialog.set_max_width("800px")
        dialog.set_min_height("100px")
        dialog.set_max_height("600px")

        # Values are stored for re-application
        assert dialog._min_width == "200px"
        assert dialog._max_width == "800px"
        assert dialog._min_height == "100px"
        assert dialog._max_height == "600px"

    def test_set_min_max_before_attach(self, tree):
        """Min/max dimensions set before attach are applied on attach."""
        dialog = Dialog()
        dialog.set_min_width("200px")
        dialog.set_max_width("800px")
        dialog._attach(tree)

        assert dialog._min_width == "200px"
        assert dialog._max_width == "800px"

    def test_add_children_before_attach(self, tree):
        """Children can be added before attach."""
        dialog = Dialog()
        span = Span("Hello")
        dialog.add(span)

        dialog._attach(tree)

        # Dialog should have the span in its children
        assert len(dialog._children) == 1

    def test_add_children_after_attach(self, tree):
        """Children can be added after attach."""
        dialog = Dialog()
        dialog._attach(tree)

        span = Span("Hello")
        dialog.add(span)

        assert len(dialog._children) == 1

    def test_open_listener(self, tree):
        """Open listener is called when dialog opens."""
        dialog = Dialog()
        dialog._attach(tree)

        events_received = []

        def on_open(event):
            events_received.append(("open", event))

        dialog.add_open_listener(on_open)

        # Open the dialog (server-initiated) - fires open listeners
        dialog.open()

        assert len(events_received) == 1
        assert events_received[0][0] == "open"

    def test_close_listener(self, tree):
        """Close listener is called when user closes the dialog."""
        dialog = Dialog()
        dialog._attach(tree)

        # Open the dialog first
        dialog.open()
        # Simulate the echo from client (consumed by pending flag)
        dialog._handle_opened_changed({})

        events_received = []

        def on_close(event):
            events_received.append(("close", event))

        dialog.add_close_listener(on_close)

        # Simulate user closing the dialog (client sends handleClientClose RPC)
        dialog.handle_client_close()

        assert len(events_received) == 1
        assert events_received[0][0] == "close"

    def test_sync_property(self, tree):
        """_sync_property updates internal state."""
        dialog = Dialog()
        dialog._attach(tree)

        dialog._sync_property("opened", True)
        assert dialog.is_opened() is True

    def test_attach_sets_virtual_child_node_ids(self, tree):
        """Attach sets virtualChildNodeIds property for renderer."""
        dialog = Dialog()
        span = Span("Content")
        dialog.add(span)
        dialog._attach(tree)

        # Dialog should have virtualChildNodeIds property set
        changes = tree.collect_changes()
        virtual_ids_change = next(
            (c for c in changes if c.get("key") == "virtualChildNodeIds"),
            None
        )
        assert virtual_ids_change is not None

    def test_initial_properties_set_on_attach(self, tree):
        """Initial properties are set on attach."""
        dialog = Dialog()
        dialog.set_header_title("Test")
        dialog._attach(tree)

        changes = tree.collect_changes()

        # Find headerTitle property change
        title_change = next(
            (c for c in changes if c.get("key") == "headerTitle" and c.get("value") == "Test"),
            None
        )
        assert title_change is not None


class TestDialogAutoAdd:
    """Test Dialog auto-add to UI behavior."""

    @pytest.fixture
    def tree(self):
        return StateTree()

    def test_open_auto_attaches_to_container(self, tree):
        """open() auto-attaches dialog to container node when not manually added."""
        from pyxflow.components.notification import _set_current_tree
        # Create body (node 1) and container (node 2)
        tree.create_node()  # node 1 = body
        tree.create_node()  # node 2 = container
        tree._container_node_id = 2

        dialog = Dialog()
        dialog.add(Span("Hello"))
        assert dialog._element is None

        _set_current_tree(tree)
        try:
            dialog.open()
        finally:
            _set_current_tree(None)

        assert dialog._element is not None
        assert dialog._auto_added is True
        assert dialog.is_opened() is True
        # Should be child of container node
        container = tree.get_node(2)
        assert dialog.element.node in container._children

    def test_close_auto_removes_from_container(self, tree):
        """close() auto-removes dialog from container (matching Java's OverlayAutoAddController)."""
        from pyxflow.components.notification import _set_current_tree
        tree.create_node()  # node 1 = body
        tree.create_node()  # node 2 = container
        tree._container_node_id = 2

        dialog = Dialog()
        _set_current_tree(tree)
        try:
            dialog.open()
        finally:
            _set_current_tree(None)

        assert dialog._auto_added is True
        container = tree.get_node(2)
        assert dialog.element.node in container._children

        dialog.close()
        # Node removed from container on close
        assert dialog.element.node not in container._children
        assert dialog.element.node._parent is None

    def test_reopen_after_close(self, tree):
        """Auto-added dialog can be reopened after being closed."""
        from pyxflow.components.notification import _set_current_tree
        tree.create_node()  # node 1 = body
        tree.create_node()  # node 2 = container
        tree._container_node_id = 2

        dialog = Dialog()
        dialog.add(Span("Hello"))
        _set_current_tree(tree)
        try:
            dialog.open()
            assert dialog.is_opened() is True
            container = tree.get_node(2)
            assert dialog.element.node in container._children

            dialog.close()
            assert dialog.is_opened() is False
            # Auto-removed from container
            assert dialog.element.node not in container._children

            # Reopen -- re-adds to container
            dialog.open()
            assert dialog.is_opened() is True
            assert dialog.element.node in container._children
            # Property must be True on the element
            props = dialog.element.node._features.get(1, {})
            assert props.get("opened") is True
        finally:
            _set_current_tree(None)

    def test_manually_added_dialog_not_auto_removed(self, tree):
        """Manually added dialogs are not auto-removed on close."""
        dialog = Dialog()
        dialog._attach(tree)
        # Simulate being added to a parent
        body = tree.create_node()
        body.add_child(dialog.element.node)

        dialog.open()
        assert dialog._auto_added is False

        dialog.close()
        # Should still be a child (not auto-removed)
        assert dialog.element.node in body._children


class TestDialogAutoAddUiPropagation:
    """Test that _ui is propagated in auto-add paths."""

    def test_auto_add_propagates_ui_to_dialog(self):
        """Auto-added dialog receives _ui from the tree."""
        from pyxflow.components.notification import _set_current_tree
        from pyxflow.core.component import UI
        tree = StateTree()
        ui = UI(tree)
        tree.create_node()  # node 1 = body
        tree.create_node()  # node 2 = container
        tree._container_node_id = 2

        dialog = Dialog()
        assert dialog._ui is None

        _set_current_tree(tree)
        try:
            dialog.open()
        finally:
            _set_current_tree(None)

        assert dialog._ui is ui

    def test_auto_add_propagates_ui_to_children(self):
        """Children added to dialog before open() get _ui propagated."""
        from pyxflow.components.notification import _set_current_tree
        from pyxflow.core.component import UI
        tree = StateTree()
        ui = UI(tree)
        tree.create_node()  # node 1 = body
        tree.create_node()  # node 2 = container
        tree._container_node_id = 2

        dialog = Dialog()
        child = Span("Hello")
        dialog.add(child)

        _set_current_tree(tree)
        try:
            dialog.open()
        finally:
            _set_current_tree(None)

        assert child._ui is ui

    def test_add_after_auto_open_propagates_ui(self):
        """Children added after auto-add open() get _ui propagated."""
        from pyxflow.components.notification import _set_current_tree
        from pyxflow.core.component import UI
        tree = StateTree()
        ui = UI(tree)
        tree.create_node()  # node 1 = body
        tree.create_node()  # node 2 = container
        tree._container_node_id = 2

        dialog = Dialog()
        _set_current_tree(tree)
        try:
            dialog.open()
        finally:
            _set_current_tree(None)

        child = Button("OK")
        dialog.add(child)
        assert child._ui is ui

    def test_header_footer_children_get_ui(self):
        """Header/footer section children get _ui from dialog."""
        from pyxflow.components.notification import _set_current_tree
        from pyxflow.core.component import UI
        tree = StateTree()
        ui = UI(tree)
        tree.create_node()  # node 1 = body
        tree.create_node()  # node 2 = container
        tree._container_node_id = 2

        dialog = Dialog()
        header_btn = Button("Close")
        footer_btn = Button("OK")
        dialog.get_header().add(header_btn)
        dialog.get_footer().add(footer_btn)

        _set_current_tree(tree)
        try:
            dialog.open()
        finally:
            _set_current_tree(None)

        assert header_btn._ui is ui
        assert footer_btn._ui is ui


class TestDialogClientCloseRace:
    """Test the Dialog client close race condition fix.

    When the client closes a dialog (ESC or click outside), the RPC batch
    contains both opened-changed event and handleClientClose publishedEventHandler.
    Due to two-pass processing (mSync first, then events/published), the node
    must remain attached when handleClientClose runs.
    """

    @pytest.fixture
    def tree(self):
        return StateTree()

    def _setup_auto_dialog(self, tree):
        """Create and open an auto-added dialog."""
        from pyxflow.components.notification import _set_current_tree
        tree.create_node()  # node 1 = body
        tree.create_node()  # node 2 = container
        tree._container_node_id = 2

        dialog = Dialog()
        dialog.add(Span("Hello"))
        _set_current_tree(tree)
        dialog.open()
        _set_current_tree(None)
        tree.collect_changes()
        return dialog

    def test_handle_client_close_without_msync(self, tree):
        """handleClientClose works when no mSync precedes it."""
        dialog = self._setup_auto_dialog(tree)
        events = []
        dialog.add_close_listener(lambda e: events.append("close"))

        # Simulate client close: opened-changed event, then handleClientClose
        dialog._handle_opened_changed({})
        dialog.handle_client_close()

        assert not dialog.is_opened()
        assert len(events) == 1
        # Node should be auto-removed
        container = tree.get_node(2)
        assert dialog.element.node not in container._children

    def test_handle_client_close_with_msync_first(self, tree):
        """handleClientClose works when mSync already set opened=False."""
        dialog = self._setup_auto_dialog(tree)
        events = []
        dialog.add_close_listener(lambda e: events.append("close"))

        # Simulate two-pass: mSync sets opened=false (pass 1)
        dialog._sync_property("opened", False)
        assert dialog._close_pending is True
        # Then opened-changed event (pass 2)
        dialog._handle_opened_changed({})
        # Then handleClientClose (pass 2)
        dialog.handle_client_close()

        assert not dialog.is_opened()
        assert len(events) == 1
        # Node should be auto-removed
        container = tree.get_node(2)
        assert dialog.element.node not in container._children

    def test_node_stays_attached_for_handle_client_close(self, tree):
        """The node must remain attached when handleClientClose processes."""
        dialog = self._setup_auto_dialog(tree)
        container = tree.get_node(2)

        # After opened-changed, node should still be in the tree
        dialog._handle_opened_changed({})
        assert dialog.element.node in container._children
        assert dialog.element.node.is_attached

        # handleClientClose can run successfully
        dialog.handle_client_close()
        assert dialog.element.node not in container._children

    def test_server_close_echo_ignored(self, tree):
        """Server-initiated close followed by client echo does not double-fire."""
        dialog = self._setup_auto_dialog(tree)
        events = []
        dialog.add_close_listener(lambda e: events.append("close"))

        # Server closes
        dialog.close()
        assert len(events) == 0  # close() doesn't fire close listeners

        # Client echo: mSync + opened-changed + handleClientClose
        dialog._sync_property("opened", False)
        dialog._handle_opened_changed({})  # absorbed by _pending_server_change
        dialog.handle_client_close()

        # No additional close listener calls
        assert len(events) == 0

    def test_reopen_after_client_close(self, tree):
        """Dialog can be reopened after client-initiated close."""
        from pyxflow.components.notification import _set_current_tree
        dialog = self._setup_auto_dialog(tree)
        container = tree.get_node(2)

        # Client close
        dialog.handle_client_close()
        assert not dialog.is_opened()
        assert dialog.element.node not in container._children

        # Reopen
        _set_current_tree(tree)
        dialog.open()
        _set_current_tree(None)
        assert dialog.is_opened()
        assert dialog._close_pending is False
        assert dialog.element.node in container._children

    def test_close_pending_reset_on_open(self, tree):
        """_close_pending is reset when dialog reopens."""
        dialog = self._setup_auto_dialog(tree)
        from pyxflow.components.notification import _set_current_tree

        # mSync sets close_pending
        dialog._sync_property("opened", False)
        assert dialog._close_pending is True

        # But then server reopens before handleClientClose arrives
        _set_current_tree(tree)
        dialog.open()
        _set_current_tree(None)
        assert dialog._close_pending is False
        assert dialog.is_opened()


class TestDialogResizeListener:
    """Tests for Dialog.add_resize_listener."""

    @pytest.fixture
    def tree(self):
        return StateTree()

    def test_add_resize_listener_registers_event(self, tree):
        """add_resize_listener should register a 'resize' event on the element."""
        dialog = Dialog()
        dialog._attach(tree)
        tree.collect_changes()  # clear initial changes

        dialog.add_resize_listener(lambda e: None)

        changes = tree.collect_changes()
        resize_listener = [c for c in changes
                           if c.get("key") == "resize"
                           and c.get("feat") == Feature.ELEMENT_LISTENER_MAP]
        assert len(resize_listener) == 1

    def test_resize_listener_called_on_event(self, tree):
        """Simulating a resize event should call the registered listener."""
        dialog = Dialog()
        dialog._attach(tree)

        events = []
        dialog.add_resize_listener(lambda e: events.append(e))

        dialog._handle_resize({"width": "500px", "height": "300px"})
        assert len(events) == 1
        assert events[0]["width"] == "500px"

    def test_multiple_resize_listeners(self, tree):
        """Multiple resize listeners should all be called."""
        dialog = Dialog()
        dialog._attach(tree)

        events1 = []
        events2 = []
        dialog.add_resize_listener(lambda e: events1.append(e))
        dialog.add_resize_listener(lambda e: events2.append(e))

        dialog._handle_resize({"width": "400px"})
        assert len(events1) == 1
        assert len(events2) == 1

    def test_resize_event_registered_only_once(self, tree):
        """Adding multiple resize listeners should only register one event listener."""
        dialog = Dialog()
        dialog._attach(tree)
        tree.collect_changes()  # clear initial

        dialog.add_resize_listener(lambda e: None)
        dialog.add_resize_listener(lambda e: None)

        changes = tree.collect_changes()
        resize_listeners = [c for c in changes
                            if c.get("key") == "resize"
                            and c.get("feat") == Feature.ELEMENT_LISTENER_MAP]
        # Only one registration (lazy: first listener triggers it)
        assert len(resize_listeners) == 1


class TestDialogDraggedListener:
    """Tests for Dialog.add_dragged_listener."""

    @pytest.fixture
    def tree(self):
        return StateTree()

    def test_add_dragged_listener_registers_event(self, tree):
        """add_dragged_listener should register a 'dragged' event on the element."""
        dialog = Dialog()
        dialog._attach(tree)
        tree.collect_changes()  # clear initial changes

        dialog.add_dragged_listener(lambda e: None)

        changes = tree.collect_changes()
        dragged_listener = [c for c in changes
                            if c.get("key") == "dragged"
                            and c.get("feat") == Feature.ELEMENT_LISTENER_MAP]
        assert len(dragged_listener) == 1

    def test_dragged_listener_called_on_event(self, tree):
        """Simulating a dragged event should call the registered listener."""
        dialog = Dialog()
        dialog._attach(tree)

        events = []
        dialog.add_dragged_listener(lambda e: events.append(e))

        dialog._handle_dragged({"top": "100px", "left": "200px"})
        assert len(events) == 1
        assert events[0]["top"] == "100px"

    def test_multiple_dragged_listeners(self, tree):
        """Multiple dragged listeners should all be called."""
        dialog = Dialog()
        dialog._attach(tree)

        events1 = []
        events2 = []
        dialog.add_dragged_listener(lambda e: events1.append(e))
        dialog.add_dragged_listener(lambda e: events2.append(e))

        dialog._handle_dragged({"top": "50px"})
        assert len(events1) == 1
        assert len(events2) == 1

    def test_dragged_event_registered_only_once(self, tree):
        """Adding multiple dragged listeners should only register one event listener."""
        dialog = Dialog()
        dialog._attach(tree)
        tree.collect_changes()  # clear initial

        dialog.add_dragged_listener(lambda e: None)
        dialog.add_dragged_listener(lambda e: None)

        changes = tree.collect_changes()
        dragged_listeners = [c for c in changes
                             if c.get("key") == "dragged"
                             and c.get("feat") == Feature.ELEMENT_LISTENER_MAP]
        assert len(dragged_listeners) == 1
