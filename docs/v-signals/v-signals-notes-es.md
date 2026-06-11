# Speaker notes for v-signals-es.html

_Auto-extracted from `v-signals-es.html`: edit me, then run `./inject-notes.py es`._

## Slide 1: Vaadin Signals

- Todos conocemos signals del mundo JavaScript: SolidJS, Preact, Angular.
- Ahora Vaadin trae el mismo modelo a Java en el servidor.
- Hoy vemos por qué importa y qué cambia.

## Slide 2: El enredo

- Todo desarrollador que haya hecho un formulario no trivial ha vivido esto.
- El vídeo lo llama "una libreta para saber qué actualiza qué".
- Es exactamente el problema que los sistemas reactivos quieren matar.

## Slide 3: ¿Por qué signals?

- El mundo frontend lleva 15 años contestando esta pregunta.
- Repasemos rápido, porque Vaadin hereda toda esa reflexión.

## Slide 4: Imperativo vs Reactivo

- La versión imperativa funciona, pero cada campo nuevo duplica el cableado.
- La reactiva no crece así: cada pieza declara de qué depende y el framework decide el orden de actualización.

## Slide 5: Push, Pull, Push-Pull

- Tres modelos.
- Pull es React: re-renderiza y haz diff.
- Push es Knockout: cualquier cambio dispara todos los suscriptores.
- Push-pull lo popularizó SolidJS y lo siguieron Preact, Angular y ahora Vaadin. Lo mejor de los dos mundos.

## Slide 6: Un trabajo de 15 años

- La idea de signals es más antigua que React. Estuvo dormida durante la era del virtual DOM y volvió con fuerza.
- TC39 es el comité de ECMA que define el estándar oficial de JavaScript.
- Las propuestas pasan por 4 fases: 1 (idea aceptada), 2 (borrador), 3 (especificación lista), 4 (en el lenguaje).
- Que signals haya llegado a fase 1 en 2024 significa consenso de la industria: la propuesta la respaldan los autores de Angular, Solid, Vue, Svelte, Preact y Qwik.
- Vaadin 25.1 lo trae a Java y su API está alineada con esa propuesta.

## Slide 7

- Ésta es la clave.
- Signals separa el QUÉ depende de qué del CUÁNDO y CÓMO actualizar.
- El framework se ocupa del CUÁNDO. Tú sólo describes el QUÉ.

## Slide 8: Tres primitivas

- Tres bloques de construcción. Eso es todo.
- Signal, computed, effect.
- Cada librería de signals es una variación sobre estos tres.

## Slide 9: signal: un valor reactivo

- Una signal es una caja que envuelve un valor.
- La caja avisa a quien esté escuchando cuando el valor cambia.
- Toda la superficie de la API de la primera primitiva.

## Slide 10: computed: estado derivado

- Computed es la fórmula de Excel.
- Sabe qué signals lee, y vuelve a evaluarse sólo cuando esas cambian.
- Y sólo cuando alguien pregunta su valor.
- Perezosa y memoizada.

## Slide 11: effect: el mundo exterior

- Los effects son donde la reactividad toca la realidad.
- Lees signals, haces un side effect (actualizar el DOM, llamar a una API, loguear).
- Cuando cualquier signal que leíste cambia, el effect se vuelve a ejecutar.
- Vaadin lo limita al ciclo de vida del componente automáticamente.

## Slide 12: Tres primitivas, un flujo

- Recorre los pasos con el botón Next.
- Muestra signal -&gt; computed -&gt; effect una vez, luego haz click en el +1 y mira cómo viaja el paquete.
- Último paso: la garantía glitch-free.
- Recalca: un push, cada suscriptor corre una vez.

## Slide 13: Sin glitches, garantizado

- Esto es lo que significa "glitch-free" y por qué las librerías de observables ingenuas fallan.
- Cuando 'a' cambia, 'b' y 'c' dependen de ella. Un sistema ingenuo dispararía el effect dos veces.
- Signals lo corre una sola vez, con el valor final correcto.
- Importa a escala.

## Slide 14: La solución de Vaadin

- Todo lo que hemos visto hasta ahora corre en el navegador.
- La aportación de Vaadin: poner las mismas primitivas en la JVM y dejar que sincronicen entre usuarios automáticamente.

## Slide 15: Signals, pero en la JVM

- Tres cosas que los signals de JS no te dan.
- Hilos, compartir entre usuarios y batches atómicos.
- Eso es lo que hace que signals en la JVM sea más que un port.

## Slide 16: El Hola Mundo con Vaadin Signals

- Un hello-world completo de Vaadin con signals.
- Fíjate: no hay ningún addValueChangeListener.
- La llamada a bindText crea la suscripción automáticamente y la desmonta cuando el componente se detacha.
- Ése es todo el argumento.

## Slide 17: La API de bindings

- La API de bindings es la fachada de alto nivel.
- La mayor parte del tiempo no escribirás un effect a mano: bindeas una propiedad del componente a una signal y Vaadin se ocupa del resto.

## Slide 18: Una signal, todos los usuarios

- Ésta es la demo asesina.
- Una ListSignal en el servidor. Tres usuarios distintos, cada uno en su navegador, ven los mismos datos en vivo.
- Sin código WebSocket, sin event bus, sin Redis pub-sub. El framework propaga.
- Intenta hacer esto con React y REST: necesitarías un pub-sub en el backend, un endpoint WS, optimistic updates...

## Slide 19: Antes y después

- Misma funcionalidad. 75% menos código.
- Y la versión "después" no tiene riesgo de olvidar un listener, ni riesgo de estado obsoleto.
- El grafo de dependencias se describe, no se orquesta.

## Slide 20: Vídeo explicativo

- Un tour corto en vídeo del equipo de Vaadin. Dos minutos.
- Lo vemos juntos y luego preguntas.

## Slide 21: Vídeo

- Reproduce el vídeo.
- La pista en español está como primera fuente: ése se carga por defecto.
- Si quieres la versión original en inglés, invierte el orden de los source en el HTML.
- Después del vídeo, pregunta: ¿quién lo usaría el lunes? ¿qué patrón de tu base de código actual mata esto?

## Slide 22: Empieza ahora

- Tres líneas: añade la dependencia, crea una signal, bindea a un componente.
- Muestra el enlace a la documentación.
- Menciona el enlace TC39 como contexto: el mismo modelo va camino del estándar de JavaScript.

## Slide 23: Signals

- Ésa es la charla entera en una frase.
- Abre el turno de preguntas.
