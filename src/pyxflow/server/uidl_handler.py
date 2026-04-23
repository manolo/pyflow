"""UIDL Protocol Handler."""

import base64
import hashlib
import inspect
import json
import logging
import random
import re
import secrets
from typing import Any, TYPE_CHECKING

log = logging.getLogger("pyxflow")

from pyxflow.core.component import FORBIDDEN_SYNC_PROPERTIES, DisabledUpdateMode
from pyxflow.core.state_node import Feature

if TYPE_CHECKING:
    from pyxflow.core.component import Component
    from pyxflow.core.state_tree import StateTree


# =============================================================================
# Event Listener Configurations
# =============================================================================
# Event hashes are computed dynamically using the same algorithm as Java Flow:
#   base64(sha256(BOM + json.encode('utf-16-be'))[:8])
# where BOM = b'\xfe\xff' (UTF-16 BE byte order mark).
#
# The hash is just a constant pool key — the client stores whatever config
# we send alongside it. So computed hashes are fully compatible.
# =============================================================================


def compute_event_hash(config: dict) -> str:
    """Compute the event hash for a given config dict.

    Uses the same algorithm as Java Flow: SHA-256 of the JSON string
    encoded as UTF-16 BE with BOM prefix, taking the first 8 bytes
    and Base64 encoding them.
    """
    json_str = json.dumps(config, separators=(",", ":"))
    data = b'\xfe\xff' + json_str.encode('utf-16-be')
    return base64.b64encode(hashlib.sha256(data).digest()[:8]).decode()


# Click event configuration (for buttons, etc.)
_CLICK_CONFIG = {
    "event.shiftKey": False,
    "event.metaKey": False,
    "event.detail": False,
    "event.ctrlKey": False,
    "event.clientX": False,
    "event.clientY": False,
    "event.altKey": False,
    "event.button": False,
    "event.screenY": False,
    "event.screenX": False
}
_CLICK_HASH = compute_event_hash(_CLICK_CONFIG)

# Change event configuration (for text fields, etc.)
# The '}' prefix means "sync this property with server"
_CHANGE_CONFIG = {
    "}value": False
}
_CHANGE_HASH = compute_event_hash(_CHANGE_CONFIG)

# Opened-changed event configuration (for dialogs, dropdowns)
_OPENED_CHANGED_CONFIG = {
    "}opened": False
}
_OPENED_CHANGED_HASH = compute_event_hash(_OPENED_CHANGED_CONFIG)

# Checked-changed event configuration (for checkboxes)
_CHECKED_CHANGED_CONFIG = {
    "}checked": False
}
_CHECKED_CHANGED_HASH = compute_event_hash(_CHECKED_CHANGED_CONFIG)

# Keydown event configuration (Enter key handling)
_KEYDOWN_CONFIG = {
    "event.shiftKey": False,
    "event.metaKey": False,
    "event.code": False,
    "event.key": False,
    "event.isComposing": False,
    "(['Enter'].indexOf(event.code) !== -1 || ['Enter'].indexOf(event.key) !== -1) && !event.getModifierState('Shift') && !event.getModifierState('Control') && !event.getModifierState('Alt') && !event.getModifierState('AltGraph') && !event.getModifierState('Meta') && (event.stopPropagation() || true)": True,
    "event.ctrlKey": False,
    "event.repeat": False,
    "event.location": False,
    "event.altKey": False
}
_KEYDOWN_HASH = compute_event_hash(_KEYDOWN_CONFIG)

# Closed event (empty config — no event data needed)
_CLOSED_CONFIG = {}
_CLOSED_HASH = compute_event_hash(_CLOSED_CONFIG)

# Selected-changed event configuration (for Tabs, ListBox)
_SELECTED_CHANGED_CONFIG = {
    "}selected": False
}
_SELECTED_CHANGED_HASH = compute_event_hash(_SELECTED_CHANGED_CONFIG)

# Selected-values-changed event configuration (for MultiSelectListBox)
_SELECTED_VALUES_CHANGED_CONFIG = {
    "}selectedValues": False
}
_SELECTED_VALUES_CHANGED_HASH = compute_event_hash(_SELECTED_VALUES_CHANGED_CONFIG)

# Value-changed event configuration (for Select, CheckboxGroup, RadioButtonGroup, etc.)
_VALUE_CHANGED_CONFIG = {
    "}value": False
}
_VALUE_CHANGED_HASH = compute_event_hash(_VALUE_CHANGED_CONFIG)

# Selected-items-changed event configuration (for MultiSelectComboBox)
_SELECTED_ITEMS_CHANGED_CONFIG = {
    "}selectedItems": False
}
_SELECTED_ITEMS_CHANGED_HASH = compute_event_hash(_SELECTED_ITEMS_CHANGED_CONFIG)

# Splitter-dragend event configuration (for SplitLayout)
_SPLITTER_DRAGEND_CONFIG = {}
_SPLITTER_DRAGEND_HASH = compute_event_hash(_SPLITTER_DRAGEND_CONFIG)

# Focus/Blur event configuration (for FocusNotifier/BlurNotifier)
# Empty config — no event data needed.  These use the same empty config
# as _CLOSED_CONFIG, so they share the same hash.
_FOCUS_CONFIG = {}
_FOCUS_HASH = compute_event_hash(_FOCUS_CONFIG)
_BLUR_CONFIG = {}
_BLUR_HASH = compute_event_hash(_BLUR_CONFIG)

# Drag and Drop event configurations
_DRAGSTART_CONFIG = {}
_DRAGSTART_HASH = compute_event_hash(_DRAGSTART_CONFIG)
_DRAGEND_CONFIG = {
    "event.dataTransfer.dropEffect": False
}
_DRAGEND_HASH = compute_event_hash(_DRAGEND_CONFIG)
_DROP_CONFIG = {}
_DROP_HASH = compute_event_hash(_DROP_CONFIG)

# =============================================================================
# UI Navigation Event Configurations
# =============================================================================
# These are registered on the body element for client-side navigation.

# UI navigate event - triggered when the user navigates to a new route
_UI_NAVIGATE_CONFIG = {
    "route": False,
    "appShellTitle": False,
    "query": False,
    "trigger": False,
    "historyState": False
}
_UI_NAVIGATE_HASH = compute_event_hash(_UI_NAVIGATE_CONFIG)

