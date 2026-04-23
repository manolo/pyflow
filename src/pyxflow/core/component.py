"""Component - base class for UI components."""

from __future__ import annotations

import functools
from enum import Enum
from typing import TYPE_CHECKING

from pyxflow.core.element import Element, Style

if TYPE_CHECKING:
    from pyxflow.core.keys import Key
    from pyxflow.core.state_tree import StateTree


class DisabledUpdateMode(Enum):
    """Controls whether client updates are accepted when a component is disabled."""
    ONLY_WHEN_ENABLED = "ONLY_WHEN_ENABLED"
    ALWAYS = "ALWAYS"


# Properties that must NEVER be synced from client (security)
FORBIDDEN_SYNC_PROPERTIES = frozenset({
    "textContent", "classList", "className", "innerHTML", "outerHTML",
})


class _BufferedStyle:
    """Style manager that buffers before the component is attached.

    Before attach, set/get/remove operate on a local dict.
    After ``_flush(real_style)`` is called, all buffered values are applied
    and subsequent calls delegate directly to the real ``Style`` object.
    """

    def __init__(self):
        self._buffer: dict[str, str] = {}
        self._delegate: Style | None = None

    def set(self, name: str, value: str):
        if self._delegate is not None:
            self._delegate.set(name, value)
        else:
            self._buffer[name] = value

    def get(self, name: str) -> str | None:
        if self._delegate is not None:
            return self._delegate.get(name)
        return self._buffer.get(name)

    def remove(self, name: str):
        if self._delegate is not None:
            self._delegate.remove(name)
        else:
            self._buffer.pop(name, None)

    def _flush(self, real_style: Style):
        """Flush buffered values to the real Style and switch to delegation."""
        for name, value in self._buffer.items():
            real_style.set(name, value)
        self._buffer.clear()
        self._delegate = real_style


def ClientCallable(func):
    """Mark a component method as callable from client-side JavaScript.

    Client code can call: this.$server.methodName(arg1, arg2)
    """
    func._client_callable = True
    return func


