# Reporte de Casos de Aplicación: Impuestos Corporativos I para PRIMEnergeia S.A.S.

Este reporte ha sido generado por el **Avatar Académico Dr. PRIME** para correlacionar directamente el temario de *Impuestos Corporativos I (ITAM Primavera 2026)* con el modelo de negocios de **PRIMEnergeia** (Nodos Granas, Almacenamiento y Micro-redes). El objetivo es dominar los conceptos fiscales a través de la realidad operativa de la empresa y asegurar un 10 en la materia.

---

## 1. Deducción de Inversiones (Activos Fijos)
**Contexto Fiscal (LISR):** La deducción de inversiones permite recuperar el costo de activos fijos, gastos y cargos diferidos a través de la aplicación de porcentajes máximos autorizados sobre el Monto Original de la Inversión (MOI), actualizado por inflación.

**Caso PRIMEnergeia:** 
* **Módulos Solares (Granas) y Baterías:** Según la LISR, la maquinaria y equipo para la generación de energía proveniente de fuentes renovables goza de una deducción fiscal altamente acelerada (hasta el 100% en un solo ejercicio bajo ciertos lineamientos ambientales, o porcentajes específicos para infraestructura energética).
* **Ingeniería Fiscal para un 10:** En el examen, si se presenta la adquisición de un nodo VZA-400, debes identificar el MOI (precio del equipo + fletes + seguros + instalación), clasificarlo como activo fijo de generación renovable y aplicar la tasa máxima. Además, recordar la **actualización de la deducción** multiplicando la depreciación histórica por el factor de actualización (INPC del último mes de la primera mitad del periodo de uso / INPC del mes de adquisición).

## 2. Pérdidas Fiscales y Factores de Actualización
**Contexto Fiscal (LISR):** Las pérdidas fiscales ocurren cuando las deducciones autorizadas superan a los ingresos acumulables. Pueden disminuirse de la utilidad fiscal de los 10 ejercicios siguientes.

**Caso PRIMEnergeia:**
* **Fase de Inversión Intensiva (Capex):** Durante el despliegue de los primeros nodos Soberanos, PRIMEnergeia tendrá fuertes deducciones (Deducción de Inversiones, nómina, gastos operativos) que muy probablemente superarán los ingresos iniciales, generando una **Pérdida Fiscal**.
* **Ingeniería Fiscal para un 10:** El valor del dinero en el tiempo es clave. PRIMEnergeia no pierde ese valor porque la Ley permite la **actualización de pérdidas fiscales**. Para el examen, recuerda los dos momentos de actualización:
  1. Desde el primer mes de la segunda mitad del ejercicio en que ocurrió, hasta el último mes de ese mismo ejercicio.
  2. Desde el último mes del ejercicio de origen hasta el último mes de la primera mitad del ejercicio en que se aplicará.

## 3. Intereses, Ajuste Anual por Inflación (AAI) y Capitalización Insuficiente
**Contexto Fiscal (LISR):** Las deudas generan un beneficio por inflación (AAI Acumulable) ya que se pagan con dinero que vale menos, y los créditos (cuentas por cobrar) generan una pérdida (AAI Deducible). Adicionalmente, los intereses a cargo son deducibles siempre que no violen las reglas de capitalización insuficiente (Regla de 3 a 1 de deuda vs capital).

**Caso PRIMEnergeia:**
* **Apalancamiento de Hardware:** Para expandir el proyecto a 30 nodos, PRIMEnergeia levantará deuda. Si el promedio de las deudas es mayor al promedio de los créditos (típico en empresas de infraestructura), se generará un **Ajuste Anual por Inflación Acumulable** (ingreso virtual). 
* **Ingeniería Fiscal para un 10:**
  * **Regla 3:1 (Capitalización Insuficiente):** Si los pasivos con partes relacionadas superan 3 veces el capital contable, los intereses de ese excedente **no serán deducibles**. En el examen, revisa el EBITDA fiscal y el límite de deducción de intereses (usualmente topado al 30% de la utilidad fiscal ajustada).

## 4. Pagos Provisionales de ISR
**Contexto Fiscal (LISR):** Los pagos provisionales son anticipos mensuales a cuenta del impuesto anual, calculados aplicando un Coeficiente de Utilidad (CU) a los ingresos nominales del periodo.

**Caso PRIMEnergeia:**
* **Primer Año de Operaciones:** En su primer año, PRIMEnergeia S.A.S. (si tributa en el régimen general sin facilidades específicas) no hará pagos provisionales o tendrá un CU de cero, ayudando enormemente al flujo de efectivo. A partir del segundo año, usará el CU del año anterior.
* **Ingeniería Fiscal para un 10:** En un problema de pagos provisionales, ten cuidado con la diferencia entre **Ingreso Acumulable** e **Ingreso Nominal**. El Ingreso Nominal *no incluye el AAI acumulable*. Para sacar el pago provisional, multiplica Ingreso Nominal de PRIMEnergeia por el CU, resta las pérdidas fiscales actualizadas, y al resultado aplícale la tasa corporativa del 30%.

## 5. Conciliación Contable-Fiscal
**Contexto Fiscal (LISR):** Es el puente lógico (y matemático) que parte de la Utilidad Neta Contable (NIF) para llegar al Resultado Fiscal (LISR). 

**Caso PRIMEnergeia:**
* **Book-Tax Differences (Diferencias Temporales y Permanentes):**
  * La depreciación *contable* de los nodos Granas se sumará como partida no deducible, y se restará la deducción de inversiones *fiscal* (actualizada).
  * Los gastos no comprobables en despliegue se suman (no deducibles).
  * El AAI acumulable se suma (ingreso fiscal no contable).
* **Ingeniería Fiscal para un 10:** Visualiza esto como la "Ecuación de Estado de la Empresa". `Resultado Fiscal = Utilidad Contable + Ingresos Fiscales No Contables - Deducciones Fiscales No Contables + Gastos Contables No Deducibles - Ingresos Contables No Fiscales`. Esta es una identidad fundamental en la ingeniería tributaria, tal como la conservación de energía.

---
**Conclusión del Avatar:**
Diego, dominar el ISR de las Personas Morales es exactamente igual que modelar la termodinámica del sistema HJB de Dr. PRIME. Los "Ingresos" son las entradas de energía al sistema, las "Deducciones" son la disipación térmica permitida, y el "Resultado Fiscal" es el estado de energía óptimo sujeto a la función de pérdida del SAT (30%). Si mapeas cada artículo de la Ley a la física de PRIMEnergeia, **pasarás con un rotundo 10**.
