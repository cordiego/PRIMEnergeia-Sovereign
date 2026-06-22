# Sección de Control Óptimo Estocástico: Estabilización de Red y Ecuación HJB

## Introducción al Control Estocástico en Sistemas de Potencia

El control óptimo estocástico provee el marco matemático natural para abordar el problema de estabilización de red en mercados eléctricos modernos. A diferencia del control determinístico clásico, que asume conocimiento perfecto de las trayectorias futuras, la formulación estocástica incorpora de manera explícita la incertidumbre inherente a la generación renovable (eólica y solar) y a la volatilidad de la demanda. En este contexto, el operador del sistema o el proveedor de servicios ancilares debe tomar decisiones continuas bajo incertidumbre para minimizar el costo esperado de operación mientras mantiene la estabilidad física de la red.

## Dinámica del Sistema y la Ecuación de Oscilación Estocástica

Consideremos un área del sistema de potencia caracterizada por su constante de inercia $H$ (medida en segundos) y su coeficiente de amortiguamiento $D$ (en pu/Hz). El estado del sistema en el instante $t$ se describe mediante el vector $x(t) \in \mathbb{R}^2$:

$$ x(t) = \begin{bmatrix} x_1(t) \\ x_2(t) \end{bmatrix} = \begin{bmatrix} \Delta f(t) \\ \text{ROCOF}(t) \end{bmatrix} $$

donde $\Delta f(t)$ representa la desviación de frecuencia respecto a su valor nominal (e.g., 60 Hz) y ROCOF es la Tasa de Cambio de Frecuencia (Rate of Change of Frequency). La física subyacente está gobernada por la ecuación de oscilación, que en un entorno incierto se modela como una Ecuación Diferencial Estocástica (SDE):

$$ 2H \frac{d(\Delta f)}{dt} = \Delta P_{\text{mec}} - D \cdot \Delta f - \Delta P_{\text{carga}} + u(t) + \sigma \frac{dW_t}{dt} $$

En representación de espacio de estados, la SDE de tiempo continuo se expresa como:

$$ dx_t = f(x_t, u_t) dt + \Sigma dW_t $$
$$ f(x_t, u_t) = \begin{bmatrix} x_2 \\ \frac{-D x_1 - u_t + \Delta P_d}{2H} \end{bmatrix} $$

donde:
- $u(t) \in \mathcal{U} = [u_{\min}, u_{\max}]$ es la acción de control de potencia activa (e.g., inyección o absorción de energía mediante un BESS).
- $\Delta P_d$ denota perturbaciones determinísticas en la carga neta.
- $W_t$ es un movimiento browniano estándar bajo la medida de probabilidad física $\mathbb{P}$.
- $\Sigma$ es la matriz de difusión que caracteriza la intensidad estocástica del ruido (volatilidad de la red).

## El Funcional de Costo y el Horizonte de Optimización

El objetivo del controlador es encontrar una política admisible $u^*(x,t) : \mathbb{R}^2 \times [0,T] \to \mathcal{U}$ que minimice el costo operativo acumulado esperado a lo largo de un horizonte finito $T$. El funcional de costo cuadrático se define como:

$$ J(x_0, t_0; u) = \mathbb{E}^{\mathbb{P}} \left[ \int_{t_0}^{T} L(x(s), u(s)) ds + \Phi(x(T)) \;\bigg|\; x(t_0) = x_0 \right] $$

donde el costo de ejecución (running cost) $L(x, u)$ penaliza cuadráticamente las desviaciones de frecuencia, niveles altos de ROCOF, y el esfuerzo de control:

$$ L(x, u) = q_1 x_1^2 + q_2 x_2^2 + r u^2 $$

- $q_1, q_2 > 0$ son los factores de penalización para el estado del sistema.
- $r > 0$ representa el costo marginal del esfuerzo de control.
- $\Phi(x(T))$ es el costo terminal, usualmente $0$ para contratos de regulación de naturaleza continua.

## La Ecuación Estocástica de Hamilton-Jacobi-Bellman (HJB)

A partir del Principio de Optimalidad de Bellman, la función de valor óptimo $V^*(x,t) = \inf_{u \in \mathcal{U}} J(x,t; u)$ es solución de la ecuación en derivadas parciales (EDP) estocástica de Hamilton-Jacobi-Bellman:

$$ -\frac{\partial V}{\partial t} = \min_{u \in \mathcal{U}} \left\{ L(x,u) + (\nabla_x V)^\top f(x,u) + \frac{1}{2} \text{Tr}\left[ \Sigma \Sigma^\top \cdot \text{Hess}_x(V) \right] \right\} $$

sujeto a la condición terminal $V^*(x,T) = \Phi(x(T))$. 

