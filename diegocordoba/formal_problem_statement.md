# Formal Problem Statement: Grid Stabilization Control Problem

Based on the theoretical framework established for the unified HJB approach in Latin American energy markets (specifically for the SIN-CENACE network), the grid stabilization control problem is formally defined as a stochastic optimal control problem under physical constraints and model ambiguity.

## 1. System Dynamics (The Plant)

Consider a power system area characterized by its inertia constant $H$ (seconds) and damping coefficient $D$ (pu/Hz). Let $x(t) = \begin{bmatrix} x_1(t) \\ x_2(t) \end{bmatrix} = \begin{bmatrix} \Delta f(t) \\ \text{ROCOF}(t) \end{bmatrix} \in \mathbb{R}^2$ represent the state vector, where $\Delta f$ is the frequency deviation and ROCOF is the Rate of Change of Frequency. 

The physical dynamics are governed by the stochastic swing equation:

$$ 2H \frac{d(\Delta f)}{dt} = \Delta P_{\text{mec}} - D \cdot \Delta f - \Delta P_{\text{carga}} + u(t) + \sigma \frac{dW_t}{dt} $$

In state-space representation, the continuous-time stochastic differential equation (SDE) is:

$$ dx_t = f(x_t, u_t) dt + \Sigma dW_t $$
$$ f(x_t, u_t) = \begin{bmatrix} x_2 \\ \frac{-D x_1 - u_t + \Delta P_d}{2H} \end{bmatrix} $$

where:
- $u(t) \in \mathcal{U} = [u_{\min}, u_{\max}]$ is the active power control action (e.g., $[-50, +50]$ MW).
- $\Delta P_d$ represents deterministic net load disturbances.
- $W_t$ is a standard Brownian motion under the physical probability measure $\mathbb{P}$.
- $\sigma$ (and by extension $\Sigma$) models the stochastic intensity of the noise (e.g., demand volatility and renewable generation intermittency).

Empirically, the unforced frequency deviation $\Delta f(t)$ follows an Ornstein-Uhlenbeck (OU) process:
$$ d(\Delta f) = \kappa(\mu - \Delta f) dt + \sigma_{OU} dW_t $$

## 2. The Objective Functional

The grid operator (or ancillary service provider) seeks an admissible control policy $u^*(x,t) : \mathbb{R}^2 \times [0,T] \to \mathcal{U}$ that minimizes the expected cumulative operational cost over a finite horizon $T$. 

The quadratic cost functional is defined as:

$$ J(x_0, t_0; u) = \mathbb{E}^{\mathbb{P}} \left[ \int_{t_0}^{T} L(x(s), u(s)) ds + \Phi(x(T)) \;\bigg|\; x(t_0) = x_0 \right] $$

where the running cost $L(x, u)$ penalizes frequency deviations, high ROCOF, and excessive control effort:

$$ L(x, u) = q_1 x_1^2 + q_2 x_2^2 + r u^2 $$

- $q_1 > 0$ is the penalty weight for frequency deviation.
- $q_2 > 0$ is the penalty weight for ROCOF.
- $r > 0$ is the cost of control effort.
- $\Phi(x(T))$ is the terminal cost (typically $0$ for continuous regulation contracts).

## 3. The Hamilton-Jacobi-Bellman (HJB) Formulation

By Bellman's Principle of Optimality, the optimal value function $V^*(x,t) = \inf_{u \in \mathcal{U}} J(x,t; u)$ satisfies the stochastic Hamilton-Jacobi-Bellman (HJB) partial differential equation:

$$ -\frac{\partial V}{\partial t} = \min_{u \in \mathcal{U}} \left\{ L(x,u) + (\nabla_x V)^\top f(x,u) + \frac{1}{2} \text{Tr}\left[ \Sigma \Sigma^\top \cdot \text{Hess}_x(V) \right] \right\} $$

with the terminal condition $V^*(x,T) = \Phi(x(T))$.

Because the control $u$ is physically bounded ($u \in \mathcal{U}$), the optimal policy $\hat{u}$ is subject to saturation:
$$ u^*(x,t) = \max\left(u_{\min}, \min\left(u_{\max}, \hat{u}_{\text{unconstrained}}(x,t)\right)\right) $$
This saturation introduces a non-linearity in the HJB equation analogous to the early-exercise premium of an American option (the Optimal Control Premium).

## 4. Robust Minimax Extension (Knightian Ambiguity)

Due to structural changes in the grid (e.g., increasing penetration of wind/solar), the true probability measure $\mathbb{P}$ governing $W_t$ is uncertain. To account for Knightian ambiguity (model uncertainty), we introduce an adversarial nature $Q_\theta \in \mathcal{P}_\varepsilon$, where $\mathcal{P}_\varepsilon$ is a Kullback-Leibler divergence ball of radius $\varepsilon$ around the reference measure $Q_0$.

The robust grid stabilization control problem becomes a two-player zero-sum differential game (Minimax HJB):

$$ V_{\text{rob}}(x,t) = \sup_{\tau} \inf_{Q_\theta \in \mathcal{P}_\varepsilon} \mathbb{E}^{Q_\theta} \left[ e^{-r_f(\tau-t)} \pi(x(\tau), u^*(x(\tau))) \cdot \mathbf{1}_{\{\tau < \tau_b\}} \;\bigg|\; x(t) = x \right] $$

Which translates to the robust HJB equation:
$$ -\frac{\partial V_{\text{rob}}}{\partial t} - \inf_{\theta \in \Theta} \left\{ \mathcal{L}_{OU}^\theta [V_{\text{rob}}] \right\} + r_f V_{\text{rob}} = g(x) $$

### Conclusion

The formal problem requires solving this constrained, stochastic, and robust optimal control problem to yield both the optimal frequency regulation policy $u^*(x,t)$ and the fair value $V^*(x,t)$ of the ancillary service contract, bridging physical grid dynamics with financial option pricing theory via the Feynman-Kac equivalence.
