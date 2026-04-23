"""Dialog component."""

from typing import Callable, TYPE_CHECKING

from pyxflow.core.component import Component
from pyxflow.core.state_node import Feature
from pyxflow.components.constants import DialogVariant

if TYPE_CHECKING:
    from pyxflow.core.state_tree import StateTree


class _DialogSection:
    """Internal container for dialog header or footer slot."""

    def __init__(self, dialog: "Dialog", slot_name: str):
        self._dialog = dialog
        self._slot_name = slot_name
        self._children: list[Component] = []

    def add(self, *components: Component):
        """Add components to this section."""
        for component in components:
            self._children.append(component)
            if self._dialog._element:
                self._attach_child(component)

    def _attach_child(self, component: Component):
        """Attach a single child to the dialog with the correct slot."""
        tree = self._dialog._element._tree
        component._ui = self._dialog._ui
        component._parent = self._dialog
        component._attach(tree)
        component.element.set_attribute("slot", self._slot_name)
        self._dialog.element.node.add_child(component.element.node)
        self._dialog._update_virtual_child_node_ids()

    def remove_all(self):
        """Remove all components from this section."""
        if self._dialog._element:
            for child in self._children:
                if child._element:
                    self._dialog.element.node.remove_child(child.element.node)
        for child in self._children:
            child._parent = None
        self._children.clear()
        if self._dialog._element:
            self._dialog._update_virtual_child_node_ids()