class Component:
    """Base class for all UI components.

    Subclasses don't need to call ``super().__init__()`` — it is invoked
    automatically via ``__init_subclass__``, matching Java Vaadin behavior
    where the no-arg super constructor is called implicitly.
    """

    _tag: str = "div"

    # Properties the client is allowed to sync back (mSync whitelist).
    # None = allow all (backwards compat for unregistered components).
    # frozenset(...) = only these properties are allowed.
    _v_sync_properties: frozenset[str] | None = None

    # Properties that sync even when the component is disabled.
    _v_disabled_sync: frozenset[str] = frozenset()

    # @ClientCallable methods that execute even when the component is disabled.
    _v_disabled_methods: frozenset[str] = frozenset()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        orig_init = cls.__dict__.get("__init__")
        if orig_init is not None:
            @functools.wraps(orig_init)
            def _auto_init(self, *args, _orig=orig_init, _cls=cls, **kwargs):
                if not hasattr(self, "_component_init_done"):
                    super(_cls, self).__init__()
                _orig(self, *args, **kwargs)
            cls.__init__ = _auto_init

    def __init__(self):
        if hasattr(self, "_component_init_done"):
            return  # Already initialized (idempotent)
        self._component_init_done = True
        self._element: Element | None = None
        self._parent: Component | None = None
        self._ui: UI | None = None
        self._visible: bool = True
        self._enabled: bool = True
        self._class_names: set[str] = set()
        self._style = _BufferedStyle()
        self._pending_theme: str | None = None
        self._tooltip_element: Element | None = None
        self._click_shortcut_registered: bool = False
        self._registered_methods: set[str] = set()

    @property
    def element(self) -> Element:
        """Get the component's element."""
        if self._element is None:
            raise RuntimeError("Component not attached to a UI")
        return self._element

    def _create_element(self, tree: "StateTree") -> Element:
        """Create the element for this component."""
        return Element(self._tag, tree)

    def _attach(self, tree: "StateTree"):
        """Attach the component to a state tree."""
        self._element = self._create_element(tree)
        # Register component for property sync
        tree.register_component(self)
        # Flush buffered styles to the real element Style
        self._style._flush(self._element.get_style())
        # Apply deferred theme
        if self._pending_theme is not None:
            self._element.set_attribute("theme", self._pending_theme)
            self._pending_theme = None
        # Apply deferred id
        pending_id = getattr(self, "_pending_id", None)
        if pending_id is not None:
            self._element.set_attribute("id", pending_id)
            del self._pending_id
        # Apply deferred attributes (aria-label, aria-labelledby, etc.)
        pending_attrs = getattr(self, "_pending_attributes", None)
        if pending_attrs:
            for attr_name, attr_value in pending_attrs.items():
                if attr_value is not None:
                    self._element.set_attribute(attr_name, attr_value)
            pending_attrs.clear()
        # Apply deferred properties (helperText, etc.)
        pending_props = getattr(self, "_pending_properties", None)
        if pending_props:
            tooltip_text = pending_props.pop("_tooltip_text", None)
            for name, value in pending_props.items():
                self._element.set_property(name, value)
            pending_props.clear()
            if tooltip_text:
                self.set_tooltip_text(tooltip_text)
        # Apply deferred click listeners (only if base add_click_listener was used)
        if getattr(self, "_base_click_listeners", None) and not getattr(self, "_click_event_registered", False):
            self._click_event_registered = True
            self._element.add_event_listener("click", self._dispatch_click)
        # Apply deferred focus/blur listeners
        if getattr(self, "_focus_listeners", None) and not getattr(self, "_focus_event_registered", False):
            self._focus_event_registered = True
            from pyxflow.server.uidl_handler import _FOCUS_HASH
            self._element.add_event_listener("focus", self._dispatch_focus, hash_key=_FOCUS_HASH)
        if getattr(self, "_blur_listeners", None) and not getattr(self, "_blur_event_registered", False):
            self._blur_event_registered = True
            from pyxflow.server.uidl_handler import _BLUR_HASH
            self._element.add_event_listener("blur", self._dispatch_blur, hash_key=_BLUR_HASH)
        # Apply deferred class names
        if self._class_names:
            self._update_class_attribute()
        # Apply deferred click shortcut
        pending_shortcut = getattr(self, "_pending_click_shortcut", None)
        if pending_shortcut is not None:
            self._register_click_shortcut(pending_shortcut)
            del self._pending_click_shortcut
        # Apply deferred JS executions
        pending_js = getattr(self, "_pending_execute_js", None)
        if pending_js:
            for script, args in pending_js:
                self._element.execute_js(script, *args)
            del self._pending_execute_js
        # Apply deferred enabled state (disabled attribute)
        if not self._enabled:
            self._element.set_attribute("disabled", "")
        # Flush deferred DnD connector calls
        if getattr(self, "_pending_dnd_drag", False):
            del self._pending_dnd_drag
            self._element.execute_js(
                "window.Vaadin.Flow.dndConnector.updateDragSource($0)")
            # Register deferred drag event listeners
            if getattr(self, "_drag_start_listeners", None) \
                    and not getattr(self, "_dragstart_event_registered", False):
                self._dragstart_event_registered = True
                from pyxflow.server.uidl_handler import _DRAGSTART_HASH
                self._element.add_event_listener(
                    "dragstart", self._on_dragstart, hash_key=_DRAGSTART_HASH)
            if getattr(self, "_drag_end_listeners", None) \
                    and not getattr(self, "_dragend_event_registered", False):
                self._dragend_event_registered = True
                from pyxflow.server.uidl_handler import _DRAGEND_HASH
                self._element.add_event_listener(
                    "dragend", self._on_dragend, hash_key=_DRAGEND_HASH)
            # Flush deferred drag image
            pending_img = getattr(self, "_pending_drag_image", None)
            if pending_img is not None:
                img_comp, ox, oy = pending_img
                if img_comp._element is not None:
                    del self._pending_drag_image
                    self._element.execute_js(
                        "window.Vaadin.Flow.dndConnector.setDragImage($1, $2, $3, $0)",
                        img_comp._element, ox, oy)
                else:
                    # Image not attached yet; register so it flushes when it does
                    refs = getattr(img_comp, "_drag_image_refs", None)
                    if refs is None:
                        img_comp._drag_image_refs = refs = []
                    refs.append(self)
        if getattr(self, "_pending_dnd_drop", False):
            del self._pending_dnd_drop
            self._element.execute_js(
                "window.Vaadin.Flow.dndConnector.updateDropTarget($0)")
            # Register deferred drop event listener
            if getattr(self, "_drop_listeners", None) \
                    and not getattr(self, "_drop_event_registered", False):
                self._drop_event_registered = True
                from pyxflow.server.uidl_handler import _DROP_HASH
                self._element.add_event_listener(
                    "drop", self._on_drop, hash_key=_DROP_HASH)
        # Flush pending drag images for components that reference this as image
        drag_refs = getattr(self, "_drag_image_refs", None)
        if drag_refs:
            del self._drag_image_refs
            for src in drag_refs:
                pending = getattr(src, "_pending_drag_image", None)
                if pending and src._element is not None:
                    del src._pending_drag_image
                    img_comp, ox, oy = pending
                    src._element.execute_js(
                        "window.Vaadin.Flow.dndConnector.setDragImage($1, $2, $3, $0)",
                        img_comp._element, ox, oy)
        # Auto-register @ClientCallable methods in Feature 19
        self._register_client_callable_methods(tree)

    def _register_client_callable_methods(self, tree: "StateTree"):
        """Register @ClientCallable methods in Feature 19 (CLIENT_DELEGATE_HANDLERS)."""
        from pyxflow.core.state_node import Feature
        callable_methods = []
        seen = set()
        for cls in type(self).__mro__:
            for name, method in cls.__dict__.items():
                if name not in seen and callable(method) and getattr(method, '_client_callable', False):
                    callable_methods.append(name)
                    seen.add(name)
        if callable_methods:
            self._registered_methods.update(callable_methods)
            tree.add_change({
                "node": self._element.node_id,
                "type": "splice",
                "feat": Feature.CLIENT_DELEGATE_HANDLERS,
                "index": 0,
                "add": callable_methods,
            })

    def _register_server_method(self, method_name: str):
        """Register a method name as callable from client (for security whitelist).

        Called by components that register methods via direct splice (Dialog,
        Grid, etc.) rather than @ClientCallable. The snake_case name must match
        the actual Python method.
        """
        self._registered_methods.add(method_name)

    def get_element(self) -> Element:
        """Get the element (public API)."""
        return self.element

    def execute_js(self, script: str, *args):
        """Execute JavaScript on this component's element.

        If the component is not yet attached, the call is buffered
        and executed when the component is attached to a UI.
        """
        if self._element is not None:
            self._element.execute_js(script, *args)
        else:
            if not hasattr(self, "_pending_execute_js"):
                self._pending_execute_js = []
            self._pending_execute_js.append((script, args))

    def _sync_property(self, name: str, value):
        """Called when a property is synced from client.

        Subclasses can override to handle specific properties.
        """
        pass

    # Visibility methods

    def is_visible(self) -> bool:
        """Check if the component is visible."""
        return self._visible

    def set_visible(self, visible: bool):
        """Set the visibility of the component.

        When a component is set to invisible, it is not rendered on the page.
        """
        self._visible = visible
        if not visible:
            self._style.set("display", "none")
        else:
            self._style.remove("display")

    # Enabled methods

    def is_enabled(self) -> bool:
        """Check if the component is enabled."""
        return self._enabled

    def set_enabled(self, enabled: bool):
        """Set the enabled state of the component.

        When a component is disabled, it cannot receive user input.
        """
        self._enabled = enabled
        if self._element:
            # Most Vaadin components use the 'disabled' attribute
            if enabled:
                self.element.remove_attribute("disabled")
            else:
                self.element.set_attribute("disabled", "")

    # Class name methods

    def add_class_name(self, *class_names: str):
        """Add one or more CSS class names to the component."""
        for class_name in class_names:
            self._class_names.add(class_name)
        self._update_class_attribute()

    def remove_class_name(self, *class_names: str):
        """Remove one or more CSS class names from the component."""
        for class_name in class_names:
            self._class_names.discard(class_name)
        self._update_class_attribute()

    def has_class_name(self, class_name: str) -> bool:
        """Check if the component has a specific CSS class name."""
        return class_name in self._class_names

    def get_class_names(self) -> set[str]:
        """Get all CSS class names of the component."""
        return self._class_names.copy()

    def set_class_name(self, class_name: str, add: bool = True):
        """Add or remove a CSS class name.

        Args:
            class_name: The class name to add or remove
            add: If True, adds the class; if False, removes it
        """
        if add:
            self.add_class_name(class_name)
        else:
            self.remove_class_name(class_name)

    def _update_class_attribute(self):
        """Update the class attribute on the element."""
        if self._element:
            if self._class_names:
                self.element.set_attribute("class", " ".join(sorted(self._class_names)))
            else:
                self.element.remove_attribute("class")

    # --- HasSize methods ---

    def set_width(self, width: str | None):
        """Set width (e.g., '100px', '50%', '10em'). None removes width."""
        self._style.set("width", width or "")

    def get_width(self) -> str | None:
        return self._style.get("width")

    def set_height(self, height: str | None):
        """Set height (e.g., '100px', '50%', '10em'). None removes height."""
        self._style.set("height", height or "")

    def get_height(self) -> str | None:
        return self._style.get("height")

    def set_min_width(self, min_width: str | None):
        self._style.set("min-width", min_width or "")

    def get_min_width(self) -> str | None:
        return self._style.get("min-width")

    def set_max_width(self, max_width: str | None):
        self._style.set("max-width", max_width or "")

    def get_max_width(self) -> str | None:
        return self._style.get("max-width")

    def set_min_height(self, min_height: str | None):
        self._style.set("min-height", min_height or "")

    def get_min_height(self) -> str | None:
        return self._style.get("min-height")

    def set_max_height(self, max_height: str | None):
        self._style.set("max-height", max_height or "")

    def get_max_height(self) -> str | None:
        return self._style.get("max-height")

    def set_size_full(self):
        """Set both width and height to 100%."""
        self.set_width("100%")
        self.set_height("100%")

    def set_width_full(self):
        """Set width to 100%."""
        self.set_width("100%")

    def set_height_full(self):
        """Set height to 100%."""
        self.set_height("100%")

    def set_size_undefined(self):
        """Remove both width and height."""
        self.set_width(None)
        self.set_height(None)

    # --- HasTheme methods ---

    def _get_theme_set(self) -> set[str]:
        """Get current theme names as a set."""
        if self._element:
            current = self._element.get_attribute("theme") or ""
        elif self._pending_theme:
            current = self._pending_theme
        else:
            current = ""
        return set(current.split()) if current else set()

    def _apply_theme_set(self, names: set[str]):
        """Apply a set of theme names."""
        value = " ".join(sorted(names)) if names else None
        if self._element:
            if value:
                self._element.set_attribute("theme", value)
            else:
                self._element.remove_attribute("theme")
        else:
            self._pending_theme = value

    def add_theme_name(self, *theme_names: str):
        """Add one or more theme names."""
        names = self._get_theme_set()
        names.update(theme_names)
        self._apply_theme_set(names)

    def remove_theme_name(self, *theme_names: str):
        """Remove one or more theme names."""
        names = self._get_theme_set()
        names -= set(theme_names)
        self._apply_theme_set(names)

    def has_theme_name(self, theme_name: str) -> bool:
        """Check if the component has a specific theme name."""
        return theme_name in self._get_theme_set()

    def get_theme_name(self) -> str | None:
        """Get theme names as space-separated string."""
        if self._element:
            return self._element.get_attribute("theme")
        return self._pending_theme

    def set_theme_name(self, theme_name: str | None):
        """Set theme names, overwriting any previous ones. None removes all."""
        if self._element:
            if theme_name:
                self._element.set_attribute("theme", theme_name)
            else:
                self._element.remove_attribute("theme")
        else:
            self._pending_theme = theme_name

    # --- Id methods ---

    def set_id(self, id: str):
        """Set the component's id attribute."""
        if self._element:
            self._element.set_attribute("id", id)
        else:
            # Buffer for later
            self._pending_id = id

    def get_id(self) -> str | None:
        """Get the component's id attribute."""
        if self._element:
            return self._element.get_attribute("id")
        return getattr(self, "_pending_id", None)

    # --- Helper text ---

    def set_helper_text(self, text: str):
        """Set the helper text shown below the field."""
        if self._element:
            self._element.set_property("helperText", text)
        else:
            if not hasattr(self, "_pending_properties"):
                self._pending_properties = {}
            self._pending_properties["helperText"] = text

    def get_helper_text(self) -> str:
        """Get the helper text."""
        if self._element:
            return self._element.get_property("helperText", "")
        return getattr(self, "_pending_properties", {}).get("helperText", "")

    # --- Focus / Blur ---

    def focus(self):
        """Focus this component."""
        if self._element:
            self._element._tree.queue_execute([
                {"@v-node": self._element.node_id},
                "return (async function() { setTimeout(function(){$0.focus()},0) }).apply($0)"
            ])

    def blur(self):
        """Remove focus from this component."""
        if self._element:
            self._element._tree.queue_execute([
                {"@v-node": self._element.node_id},
                "return (async function() { setTimeout(function(){$0.blur()},0) }).apply($0)"
            ])

    # --- ARIA Label (HasAriaLabel) ---

    def set_aria_label(self, label: str | None):
        """Set the aria-label attribute."""
        if self._element:
            if label is not None:
                self._element.set_attribute("aria-label", label)
            else:
                self._element.remove_attribute("aria-label")
        else:
            if not hasattr(self, "_pending_attributes"):
                self._pending_attributes = {}
            self._pending_attributes["aria-label"] = label

    def get_aria_label(self) -> str | None:
        """Get the aria-label attribute."""
        if self._element:
            return self._element.get_attribute("aria-label")
        return getattr(self, "_pending_attributes", {}).get("aria-label")

    def set_aria_labelled_by(self, labelled_by: str | None):
        """Set the aria-labelledby attribute."""
        if self._element:
            if labelled_by is not None:
                self._element.set_attribute("aria-labelledby", labelled_by)
            else:
                self._element.remove_attribute("aria-labelledby")
        else:
            if not hasattr(self, "_pending_attributes"):
                self._pending_attributes = {}
            self._pending_attributes["aria-labelledby"] = labelled_by

    def get_aria_labelled_by(self) -> str | None:
        """Get the aria-labelledby attribute."""
        if self._element:
            return self._element.get_attribute("aria-labelledby")
        return getattr(self, "_pending_attributes", {}).get("aria-labelledby")

    # --- Focus / Blur listeners (FocusNotifier / BlurNotifier) ---

    def add_focus_listener(self, listener):
        """Add a focus event listener."""
        if not hasattr(self, "_focus_listeners"):
            self._focus_listeners = []
        self._focus_listeners.append(listener)
        if self._element is not None and not getattr(self, "_focus_event_registered", False):
            self._focus_event_registered = True
            from pyxflow.server.uidl_handler import _FOCUS_HASH
            self._element.add_event_listener("focus", self._dispatch_focus, hash_key=_FOCUS_HASH)

    def _dispatch_focus(self, event_data: dict):
        for listener in getattr(self, "_focus_listeners", []):
            listener(event_data)

    def add_blur_listener(self, listener):
        """Add a blur event listener."""
        if not hasattr(self, "_blur_listeners"):
            self._blur_listeners = []
        self._blur_listeners.append(listener)
        if self._element is not None and not getattr(self, "_blur_event_registered", False):
            self._blur_event_registered = True
            from pyxflow.server.uidl_handler import _BLUR_HASH
            self._element.add_event_listener("blur", self._dispatch_blur, hash_key=_BLUR_HASH)

    def _dispatch_blur(self, event_data: dict):
        for listener in getattr(self, "_blur_listeners", []):
            listener(event_data)

    # --- Tooltip ---

    def set_tooltip_text(self, text: str):
        """Set the tooltip text. Creates a <vaadin-tooltip> child element."""
        if not self._element:
            if not hasattr(self, "_pending_properties"):
                self._pending_properties = {}
            self._pending_properties["_tooltip_text"] = text
            return

        if self._tooltip_element is None:
            # Create tooltip element as child
            tooltip = Element("vaadin-tooltip", self._element._tree)
            tooltip.set_attribute("slot", "tooltip")
            tooltip.set_property("text", text)
            self._element.add_child(tooltip)
            self._tooltip_element = tooltip
        else:
            self._tooltip_element.set_property("text", text)

    def get_tooltip_text(self) -> str | None:
        """Get the tooltip text."""
        if self._tooltip_element:
            return self._tooltip_element.get_property("text")
        props = getattr(self, "_pending_properties", {})
        return props.get("_tooltip_text")

    # --- Click listener (base) ---

    def add_click_listener(self, listener):
        """Add a click listener. Works on any component."""
        if not hasattr(self, "_base_click_listeners"):
            self._base_click_listeners = []
        self._base_click_listeners.append(listener)
        # Register click event on element if attached and not already registered
        if self._element and not getattr(self, "_click_event_registered", False):
            self._click_event_registered = True
            self.element.add_event_listener("click", self._dispatch_click)

    def _dispatch_click(self, event_data: dict):
        """Dispatch click event to base click listeners."""
        for listener in getattr(self, "_base_click_listeners", []):
            listener(event_data)

    # --- Keyboard Shortcuts ---

    def add_click_shortcut(self, key: Key):
        """Register a keyboard shortcut that triggers click on this component.

        Args:
            key: The Key to use as shortcut (e.g., Key.ENTER).
        """
        if self._click_shortcut_registered:
            return
        self._click_shortcut_registered = True
        self._click_shortcut_key = key

        if self._element:
            self._register_click_shortcut(key)
        else:
            self._pending_click_shortcut = key

    def _register_click_shortcut(self, key: Key):
        """Internal: register the keydown listener for the click shortcut."""
        from pyxflow.server.uidl_handler import _KEYDOWN_HASH

        # Register keydown event listener with the ENTER hash
        # The uidl_handler will dispatch keydown → click for this component
        self.element.add_event_listener("keydown", lambda e: None, hash_key=_KEYDOWN_HASH)

    # --- UI access ---

    def get_ui(self) -> "UI | None":
        """Get the UI this component belongs to."""
        return self._ui

    # --- HasStyle shortcut ---

    def get_style(self) -> _BufferedStyle:
        """Get the inline style manager.

        Works both before and after the component is attached.
        Before attach, operations are buffered and flushed on attach.
        """
        return self._style


