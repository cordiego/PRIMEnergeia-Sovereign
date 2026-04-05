# PRIMEnergeia S.A.S. — Propuesta Ejecutiva de Valor

**Sistema de Control Inteligente Multi-Mercado para Redes Eléctricas**

---

## A la atención de: Dirección de Operaciones

**Fecha:** Abril 2026  
**Preparado por:** Diego Córdoba Urrutia — Lead Computational Physicist  
**Entidad:** PRIMEnergeia S.A.S.

---

## 1. El Problema

Las redes eléctricas a nivel global pierden millones anualmente por tres razones:

1. **Penalizaciones del operador** — Desviaciones de frecuencia generan multas automáticas (CENACE, NERC, ENTSO-E)
2. **Inyección subóptima** — Los sistemas de control actuales reaccionan *después* de la inestabilidad
3. **Disipación de exergía** — La diferencia entre potencia óptima y potencia real es capital evaporado

**Estimación conservadora:** Un nodo de 100 MW pierde entre **$150,000 – $400,000 USD mensuales**.

---

## 2. La Solución PRIMEnergeia

Nuestra plataforma resuelve la ecuación **Hamilton-Jacobi-Bellman (HJB)** en tiempo real para calcular la acción de control óptima *antes* de que la inestabilidad se manifieste.

### 17 Mercados Globales — 1,770 GW

#### 🇺🇸 Estados Unidos (7 ISOs — 665 GW)

| Mercado | Región | Frecuencia | Capacidad | Pricing | Moneda |
|---------|--------|-----------|-----------|---------|--------|
| **ERCOT** | Texas | 60 Hz | 85 GW | LMP ($5k cap) | USD |
| **PJM** | US East (13 estados) | 60 Hz | 180 GW | LMP | USD |
| **CAISO** | California | 60 Hz | 80 GW | LMP | USD |
| **MISO** | US Midwest | 60 Hz | 190 GW | LMP | USD |
| **SPP** | US Central | 60 Hz | 65 GW | LMP | USD |
| **NYISO** | New York | 60 Hz | 35 GW | LBMP | USD |
| **ISONE** | New England | 60 Hz | 30 GW | LMP | USD |

#### 🇨🇦 Canadá (2 ISOs — 55 GW)

| Mercado | Región | Frecuencia | Capacidad | Pricing | Moneda |
|---------|--------|-----------|-----------|---------|--------|
| **IESO** | Ontario | 60 Hz | 38 GW | HOEP | CAD |
| **AESO** | Alberta | 60 Hz | 17 GW | Pool Price | CAD |

#### 🇲🇽 México (1 ISO — 75 GW)

| Mercado | Región | Frecuencia | Capacidad | Pricing | Moneda |
|---------|--------|-----------|-----------|---------|--------|
| **SEN** | México (9 regiones CENACE) | 60 Hz | 75 GW | PML / CENACE | USD |

#### 🇪🇺 Europa (5 Mercados — 640 GW)

| Mercado | Región | Frecuencia | Capacidad | Pricing | Moneda |
|---------|--------|-----------|-----------|---------|--------|
| **MIBEL** | 🇪🇸🇵🇹 España + Portugal | 50 Hz | 110 GW | OMIE Pool | EUR |
| **EPEX** | 🇩🇪 Alemania | 50 Hz | 220 GW | EPEX SPOT | EUR |
| **EPEX FR** | 🇫🇷 Francia | 50 Hz | 130 GW | EPEX SPOT | EUR |
| **Nord Pool** | 🇳🇴🇸🇪🇫🇮🇩🇰 Nórdicos | 50 Hz | 100 GW | Nord Pool | EUR |
| **Elexon** | 🇬🇧 Reino Unido | 50 Hz | 80 GW | BMRS | GBP |

#### 🌏 Asia-Pacífico (2 Mercados — 335 GW)

| Mercado | Región | Frecuencia | Capacidad | Pricing | Moneda |
|---------|--------|-----------|-----------|---------|--------|
| **NEM** | 🇦🇺 Australia | 50 Hz | 55 GW | AEMO Pool | AUD |
| **JEPX** | 🇯🇵 Japón | 50/60 Hz | 280 GW | JEPX Spot | JPY |

### Capacidades Técnicas

| Función | Mecanismo |
|---------|-----------|
| Predicción de excursiones de frecuencia | Modelo estocástico de dinámica de red |
| Inyección proactiva de inercia sintética | Ley de control óptimo HJB |
| Eliminación de penalizaciones | Resolución de Ecuación de Oscilación (50/60 Hz) |
| Captura de arbitraje de precios | Optimización de despacho multi-mercado |
| Auto-reparación post-disturbio | Red neuronal actor-crítico (Deep RL) |

**Latencia:** < 0.5 ms | **Sin cambios de hardware** | **17 mercados · 1,770 GW**

---

## 3. Resultados Certificados — Nodo VZA-400 (SEN)

| Métrica | Resultado |
|---------|-----------|
| **Capital Total Rescatado** | **$231,243 USD** |
| Ahorro Neto para el Cliente (75%) | $173,432 USD |
| Fee Operativo PRIMEnergeia (25%) | $57,811 USD |
| Estabilidad de Frecuencia | 99.96% |
| Eventos de Inestabilidad Mitigados | 6 |

---

## 4. Proyecciones de Ingresos — Multi-Mercado (17 ISOs)

### Mercados de Lanzamiento (Año 1)

| Mercado | Capacidad | Rescate Anual | Ingreso PRIME (25%) |
|---------|-----------|--------------|---------------------|
| SEN 🇲🇽 | 75 GW | $64.7M USD | $16.2M USD |
| ERCOT 🇺🇸 | 85 GW | $71.7M USD | $17.9M USD |
| MIBEL 🇪🇸🇵🇹 | 110 GW | €51.6M EUR | €12.9M EUR |

### Expansión Completa (Año 5 — 17 Mercados)

| Región | Mercados | Capacidad | Rescate Potencial | Ingreso PRIME (25%) |
|--------|----------|-----------|-------------------|---------------------|
| 🇺🇸 US ISOs | ERCOT, PJM, CAISO, MISO, SPP, NYISO, ISONE | 665 GW | ~$350M USD | ~$87M USD |
| 🇨🇦 Canadá | IESO, AESO | 55 GW | ~$25M CAD | ~$5M USD |
| 🇲🇽 México | SEN | 75 GW | ~$65M USD | ~$16M USD |
| 🇪🇺 Europa | MIBEL, EPEX, EPEX FR, Nord Pool, Elexon | 640 GW | ~€280M EUR | ~€70M EUR |
| 🌏 Asia-Pac | NEM, JEPX | 335 GW | ~$50M USD | ~$12M USD |
| **TOTAL** | **17 ISOs** | **1,770 GW** | **~$770M** | **~$190M** |

---

## 5. Modelo Comercial

| Concepto | Valor |
|----------|-------|
| **Fee de Implementación** | $50,000 USD (por nodo) |
| **Royalty Operativo** | 25% del capital rescatado |
| **Plazo de Contrato** | 12 meses renovables |

**Alineación de incentivos:** PRIMEnergeia solo cobra sobre el valor *que realmente genera*.

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

*PRIMEnergeia S.A.S. — Soberanía Energética Global* ⚡🇲🇽🇺🇸🇪🇺🇦🇺🇯🇵🇨🇦🇬🇧
