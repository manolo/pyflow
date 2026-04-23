"""ConfirmDialog component."""

from typing import Callable, TYPE_CHECKING

from pyxflow.core.component import Component
from pyxflow.components.constants import DialogVariant
from pyxflow.server.uidl_handler import _CLOSED_HASH

if TYPE_CHECKING:
    from pyxflow.core.state_tree import StateTree


class ConfirmDialog(Component):
    """A dialog for asking the user to confirm or cancel an action.

    ConfirmDialog is a modal dialog that presents a header, message, and
    up to three buttons: confirm, reject, and cancel. Unlike Dialog, it
    does not use FlowComponentHost or virtual children — all content is
    controlled via properties.
    """

    _v_fqcn = "com.vaadin.flow.component.confirmdialog.ConfirmDialog"
    _tag = "vaadin-confirm-dialog"
    _v_sync_properties = frozenset({"opened"})
    _v_disabled_sync = frozenset({"opened"})
    _v_disabled_methods = frozenset({"handle_client_close"})

    def __init__(self, header: str = "", text: str = "", confirm_text: str = "Confirm"):
        super().__init__()
        self._header = header
        self._message = text
        self._confirm_text = confirm_text
        self._cancel_text = "Cancel"
        self._reject_text = ""
        self._cancelable = False
        self._rejectable = False
        self._confirm_theme = ""
        self._cancel_theme = ""
        self._reject_theme = ""
        self._opened = False
        self._confirm_listeners: list[Callable] = []
        self._cancel_listeners: list[Callable] = []
        self._reject_listeners: list[Callable] = []
        self._close_on_esc = True
        self._opened_change_listeners: list[Callable] = []
        self._auto_added = False

    def _attach(self, tree: "StateTree"):
        super()._attach(tree)

        # Set initial properties
        if self._header:
            self.element.set_property("header", self._header)
        if self._message:
            self.element.set_property("message", self._message)
        if self._confirm_text:
            self.element.set_property("confirmText", self._confirm_text)
        if self._confirm_theme:
            self.element.set_property("confirmTheme", self._confirm_theme)

        self.element.set_property("cancelButtonVisible", self._cancelable)
        if self._cancel_text:
            self.element.set_property("cancelText", self._cancel_text)
        if self._cancel_theme:
            self.element.set_property("cancelTheme", self._cancel_theme)

        self.element.set_property("rejectButtonVisible", self._rejectable)
        if self._reject_text:
            self.element.set_property("rejectText", self._reject_text)
        if self._reject_theme:
            self.element.set_property("rejectTheme", self._reject_theme)

        if not self._close_on_esc:
            self.element.set_property("closeOnEsc", False)

        if self._opened:
            self.element.set_property("opened", True)

        # Register event listeners with explicit hash (empty config)
        self.element.add_event_listener("confirm", self._on_confirm, _CLOSED_HASH)
        self.element.add_event_listener("cancel", self._on_cancel, _CLOSED_HASH)
        self.element.add_event_listener("reject", self._on_reject, _CLOSED_HASH)

    def open(self):
        """Open the confirm dialog.

        If the dialog was not added manually to a parent component, it will be
        automatically added to the UI when opened, and automatically removed
        when closed.
        """
        self._opened = True
        if not self._element:
            from pyxflow.components.notification import _get_current_tree
            tree = _get_current_tree()
            if tree:
                self._ui = getattr(tree, '_ui', None)
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
            self.element.set_property("opened", True)
        for listener in self._opened_change_listeners:
            listener({"opened": True})

    def close(self):
        """Close the confirm dialog."""
        self._opened = False
        if self._element:
            self.element.set_property("opened", False)
            self._auto_remove()
        for listener in self._opened_change_listeners:
            listener({"opened": False})

    def is_opened(self) -> bool:
        """Check if the dialog is open."""
        return self._opened

    def set_header(self, header: str):
        """Set the dialog header text."""
        self._header = header
        if self._element:
            self.element.set_property("header", header)

    def get_header(self) -> str:
        """Get the dialog header text."""
        return self._header

    def set_text(self, message: str):
        """Set the dialog message text."""
        self._message = message
        if self._element:
            self.element.set_property("message", message)

    def get_text(self) -> str:
        """Get the dialog message text."""
        return self._message

    def set_confirm_text(self, text: str):
        """Set the confirm button text."""
        self._confirm_text = text
        if self._element:
            self.element.set_property("confirmText", text)

    def get_confirm_text(self) -> str:
        """Get the confirm button text."""
        return self._confirm_text

    def set_confirm_button_theme(self, theme: str):
        """Set the confirm button theme (e.g., 'error primary')."""
        self._confirm_theme = theme
        if self._element:
            self.element.set_property("confirmTheme", theme)

    def set_cancelable(self, cancelable: bool):
        """Set whether the cancel button is visible."""
        self._cancelable = cancelable
        if self._element:
            self.element.set_property("cancelButtonVisible", cancelable)

    def is_cancelable(self) -> bool:
        """Check if the cancel button is visible."""
        return self._cancelable

    def set_cancel_text(self, text: str):
        """Set the cancel button text."""
        self._cancel_text = text
        if self._element:
            self.element.set_property("cancelText", text)

    def get_cancel_text(self) -> str:
        """Get the cancel button text."""
        return self._cancel_text

    def set_cancel_button_theme(self, theme: str):
        """Set the cancel button theme."""
        self._cancel_theme = theme
        if self._element:
            self.element.set_property("cancelTheme", theme)

    def set_rejectable(self, rejectable: bool):
        """Set whether the reject button is visible."""
        self._rejectable = rejectable
        if self._element:
            self.element.set_property("rejectButtonVisible", rejectable)

    def is_rejectable(self) -> bool:
        """Check if the reject button is visible."""
        return self._rejectable

    def set_reject_text(self, text: str):
        """Set the reject button text."""
        self._reject_text = text
        if self._element:
            self.element.set_property("rejectText", text)

    def get_reject_text(self) -> str:
        """Get the reject button text."""
        return self._reject_text

    def set_reject_button_theme(self, theme: str):
        """Set the reject button theme."""
        self._reject_theme = theme
        if self._element:
            self.element.set_property("rejectTheme", theme)

    def add_confirm_listener(self, listener: Callable):
        """Add a listener called when the confirm button is clicked."""
        self._confirm_listeners.append(listener)

    def add_cancel_listener(self, listener: Callable):
        """Add a listener called when the cancel button is clicked."""
        self._cancel_listeners.append(listener)

    def add_reject_listener(self, listener: Callable):
        """Add a listener called when the reject button is clicked."""
        self._reject_listeners.append(listener)

    def set_close_on_esc(self, close_on_esc: bool):
        """Set whether the dialog closes on Escape key."""
        self._close_on_esc = close_on_esc
        if self._element:
            self.element.set_property("closeOnEsc", close_on_esc)

    def is_close_on_esc(self) -> bool:
        return self._close_on_esc

    def add_opened_change_listener(self, listener: Callable):
        """Add a listener for opened state changes."""
        self._opened_change_listeners.append(listener)

    def _auto_remove(self):
        """Remove auto-added dialog from container (matching Java's OverlayAutoAddController)."""
        if self._auto_added and self._element and self.element.node._parent is not None:
            self.element.node._parent.remove_child(self.element.node)

    def _on_confirm(self, event_data: dict):
        """Handle confirm event from client."""
        self._opened = False
        if self._element:
            self.element.set_property("opened", False)
            self._auto_remove()
        for listener in self._confirm_listeners:
            listener(event_data)

    def _on_cancel(self, event_data: dict):
        """Handle cancel event from client."""
        self._opened = False
        if self._element:
            self.element.set_property("opened", False)
            self._auto_remove()
        for listener in self._cancel_listeners:
            listener(event_data)

    def _on_reject(self, event_data: dict):
        """Handle reject event from client."""
        self._opened = False
        if self._element:
            self.element.set_property("opened", False)
            self._auto_remove()
        for listener in self._reject_listeners:
            listener(event_data)

    def add_theme_variants(self, *variants: DialogVariant):
        """Add theme variants to the confirm dialog."""
        self.add_theme_name(*variants)

    def remove_theme_variants(self, *variants: DialogVariant):
        """Remove theme variants from the confirm dialog."""
        self.remove_theme_name(*variants)

    def _sync_property(self, name: str, value):
        """Handle property sync from client."""
        if name == "opened":
            self._opened = value
