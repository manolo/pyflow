"""Notification component."""

import threading
from enum import Enum
from typing import Callable, TYPE_CHECKING

from pyxflow.core.component import Component
from pyxflow.core.state_node import Feature
from pyxflow.components.constants import NotificationVariant
from pyxflow.server.uidl_handler import _CLOSED_HASH, _OPENED_CHANGED_HASH

if TYPE_CHECKING:
    from pyxflow.core.state_tree import StateTree


# Thread-local storage for the current tree context.
# Used by Notification.show() to auto-attach without an explicit tree reference.
_current_tree_local = threading.local()


def _set_current_tree(tree: "StateTree | None"):
    """Set the current tree context (called by UidlHandler during RPC processing)."""
    _current_tree_local.tree = tree


def _get_current_tree() -> "StateTree | None":
    """Get the current tree context."""
    return getattr(_current_tree_local, "tree", None)


class Notification(Component):
    """A notification overlay component.

    Notification is used to show brief messages to the user.
    It appears as a small popup and can auto-close after a duration.

    The notification is attached to the body (node 1) of the StateTree,
    not to the current view.
    """

    _v_fqcn = "com.vaadin.flow.component.notification.Notification"
    _tag = "vaadin-notification"
    _v_sync_properties = frozenset({"opened"})
    _v_disabled_sync = frozenset({"opened"})

    class Position(Enum):
        """Notification position on the screen."""

        TOP_STRETCH = "top-stretch"
        TOP_START = "top-start"
        TOP_CENTER = "top-center"
        TOP_END = "top-end"
        MIDDLE = "middle"
        BOTTOM_START = "bottom-start"
        BOTTOM_CENTER = "bottom-center"
        BOTTOM_END = "bottom-end"
        BOTTOM_STRETCH = "bottom-stretch"

    def __init__(self, text: str = "", duration: int = 0,
                 position: "Notification.Position | None" = None,
                 assertive: bool = False):
        super().__init__()
        self._text = text
        self._duration = duration
        self._position = position or Notification.Position.BOTTOM_START
        self._assertive = assertive
        self._opened = False
        self._pending_server_change = False
        self._children: list[Component] = []
        self._open_listeners: list[Callable] = []
        self._close_listeners: list[Callable] = []
        self._theme_variants: set[str] = set()

    def _attach(self, tree: "StateTree"):
        super()._attach(tree)

        # Clear children list (matches UIDL captured: clear feat 2)
        tree.add_change({
            "node": self.element.node_id,
            "type": "clear",
            "feat": Feature.ELEMENT_CHILDREN_LIST,
        })

        # Set initial properties (order matches captured UIDL)
        self.element.set_property("duration", float(self._duration))
        self.element.set_property("assertive", self._assertive)
        self.element.set_property("opened", self._opened)
        if self._text:
            self.element.set_property("text", self._text)
        self.element.set_property("position", self._position.value)

        # Attach children if any
        for child in self._children:
            child._attach(tree)
            self.element.node.add_child(child.element.node)

        # virtualChildNodeIds — empty for text-only, child IDs for component mode
        self._update_virtual_child_node_ids()

        # Register event listeners with explicit hashes
        self.element.add_event_listener(
            "closed", self._handle_closed, _CLOSED_HASH
        )
        self.element.add_event_listener(
            "opened-changed", self._handle_opened_changed, _OPENED_CHANGED_HASH
        )

        # Set theme attribute if variants were added before attach
        if self._theme_variants:
            self.element.set_attribute("theme", " ".join(sorted(self._theme_variants)))

    def _update_virtual_child_node_ids(self):
        """Update the virtualChildNodeIds property with child node IDs."""
        if not self._element:
            return
        child_ids = [child.element.node_id for child in self._children if child._element]
        self.element.set_property("virtualChildNodeIds", child_ids)

    # --- Text ---

    @property
    def text(self) -> str:
        """Get the notification text."""
        return self._text

    @text.setter
    def text(self, value: str):
        """Set the notification text."""
        self._text = value
        if self._element:
            self.element.set_property("text", value)

    # --- Duration ---

    @property
    def duration(self) -> int:
        """Get the duration in milliseconds. 0 means no auto-close."""
        return self._duration

    @duration.setter
    def duration(self, value: int):
        """Set the duration in milliseconds."""
        self._duration = value
        if self._element:
            self.element.set_property("duration", float(value))

    # --- Position ---

    @property
    def position(self) -> "Notification.Position":
        """Get the notification position."""
        return self._position

    @position.setter
    def position(self, value: "Notification.Position"):
        """Set the notification position."""
        self._position = value
        if self._element:
            self.element.set_property("position", value.value)

    # --- Assertive ---

    @property
    def assertive(self) -> bool:
        """Get whether the notification uses assertive aria-live."""
        return self._assertive

    @assertive.setter
    def assertive(self, value: bool):
        """Set whether the notification uses assertive aria-live."""
        self._assertive = value
        if self._element:
            self.element.set_property("assertive", value)

    # --- Open / Close ---

    def open(self):
        """Open the notification."""
        self._opened = True
        if not self._element:
            # Auto-attach using current tree context
            tree = _get_current_tree()
            if tree:
                self._ui = getattr(tree, '_ui', None)
                self._pending_server_change = True
                self._attach(tree)
                # Add to body node (node 1) so client can render it.
                # This is only for the auto-attach path (Notification.show()).
                # When a parent layout calls add(notification), the parent
                # handles adding the node as its child — no body attach needed.
                body_node = tree.get_node(1)
                if body_node:
                    body_node.add_child(self.element.node)
                for listener in self._open_listeners:
                    listener({})
                return
        if self._element:
            self._pending_server_change = True
            self.element.set_property("opened", True)
        for listener in self._open_listeners:
            listener({})

    def close(self):
        """Close the notification."""
        self._opened = False
        if self._element:
            self._pending_server_change = True
            self.element.set_property("opened", False)

    def is_opened(self) -> bool:
        """Check if the notification is open."""
        return self._opened

    def set_opened(self, opened: bool):
        """Set the opened state."""
        if opened:
            self.open()
        else:
            self.close()

    # --- Content (component mode) ---

    def add(self, *components: Component):
        """Add components to the notification content.

        When components are added, the text property is removed
        and content is rendered via FlowComponentHost.
        """
        for component in components:
            self._children.append(component)
            if self._element:
                component._attach(self._element._tree)
                self.element.node.add_child(component.element.node)
                self._update_virtual_child_node_ids()
                # Remove text property when using component content
                self.element.remove_property("text")
                self._text = ""

    def remove(self, *components: Component):
        """Remove specific components from the notification content."""
        for component in components:
            if component in self._children:
                self._children.remove(component)
                component._parent = None
                if self._element and component._element:
                    self.element.node.remove_child(component.element.node)
        if self._element:
            self._update_virtual_child_node_ids()

    def remove_all(self):
        """Remove all components from the notification content."""
        if self._element:
            for child in self._children:
                if child._element:
                    self.element.node.remove_child(child.element.node)
        for child in self._children:
            child._parent = None
        self._children.clear()
        if self._element:
            self._update_virtual_child_node_ids()

    # --- Theme Variants ---

    def add_theme_variants(self, *variants: NotificationVariant):
        """Add theme variants to the notification."""
        for variant in variants:
            self._theme_variants.add(variant.value)
        if self._element:
            self.element.set_attribute("theme", " ".join(sorted(self._theme_variants)))

    def remove_theme_variants(self, *variants: NotificationVariant):
        """Remove theme variants from the notification."""
        for variant in variants:
            self._theme_variants.discard(variant.value)
        if self._element:
            if self._theme_variants:
                self.element.set_attribute("theme", " ".join(sorted(self._theme_variants)))
            else:
                self.element.remove_attribute("theme")

    # --- Listeners ---

    def add_open_listener(self, listener: Callable):
        """Add a listener for when the notification opens."""
        self._open_listeners.append(listener)

    def add_close_listener(self, listener: Callable):
        """Add a listener for when the notification closes."""
        self._close_listeners.append(listener)

    def _handle_opened_changed(self, event_data: dict):
        """Handle opened-changed event from client.

        Same pattern as Dialog: track server-initiated changes to distinguish
        echoes from user/auto-close events. Sync server tree on client close.
        """
        if self._pending_server_change:
            self._pending_server_change = False
            return

        # Client-initiated close (user dismissed or duration expired)
        self._opened = False
        if self._element:
            self._pending_server_change = True
            self.element.set_property("opened", False)

    def _handle_closed(self, event_data: dict):
        """Handle closed event from client."""
        self._opened = False
        for listener in self._close_listeners:
            listener(event_data)

    def _sync_property(self, name: str, value):
        """Handle property sync from client."""
        if name == "opened":
            self._opened = value

    # --- Static factory ---

    @staticmethod
    def show(text: str, duration: int = 5000,
             position: "Notification.Position | None" = None,
             assertive: bool = False) -> "Notification":
        """Show a text notification.

        This is the most common way to show a notification.
        The notification auto-attaches to the current tree context.

        Args:
            text: The notification text.
            duration: Auto-close duration in ms. 0 means no auto-close.
            position: Position on screen. Default is BOTTOM_START.
            assertive: Use assertive aria-live for screen readers.

        Returns:
            The created Notification instance.
        """
        if position is None:
            position = Notification.Position.BOTTOM_START
        n = Notification(text, duration, position, assertive)
        n.open()
        return n