El término de segundo orden $\frac{1}{2} \text{Tr}\left[ \Sigma \Sigma^\top \cdot \text{Hess}_x(V) \right]$, ausente en la formulación determinística, captura directamente la aportación de la volatilidad estocástica a la función de valor. Este término es el puente fundamental que conecta la teoría de control con la valoración de derivados financieros.

## Restricciones Físicas y la Prima de Control Óptimo

En aplicaciones reales, la capacidad del activo de regulación está estrictamente acotada ($u \in \mathcal{U}$). Al minimizar el hamiltoniano con respecto a $u$, la política óptima $\hat{u}$ exhibe saturación:

$$ u^*(x,t) = \max\left(u_{\min}, \min\left(u_{\max}, \hat{u}_{\text{libre}}(x,t)\right)\right) $$

Esta restricción introduce una no-linealidad profunda en la ecuación HJB. Matemáticamente, el efecto de esta saturación en la función de valor es análogo a la **prima de ejercicio anticipado** presente en las opciones americanas. A esta diferencia la denominamos **Prima de Control Óptimo (PCO)**:

$$ \text{PCO}(x,t) = V_{\text{HJB}}^{\text{restringido}}(x,t) - V_{\text{HJB}}^{\text{libre}}(x,t) \ge 0 $$

La PCO cuantifica el valor económico de la restricción de capacidad, reflejando que un sistema con límites de actuación estrictos incurrirá en costos esperados mayores frente a perturbaciones extremas.

## Dualidad de Feynman-Kac y la Equivalencia con Black-Scholes

La formulación expuesta permite establecer una equivalencia directa entre el control de la red y la teoría de valoración de opciones (Pricing). Mediante el Teorema de Feynman-Kac, la ecuación HJB sin restricciones (o en la región donde las restricciones no están activas) se mapea exactamente a la ecuación diferencial parcial de Black-Scholes-Merton. 

Bajo esta dualidad:
1. El estado del sistema $\Delta f$ actúa como el precio del activo subyacente.
2. El coeficiente de amortiguamiento $D/(2H)$ actúa como la tasa de reversión (o tasa libre de riesgo en un entorno neutral al riesgo).
3. La matriz de covarianza de la red estocástica $\Sigma$ corresponde a la volatilidad del subyacente.

Esta equivalencia permite valorar los contratos de servicios ancilares (e.g., regulación de frecuencia) no solo como mecanismos de compensación por energía, sino como **opciones reales americanas** vendidas por el operador de la red, abriendo la puerta a esquemas de subasta y compensación mucho más eficientes y precisos basados en información compartida (Milgrom-Weber).

## Extensión SPDE: La Conexión con Navier-Stokes y Regularización por Ruido

Al transicionar de una representación nodal aislada (SDE) a una red de transmisión extendida espacialmente, el modelo evoluciona hacia una Ecuación Diferencial Parcial Estocástica (SPDE). Este salto dimensional nos conecta directamente con las fronteras de la física matemática, específicamente con el análisis de las ecuaciones de Navier-Stokes.

1. **La Singularidad y el "Blowup":** En Navier-Stokes, la no-linealidad geométrica (vortex stretching) puede causar que la energía se concentre infinitamente rápido, creando una singularidad en tiempo finito (Barrera de Tao). En la red eléctrica, el equivalente exacto de esta singularidad es una **falla en cascada**; una perturbación severa que satura los controles ($u \in \mathcal{U}$) y dispara eventos no-lineales (como el deslastre de carga), colapsando el sistema.
2. **Regularización por Ruido (Da Prato & Flandoli):** La solución teórica (Franco Flandoli, 1995) para evitar este colapso en fluidos es inyectar ruido espacial correlacionado (ruido de transporte o $Q$-Wiener) que "esparce" la concentración de energía. En nuestra red eléctrica, este rol lo asumen los **sistemas BESS distribuidos**. Al operar mediante políticas de control estocástico de alta frecuencia a lo largo de la topología de la red, el BESS inyecta "ruido de control" estabilizador. Este ruido interrumpe la concentración focalizada del disturbio, disipando la energía antes de que la singularidad no-lineal del colapso en cascada pueda formarse, garantizando que el sistema permanezca en una medida estacionaria (estabilizado).
3. **El Rendimiento de la Tesis: Pricing de Opciones Reales de la Regularización.** Como se estableció mediante la dualidad de Feynman-Kac, la ecuación HJB valora los servicios ancilares como opciones reales americanas. Al fusionar ambos conceptos, el *costo* de inyectar este "ruido estabilizador" (el despacho estocástico de los BESS) se convierte intrínsecamente en el **precio de la regularización**. Esto transforma una conjetura matemática abstracta de las SPDEs en un **problema de control económico cuantificable** — la aportación única de esta tesis HJB. Ningún enfoque matemático puro puede asignar un valor de mercado al esfuerzo para evitar el *blowup*; este marco logra exactamente eso, traduciendo la regularización por ruido en una prima de riesgo financieramente transable.
