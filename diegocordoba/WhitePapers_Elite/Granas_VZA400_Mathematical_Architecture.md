# Granas Core Architecture: Deep Formalization

This document establishes the formal mathematical architecture for the **Granas VZA-400 PV-HB** integrated state-space model. It derives the stochastic field equations governing photovoltaic energy generation, alongside the deterministic thermochemical kinetics of the VZA-400 Haber-Bosch reactor.

## 1. State and Control Space

The system state $x(t) \in \mathcal{X} \subset \mathbb{R}^4$ is defined as the tuple:
$$ x(t) = \begin{bmatrix} E_{PV}(t) \\ T_r(t) \\ P_r(t) \\ S_{H2}(t) \end{bmatrix} $$

Where:
*   $E_{PV}(t) \in [0, 100]$ MW: Stochastic photovoltaic energy generation.
*   $T_r(t) \in [300, 550]$ °C: Reactor temperature.
*   $P_r(t) \in [100, 300]$ bar: Reactor pressure.
*   $S_{H2}(t) \in [0.1, 1.0]$: Hydrogen buffer state of charge (SoC).

The control variable $u_{hb}(t) \in \mathcal{U}(x) \subset \mathbb{R}$ governs the power dispatched to the VZA-400 reactor, bounded by the instantaneous PV generation:
$$ u_{hb}(t) \in [0, E_{PV}(t)] $$

## 2. Stochastic Field Equations

### 2.1 Photovoltaic Generation (Ornstein-Uhlenbeck)
The continuous-time stochastic generation profile $E_{PV}(t)$ follows a mean-reverting Ornstein-Uhlenbeck (OU) process, capturing intra-day volatility and structural generation bounds:
$$ dE_{PV}(t) = \kappa_{pv} (\mu_{pv} - E_{PV}(t)) dt + \sigma_{pv} dW(t) $$
Where $\kappa_{pv}$ is the mean-reversion speed, $\mu_{pv}$ is the equilibrium mean, and $\sigma_{pv}$ is the volatility of the underlying standard Wiener process $W(t)$.

## 3. VZA-400 Coupling Structure

The core PV-HB coupling emerges through the translation of $u_{hb}(t)$ into thermochemical forces.

### 3.1 Reaction Kinetics (Modified Temkin-Pyzhev)
The green ammonia synthesis rate $R_{NH3}$ is modeled via a simplified kinetic proxy dependent on reactor state:
$$ R_{NH3}(T_r, P_r) = \max\left(0, \ k_0 \exp\left(-\frac{E_a}{R (T_r + 273.15)}\right) \sqrt{P_r}\right) $$

### 3.2 Reactor Thermal Dynamics
The temperature flow couples the heating fraction ($\alpha$) of the dispatched energy to exothermic reaction heat:
$$ dT_r(t) = \left[ \frac{\alpha}{C_{th}} u_{hb}(t) - k_{loss} (T_r(t) - T_{amb}) + Q_{rxn} R_{NH3}(T_r, P_r) \right] dt $$

### 3.3 Reactor Pressure Dynamics
Pressure dynamics capture the compression efficiency ($\beta$) mapping residual energy to pressure, minus synthesis consumption ($\gamma$) and natural leakage:
$$ dP_r(t) = \left[ \beta(1 - \alpha) u_{hb}(t) - \gamma R_{NH3}(T_r, P_r) - k_{leak} P_r(t) \right] dt $$

### 3.4 Hydrogen Buffer Dynamics
The buffer depletion maps linearly to the synthesis rate via the stoichiometric efficiency factor $\eta_{H2}$:
$$ dS_{H2}(t) = - \eta_{H2} R_{NH3}(T_r, P_r) dt $$

## 4. Hamilton-Jacobi-Bellman (HJB) Formulation

To optimize the dispatch policy $u_{hb}^*(t)$, we define the running cost functional $L(x, u_{hb})$ mapping grid and ammonia revenues against physical penalties:

$$ L(x, u_{hb}) = - \lambda_{grid} (E_{PV} - u_{hb}) - \lambda_{NH3} R_{NH3} + c_{temp} \max(0, T_r - 500)^2 + c_{H2} \max(0, 0.2 - S_{H2})^2 $$

The optimal value function $V(x, t)$ must satisfy the non-linear second-order partial differential equation:
$$ - \frac{\partial V}{\partial t} = \min_{u_{hb} \in [0, E_{PV}]} \left\{ L(x, u_{hb}) + \nabla V \cdot f(x, u_{hb}) + \frac{1}{2} \sigma_{pv}^2 \frac{\partial^2 V}{\partial E_{PV}^2} \right\} $$

Where $f(x, u_{hb})$ encapsulates the drift vector $\begin{bmatrix} \kappa_{pv}(\mu_{pv}-E_{PV}) & dT_r/dt & dP_r/dt & dS_{H2}/dt \end{bmatrix}^T$.
