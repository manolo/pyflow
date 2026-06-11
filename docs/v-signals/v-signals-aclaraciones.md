# Aclaraciones para la charla de Vaadin Signals

Notas de apoyo para responder preguntas durante o despues de la presentacion `v-signals-es.html`.

---

## 1. ¿Que es un "glitch"?

Un glitch en programacion reactiva es un **valor intermedio incorrecto** que un suscriptor ve durante una actualizacion.

### Ejemplo

```js
a = signal(1)            // a=1
b = computed(() => a * 2)   // b=2 (depende de a)
c = computed(() => a + b)   // c=3 (depende de a Y b)
```

Cambias `a = 5`. Lo correcto: `b=10`, `c=15`.

**Sistema ingenuo (push directo):**

1. `a` cambia → notifica a `c` primero → `c` lee `a=5`, `b=2` (aun no actualizado) → `c=7` ← **GLITCH**
2. `a` notifica a `b` → `b=10`
3. `b` notifica a `c` → `c=15` (ya correcto)

Durante un instante `c` valio `7`. Si en ese instante se renderizo en pantalla, el usuario vio un parpadeo.

**Signals lo evita:** ordena el grafo de dependencias topologicamente. Actualiza `b` antes que `c`. `c` se calcula UNA sola vez con los valores correctos. No hay valor intermedio.

### Terminos relacionados

| Termino | Significado tecnico |
|---|---|
| **Atomico** | Indivisible bajo acceso concurrente. No se ve estado parcial entre hilos. |
| **Transaccional** | Varias escrituras agrupadas en una unidad. Los subscribers solo ven el estado final del bloque. |
| **Glitch-free** | El grafo de dependencias se propaga en orden correcto. Cada subscriber corre una sola vez con valores consistentes. |

Los tres comparten la idea de "no se ve estado intermedio" pero responden a problemas diferentes (hilos vs lotes vs grafo).

---

## 2. ¿Preact es parte de React?

**No.** Son dos librerias distintas e independientes.

| | React | Preact |
|---|---|---|
| **Quien** | Meta (Facebook) | Jason Miller, independiente |
| **Año** | 2013 | 2015 |
| **Tamaño** | ~45 KB | ~3 KB |
| **API** | `useState`, `useEffect`, JSX, hooks | **La misma API que React** |
| **Signals nativos** | No | Si (`@preact/signals`) |

Preact es una **alternativa compatible** con React. La idea: "lo mismo que React pero 15 veces mas pequeño". Tu codigo React funciona en Preact con un alias (`preact/compat`).

**Quien usa Preact:** Uber (app movil web), NYT, Bloomberg, Lyft, Etsy, Tencent, Google Lighthouse.

### El detalle importante

El equipo de Preact creo `@preact/signals` como **libreria standalone**, y la portaron a React con `@preact/signals-react`. Asi que **puedes usar signals de Preact en una app React**.

Pero React core, el oficial de Meta, **no tiene signals como API nativa**.

---

## 3. ¿Por que React no aparece en el timeline?

Porque React **no tiene signals como API nativa**. Usa hooks (`useState` + `useEffect`) que son fundamentalmente distintos.

### Frameworks con signals nativos (los del timeline)

| Framework | Año | API |
|---|---|---|
| Knockout | 2010 | `ko.observable()`, `ko.computed()` |
| SolidJS | 2018 | `createSignal()`, `createMemo()`, `createEffect()` |
| Vue 3 | 2020 | `ref()`, `computed()`, `watch()` |
| @preact/signals | 2022 | `signal()`, `computed()`, `effect()` |
| Angular | 2023 | `signal()`, `computed()`, `effect()` |
| TC39 | 2024 | propuesta Stage 1 |
| Vaadin | 2025 | `ValueSignal`, `Signal.computed()`, `Signal.effect()` |

### La respuesta de React

React eligio resolver el mismo problema (re-renders innecesarios) de otra forma: el **React Compiler** (2024+).

---

## 4. ¿Que es el React Compiler?

Es el camino que tomo React **en lugar** de signals. Salio en 2024.

### El problema que ambos resuelven