# UI leave navigation event - triggered when leaving a route
_UI_LEAVE_NAVIGATION_CONFIG = {
    "route": False,
    "query": False
}
_UI_LEAVE_NAVIGATION_HASH = compute_event_hash(_UI_LEAVE_NAVIGATION_CONFIG)

# UI refresh event - triggered on page refresh
_UI_REFRESH_CONFIG = {
    "fullRefresh": False
}
_UI_REFRESH_HASH = compute_event_hash(_UI_REFRESH_CONFIG)


# Upload event configurations
_FILE_REJECT_CONFIG = {
    "event.detail.file.name": False,
    "event.detail.error": False,
}
_FILE_REJECT_HASH = compute_event_hash(_FILE_REJECT_CONFIG)

_UPLOAD_SUCCESS_CONFIG = {
    "element.files": False,
}
_UPLOAD_SUCCESS_HASH = compute_event_hash(_UPLOAD_SUCCESS_CONFIG)

_UPLOAD_ERROR_CONFIG = {
    "element.files": False,
}
_UPLOAD_ERROR_HASH = compute_event_hash(_UPLOAD_ERROR_CONFIG)

# file-remove: captures event.detail.file.name
_FILE_REMOVE_CONFIG = {
    "event.detail.file.name": False,
}
_FILE_REMOVE_HASH = compute_event_hash(_FILE_REMOVE_CONFIG)

# Submit event configuration (MessageInput: event.detail.value)
_SUBMIT_CONFIG = {
    "event.detail.value": False,
}
_SUBMIT_HASH = compute_event_hash(_SUBMIT_CONFIG)

# Login event configuration (LoginForm: event.detail.username + event.detail.password)
_LOGIN_CONFIG = {
    "event.detail.password": False,
    "event.detail.username": False,
}
_LOGIN_HASH = compute_event_hash(_LOGIN_CONFIG)

# Grid item-click event configuration (gridConnector dispatches CustomEvent with detail.itemKey)
_ITEM_CLICK_CONFIG = {
    "event.detail.itemKey": False,
}
_ITEM_CLICK_HASH = compute_event_hash(_ITEM_CLICK_CONFIG)


# Reverse lookup: hash → config for all known event hashes.
# Used when a component registers a listener with an explicit hash_key
# (value is a string, not True) so we can add the config to constants.
_HASH_TO_CONFIG = {
    _CLICK_HASH: _CLICK_CONFIG,
    _CHANGE_HASH: _CHANGE_CONFIG,
    _OPENED_CHANGED_HASH: _OPENED_CHANGED_CONFIG,
    _CHECKED_CHANGED_HASH: _CHECKED_CHANGED_CONFIG,
    _KEYDOWN_HASH: _KEYDOWN_CONFIG,
    _CLOSED_HASH: _CLOSED_CONFIG,
    _SELECTED_CHANGED_HASH: _SELECTED_CHANGED_CONFIG,
    _FILE_REJECT_HASH: _FILE_REJECT_CONFIG,
    _UPLOAD_SUCCESS_HASH: _UPLOAD_SUCCESS_CONFIG,
    _UPLOAD_ERROR_HASH: _UPLOAD_ERROR_CONFIG,
    _FILE_REMOVE_HASH: _FILE_REMOVE_CONFIG,
    _SUBMIT_HASH: _SUBMIT_CONFIG,
    _LOGIN_HASH: _LOGIN_CONFIG,
    _SELECTED_VALUES_CHANGED_HASH: _SELECTED_VALUES_CHANGED_CONFIG,
    _VALUE_CHANGED_HASH: _VALUE_CHANGED_CONFIG,
    _SELECTED_ITEMS_CHANGED_HASH: _SELECTED_ITEMS_CHANGED_CONFIG,
    _SPLITTER_DRAGEND_HASH: _SPLITTER_DRAGEND_CONFIG,
    _ITEM_CLICK_HASH: _ITEM_CLICK_CONFIG,
    _DRAGSTART_HASH: _DRAGSTART_CONFIG,
    _DRAGEND_HASH: _DRAGEND_CONFIG,
    _DROP_HASH: _DROP_CONFIG,
}


