# Guía de presentación — Sesión 13

## Presentación de 60–90 segundos

> En la Sesión 12 tenía un bucle agéntico escrito a mano. Funcionaba,
> pero el flujo, el estado y las decisiones estaban mezclados. En la
> Sesión 13 lo convertí en un grafo explícito de LangGraph con cinco
> nodos secuenciales: extracción, clasificación, búsqueda de
> presupuestos, generación de la estimación y validación.
>
> El estado está tipado y utiliza reducers para acumular referencias,
> errores y eventos de dominio. Los nodos no modifican el estado
> recibido: devuelven actualizaciones parciales.
>
> Las llamadas externas están detrás de interfaces inyectadas. La
> extracción y clasificación pueden usar modelos; la búsqueda reutiliza
> mi pipeline RAG. Los cálculos de horas y totales se hacen de forma
> determinista en Python.
>
> El grafo persiste checkpoints en el PostgreSQL existente mediante
> AsyncPostgresSaver y usa el identificador de la estimación como
> identidad estable del thread. Logfire muestra un span raíz y un span
> por nodo.
>
> Mantengo el endpoint anterior y añadí `/api/v1/estimate/graph` para
> validar la migración sin romper el producto. Paralelismo, HITL y
> recuperación avanzada están documentados como trabajo Plus.

## Flujo que debes explicar

1. `extract_requirements` produce requisitos atómicos.
2. `classify_components` los agrupa en componentes.
3. `search_budgets` recupera referencias secuencialmente.
4. `generate_estimate` calcula horas y totales en Python.
5. `validate_and_consolidate` fija `validated` o `needs_review`.

## Preguntas típicas

### ¿Dónde haces las llamadas?

La topología no llama directamente a un SDK concreto.

- `extract_requirements` usa el puerto de extracción inyectado.
- `classify_components` usa el puerto de clasificación.
- `search_budgets` usa el puerto de recuperación por componente.
- En CI esos puertos usan fakes deterministas.
- En runtime se enlazan con adaptadores reales.

Así puedo cambiar DeepSeek, Kimi o el mecanismo de búsqueda sin
rediseñar el grafo.

### ¿Dónde construyes la respuesta?

La respuesta se construye en dos niveles:

1. `generate_estimate` crea la estimación interna y calcula horas,
   rangos, contingencia y total de forma determinista.
2. La capa de servicio adapta el estado terminal al contrato HTTP.

El modelo no decide el total final mediante aritmética libre.

### ¿Cómo gestionas las decisiones?

- El orden obligatorio está en las aristas explícitas.
- `validate_and_consolidate` fija `validated` o `needs_review`.
- La capa de servicio distingue ejecución nueva, resume, resultado
  completado, replay y recalculación.

No implementé retries complejos ni HITL porque estaban fuera del
pre-work.

### ¿Por qué LangGraph y no mantener el bucle?

No porque un framework sea siempre mejor. El grafo empieza a justificar
su coste cuando necesito estado explícito, etapas dependientes,
checkpoints, resume, trazas por nodo, futuras ramas, futuro paralelismo
y futura intervención humana.

### ¿Qué es el estado?

Es el contrato de datos compartido entre nodos. Contiene datos
serializables, no clientes, conexiones ni objetos de SDK.

### ¿Qué es un reducer?

Es la regla de combinación de actualizaciones. Con `operator.add`, los
elementos nuevos se acumulan en vez de reemplazar la lista anterior.

### ¿Cómo evitas duplicados al reanudar?

- Los nodos acumuladores devuelven solo elementos nuevos.
- No reenvío el estado acumulado como entrada nueva.
- Una ejecución completada no vuelve a ejecutar nodos.
- Replay requiere checkpoint explícito.
- Recalcular usa un thread nuevo.

### ¿Qué identifica `thread_id`?

Identifica la historia persistente de una estimación. El mismo
`thread_id` permite continuar o inspeccionar la ejecución.

### ¿Cómo probaste la persistencia?

1. Ejecuté el grafo con PostgreSQL real.
2. Cerré el checkpointer.
3. Abrí otro checkpointer.
4. Leí el mismo thread.
5. Comparé el estado.
6. Verifiqué que los nodos no se ejecutaron otra vez.

### ¿Qué diferencia hay entre traza de dominio y Logfire?

La traza de dominio explica qué produjo cada nodo y qué evidencia usó.
Logfire explica duración, jerarquía padre/hijo, errores y atributos
operativos. Los logs son mensajes operativos.

### ¿Por qué no hiciste `Send`, retries o HITL?

Porque el enunciado los excluía de la pre-sesión. Primero demostré
corrección secuencial, reducers, persistencia, identidad de thread,
observabilidad y CI.

### ¿Qué mejoraste respecto al esqueleto?

- estado más rico y tipado;
- procedencia de recuperación;
- matemáticas deterministas;
- puertos neutrales respecto al proveedor;
- fakes deterministas;
- semántica idempotente;
- prueba real de recuperación PostgreSQL;
- span raíz más spans de nodo;
- sanitización de telemetría;
- aislamiento de mutaciones;
- separación entre CI y pruebas live.

### ¿Qué parte es opcional y no está hecha?

- arista condicional real;
- paralelismo con `Send`;
- retry/backoff;
- fallbacks;
- circuit breakers;
- `interrupt()`;
- Critic y Boss;
- wizard completo;
- benchmark de proveedores.

Está registrado en el roadmap Plus.

### ¿Qué distingue tu proyecto del promedio?

Una solución mínima demuestra que el grafo compila. Este proyecto
también demuestra procedencia, persistencia tras reabrir recursos,
no repetición de nodos completados, seguridad de reducers,
observabilidad sanitizada, CI determinista, evidencia live separada y
resultados negativos documentados honestamente.

## Respuestas que no debes dar

No digas:

- “LangGraph decide todo automáticamente”.
- “Los reducers evitan cualquier duplicado”.
- “Logfire es el razonamiento interno del modelo”.
- “El smoke live demuestra que la calidad es buena”.
- “Ya implementé paralelismo o HITL”.
- “El endpoint viejo ya usa el grafo”.
- “PostgreSQL es la memoria de negocio”.

## Frase final

> La mejora principal no es haber añadido LangGraph. Es haber separado
> datos, trabajo, control, persistencia y observabilidad de una forma
> comprobable y preparada para evolucionar.