class Dialog(Component):
    """A dialog overlay component.

    Dialog is a small window that can be used to present information
    and user interface elements in an overlay.

    The dialog content is rendered using FlowComponentHost which requires
    the flow-component-renderer.js to be in the bundle.
    """

    _v_fqcn = "com.vaadin.flow.component.dialog.Dialog"
    _tag = "vaadin-dialog"
    _v_sync_properties = frozenset({"opened"})
    _v_disabled_sync = frozenset({"opened"})
    _v_disabled_methods = frozenset({"handle_client_close"})

    def __init__(self):
        super().__init__()
        self._opened = False
        self._pending_server_change = False
        self._modal = True
        self._draggable = False
        self._resizable = False
        self._header_title = ""
        self._width = None
        self._height = None
        self._min_width = None
        self._max_width = None
        self._min_height = None
        self._max_height = None
        self._close_on_esc = True
        self._close_on_outside_click = True
        self._children: list[Component] = []
        self._header_section = _DialogSection(self, "header")
        self._footer_section = _DialogSection(self, "footer")
        self._open_listeners: list[Callable] = []
        self._close_listeners: list[Callable] = []
        self._auto_added = False
        self._close_pending = False

    def _attach(self, tree: "StateTree"):
        super()._attach(tree)

        # Set initial properties
        self.element.set_property("modeless", not self._modal)
        self.element.set_property("draggable", self._draggable)
        self.element.set_property("resizable", self._resizable)
        if self._header_title:
            self.element.set_property("headerTitle", self._header_title)
        if not self._close_on_esc:
            self.element.set_property("closeOnEsc", False)
        if not self._close_on_outside_click:
            self.element.set_property("closeOnOutsideClick", False)
        if self._width:
            self.element.set_property("width", self._width)
        if self._height:
            self.element.set_property("height", self._height)

        # Re-apply min/max dimensions on overlay (must be after attach)
        if self._min_width:
            self._set_overlay_dimension("min-width", self._min_width)
        if self._max_width:
            self._set_overlay_dimension("max-width", self._max_width)
        if self._min_height:
            self._set_overlay_dimension("min-height", self._min_height)
        if self._max_height:
            self._set_overlay_dimension("max-height", self._max_height)

        # Attach children as regular children of the dialog element
        # (not virtual children - the renderer handles placing them in the overlay)
        for child in self._children:
            child._attach(tree)
            self.element.node.add_child(child.element.node)

        # Attach header/footer section children
        for child in self._header_section._children:
            self._header_section._attach_child(child)
        for child in self._footer_section._children:
            self._footer_section._attach_child(child)

        # Update virtualChildNodeIds property
        self._update_virtual_child_node_ids()

        # Register opened-changed listener (absorbs echoes from server-initiated changes)
        self.element.add_event_listener("opened-changed", self._handle_opened_changed)

        # Register handleClientClose as a client-callable method (feature 19).
        # FlowClient creates $server proxy with this method on the dialog element.
        self._register_server_method("handle_client_close")
        tree.add_change({
            "node": self.element.node_id,
            "type": "splice",
            "feat": Feature.CLIENT_DELEGATE_HANDLERS,
            "index": 0,
            "add": ["handleClientClose"]
        })

    def _update_virtual_child_node_ids(self):
        """Update the virtualChildNodeIds property with child node IDs."""
        if not self._element:
            return
        child_ids = [child.element.node_id for child in self._children if child._element]
        for child in self._header_section._children:
            if child._element:
                child_ids.append(child.element.node_id)
        for child in self._footer_section._children:
            if child._element:
                child_ids.append(child.element.node_id)
        self.element.set_property("virtualChildNodeIds", child_ids)

    def add(self, *components: Component):
        """Add components to the dialog content."""
        for component in components:
            self._children.append(component)
            if self._element:
                component._attach(self._element._tree)
                self.element.node.add_child(component.element.node)
                self._update_virtual_child_node_ids()

    def remove_all(self):
        """Remove all components from the dialog content."""
        if self._element:
            for child in self._children:
                if child._element:
                    self.element.node.remove_child(child.element.node)
        for child in self._children:
            child._parent = None
        self._children.clear()
        if self._element:
            self._update_virtual_child_node_ids()

    def open(self):
        """Open the dialog.

        If the dialog was not added manually to a parent component, it will be
        automatically added to the UI when opened, and automatically removed
        from the UI when closed.
        """
        self._opened = True
        self._close_pending = False
        if not self._element:
            # Auto-attach to UI container (same as Java's OverlayAutoAddController)
            from pyxflow.components.notification import _get_current_tree
            tree = _get_current_tree()
            if tree:
                self._attach(tree)
                container = tree.get_node(tree._container_node_id)
                if container:
                    container.add_child(self.element.node)
                self._auto_added = True
        elif self._auto_added and self.element.node._parent is None:
            # Was auto-removed on close, re-add to container
            tree = self.element.node._tree
            container = tree.get_node(tree._container_node_id)
            if container:
                container.add_child(self.element.node)
        if self._element:
            self._pending_server_change = True
            self.element.set_property("opened", True)
        for listener in self._open_listeners:
            listener({})

    def close(self):
        """Close the dialog.

        If the dialog was auto-added to the UI when opened, it will be
        automatically removed from the UI when closed.
        """
        self._opened = False
        self._close_pending = False
        if self._element:
            self._pending_server_change = True
            self.element.set_property("opened", False)
            self._auto_remove()

    def is_opened(self) -> bool:
        """Check if the dialog is open."""
        return self._opened

    def set_opened(self, opened: bool):
        """Set the opened state."""
        if opened:
            self.open()
        else:
            self.close()

    def set_modal(self, modal: bool):
        """Set whether the dialog is modal."""
        self._modal = modal
        if self._element:
            self.element.set_property("modeless", not modal)

    def is_modal(self) -> bool:
        """Check if the dialog is modal."""
        return self._modal

    def set_draggable(self, draggable: bool):
        """Set whether the dialog can be dragged."""
        self._draggable = draggable
        if self._element:
            self.element.set_property("draggable", draggable)

    def is_draggable(self) -> bool:
        """Check if the dialog is draggable."""
        return self._draggable

    def set_resizable(self, resizable: bool):
        """Set whether the dialog can be resized."""
        self._resizable = resizable
        if self._element:
            self.element.set_property("resizable", resizable)

    def is_resizable(self) -> bool:
        """Check if the dialog is resizable."""
        return self._resizable

    def get_header(self) -> _DialogSection:
        """Get the header section for adding components to the dialog header."""
        return self._header_section

    def get_footer(self) -> _DialogSection:
        """Get the footer section for adding components to the dialog footer."""
        return self._footer_section

    def set_header_title(self, title: str):
        """Set the dialog header title."""
        self._header_title = title
        if self._element:
            self.element.set_property("headerTitle", title)

    def get_header_title(self) -> str:
        """Get the dialog header title."""
        return self._header_title

    def set_width(self, width: str | None):
        """Set the dialog width (e.g., '400px', '50%')."""
        self._width = width
        if self._element:
            self.element.set_property("width", width or "")

    def get_width(self) -> str | None:
        """Get the dialog width."""
        return self._width

    def set_height(self, height: str | None):
        """Set the dialog height (e.g., '300px', '50%')."""
        self._height = height
        if self._element:
            self.element.set_property("height", height or "")

    def get_height(self) -> str | None:
        """Get the dialog height."""
        return self._height

    def set_min_width(self, min_width: str | None):
        """Set the minimum width of the dialog overlay."""
        self._min_width = min_width
        self._set_overlay_dimension("min-width", min_width)

    def set_max_width(self, max_width: str | None):
        """Set the maximum width of the dialog overlay."""
        self._max_width = max_width
        self._set_overlay_dimension("max-width", max_width)

    def set_min_height(self, min_height: str | None):
        """Set the minimum height of the dialog overlay."""
        self._min_height = min_height
        self._set_overlay_dimension("min-height", min_height)

    def set_max_height(self, max_height: str | None):
        """Set the maximum height of the dialog overlay."""
        self._max_height = max_height
        self._set_overlay_dimension("max-height", max_height)

    def _set_overlay_dimension(self, dimension: str, value: str | None):
        """Set a CSS dimension on the overlay element via JS."""
        self.execute_js(
            "$0.$.overlay.$.overlay.style[$1]=$2", dimension, value or ""
        )

    def set_close_on_esc(self, close_on_esc: bool):
        """Set whether the dialog closes on Escape key."""
        self._close_on_esc = close_on_esc
        if self._element:
            self.element.set_property("closeOnEsc", close_on_esc)

    def is_close_on_esc(self) -> bool:
        """Check if the dialog closes on Escape key."""
        return self._close_on_esc

    def set_close_on_outside_click(self, close_on_outside_click: bool):
        """Set whether the dialog closes on outside click."""
        self._close_on_outside_click = close_on_outside_click
        if self._element:
            self.element.set_property("closeOnOutsideClick", close_on_outside_click)

    def is_close_on_outside_click(self) -> bool:
        """Check if the dialog closes on outside click."""
        return self._close_on_outside_click

    def add_open_listener(self, listener: Callable):
        """Add a listener for when the dialog opens."""
        self._open_listeners.append(listener)

    def add_close_listener(self, listener: Callable):
        """Add a listener for when the dialog closes."""
        self._close_listeners.append(listener)

    def _handle_opened_changed(self, event_data: dict):
        """Handle opened-changed event from client.

        Absorbs echoes from server-initiated open/close calls.
        Client-initiated close is handled entirely by handle_client_close
        (publishedEventHandler from the overlay's close event).
        We must NOT call _auto_remove() here because handle_client_close
        arrives later in the same RPC batch and needs the node attached.
        """
        if self._pending_server_change:
            self._pending_server_change = False

    def _auto_remove(self):
        """Remove auto-added dialog from container (matching Java's OverlayAutoAddController)."""
        if self._auto_added and self._element and self.element.node._parent is not None:
            self.element.node._parent.remove_child(self.element.node)

    def handle_client_close(self):
        """Called when the client reports the dialog was closed.

        This is triggered by the overlay's vaadin-overlay-close event
        via $server.handleClientClose() (publishedEventHandler RPC).

        Due to two-pass RPC processing, mSync may have already set
        _opened=False before this method runs. The _close_pending flag
        tracks that case so we still run the full close sequence
        (auto-remove + listeners).
        """
        if not self._close_pending and not self._opened:
            return
        needs_property_update = self._opened
        self._close_pending = False
        self._opened = False
        if self._element:
            if needs_property_update:
                self._pending_server_change = True
                self.element.set_property("opened", False)
            self._auto_remove()
        for listener in self._close_listeners:
            listener({})

    def remove(self, *components: Component):
        """Remove specific components from the dialog content."""
        for component in components:
            if component in self._children:
                self._children.remove(component)
                component._parent = None
                if self._element and component._element:
                    self.element.node.remove_child(component.element.node)
        if self._element:
            self._update_virtual_child_node_ids()

    def set_top(self, top: str):
        """Set the dialog top position (e.g., '100px')."""
        if self._element:
            self.element.get_style().set("--vaadin-dialog-overlay-offset-top", top)

    def set_left(self, left: str):
        """Set the dialog left position (e.g., '100px')."""
        if self._element:
            self.element.get_style().set("--vaadin-dialog-overlay-offset-left", left)

    def add_resize_listener(self, listener: Callable):
        """Add a listener called when the dialog is resized."""
        if not hasattr(self, "_resize_listeners"):
            self._resize_listeners = []
        self._resize_listeners.append(listener)
        if self._element and len(self._resize_listeners) == 1:
            self.element.add_event_listener("resize", self._handle_resize)

    def add_dragged_listener(self, listener: Callable):
        """Add a listener called when the dialog is dragged."""
        if not hasattr(self, "_dragged_listeners"):
            self._dragged_listeners = []
        self._dragged_listeners.append(listener)
        if self._element and len(self._dragged_listeners) == 1:
            self.element.add_event_listener("dragged", self._handle_dragged)

    def _handle_resize(self, event_data: dict):
        """Handle resize event."""
        for listener in getattr(self, "_resize_listeners", []):
            listener(event_data)

    def _handle_dragged(self, event_data: dict):
        """Handle dragged event."""
        for listener in getattr(self, "_dragged_listeners", []):
            listener(event_data)

    def add_theme_variants(self, *variants: DialogVariant):
        """Add theme variants to the dialog."""
        self.add_theme_name(*variants)

    def remove_theme_variants(self, *variants: DialogVariant):
        """Remove theme variants from the dialog."""
        self.remove_theme_name(*variants)

    def _sync_property(self, name: str, value):
        """Handle property sync from client."""
        if name == "opened":
            if self._opened and not value:
                self._close_pending = True
            self._opened = value