class UidlHandler:
    """Handles UIDL protocol messages."""

    def __init__(self, tree: "StateTree", csrf_token: str | None = None):
        self._tree = tree
        self._sync_id = 0
        self._client_id = 0
        self._csrf_token = csrf_token or secrets.token_hex(16)
        self._app_id = f"ROOT-{random.randint(1000000, 9999999)}"
        self._client_key = self._app_id.split("-")[0]  # "ROOT" — client registry key
        self._initialized = False
        self._view: Any = None
        self._layout: Any = None  # Persistent layout instance for RouterLayout
        self._layout_class: type | None = None  # Class of current layout
        self._current_route: str | None = None  # Track current route for re-navigation
        # UI is a singleton per session (like Java Flow's VaadinSession → UI)
        from pyxflow.core.component import UI
        self._ui = UI(tree)

        # Node references
        self._body_node: Any = None
        self._container_node: Any = None
        self._pending_execute: list = []  # Execute commands for next response
        self._server_connected_cmd: list | None = None  # serverConnected must be last
        self._last_client_id = 0  # Track client's message counter
        self._sent_constants: set[str] = set()  # Track already-sent constant hashes
        self._pending_dependencies: list[dict] = []  # EAGER deps for next response
        self._sent_stylesheets: set[str] = set()  # Track sent stylesheet URLs
        self._last_processed_client_id = -1  # Last successfully processed clientId
        self._last_response: dict | None = None  # Cached for duplicate detection

    def handle_init(self, browser_details: dict, initial_route: str = "", ui_id: int = 0) -> dict:
        """Handle init request.

        Returns appConfig with initial UIDL.
        Each init creates a fresh UI (handles page reload).

        Args:
            browser_details: Browser details from client
            initial_route: The route from the request path (e.g., "about" for /about)
            ui_id: The UI ID for this browser tab (0, 1, 2, ...)
        """
        # Reset state for fresh UI (handles page reload)
        self._tree.reset()
        self._sync_id = 0
        self._client_id = 0
        self._view = None
        self._layout = None
        self._layout_class = None
        self._current_route = None
        self._body_node = None
        self._container_node = None
        self._pending_execute = []
        self._server_connected_cmd = None
        self._last_client_id = 0
        self._sent_constants = set()
        self._pending_dependencies = []
        self._sent_stylesheets = set()
        self._last_processed_client_id = -1
        self._last_response = None
        self._initial_route = initial_route  # Store for use in navigation

        self._tree._app_id = self._app_id
        self._create_initial_nodes()
        self._initialized = True

        changes = self._tree.collect_changes()

        # Constants for UI navigation events (using Java Flow hashes)
        constants = {
            _UI_NAVIGATE_HASH: _UI_NAVIGATE_CONFIG,
            _UI_LEAVE_NAVIGATION_HASH: _UI_LEAVE_NAVIGATION_CONFIG,
            _UI_REFRESH_HASH: _UI_REFRESH_CONFIG,
        }
        # Track these as sent so they won't be resent in UIDL responses
        self._sent_constants.update(constants.keys())

        self._push_id = secrets.token_hex(16)
        push_enabled = self._is_push_enabled()

        # Build inner UIDL dict
        uidl_data = {
            "clientId": self._client_id,
            "syncId": self._sync_id,
            "Vaadin-Security-Key": self._csrf_token,
            "Vaadin-Push-ID": self._push_id,
            "constants": constants,
            "changes": changes,
        }

        # AppShell stylesheets → included in init UIDL as EAGER dependencies
        from pyxflow.router import get_app_shell
        app_shell = get_app_shell()
        if app_shell:
            sheets = getattr(app_shell, '_stylesheets', [])
            if sheets:
                uidl_data["EAGER"] = [{"type": "STYLESHEET", "url": u, "loadMode": "EAGER"} for u in sheets]
                self._sent_stylesheets.update(sheets)

        response = {
            "appConfig": {
                "productionMode": True,
                "v-uiId": ui_id,
                "appId": self._app_id,
                "contextRootUrl": "./",
                "heartbeatInterval": 300,
                "maxMessageSuspendTimeout": 5000,
                "sessExpMsg": {"caption": None, "message": None, "url": None},
                "uidl": uidl_data,
            },
            "errors": None,
        }

        # Only include pushScript if push is enabled
        if push_enabled:
            response["pushScript"] = "VAADIN/static/push/vaadinPush.js"

        return response

    def _is_push_enabled(self) -> bool:
        """Check if push is enabled via @AppShell @Push."""
        from pyxflow.router import get_app_shell
        app_shell = get_app_shell()
        return getattr(app_shell, '_push_enabled', False) if app_shell else False

    def _create_initial_nodes(self):
        """Create the initial node structure matching Java Flow exactly."""
        app_num = self._app_id.split("-")[1]
        push_enabled = self._is_push_enabled()

        # Node 1: body (UI root) - no attach for root node
        self._body_node = self._tree.create_node()
        # Don't call attach() - body is implicit root

        # Build changes manually to match exact order from Java
        changes = []

        # Node 1 tag
        changes.append({"node": 1, "type": "put", "key": "tag", "feat": 0, "value": "body"})

        # Node 1 listeners (using Java Flow hashes as constant references)
        changes.append({"node": 1, "type": "put", "key": "ui-navigate", "feat": 4, "value": _UI_NAVIGATE_HASH})
        changes.append({"node": 1, "type": "put", "key": "ui-leave-navigation", "feat": 4, "value": _UI_LEAVE_NAVIGATION_HASH})
        changes.append({"node": 1, "type": "put", "key": "ui-refresh", "feat": 4, "value": _UI_REFRESH_HASH})

        # Container node ID depends on whether push nodes are present
        if push_enabled:
            # Node 1 virtual children splice (node 3)
            changes.append({"node": 1, "type": "splice", "feat": 24, "index": 0, "addNodes": [3]})

            # Node 1 push config
            changes.append({"node": 1, "type": "put", "key": "pushServletMapping", "feat": 5, "value": "/"})
            changes.append({"node": 1, "type": "put", "key": "alwaysXhrToServer", "feat": 5, "value": True})
            changes.append({"node": 1, "type": "put", "key": "pushMode", "feat": 5, "value": "AUTOMATIC"})
            changes.append({"node": 1, "type": "put", "key": "parameters", "feat": 5, "nodeValue": 2})

            # Node 2: push parameters
            params_node = self._tree.create_node()  # This will be node 2
            changes.append({"node": 2, "type": "attach"})
            changes.append({"node": 2, "type": "put", "key": "fallbackTransport", "feat": 6, "value": "long-polling"})
            changes.append({"node": 2, "type": "put", "key": "transport", "feat": 6, "value": "websocket"})

            # Node 3: flow-container
            self._container_node = self._tree.create_node()  # This will be node 3
            self._tree._container_node_id = 3
            changes.append({"node": 3, "type": "attach"})
            changes.append({"node": 3, "type": "put", "key": "payload", "feat": 0, "value": {"type": "@id", "payload": self._app_id}})
            changes.append({"node": 3, "type": "put", "key": "tag", "feat": 0, "value": f"flow-container-root-{app_num}"})
        else:
            # No push — container is node 2 (no push parameter node)
            # Node 1 virtual children splice (node 2)
            changes.append({"node": 1, "type": "splice", "feat": 24, "index": 0, "addNodes": [2]})

            # Node 2: flow-container
            self._container_node = self._tree.create_node()  # This will be node 2
            self._tree._container_node_id = 2
            changes.append({"node": 2, "type": "attach"})
            changes.append({"node": 2, "type": "put", "key": "payload", "feat": 0, "value": {"type": "@id", "payload": self._app_id}})
            changes.append({"node": 2, "type": "put", "key": "tag", "feat": 0, "value": f"flow-container-root-{app_num}"})

        # Add all changes
        for change in changes:
            self._tree.add_change(change)

    def handle_uidl(self, payload: dict[str, Any]) -> dict:
        """Handle UIDL request.

        Validates syncId and clientId before processing RPCs.
        Returns UIDL response with changes, or a resync response on mismatch.
        """
        client_sync_id = payload.get("syncId", -1)
        client_client_id = payload.get("clientId", -1)
        expected_client_id = self._last_processed_client_id + 1

        # Client requests resync
        if payload.get("resynchronize"):
            return self._build_resync_response()

        # SyncId mismatch → resync
        if client_sync_id != -1 and client_sync_id != self._sync_id:
            return self._build_resync_response()

        # ClientId validation
        if client_client_id != -1 and client_client_id != expected_client_id:
            if client_client_id == self._last_processed_client_id and self._last_response:
                # Duplicate request → return cached response
                return self._last_response
            else:
                # Out of sync → resync
                return self._build_resync_response()

        # Valid → update tracking and process
        self._last_processed_client_id = expected_client_id
        self._last_client_id = client_client_id

        # Process RPC calls
        rpc_list = payload.get("rpc", [])
        self._process_rpc(rpc_list)

        # Collect changes and build response
        return self._build_response()

    def _process_rpc(self, rpc_list: list[dict[str, Any]]):
        """Process RPC calls from client.

        Follows Java Flow's two-pass approach: mSync RPCs are processed first
        so that property values (e.g. text field value) are up-to-date before
        event handlers (e.g. click shortcuts) run.
        """
        from pyxflow.components.notification import _set_current_tree
        _set_current_tree(self._tree)
        try:
            # Pass 1: process all mSync RPCs first (property syncs)
            other_rpcs: list = []
            for rpc in rpc_list:
                try:
                    if isinstance(rpc, list):
                        # Array-form RPCs (e.g. serverConnected) -- handle in pass 2
                        other_rpcs.append(rpc)
                        continue
                    if rpc.get("type") == "mSync":
                        self._handle_msync(rpc)
                    else:
                        other_rpcs.append(rpc)
                except Exception:
                    rpc_type = rpc.get("type", "unknown") if isinstance(rpc, dict) else rpc[0] if rpc else "unknown"
                    log.exception("Error processing RPC: %s", rpc_type)
                    self._show_error_notification()

            # Pass 2: process events and other RPCs
            for rpc in other_rpcs:
                try:
                    if isinstance(rpc, list):
                        # Array-form RPC (e.g. ["serverConnected", ...])
                        # These are handled by the client, nothing to do server-side
                        continue
                    rpc_type = rpc.get("type")
                    if rpc_type == "event":
                        self._handle_event(rpc)
                    elif rpc_type == "publishedEventHandler":
                        self._handle_published_event(rpc)
                    elif rpc_type == "channel":
                        node_id: int = rpc["node"]
                        channel_id: int = rpc["channel"]
                        args = rpc.get("args", [])
                        self._tree.handle_return_channel(node_id, channel_id, args)
                except Exception:
                    rpc_type = rpc.get("type", "unknown") if isinstance(rpc, dict) else rpc[0] if rpc else "unknown"
                    log.exception("Error processing RPC: %s", rpc_type)
                    self._show_error_notification()
        finally:
            _set_current_tree(None)

    def _show_error_notification(self):
        """Show an error notification in the UI after an unhandled exception."""
        from pyxflow.components.notification import Notification, NotificationVariant
        n = Notification("An internal error has occurred. Please contact the administrator.")
        n.position = Notification.Position.MIDDLE
        n.duration = 5000
        n.add_theme_variants(NotificationVariant.LUMO_ERROR)
        n.open()

    # =========================================================================
    # RPC Security Validation (matches Java Flow AbstractRpcInvocationHandler)
    # =========================================================================

    def _validate_rpc_node(self, node_id: int, rpc_type: str,
                           check_enabled: bool = True) -> bool:
        """Validate that a node is eligible for RPC processing.

        Checks (matching Java Flow's AbstractRpcInvocationHandler):
        1. Node exists in the state tree
        2. Node is attached (not detached/removed)
        3. Component is enabled (unless check_enabled=False)

        Returns True if the RPC should proceed, False if it should be ignored.
        """
        node = self._tree.get_node(node_id)
        if node is None:
            log.debug("Ignoring %s RPC for non-existent node: %d",
                      rpc_type, node_id)
            return False

        if not node.is_attached:
            log.debug("Ignoring %s RPC for detached node: %d",
                      rpc_type, node_id)
            return False

        if check_enabled:
            component = self._tree.get_component(node_id)
            if component and not component.is_enabled():
                log.debug("Ignoring %s RPC for disabled component: %d (%s)",
                          rpc_type, node_id, type(component).__name__)
                return False

        return True

    def _handle_event(self, rpc: dict[str, Any]):
        """Handle event RPC."""
        node_id: int = rpc["node"]
        event_type: str = rpc["event"]
        event_data = rpc.get("data", {})

        # ui-navigate is a global event, no node validation needed
        if event_type == "ui-navigate":
            self._handle_navigation(event_data)
            return

        # Validate node (attached + enabled) before processing
        if not self._validate_rpc_node(node_id, "event"):
            return

        if event_type == "click":
            self._handle_click(node_id, event_data)
        elif event_type == "change":
            self._handle_change(node_id, event_data)
        elif event_type == "keydown":
            self._handle_keydown(node_id, event_data)
        else:
            # Generic dispatch for events like opened-changed, closed, etc.
            element = self._tree.get_element(node_id)
            if element:
                element.fire_event(event_type, event_data)

    @staticmethod
    def _make_not_found_view(route: str) -> type:
        """Create a one-off view class that shows a 'Route not found' message.

        In dev mode, also lists all registered routes as clickable links.
        """
        from pyxflow.components.html import H3, Paragraph, Div
        from pyxflow.server.http_server import _dev_mode

        if _dev_mode:
            class _NotFoundView(Div):
                def __init__(self):
                    super().__init__()
                    from pyxflow.router import _routes
                    from pyxflow.components.router_link import RouterLink
                    from pyxflow.components.vertical_layout import VerticalLayout

                    self.get_style().set("padding", "1em")
                    self.add(H3(f"Could not navigate to '{route}'"))
                    links = VerticalLayout()
                    links.set_padding(False)
                    links.set_spacing(False)
                    for path in sorted(_routes):
                        label = f"/{path}" if path else "/"
                        links.add(RouterLink(label, f"/{path}"))
                    self.add(Paragraph("Available routes:"), links)
        else:
            class _NotFoundView(Div):
                def __init__(self):
                    super().__init__()
                    self.get_style().set("padding", "1em")
                    self.add(
                        H3(f"Could not navigate to '{route}'"),
                        Paragraph("Check that the route exists and is correctly registered."),
                    )
        return _NotFoundView

    def _handle_navigation(self, event_data: dict):
        """Handle navigation event - create or switch views.

        Supports three layout modes:
        1. Same layout class → reuse layout, only swap content
        2. New/different layout → create layout + view
        3. No layout → direct view in container (backward-compatible)
        """
        route = event_data.get("route", "")
        query_string = event_data.get("query", "")

        # Normalize route - strip leading/trailing slashes
        route = route.strip("/")

        # Use initial_route from request path if client sent empty or root route
        # This handles the case where the client's contextRootUrl calculation is wrong
        initial_route = getattr(self, "_initial_route", "")
        if not route and initial_route:
            route = initial_route

        # Note: we do NOT skip same-route navigations.  Even if route ==
        # _current_route, the browser URL may have changed via push_url()
        # (pushState without server navigation).  When the user presses
        # back, the route looks the same to us but before_enter() must
        # still run so the view can react (e.g. close a detail panel).
        # Java Flow also calls beforeEnter on every navigation.

        # Use router to find view class and params
        from pyxflow.router import match_route, _resolve_title

        result = match_route(route)
        view_class = None
        page_title = None
        params = {}
        layout_class = None

        if result:
            view_class, page_title, params, layout_class = result

        if view_class is None:
            # Fallback to http_server._view_class for backwards compatibility
            from pyxflow.server.http_server import _view_class
            if _view_class is not None:
                view_class = _view_class
            else:
                view_class = self._make_not_found_view(route)
                page_title = "Not Found"

        # --- Before leave guard on current view ---
        if self._view is not None and hasattr(self._view, 'before_leave'):
            if self._view.before_leave() is False:
                return  # Navigation cancelled

        is_first_navigation = (self._view is None and self._layout is None)

        # Set tree context so Notification.show() works during view construction
        from pyxflow.components.notification import _set_current_tree
        _set_current_tree(self._tree)
        try:
            ui = self._ui

            # Same view class → reuse instance, just re-invoke before_enter
            # (Java Flow reuses views for same-route-pattern navigations)
            if (self._view is not None
                    and type(self._view) is view_class):
                self._reenter_view(self._view, view_class, params,
                                   ui, query_string)
                view = self._view
            elif layout_class is not None:
                # --- Layout mode ---
                if self._layout_class is layout_class and self._layout is not None:
                    # Same layout class → reuse layout, just swap content
                    if self._view is not None:
                        self._layout.remove_router_layout_content(self._view)
                        self._view = None

                    view = self._create_view(view_class, params, ui, query_string)
                    self._layout.show_router_layout_content(view)
                else:
                    # Different/new layout → remove old root, create layout + view
                    if self._layout is not None:
                        self._container_node.remove_child(self._layout.element.node)
                        self._layout = None
                        self._layout_class = None
                        self._view = None
                    elif self._view is not None:
                        self._container_node.remove_child(self._view.element.node)
                        self._view = None

                    layout = layout_class()
                    layout._ui = ui
                    layout._attach(self._tree)

                    view = self._create_view(view_class, params, ui, query_string)
                    layout.show_router_layout_content(view)  # type: ignore[attr-defined]

                    self._container_node.add_child(layout.element.node)
                    self._layout = layout
                    self._layout_class = layout_class
            else:
                # --- No layout (backward-compatible) ---
                if self._layout is not None:
                    self._container_node.remove_child(self._layout.element.node)
                    self._layout = None
                    self._layout_class = None
                    self._view = None
                elif self._view is not None:
                    self._container_node.remove_child(self._view.element.node)
                    self._view = None

                view = self._create_view(view_class, params, ui, query_string)
                self._container_node.add_child(view.element.node)

            self._view = view
            self._current_route = route

            # Collect stylesheets from view/layout for EAGER dependencies
            self._collect_stylesheets(view_class, layout_class)

        except Exception as e:
            log.exception("Error creating view: %s", e)
            self._view = None
            self._show_error_notification()
            return
        finally:
            _set_current_tree(None)

        # After navigation callback
        if hasattr(view, 'after_navigation'):
            view.after_navigation()

        # Resolve dynamic title (instance method takes priority)
        page_title = _resolve_title(view_class, view) or "PyXFlow"

        # Build execute commands
        self._setup_execute_commands(page_title, is_first_navigation)

    def _reenter_view(self, view: Any, view_class: type, params: dict,
                       ui: Any, query_string: str = "") -> None:
        """Re-invoke lifecycle on an existing view (same route pattern, different params).

        Like Java Flow, reuses the view instance so that the DOM is NOT
        replaced -- enabling animations (e.g., MasterDetailLayout close)
        to complete without interruption.
        """
        from pyxflow.router import (
            BeforeEnterEvent, Location, QueryParameters, RouteParameters,
        )
        if params and hasattr(view, 'set_parameter'):
            view.set_parameter(params)

        if hasattr(view, 'before_enter'):
            route_params = RouteParameters(params)
            query_params = QueryParameters.from_string(query_string)
            path = getattr(view_class, '_route_path', '')
            location = Location(path, query_params)
            event = BeforeEnterEvent(
                location=location,
                route_parameters=route_params,
                navigation_target=view_class,
                ui=ui,
            )
            view.before_enter(event)

    def _create_view(self, view_class: type, params: dict, ui: Any,
                      query_string: str = "") -> Any:
        """Create and attach a view instance."""
        from pyxflow.router import (
            BeforeEnterEvent, Location, QueryParameters, RouteParameters,
        )
        view = view_class()
        view._ui = ui

        if params and hasattr(view, 'set_parameter'):
            view.set_parameter(params)

        if hasattr(view, 'before_enter'):
            route_params = RouteParameters(params)
            query_params = QueryParameters.from_string(query_string)
            path = getattr(view_class, '_route_path', '')
            location = Location(path, query_params)
            event = BeforeEnterEvent(
                location=location,
                route_parameters=route_params,
                navigation_target=view_class,
                ui=ui,
            )
            view.before_enter(event)

        view._attach(self._tree)
        return view

    def _setup_execute_commands(self, page_title: str, is_first_navigation: bool):
        """Build execute commands for navigation response.

        Args:
            page_title: The resolved page title
            is_first_navigation: True if this is the first navigation (needs keydown + serverConnected)
        """
        # Title is always set
        self._pending_execute.append([page_title, "document.title = $0"])

        # TextField invalid property (always)
        textfield_nodes = self._find_textfield_nodes()
        for tf_node_id in textfield_nodes:
            self._pending_execute.append(
                [False, {"@v-node": tf_node_id}, "return (async function() { this.invalid = $0}).apply($1)"]
            )

        # Dialog execute commands (always)
        dialog_nodes = self._find_dialog_nodes()
        for dialog_node_id in dialog_nodes:
            self._pending_execute.append(
                [{"@v-node": dialog_node_id}, "return (async function() { Vaadin.FlowComponentHost.patchVirtualContainer(this) }).apply($0)"]
            )
            self._pending_execute.append(
                [self._client_key, {"@v-node": dialog_node_id}, "return (async function() { this.renderer = (root) => Vaadin.FlowComponentHost.setChildNodes($0, this.virtualChildNodeIds, root) }).apply($1)"]
            )
            self._pending_execute.append(
                [{"@v-node": dialog_node_id}, "return (async function() { this.requestContentUpdate() }).apply($0)"]
            )
            self._pending_execute.append(
                [{"@v-node": dialog_node_id},
                 "return (async function() {"
                 "  this.$.overlay.addEventListener('vaadin-overlay-close', () => {"
                 "    document.addEventListener('vaadin-overlay-close', (e) => {"
                 "      if(!e.defaultPrevented && e.detail.overlay === this.$.overlay) {"
                 "        e.preventDefault();"
                 "        this.$server.handleClientClose();"
                 "      }"
                 "    }, {once: true})"
                 "  })"
                 "}).apply($0)"]
            )

        # First navigation only: keydown listener on body
        if is_first_navigation:
            self._tree.add_change({
                "node": self._body_node.id,
                "type": "put",
                "key": "keydown",
                "feat": Feature.ELEMENT_LISTENER_MAP,
                "value": _KEYDOWN_HASH
            })

        # serverConnected on every navigation (React Router waits for this
        # callback before completing pushState URL update).
        # Stored separately so _build_response can place it LAST -- after all
        # component execute_js commands.  If it fires earlier, the client
        # considers navigation "done" before component JS has run, which can
        # trigger a resync.
        self._server_connected_cmd = [
            False, {"@v-node": self._container_node.id},
            "return (async function() { this.serverConnected($0)}).apply($1)"
        ]

    def _collect_stylesheets(self, view_class: type, layout_class: type | None):
        """Collect stylesheets from view and layout classes as EAGER dependencies."""
        urls: list[str] = []
        # Layout stylesheets first
        if layout_class is not None:
            for url in getattr(layout_class, '_stylesheets', []):
                if url not in self._sent_stylesheets:
                    urls.append(url)
        # View stylesheets
        for url in getattr(view_class, '_stylesheets', []):
            if url not in self._sent_stylesheets:
                urls.append(url)
        for url in urls:
            self._pending_dependencies.append(
                {"type": "STYLESHEET", "url": url, "loadMode": "EAGER"}
            )
            self._sent_stylesheets.add(url)

    def _find_textfield_nodes(self) -> list[int]:
        """Find all TextField node IDs in the current view."""
        textfield_nodes = []
        for node_id, node in self._tree._nodes.items():
            tag = node.get(Feature.ELEMENT_DATA, "tag")
            if tag == "vaadin-text-field":
                textfield_nodes.append(node_id)
        return textfield_nodes

    def _find_dialog_nodes(self) -> list[int]:
        """Find all Dialog node IDs in the current view."""
        dialog_nodes = []
        for node_id, node in self._tree._nodes.items():
            tag = node.get(Feature.ELEMENT_DATA, "tag")
            if tag == "vaadin-dialog":
                dialog_nodes.append(node_id)
        return dialog_nodes

    def _add_execute_for_new_overlays(self, changes: list[dict]):
        """Add execute commands for newly attached dialog nodes.

        This scans the changes for 'attach' operations and adds FlowComponentHost
        execute commands for any newly attached overlay components.
        """
        # Find newly attached node IDs
        newly_attached = set()
        for change in changes:
            if change.get("type") == "attach":
                newly_attached.add(change.get("node"))

        # Check each newly attached node to see if it's a dialog
        for node_id in newly_attached:
            node = self._tree.get_node(node_id)
            if not node:
                continue
            tag = node.get(Feature.ELEMENT_DATA, "tag")

            if tag == "vaadin-dialog":
                # Patch the virtual container
                self._pending_execute.append(
                    [{"@v-node": node_id}, "return (async function() { Vaadin.FlowComponentHost.patchVirtualContainer(this) }).apply($0)"]
                )
                # Set up the renderer
                self._pending_execute.append(
                    [self._client_key, {"@v-node": node_id}, "return (async function() { this.renderer = (root) => Vaadin.FlowComponentHost.setChildNodes($0, this.virtualChildNodeIds, root) }).apply($1)"]
                )
                # Request content update
                self._pending_execute.append(
                    [{"@v-node": node_id}, "return (async function() { this.requestContentUpdate() }).apply($0)"]
                )
                # Register overlay close handler (calls $server.handleClientClose)
                self._pending_execute.append(
                    [{"@v-node": node_id},
                     "return (async function() {"
                     "  this.$.overlay.addEventListener('vaadin-overlay-close', () => {"
                     "    document.addEventListener('vaadin-overlay-close', (e) => {"
                     "      if(!e.defaultPrevented && e.detail.overlay === this.$.overlay) {"
                     "        e.preventDefault();"
                     "        this.$server.handleClientClose();"
                     "      }"
                     "    }, {once: true})"
                     "  })"
                     "}).apply($0)"]
                )
            elif tag == "vaadin-notification":
                # 1. Request content update BEFORE patching
                self._pending_execute.append(
                    [{"@v-node": node_id}, "return $0.requestContentUpdate()"]
                )
                # 2. Patch virtual container for FlowComponentHost
                self._pending_execute.append(
                    [{"@v-node": node_id}, "return (async function() { Vaadin.FlowComponentHost.patchVirtualContainer(this)}).apply($0)"]
                )
                # 3. Set renderer - uses text property or FlowComponentHost for children
                self._pending_execute.append(
                    [self._client_key, {"@v-node": node_id}, "return (async function() { this.renderer = (root) => {  if (this.text) {    root.textContent = this.text;  } else {    Vaadin.FlowComponentHost.setChildNodes($0, this.virtualChildNodeIds, root)  }}}).apply($1)"]
                )
                # 4. Request content update AFTER setting renderer
                self._pending_execute.append(
                    [{"@v-node": node_id}, "return $0.requestContentUpdate()"]
                )

    def _handle_click(self, node_id: int, event_data: dict):
        """Handle click event."""
        element = self._tree.get_element(node_id)
        if element:
            element.fire_event("click", event_data)

    def _handle_change(self, node_id: int, event_data: dict):
        """Handle change event."""
        element = self._tree.get_element(node_id)
        if element:
            element.fire_event("change", event_data)

    def _handle_keydown(self, node_id: int, event_data: dict):
        """Handle keydown event.

        If the component has a click shortcut registered, dispatch as click.
        Matches the pressed key against each component's shortcut key.
        """
        pressed_key = event_data.get("event.key", "")

        def _key_matches(shortcut_key):
            """Match if no shortcut key set, no key data sent, or keys match."""
            if shortcut_key is None or not pressed_key:
                return True
            return shortcut_key.value == pressed_key

        component = self._tree.get_component(node_id)
        if component and getattr(component, "_click_shortcut_registered", False):
            shortcut_key = getattr(component, "_click_shortcut_key", None)
            if _key_matches(shortcut_key):
                self._handle_click(node_id, event_data)
                return
        if node_id == self._body_node.id:
            # Global shortcut: scan all components for matching click shortcuts
            for comp in self._tree._components.values():
                if not getattr(comp, "_click_shortcut_registered", False):
                    continue
                shortcut_key = getattr(comp, "_click_shortcut_key", None)
                if _key_matches(shortcut_key):
                    self._handle_click(comp.element.node_id, event_data)
                    return
        # Generic keydown dispatch
        element = self._tree.get_element(node_id)
        if element:
            element.fire_event("keydown", event_data)

    def _handle_msync(self, rpc: dict[str, Any]):
        """Handle property sync RPC.

        Security checks (matching Java Flow MapSyncRpcHandler):
        1. Reject forbidden properties (textContent, classList, className, etc.)
        2. Reject if node is detached
        3. Reject if component is disabled (unless property has ALWAYS mode)
        4. Reject if property is not in the component's sync whitelist
        """
        node_id: int = rpc["node"]
        feature = rpc.get("feature")
        prop: str = rpc["property"]
        value = rpc.get("value")

        if feature != Feature.ELEMENT_PROPERTY_MAP:
            return

        # Security: reject forbidden properties
        if prop in FORBIDDEN_SYNC_PROPERTIES:
            log.warning("mSync blocked: forbidden property '%s' on node %d",
                        prop, node_id)
            return

        # Security: validate node exists and is attached
        node = self._tree.get_node(node_id)
        if node is None or not node.is_attached:
            log.debug("mSync ignored: node %d not found or detached", node_id)
            return

        component = self._tree.get_component(node_id)

        # Security: check disabled state with DisabledUpdateMode
        if component and not component.is_enabled():
            if prop not in type(component)._v_disabled_sync:
                log.debug("mSync blocked: property '%s' on disabled %s (node %d)",
                          prop, type(component).__name__, node_id)
                return

        # Security: property whitelist (None = allow all for backwards compat)
        if component:
            whitelist = type(component)._v_sync_properties
            if whitelist is not None and prop not in whitelist:
                log.warning("mSync blocked: property '%s' not in sync whitelist "
                            "for %s (node %d)",
                            prop, type(component).__name__, node_id)
                return

        # Update the node's property (without generating a change back)
        if feature not in node._features:
            node._features[feature] = {}
        node._features[feature][prop] = value

        # Also update the component's internal state
        if component:
            component._sync_property(prop, value)

    def _handle_published_event(self, rpc: dict[str, Any]):
        """Handle publishedEventHandler RPC (client-callable methods).

        Security checks (matching Java Flow PublishedServerEventHandlerRpcHandler):
        1. Node must exist, be attached, and be enabled (with DisabledUpdateMode)
        2. Method must be registered in Feature 19 (CLIENT_DELEGATE_HANDLERS)
        3. Argument count must match method signature
        4. Component must be attached to a UI

        Dispatches to the component method named by templateEventMethodName.
        Used by Dialog (handleClientClose), Grid (select, deselect, etc.),
        and user-defined @ClientCallable methods.

        When `promise` >= 0, the client expects a return value. The result
        is sent back via the internal `}p` promise-resolution method.
        """
        node_id: int = rpc["node"]
        method_name = rpc.get("templateEventMethodName")
        args = rpc.get("templateEventMethodArgs", [])
        promise_id = rpc.get("promise", -1)

        if not method_name:
            return

        # Security: validate node exists and is attached (skip enabled check,
        # we handle it below with DisabledUpdateMode)
        if not self._validate_rpc_node(node_id, "publishedEventHandler",
                                       check_enabled=False):
            return

        component = self._tree.get_component(node_id)
        if not component:
            log.debug("publishedEventHandler ignored: no component for node %d",
                      node_id)
            return

        # Security: check component is attached to UI
        if component._ui is None:
            log.warning("publishedEventHandler blocked: component not attached "
                        "to UI (node %d, method=%s, component=%s)",
                        node_id, method_name, type(component).__name__)
            return

        # Convert camelCase to snake_case for Python method lookup
        py_name = re.sub(r'([A-Z])', r'_\1', method_name).lower().lstrip('_')

        # Security: check disabled state with DisabledUpdateMode
        if not component.is_enabled():
            if py_name not in type(component)._v_disabled_methods:
                log.debug("publishedEventHandler blocked: method '%s' on "
                          "disabled %s (node %d)",
                          py_name, type(component).__name__, node_id)
                return

        # Security: verify method is registered (via @ClientCallable or _register_server_method)
        registered = getattr(component, '_registered_methods', set())
        if py_name not in registered:
            log.warning("publishedEventHandler blocked: method '%s' not "
                        "registered on %s (node %d). Registered: %s",
                        py_name, type(component).__name__, node_id,
                        registered)
            return

        method = getattr(component, py_name, None)
        if not method or not callable(method):
            log.warning("publishedEventHandler blocked: method '%s' not found "
                        "on %s (node %d)", py_name, type(component).__name__,
                        node_id)
            return

        # Security: validate argument count
        try:
            sig = inspect.signature(method)
            params = [p for p in sig.parameters.values()
                      if p.kind not in (inspect.Parameter.VAR_POSITIONAL,
                                        inspect.Parameter.VAR_KEYWORD)]
            required = sum(1 for p in params
                           if p.default is inspect.Parameter.empty)
            max_args = len(params)
            has_var = any(p.kind == inspect.Parameter.VAR_POSITIONAL
                         for p in sig.parameters.values())
            if not has_var and (len(args) < required or len(args) > max_args):
                log.warning("publishedEventHandler blocked: %s.%s expects "
                            "%d-%d args, got %d",
                            type(component).__name__, py_name,
                            required, max_args, len(args))
                return
        except (ValueError, TypeError):
            pass  # Can't inspect, allow through

        if promise_id == -1:
            method(*args)
        else:
            try:
                result = method(*args)
                component.element.execute_js(
                    "$0.$server['}p']($1, true, $2)",
                    promise_id, result
                )
            except Exception:
                component.element.execute_js(
                    "$0.$server['}p']($1, false)",
                    promise_id
                )
                raise

    def _build_resync_response(self) -> dict:
        """Build a resynchronize response with the full state tree.

        Like Java Flow's ``prepareForResync()``, re-emits all nodes so the
        client can rebuild its DOM from scratch.  We rebuild the entire view
        hierarchy (infrastructure nodes + navigation) so that connector init
        scripts and execute_js commands are also re-sent.

        Constants are NOT re-sent: FlowClient keeps its constant registry
        across resync and throws on duplicate hashes.
        """
        saved_route = self._current_route

        # Reset tree and handler state (like handle_init, but keep session)
        self._tree.reset()
        self._view = None
        self._layout = None
        self._layout_class = None
        self._current_route = None
        self._body_node = None
        self._container_node = None
        self._pending_execute = []
        self._server_connected_cmd = None
        # NOTE: Do NOT clear _sent_constants -- FlowClient keeps its constant
        # registry across resync (Y2/eE) and throws on duplicate hashes.
        self._sent_stylesheets.clear()
        self._pending_dependencies = []

        # Rebuild infrastructure nodes
        self._tree._app_id = self._app_id
        self._create_initial_nodes()

        # Re-navigate to current route (rebuilds view + layout + connectors)
        if saved_route is not None:
            self._handle_navigation({"route": saved_route})

        # Build a normal response (increments syncId, resolves constants)
        response = self._build_response()
        response["resynchronize"] = True
        return response

    def _build_response(self) -> dict:
        """Build UIDL response."""
        changes = self._tree.collect_changes()
        self._sync_id += 1
        # clientId reflects the last client message we processed
        self._client_id = self._last_client_id + 1

        # Check for newly attached notification or dialog nodes
        # and add execute commands for FlowComponentHost
        self._add_execute_for_new_overlays(changes)

        # Build constants dict with Base64 hashes
        # Only include constants that are actually used in changes
        constants = {}
        used_event_types = set()

        # Scan changes to find which event types are used
        for change in changes:
            if change.get("feat") == Feature.ELEMENT_LISTENER_MAP and change.get("value") is True:
                used_event_types.add(change.get("key"))

        # Map event types to their hashes and configs
        event_configs = {
            "click": (_CLICK_HASH, _CLICK_CONFIG),
            "change": (_CHANGE_HASH, _CHANGE_CONFIG),
            "input": (_CHANGE_HASH, _CHANGE_CONFIG),
            "blur": (_CHANGE_HASH, _CHANGE_CONFIG),
            "opened-changed": (_OPENED_CHANGED_HASH, _OPENED_CHANGED_CONFIG),
            "checked-changed": (_CHECKED_CHANGED_HASH, _CHECKED_CHANGED_CONFIG),
            "keydown": (_KEYDOWN_HASH, _KEYDOWN_CONFIG),
            "selected-changed": (_SELECTED_CHANGED_HASH, _SELECTED_CHANGED_CONFIG),
            "selected-values-changed": (_SELECTED_VALUES_CHANGED_HASH, _SELECTED_VALUES_CHANGED_CONFIG),
            "value-changed": (_VALUE_CHANGED_HASH, _VALUE_CHANGED_CONFIG),
            "selected-items-changed": (_SELECTED_ITEMS_CHANGED_HASH, _SELECTED_ITEMS_CHANGED_CONFIG),
            "splitter-dragend": (_SPLITTER_DRAGEND_HASH, _SPLITTER_DRAGEND_CONFIG),
        }

        # Add used constants and replace values with hash references.
        # Only send constants that haven't been sent in a previous response,
        # as FlowClient caches them and resending causes processing errors.
        for change in changes:
            if change.get("feat") == Feature.ELEMENT_LISTENER_MAP:
                value = change.get("value")
                if value is True:
                    # Resolve event type → hash via event_configs lookup
                    event_type = change.get("key")
                    if event_type in event_configs:
                        hash_key, config = event_configs[event_type]
                        if hash_key not in self._sent_constants:
                            constants[hash_key] = config
                            self._sent_constants.add(hash_key)
                        change["value"] = hash_key
                elif isinstance(value, str) and value in _HASH_TO_CONFIG:
                    # Explicit hash from component — only send config if new
                    if value not in self._sent_constants:
                        constants[value] = _HASH_TO_CONFIG[value]
                        self._sent_constants.add(value)

        response = {
            "syncId": self._sync_id,
            "clientId": self._client_id,
            "constants": constants,
            "changes": changes,
        }
        # Include EAGER stylesheet dependencies
        if self._pending_dependencies:
            response["EAGER"] = self._pending_dependencies
            self._pending_dependencies = []

        # Merge execute commands from both UidlHandler and tree (components).
        # serverConnected is always last -- it tells the client "navigation is
        # done", so all component JS must have been queued before it fires.
        tree_execute = self._tree.collect_execute()
        all_execute = self._pending_execute + tree_execute
        if self._server_connected_cmd is not None:
            all_execute.append(self._server_connected_cmd)
            self._server_connected_cmd = None
        if all_execute:
            response["execute"] = all_execute
        self._pending_execute = []
        self._last_response = response
        return response