React por defecto re-renderiza componentes enteros cuando algo cambia. Desperdicia CPU. Los devs llevan años poniendo `useMemo`, `useCallback`, `React.memo` a mano para evitarlo.

### Dos soluciones distintas

**Signals (SolidJS, Preact, Angular, Vaadin):**
- Declara dependencias explicitas en el codigo.
- El framework actualiza solo lo necesario, en orden correcto, sin re-render.
- Cambias el modelo mental.

**React Compiler:**
- Un compilador que analiza tu codigo en build-time.
- Mete automaticamente todos los `useMemo` y `React.memo` que tendrias que escribir a mano.
- Mismo codigo, mismo modelo mental (hooks + virtual DOM).

```jsx
// Tu escribes esto:
function Hello({ name }) {
  return <h1>Hola {name}</h1>;
}

// React Compiler lo transforma en build a algo
// equivalente a memoizarlo automaticamente.
```

### Resumen

- **Signals:** cambia el modelo, declara dependencias, el problema desaparece.
- **React Compiler:** mantiene el modelo, automatiza las optimizaciones.

---

## 5. ¿Que es Knockout?

**Knockout.js** es una libreria JavaScript de **2010**, anterior a React, Angular y Vue. Fue de las primeras en popularizar la programacion declarativa y reactiva en el navegador.

### Datos basicos

- **Creador:** Steve Sanderson, ingeniero de Microsoft
- **Lanzamiento:** Julio 2010
- **Estado:** mantenida pero ya no popular (en declive desde 2016)

### El modelo: observables

Knockout introdujo en el mundo JS los **observables**, ancestro directo de los signals modernos:

```js
// Declarar
var name = ko.observable("Ada");

// Leer
console.log(name());        // "Ada"

// Escribir
name("Lovelace");

// Suscribirse
name.subscribe(function(newValue) {
  console.log("Name changed to " + newValue);
});

// Computed
var fullName = ko.computed(function() {
  return name() + " Lovelace";
});
```

Practicamente el mismo modelo que `@preact/signals` 12 años despues. La diferencia es que Knockout usaba `name()` (llamada de funcion) en vez de `name.value` (propiedad).

### Binding al DOM

```html
<input data-bind="value: name" />
<span data-bind="text: fullName"></span>
```

Cuando escribias en el input, `name` cambiaba y el span se actualizaba solo. Es el mismo patron que hoy hace `bindValue` en Vaadin Signals.

### Por que cayo en el olvido

- 2013: aparece React con virtual DOM. Mas simple para apps grandes.
- 2014: Angular 2, modelo distinto basado en zonas.
- 2014: Vue, copia parte de Knockout con mejor sintaxis y crece mas rapido.
- Knockout no tenia componentes (los añadio tarde) ni un ecosistema fuerte.
- Equipo pequeño (basicamente Steve Sanderson solo).

### Dato curioso