class UI:
    """The root UI component."""

    def __init__(self, tree: "StateTree"):
        self._tree = tree
        tree._ui = self  # Back-reference so auto-add paths can find the UI
        self._root: Component | None = None
        self._theme: str = "lumo"
        self._variant: str = "light"
        self._active_drag_source: Component | None = None
        # Initialize from @ColorScheme on @AppShell if set
        from pyxflow.router import get_app_shell
        app_shell = get_app_shell()
        cs = getattr(app_shell, '_color_scheme', None) if app_shell else None
        if cs and cs != "normal":
            self._variant = "dark" if "dark" in cs else "light"

    @property
    def tree(self) -> "StateTree":
        return self._tree

    def set_content(self, component: Component):
        """Set the root content."""
        self._root = component
        component._ui = self
        component._attach(self._tree)

    def access(self, callback):
        """Execute callback and push changes to client.

        Use this to modify UI from background tasks/coroutines.
        The callback runs synchronously, then pending changes are pushed.
        """
        callback()
        self._tree.notify_push()

    def push(self):
        """Manually push pending changes to client."""
        self._tree.notify_push()

    _THEME_CSS = {"lumo": "lumo/lumo.css", "aura": "aura/aura.css"}

    def get_theme(self) -> str:
        """Get the current theme name ("lumo" or "aura")."""
        return self._theme

    def get_theme_variant(self) -> str:
        """Get the current theme variant ("light" or "dark")."""
        return self._variant

    def set_theme(self, theme: str, variant: str = "light") -> None:
        """Switch theme and color variant at runtime.

        Args:
            theme: "lumo" or "aura".
            variant: "light" or "dark".

        Lumo dark uses ``theme="dark"`` attribute on ``<html>``.
        Aura dark uses the native ``color-scheme: dark`` CSS property.
        """
        if not theme:
            return
        self._theme = theme
        self._variant = variant
        new_href = self._THEME_CSS[theme]
        other_href = self._THEME_CSS["aura" if theme == "lumo" else "lumo"]
        is_dark = "1" if variant == "dark" else ""
        is_lumo = "1" if theme == "lumo" else ""

        # Remove ALL theme links (both lumo and aura) then add the new one.
        # Lumo: theme="dark" attr, Aura: color-scheme CSS property.
        js = (
            "return (async function() {"
            "  var h = document.documentElement;"
            "  document.querySelectorAll("
            "    'link[rel=stylesheet][href*=\"' + $0 + '\"],"
            "     link[rel=stylesheet][href*=\"' + $1 + '\"]'"
            "  ).forEach(function(l) { l.remove(); });"
            "  var l = document.createElement('link');"
            "  l.rel = 'stylesheet'; l.href = $1;"
            "  document.head.appendChild(l);"
            "  if ($3) {"
            "    h.removeAttribute('theme');"
            "    h.style.colorScheme = '';"
            "    if ($2) h.setAttribute('theme', 'dark');"
            "  } else {"
            "    h.removeAttribute('theme');"
            "    h.style.colorScheme = $2 ? 'dark' : 'light';"
            "  }"
            "})()"
        )
        self._tree.queue_execute([other_href, new_href, is_dark, is_lumo, js])

    def set_color_scheme(self, value: str) -> None:
        """Set the color scheme at runtime.

        Modifies ``<html>`` theme attribute and CSS color-scheme property.

        Args:
            value: "dark", "light", "light dark", "dark light", "system",
                   or "normal" (removes both attributes).
        """
        if value == "system":
            value = "light dark"
        if value and value not in ("normal", "light dark"):
            self._variant = "dark" if "dark" in value else "light"
        if not value or value == "normal":
            js = (
                "return (function(){"
                "var h=document.documentElement;"
                "h.removeAttribute('theme');"
                "h.style.colorScheme='';"
                "})()"
            )
            self._tree.queue_execute([js])
        else:
            theme_attr = value.replace(' ', '-')
            js = (
                "return (function(){"
                "var h=document.documentElement;"
                "h.setAttribute('theme',$0);"
                "h.style.colorScheme=$1;"
                "})()"
            )
            self._tree.queue_execute([theme_attr, value, js])

    def navigate(self, path: str) -> None:
        """Navigate to a new route (SPA-style, no page reload).

        Triggers a full client-side navigation through React Router,
        which sends a ``ui-navigate`` event back to the server.
        The target view will be created (or re-created) normally.

        Args:
            path: The target route path (e.g., ``"about"``, ``"user/123"``).
        """
        js = (
            "return (function(){"
            "window.dispatchEvent(new CustomEvent('vaadin-navigate',"
            "{detail:{url:$0,state:null,replace:false,callback:true}}));"
            "})()"
        )
        self._tree.queue_execute([path, js])

    def push_url(self, path: str) -> None:
        """Update the browser URL without triggering navigation.

        Adds a new entry to the browser history stack so the back button
        returns to the previous URL.  Uses ``vaadin-navigate`` with
        ``callback:false`` so React Router manages the history state
        (incrementing its internal ``idx``), but no server round-trip
        is triggered.

        The path must be relative (no leading ``/``).  A leading slash
        is stripped automatically to match ``navigate()`` semantics --
        ``vaadin-navigate`` URLs are relative to ``<base href="/">``.

        Args:
            path: The route path (e.g., ``"crud/42"``, ``"/crud/42"``).
        """
        path = path.lstrip("/")
        js = (
            "return (function(){"
            "window.dispatchEvent(new CustomEvent('vaadin-navigate',"
            "{detail:{url:$0,state:null,replace:false,callback:false}}));"
            "})()"
        )
        self._tree.queue_execute([path, js])

    def set_theme_variant(self, variant: str) -> None:
        """Switch only the color variant (light/dark) without changing the theme.

        Args:
            variant: "light" or "dark".
        """
        self._variant = variant
        theme_attr = variant if variant == "dark" else ""
        js = (
            "return (async function() {"
            "  if ($0) document.documentElement.setAttribute('theme', $0);"
            "  else document.documentElement.removeAttribute('theme');"
            "})()"
        )
        self._tree.queue_execute([theme_attr, js])
