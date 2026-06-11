# JMad 2026 — Propuesta de unconference

Material para proponer el tema en [jmad.madridjug.es](https://jmad.madridjug.es/).

---

## Título

**Adiós a los listeners: signals llegan a Java**

---

## Descripción (≈140 palabras)

El frontend lleva 15 años puliendo el modelo "signals" 
Knockout, SolidJS, Angular, Vue, Preact ...
Ahora TC39 (ECMA) lo han adoptado como estándar para UI reactiva.

Vaadin 25.1 acaba de traer ese mismo modelo a Java en
el servidor. Tres primitivas: signal, computed, effect.
Cero `addValueChangeListener`.

A debatir:

- ¿Es signals el patrón que mata a los listeners, RxJava y los observables de Project Reactor en código de UI?
- Si JS lleva una década con esto, ¿llegamos tarde los de Java o estamos esperando al modelo bueno?
- ¿Cómo encaja con CDI, Spring events, transacciones?
- Multi-usuario sin WebSockets a mano: ¿demo killer o complicación innecesaria?


Nivel: intermedio. Formato: 10 min intro + 30 min debate.

---

## Tagline corto

> Tres primitivas. Cero listeners. ¿Es el futuro de la UI reactiva en Java?

---

## Post de aviso (Twitter/Mastodon/Slack)

> Mañana en @jmadconf debato si **signals** mata a los listeners en Java. Vaadin 25.1 trae el mismo modelo que SolidJS, Angular y Vue llevan usando una década. ¿Llegamos tarde o esperábamos al modelo bueno?
>
> #MadridJUG #Java #Reactividad

---

## Pitch de 60 segundos (para vender el topic en la sala)

> Hola, soy Manolo. Quiero proponer un tema que lleva 15 años madurando en el frontend y que acaba de aterrizar en Java esta semana: **signals**.
>
> Si has escrito un formulario en Vaadin Flow, sabes lo que es la cadena de `addValueChangeListener`. Si has tocado RxJava o Project Reactor, sabes que los observables son potentes pero pesados. Si vienes del frontend, ya conoces SolidJS, Preact, Angular Signals.
>
> Vaadin 25.1 trae el mismo modelo a Java en el servidor. La pregunta no es "¿cómo funciona?" sino "¿es el patrón que necesita Java para reactividad de UI, o es otra moda del JS?".
>
> Traigo ejemplos en código y comparativa con otros enfoques. Quiero **debate abierto**, no charla magistral. Si te interesa la reactividad fina, vota este tema.

---

## Recordatorios para el día

- [ ] Llevar las slides cargadas en local: `v-signals-es.html` (no depender de wifi de la sala)
- [ ] Tener el iframe `extras/signals-pipeline-es.html` probado en pantalla grande
- [ ] Tener el vídeo `video/vaadin-signals-es.mp4` accesible offline
- [ ] El PDF `extras/think-signals.pdf` como material de referencia post-charla
- [ ] Mirar antes de la votación quién está en la sala (perfil Spring-heavy vs frontend-curious)

---

## Estructura sugerida (40 min)

1. **Hook (2 min)** — slide 2 "El enredo": "necesitas una libreta para apuntar qué actualiza qué". Risas y asentimientos.
2. **Por qué signals (5 min)** — slides 5-7: push vs pull vs push-pull, timeline 2010-2025, quote TC39.
3. **Tres primitivas (5 min)** — slides 9-12: signal/computed/effect con código JS y Java en paralelo. Demo del iframe.
4. **Lo que aporta Vaadin (5 min)** — slides 14-18: thread-safe, multi-usuario, ListSignal compartido en el servidor.
5. **Antes y después (3 min)** — slide 19: 26 líneas vs 15.
6. **Vídeo (2 min)** — slide 20: el explainer oficial.
7. **Debate abierto (15-18 min)** — preguntas:
   - ¿Reemplaza signals al Observer pattern en backend también?
   - ¿RxJava sigue teniendo sentido para UI?
   - ¿Cómo encaja con Spring eventos y transacciones?
   - ¿Multi-usuario con `ListSignal` mata al WebSocket manual?

---

## Preguntas que probablemente saldrán y respuestas cortas

**P: ¿Esto es solo para Vaadin?**
R: No. El patrón es estándar (TC39 fase 1). Vaadin es la implementación más fresca para Java; en JS lo tienes en Solid, Angular, Vue 3, Preact.

**P: ¿En qué se diferencia de RxJava?**
R: RxJava es push puro con backpressure, pensado para streams asíncronos. Signals es push-pull para estado UI; sin glitches, sin operadores que aprender. Casos distintos.

**P: ¿Y Project Reactor / Flux en backend?**
R: Mismo argumento. Signals brilla en UI state; Reactor brilla en pipelines de datos. No compiten directamente.

**P: ¿Funciona con Spring transactions?**
R: Vaadin Signals es thread-safe y transaccional a nivel de signals (`Signal.transaction(() -> ...)`). No reemplaza `@Transactional` pero coexisten sin problemas.

**P: ¿`ValueSignal` se serializa para sesiones?**
R: Sí, vive en el StateTree de Vaadin que ya se serializa. No hay magia adicional.

**P: ¿Y para apps no-Vaadin?**
R: La API de signals es Vaadin-specific por ahora. Si la propuesta TC39 madura y JVM la adopta (vía proyecto independiente), podría haber `java.signals` algún día.

---

## Material de apoyo enlazado

- Presentación ES: `v-signals-es.html`
- Presentación EN: `v-signals.html`
- Iframe interactivo: `extras/signals-pipeline-es.html`
- PDF de profundización: `extras/think-signals.pdf`
- Vídeo Vaadin: `video/vaadin-signals-es.mp4`
- Aclaraciones técnicas (Knockout, TC39, glitches): `v-signals-aclaraciones.md`
