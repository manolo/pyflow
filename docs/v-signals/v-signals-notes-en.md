# Speaker notes for v-signals.html

_Auto-extracted from `v-signals.html`: edit me, then run `./inject-notes.py en`._

## Slide 1: Vaadin Signals

- We all know signals from the JS world: SolidJS, Preact, Angular.
- Now Vaadin brings the same model to server-side Java.
- Today we'll see why this matters and what's different.

## Slide 2: The tangle

- Every dev who has built a non-trivial form has lived this.
- The video calls it a "notepad to keep track of what updates what".
- That's exactly the problem reactive systems were designed to kill.

## Slide 3: Why signals?

- The frontend world has spent 15 years answering this question.
- Let's recap quickly because Vaadin inherits all of that thinking.

## Slide 4: Imperative vs Reactive

- The imperative version works, but each new field doubles the listener wiring.
- The reactive version doesn't grow that way: each piece of state declares what it depends on.
- The framework figures out the update order.

## Slide 5: Push, Pull, Push-Pull

- Three models.
- Pull is React: rerender and diff.
- Push is Knockout-style observables: any change fires every subscriber.
- Push-pull is what SolidJS popularised and Preact/Angular/Vaadin all adopted. Best of both worlds.

## Slide 6: A 15-year overnight success

- The signal idea is older than React. It went dormant during the virtual-DOM era and came back stronger.
- TC39 is the ECMA committee that defines the official JavaScript standard.
- Proposals go through 4 stages: 1 (idea accepted), 2 (draft), 3 (spec ready), 4 (in the language).
- Signals reaching stage 1 in 2024 means industry consensus: the proposal is backed by authors from Angular, Solid, Vue, Svelte, Preact and Qwik.
- Vaadin 25.1 brings it to Java, and its API is aligned with that proposal.

## Slide 7

- This is the key insight.
- Signals separate WHAT depends on what from WHEN and HOW to update.
- The framework owns the WHEN. You only describe the WHAT.

## Slide 8: Three primitives

- Three building blocks. That's it.
- Signal, computed, effect.
- Every signals library is some flavour of these three.

## Slide 9: signal: a reactive value

- A signal is a box around a value.
- The box notifies anyone listening when the value changes.
- That's the whole API surface for the first primitive.

## Slide 10: computed: derived state

- Computed is the Excel formula.
- It tracks which signals it reads, and re-evaluates only when those change.
- And only when someone actually asks for its value.
- Lazy and memoised.

## Slide 11: effect: the outside world

- Effects are where reactivity meets reality.
- You read signals, you do a side effect (update the DOM, call an API, log).
- When any signal you read changes, the effect re-runs.
- Vaadin scopes effects to the component lifecycle automatically.

## Slide 12: Three primitives, one flow

- Walk through the steps with the Next button.
- Show signal -&gt; computed -&gt; effect once, then click the increment and watch the packet propagate.
- Last step: glitch-free guarantee.
- Emphasise: one push, each subscriber runs once.

## Slide 13: Glitch-free, guaranteed

- This is what "glitch-free" means and why naive observable libraries get it wrong.
- When 'a' changes, 'b' and 'c' both depend on it. A naive system would fire the effect twice.
- Signals run it once, with the correct final value.
- This matters at scale.

## Slide 14: Vaadin's solution

- Everything we've seen so far runs in the browser.
- Vaadin's contribution: put the same primitives on the JVM, and let them sync across users automatically.

## Slide 15: Signals, but on the JVM

- Three things JS signals don't give you.
- Threads, sharing across users, and atomic batches.
- That's what makes signals on the JVM more than just a port.

## Slide 16: Hello world with Vaadin Signals

- A full Vaadin hello-world with signals.
- Notice: no addValueChangeListener anywhere.
- The bindText call creates a subscription automatically and tears it down when the component is detached.
- That's the whole pitch.

## Slide 17: The binding API

- The binding API is the high-level facade.
- Most of the time you'll never write a raw effect: you'll bind a component property to a signal and Vaadin handles the rest.

## Slide 18: One signal, every user

- This is the killer demo.
- One ListSignal on the server. Three distinct users, each in their own browser, see the same data live.
- No WebSocket code, no event bus, no Redis pub-sub. The framework handles propagation.
- Try doing this with React + REST. You'd need a backend pub-sub, a WS endpoint, optimistic updates...

## Slide 19: Before & after

- Same feature. 75% less code.
- And the "after" version has no risk of forgetting a listener, no risk of stale state.
- The dependency graph is described, not orchestrated.

## Slide 20: Explainer video

- A short video tour from the Vaadin team. Two minutes.
- Watch it together, then questions.

## Slide 21: Video

- Play the video.
- The Spanish dub is the second source: remove the English source above it if you want the Spanish version to play by default.
- After the video, ask: who would use this on Monday? What pattern in your current codebase does this kill?

## Slide 22: Get started

- Three lines: add the dependency, create a signal, bind it to a component.
- Show the docs link.
- Mention the TC39 link for context: the same model is heading into the JS standard library.

## Slide 23: Signals

- That's the whole talk in one line.
- Open the floor.
