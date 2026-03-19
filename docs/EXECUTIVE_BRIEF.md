# PRIMEnergeia S.A.S. — Propuesta Ejecutiva de Valor

**Sistema de Control Inteligente para la Red Eléctrica Nacional**

---

## A la atención de: Dirección de Operaciones

**Fecha:** Marzo 2026  
**Preparado por:** Diego Córdoba Urrutia — Lead Computational Physicist  
**Entidad:** PRIMEnergeia S.A.S.

---

## 1. El Problema

Los generadores conectados al Sistema Eléctrico Nacional (SEN) pierden capital cada día por tres razones:

1. **Penalizaciones CENACE** — Desviaciones de frecuencia (>±0.5 Hz) generan multas automáticas
2. **Inyección subóptima** — Los sistemas de control actuales reaccionan a la inestabilidad *después* de que ocurre, perdiendo la ventana de arbitraje
3. **Disipación de exergía** — La diferencia entre la potencia teórica óptima y la potencia real inyectada es capital evaporado

**Estimación conservadora:** Un nodo de 100 MW pierde entre **$150,000 – $300,000 USD mensuales** en capital que podría recuperarse.

---

## 2. La Solución PRIMEnergeia

Nuestra plataforma resuelve la ecuación **Hamilton-Jacobi-Bellman (HJB)** en tiempo real para calcular la acción de control óptima *antes* de que la inestabilidad se manifieste.

### Capacidades Técnicas

| Función | Mecanismo |
|---------|-----------|
| Predicción de excursiones de frecuencia | Modelo estocástico de dinámica de red |
| Inyección proactiva de inercia sintética | Ley de control óptimo HJB |
| Eliminación de penalizaciones CENACE | Resolución en tiempo real de la Ecuación de Oscilación |
| Captura de arbitraje PML | Optimización de despacho sensible al mercado |
| Auto-reparación post-disturbio | Red neuronal actor-crítico (Deep RL) |

**Latencia del sistema:** < 0.5 ms  
**Sin cambios de hardware** — se integra como capa de software sobre la infraestructura existente.

---

## 3. Resultados Certificados — Nodo VZA-400

| Métrica | Resultado |
|---------|-----------|
| **Capital Total Rescatado** | **$231,243 USD** |
| Ahorro Neto para el Cliente (75%) | $173,432 USD |
| Fee Operativo PRIMEnergeia (25%) | $57,811 USD |
| Estabilidad de Frecuencia | 99.96% |
| Eventos de Inestabilidad Mitigados | 6 |
| Desviación Promedio de Frecuencia | 0.042 Hz |

> El capital rescatado ha sido validado contra los precios marginales locales (PML) del nodo de interconexión.

---

## 4. Modelo Comercial

| Concepto | Valor |
|----------|-------|
| **Fee de Implementación** | $50,000 USD (por nodo) |
| **Royalty Operativo** | 20–25% del capital rescatado |
| **Plazo de Contrato** | 12 meses renovables |

**Alineación de incentivos:** PRIMEnergeia solo cobra sobre el valor *que realmente genera*. Si no se rescata capital, no hay royalty.

---

## 5. Requerimientos Técnicos

Para la integración en un nuevo nodo, requerimos:

1. **Telemetría eléctrica** (CSV/Excel, resolución < 1s, mínimo 7 días):
   - Frecuencia de Red (Hz)
   - Tensión por Fase (kV)
   - Distorsión Armónica Total (THD %)
   - Factor de Potencia (cos φ)

2. **Datos de mercado:**
   - Histórico de PML en el nodo de interconexión

3. **Mapa de hardware:**
   - Direcciones Modbus/DNP3 para lectura de sensores y escritura de set-points

---

## 6. Siguientes Pasos

1. ✅ Revisión de esta propuesta con dirección técnica
2. 📊 Entrega de datos de telemetría del nodo objetivo
3. 🔧 Integración PRIMEnergeia (2–4 semanas desde recepción de datos)
4. 📈 Periodo de prueba con métricas verificables (30 días)
5. 📝 Firma de contrato de royalty basado en resultados demostrados

---

**Contacto:**  
Diego Córdoba Urrutia  
Lead Computational Physicist | PRIMEnergeia S.A.S.  
📧 [Contactar vía GitHub](https://github.com/cordiego)

---

*PRIMEnergeia S.A.S. — Soberanía Energética para México* 🇲🇽