Steve Sanderson hoy trabaja en **Blazor** (el equivalente Microsoft de Vaadin Flow, para C#/.NET). UI en servidor, navegador como cliente fino. El circulo se cierra.

### Por que aparece en el timeline

- Demostro que era viable la reactividad fina en el navegador, 3 años antes de React.
- Es el ejemplo canonico del modelo **push puro** (slide 5).
- El problema de los **glitches** se descubrio con Knockout: con muchos `computed` interdependientes, el orden de actualizacion se desordenaba.
- Tanto en libros academicos sobre reactividad como en la propuesta TC39 de signals se cita Knockout como el primer sistema reactivo masivo en la web.

---

## 6. ¿Preact en slide 5 o en slide 6? ¿No es contradictorio?

En la slide 5 (Push/Pull/Push-Pull) Preact aparece en **Pull** junto a React.
En la slide 6 (Timeline) `@preact/signals` aparece en **2022**.

Parece contradictorio pero no lo es.

### Lo que pasa

**Preact-the-framework (2015)** funciona igual que React: pull-based, re-render, virtual DOM. Si estuviera en la slide 5, estaria al lado de React en la columna pull. (Y de hecho, lo añadi: "Pull (React, Preact, Vue 2)").

**`@preact/signals` (2022)** es una libreria **separada** que el equipo de Preact creo encima. Añade signals encima de Preact (y de React via `@preact/signals-react`). Eso es lo que aparece en el timeline.

### Resumen

| | Preact-the-framework | @preact/signals |
|---|---|---|
| Año | 2015 | 2022 |
| Categoria slide 5 | Pull (igual que React) | Push-Pull |
| Sirve para | Mini-framework compatible con React | Añadir signals a Preact o React |

---

## 7. Push vs Pull vs Push-Pull (slide 5)

Los tres modelos de reactividad en frameworks UI.

### Pull (React, Preact, Vue 2)

"Algo cambio. Re-renderiza el arbol entero y haz diff."

- **Como funciona:** cuando algo cambia, re-renderiza el componente y compara el virtual DOM con el real. Aplica solo las diferencias.
- **Granularidad:** gruesa. Re-ejecuta funciones componentes enteras.
- **Pro:** modelo mental simple. Sin suscripciones manuales.
- **Contra:** desperdicia CPU. Necesita `useMemo` / `React.memo` para optimizar.

### Push (Knockout, RxJS basico, observables ingenuos)

"Avisa a todos los observadores ya."

- **Como funciona:** cuando un observable cambia, llama inmediatamente a todos los subscribers en cadena.
- **Granularidad:** fina. Solo se ejecuta lo suscrito.
- **Pro:** rapido y directo.
- **Contra:** puede actualizar la misma cosa varias veces en un tick (glitches). Dificil de razonar con muchas dependencias.

### Push-Pull (Signals: SolidJS, @preact/signals, Vue 3 ref, Angular signals, Vaadin signals)

"Marca como sucio al escribir (push), recalcula solo lo que se lee (pull)."

- **Como funciona:** al escribir, marca dependientes como "sucios" (no recalcula). Al leer un computed, si esta sucio, recalcula. El framework conoce el grafo y ordena.
- **Granularidad:** fina.
- **Pro:** sin glitches, eficiente, declarativo, sin re-renders.
- **Contra:** mas conceptos a aprender (signal, computed, effect).

---

## 8. ¿Que aporta Vaadin Signals sobre las versiones JS?

Tres cosas que los signals de JavaScript no te dan:

### Thread-safe

Las signals de JS asumen un solo hilo (el event loop). En el servidor Java tienes hilos: tareas en background, callbacks REST, jobs programados, push asincrono.

Vaadin Signals garantiza atomicidad en lecturas y escrituras concurrentes. Puedes escribir a una signal desde cualquier hilo sin race conditions.

### Compartidos por defecto

Las signals de JS viven en una pestaña del navegador. Cada usuario tiene su copia.

En Vaadin puedes tener una signal **en el scope de la aplicacion** (singleton de Spring). Una `ListSignal<Order>` puede ser **la misma instancia** que ven los 50 usuarios conectados. Si uno añade una orden, los 50 grids se actualizan en vivo.

Sin WebSocket pub-sub a mano. Sin Redis. Sin event bus. La propagacion la hace el framework.

### Transaccionales

Multiples escrituras en un bloque atomico: los suscriptores solo ven el estado final del bloque, no parpadeos intermedios.

```java
Signal.transaction(() -> {
  user.value(newUser);
  order.value(newOrder);
  status.value("ready");
});
// Los subscribers ven los 3 cambios como una sola actualizacion.
```

---

## 9. Frameworks comparados (referencia rapida)

| Framework | Lenguaje | Modelo | API de signals | Notas |
|---|---|---|---|---|
| React | JS/TS | Pull + virtual DOM | No nativa | React Compiler 2024 automatiza optimizaciones |
| Preact | JS/TS | Pull (mismo que React) | Via `@preact/signals` | 3KB, drop-in replacement |
| Vue 2 | JS/TS | Pull + virtual DOM | No (data + watch) | Modelo antiguo |
| Vue 3 | JS/TS | Push-Pull | `ref()`, `computed()` | Reactivity API es signals |
| SolidJS | JS/TS | Push-Pull (sin VDOM) | `createSignal()` | El que invento el modelo moderno |
| Angular | TS | Push-Pull (desde v16) | `signal()` | Coexisten con RxJS |
| Knockout | JS | Push puro | `ko.observable()` | El abuelo (2010) |
| Vaadin Flow | Java | Server-side + push WS | `ValueSignal`, etc. (25.1+) | Multi-user, thread-safe, transaccional |
| Blazor | C# | Server-side (igual que Flow) | No es signals (binding clasico) | Steve Sanderson, ex-Knockout |

---

## 10. ¿Que es TC39?

**TC39** = "Technical Committee 39", el comite de **ECMA International** que define el estandar oficial de JavaScript (formalmente "ECMAScript").

### Quien lo compone

Representantes de las empresas con interes en JavaScript:
- **Browsers:** Google (V8/Chrome), Mozilla, Apple, Microsoft
- **Runtimes:** Node.js, Deno, Bun
- **Frameworks:** Vue, Angular, Solid, Preact, Svelte
- **Otros:** Igalia, Bloomberg, Salesforce

Se reunen cada 2 meses. Las reuniones son publicas y las actas estan en GitHub.

### Como funciona: las 4 fases

| Fase | Significado |
|---|---|
| 0: Strawperson | "Tengo una idea" (no se cuenta oficialmente) |
| **1: Proposal** | Idea formal con motivacion y casos de uso |
| **2: Draft** | Especificacion tecnica preliminar |
| **3: Candidate** | Especificacion completa, browsers implementando |
| **4: Finished** | Aprobado, en la siguiente version de JavaScript |

Solo lo que llega a fase 4 entra oficialmente en el lenguaje.

### Por que aparece en el timeline

En abril 2024 la propuesta de Signals llego a **fase 1**. Lo importante es **quien la propone y respalda**:

- **Autores:** Rob Eisenberg (Microsoft, ex-Aurelia), Daniel Ehrenberg (Bloomberg)
- **Respaldo:** los autores tecnicos de Angular, SolidJS, Vue, Svelte, Preact, Qwik

Nunca habia pasado que los autores de los frameworks rivales se sentaran juntos para definir un modelo comun de signals.

### Que significa fase 1

- La idea esta oficialmente aceptada como digna de ser explorada.
- **No significa que entrara** en JavaScript: muchas propuestas se quedan en fase 1 o 2 durante años.
- Pero implica que browsers, frameworks y comunidad **ven valor en estandarizarlo**.

### Por que importa para la charla

1. **Legitimidad:** signals no es moda de un framework. Es lo suficientemente importante para estandarizar.
2. **Compatibilidad futura:** si llega a fase 4, todos los frameworks (Vue, Solid, Angular, Preact, Vaadin) podran usar el signal nativo del navegador en lugar de su implementacion propia.
3. **Vaadin se alinea:** la API de Vaadin Signals esta diseñada para parecerse a la propuesta TC39. Cuando JS lo estandarice, Vaadin no tendra que cambiar nada.

### Donde verlo

- Propuesta: https://github.com/tc39/proposal-signals
- Polyfill: https://github.com/proposal-signals/signal-polyfill

### Respuesta corta a "signals es hype"

"Los autores de Angular, Vue, Solid, Svelte, Preact y Qwik se reunieron en TC39 para definir un standard comun. Es lo opuesto a hype: es **consenso de la industria**."

---

## 11. Recursos para profundizar

- [Vaadin Signals docs](https://vaadin.com/docs/latest/flow/advanced/signals)
- [TC39 Signals proposal](https://tc39.es/proposal-signals/)
- [Preact Signals guide](https://preactjs.com/guide/v10/signals/)
- [SolidJS Reactivity](https://www.solidjs.com/guides/reactivity)
- [Angular Signals guide](https://angular.dev/guide/signals)
- [Vue 3 Reactivity in Depth](https://vuejs.org/guide/extras/reactivity-in-depth.html)
- [The Evolution of Signals in JavaScript](https://dev.to/this-is-learning/the-evolution-of-signals-in-javascript-8ob)
- [Fine-Grained Reactivity intro (Ryan Carniato)](https://dev.to/ryansolid/a-hands-on-introduction-to-fine-grained-reactivity-3ndf)
