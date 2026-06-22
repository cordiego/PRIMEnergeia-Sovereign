"""
PRIMEnergeia — DRL Training Pipeline (PPO)
=============================================
Proximal Policy Optimization training for the Auto-Healing Actor-Critic.
Replaces the randomly-initialized networks with trained frequency
stabilization policy.

Usage:
    python -m core.drl_trainer --market ERCOT --episodes 500

PRIMEnergeia S.A.S. — Grid Optimization Division
"""

import numpy as np
import logging
import os
import json
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger("prime.drl_trainer")

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.distributions import Normal
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available — DRL training disabled")


# ─────────────────────────────────────────────────────────────
# Grid Environment (Gymnasium-compatible)
# ─────────────────────────────────────────────────────────────

@dataclass
class EnvConfig:
    """Grid environment configuration."""
    f_nom: float = 60.0
    H: float = 5.0
    D: float = 1.0
    max_injection_mw: float = 100.0
    dt: float = 0.05
    episode_length_s: float = 120.0
    penalty_threshold_hz: float = 0.05
    disturbance_severity: float = 1.0
    market: str = "ERCOT"


class GridEnv:
    """Swing equation environment for DRL training.

    Observation space: [freq_deviation, rocof, injection, soc, price_norm]
    Action space: [-1, 1] → scaled to [-max_inj, max_inj]
    """

    def __init__(self, config: Optional[EnvConfig] = None):
        self.cfg = config or EnvConfig()
        self.observation_dim = 5
        self.action_dim = 1
        self._step_count = 0
        self._max_steps = int(self.cfg.episode_length_s / self.cfg.dt)

        # State
        self.freq_dev = 0.0
        self.injection = 0.0
        self.soc = 0.5  # Battery state of charge [0, 1]
        self.prev_freq_dev = 0.0
        self.price = 50.0

        # Disturbance RNG
        self.rng = np.random.RandomState()

    def reset(self, seed: Optional[int] = None) -> np.ndarray:
        """Reset environment for new episode."""
        if seed is not None:
            self.rng = np.random.RandomState(seed)

        self.freq_dev = self.rng.normal(0, 0.01)
        self.injection = 0.0
        self.soc = self.rng.uniform(0.3, 0.7)
        self.prev_freq_dev = 0.0
        self.price = self.rng.uniform(30, 80)
        self._step_count = 0

        return self._get_obs()

    def step(self, action: float) -> Tuple[np.ndarray, float, bool, dict]:
        """Execute one environment step.

        Returns: (observation, reward, done, info)
        """
        # Scale action from [-1, 1] to [-max_inj, max_inj]
        injection_cmd = float(np.clip(action, -1, 1)) * self.cfg.max_injection_mw

        # Ramp limit
        ramp_limit = 50.0 * self.cfg.dt
        delta = np.clip(injection_cmd - self.injection, -ramp_limit, ramp_limit)
        self.injection += delta

        # Disturbance
        disturbance = self._get_disturbance()

        # Swing equation
        self.prev_freq_dev = self.freq_dev
        ddf_dt = (self.injection - self.cfg.D * self.freq_dev - disturbance) / (2 * self.cfg.H)
        self.freq_dev += ddf_dt * self.cfg.dt
        self.freq_dev = np.clip(self.freq_dev, -3.0, 3.0)

        # SoC dynamics
        energy_mwh = self.injection * self.cfg.dt / 3600
        efficiency = 0.92 if self.injection >= 0 else 1.0 / 0.92
        self.soc -= energy_mwh * efficiency / 400.0  # 400 MWh capacity
        self.soc = np.clip(self.soc, 0.0, 1.0)

        # Price evolution
        self.price += self.rng.normal(0, 1.0) + 0.01 * (50 - self.price)
        self.price = np.clip(self.price, 5.0, 5000.0)

        # Reward
        reward = self._compute_reward()

        self._step_count += 1
        done = self._step_count >= self._max_steps

        info = {
            "freq_deviation": self.freq_dev,
            "injection": self.injection,
            "soc": self.soc,
            "disturbance": disturbance,
            "price": self.price,
        }

        return self._get_obs(), reward, done, info

    def _get_obs(self) -> np.ndarray:
        rocof = (self.freq_dev - self.prev_freq_dev) / self.cfg.dt if self._step_count > 0 else 0.0
        return np.array([
            self.freq_dev / 2.0,         # Normalize to ~[-1, 1]
            rocof / 5.0,
            self.injection / self.cfg.max_injection_mw,
            self.soc * 2.0 - 1.0,       # [0,1] → [-1,1]
            (self.price - 50) / 200.0,   # Normalize price
        ], dtype=np.float32)

    def _compute_reward(self) -> float:
        # Primary: penalize frequency deviation (quadratic)
        freq_penalty = -50.0 * self.freq_dev ** 2

        # Severe penalty beyond threshold
        violation_penalty = 0.0
        if abs(self.freq_dev) > self.cfg.penalty_threshold_hz:
            violation_penalty = -200.0 * (abs(self.freq_dev) - self.cfg.penalty_threshold_hz) ** 2

        # Energy cost
        energy_cost = -0.01 * abs(self.injection) / self.cfg.max_injection_mw

        # Revenue from frequency response (when actively stabilizing)
        revenue = 0.0
        if abs(self.freq_dev) > 0.01 and abs(self.injection) > 1.0:
            revenue = 0.1 * abs(self.injection) / self.cfg.max_injection_mw

        # SoC boundary penalty
        soc_penalty = 0.0
        if self.soc < 0.1 or self.soc > 0.9:
            soc_penalty = -5.0

        # Bonus for keeping frequency near nominal
        stability_bonus = 1.0 if abs(self.freq_dev) < 0.01 else 0.0

        return freq_penalty + violation_penalty + energy_cost + revenue + soc_penalty + stability_bonus

    def _get_disturbance(self) -> float:
        """Curriculum-based disturbance generation."""
        t = self._step_count * self.cfg.dt
        base = self.rng.normal(0, 3.0 * self.cfg.disturbance_severity)

        # Random events
        if self.rng.random() < 0.005:
            base += self.rng.choice([-1, 1]) * self.rng.uniform(30, 100) * self.cfg.disturbance_severity

        # Periodic load pattern
        base += 10.0 * np.sin(2 * np.pi * t / 60) * self.cfg.disturbance_severity

        return base


# ─────────────────────────────────────────────────────────────
# Actor-Critic Networks (enhanced from auto_healing_core.py)
# ─────────────────────────────────────────────────────────────

if TORCH_AVAILABLE:
    class Actor(nn.Module):
        """Policy network: state → action distribution."""
        def __init__(self, state_dim: int = 5, action_dim: int = 1, hidden: int = 256):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(state_dim, hidden),
                nn.LayerNorm(hidden),
                nn.ReLU(),
                nn.Linear(hidden, hidden),
                nn.LayerNorm(hidden),
                nn.ReLU(),
            )
            self.mu = nn.Linear(hidden, action_dim)
            self.log_std = nn.Parameter(torch.zeros(action_dim))

        def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
            features = self.net(state)
            mu = torch.tanh(self.mu(features))
            std = torch.exp(torch.clamp(self.log_std, -2.0, 1.0))
            return mu, std

        def get_action(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
            mu, std = self.forward(state)
            dist = Normal(mu, std)
            action = dist.sample()
            log_prob = dist.log_prob(action).sum(-1)
            return torch.clamp(action, -1, 1), log_prob

        def evaluate(self, state: torch.Tensor, action: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
            mu, std = self.forward(state)
            dist = Normal(mu, std)
            log_prob = dist.log_prob(action).sum(-1)
            entropy = dist.entropy().sum(-1)
            return log_prob, entropy

    class Critic(nn.Module):
        """Value network: state → V(s)."""
        def __init__(self, state_dim: int = 5, hidden: int = 256):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(state_dim, hidden),
                nn.LayerNorm(hidden),
                nn.ReLU(),
                nn.Linear(hidden, hidden),
                nn.LayerNorm(hidden),
                nn.ReLU(),
                nn.Linear(hidden, 1),
            )

        def forward(self, state: torch.Tensor) -> torch.Tensor:
            return self.net(state).squeeze(-1)


# ─────────────────────────────────────────────────────────────
# Experience Buffer
# ─────────────────────────────────────────────────────────────

@dataclass
class Experience:
    states: np.ndarray
    actions: np.ndarray
    rewards: np.ndarray
    log_probs: np.ndarray
    values: np.ndarray
    dones: np.ndarray


class RolloutBuffer:
    """Collects trajectories for PPO updates."""

    def __init__(self):
        self.states: List[np.ndarray] = []
        self.actions: List[float] = []
        self.rewards: List[float] = []
        self.log_probs: List[float] = []
        self.values: List[float] = []
        self.dones: List[bool] = []

    def store(self, state, action, reward, log_prob, value, done):
        self.states.append(state)
        self.actions.append(action)
        self.rewards.append(reward)
        self.log_probs.append(log_prob)
        self.values.append(value)
        self.dones.append(done)

    def get(self) -> Experience:
        return Experience(
            states=np.array(self.states, dtype=np.float32),
            actions=np.array(self.actions, dtype=np.float32),
            rewards=np.array(self.rewards, dtype=np.float32),
            log_probs=np.array(self.log_probs, dtype=np.float32),
            values=np.array(self.values, dtype=np.float32),
            dones=np.array(self.dones, dtype=np.float32),
        )

    def clear(self):
        self.__init__()

    def __len__(self):
        return len(self.states)


# ─────────────────────────────────────────────────────────────
# PPO Trainer
# ─────────────────────────────────────────────────────────────

@dataclass
class TrainingConfig:
    """PPO hyperparameters."""
    lr_actor: float = 3e-4
    lr_critic: float = 1e-3
    gamma: float = 0.99
    lam: float = 0.95          # GAE lambda
    clip_eps: float = 0.2
    entropy_coef: float = 0.01
    value_coef: float = 0.5
    max_grad_norm: float = 0.5
    ppo_epochs: int = 4
    mini_batch_size: int = 64
    n_episodes: int = 500
    eval_interval: int = 50
    save_interval: int = 100
    curriculum_stages: int = 5
    model_dir: str = ""


class PPOTrainer:
    """Proximal Policy Optimization trainer for grid stabilization."""

    def __init__(self, config: Optional[TrainingConfig] = None):
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch required for DRL training")

        self.cfg = config or TrainingConfig()
        if not self.cfg.model_dir:
            self.cfg.model_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "models"
            )
        os.makedirs(self.cfg.model_dir, exist_ok=True)

        self.device = torch.device(
            "mps" if torch.backends.mps.is_available()
            else "cuda" if torch.cuda.is_available()
            else "cpu"
        )

        # Networks
        self.actor = Actor().to(self.device)
        self.critic = Critic().to(self.device)
        self.actor_optim = optim.Adam(self.actor.parameters(), lr=self.cfg.lr_actor)
        self.critic_optim = optim.Adam(self.critic.parameters(), lr=self.cfg.lr_critic)

        # Logging
        self.training_log: List[Dict] = []

    def compute_gae(self, rewards, values, dones) -> Tuple[np.ndarray, np.ndarray]:
        """Generalized Advantage Estimation."""
        n = len(rewards)
        advantages = np.zeros(n, dtype=np.float32)
        returns = np.zeros(n, dtype=np.float32)
        gae = 0.0

        for t in reversed(range(n)):
            next_value = values[t + 1] if t + 1 < n else 0.0
            delta = rewards[t] + self.cfg.gamma * next_value * (1 - dones[t]) - values[t]
            gae = delta + self.cfg.gamma * self.cfg.lam * (1 - dones[t]) * gae
            advantages[t] = gae
            returns[t] = advantages[t] + values[t]

        return advantages, returns

    def ppo_update(self, experience: Experience):
        """Run PPO clipped surrogate update."""
        advantages, returns = self.compute_gae(
            experience.rewards, experience.values, experience.dones
        )

        # Normalize advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # Convert to tensors
        states = torch.FloatTensor(experience.states).to(self.device)
        actions = torch.FloatTensor(experience.actions).to(self.device)
        old_log_probs = torch.FloatTensor(experience.log_probs).to(self.device)
        advantages_t = torch.FloatTensor(advantages).to(self.device)
        returns_t = torch.FloatTensor(returns).to(self.device)

        n = len(experience.states)
        total_actor_loss = 0.0
        total_critic_loss = 0.0

        for _ in range(self.cfg.ppo_epochs):
            indices = np.random.permutation(n)

            for start in range(0, n, self.cfg.mini_batch_size):
                end = start + self.cfg.mini_batch_size
                idx = indices[start:end]

                batch_states = states[idx]
                batch_actions = actions[idx].unsqueeze(-1) if actions[idx].dim() == 1 else actions[idx]
                batch_old_lp = old_log_probs[idx]
                batch_adv = advantages_t[idx]
                batch_ret = returns_t[idx]

                # Actor loss (clipped surrogate)
                new_lp, entropy = self.actor.evaluate(batch_states, batch_actions)
                ratio = torch.exp(new_lp - batch_old_lp)
                surr1 = ratio * batch_adv
                surr2 = torch.clamp(ratio, 1 - self.cfg.clip_eps, 1 + self.cfg.clip_eps) * batch_adv
                actor_loss = -torch.min(surr1, surr2).mean() - self.cfg.entropy_coef * entropy.mean()

                self.actor_optim.zero_grad()
                actor_loss.backward()
                nn.utils.clip_grad_norm_(self.actor.parameters(), self.cfg.max_grad_norm)
                self.actor_optim.step()

                # Critic loss
                values_pred = self.critic(batch_states)
                critic_loss = self.cfg.value_coef * nn.functional.mse_loss(values_pred, batch_ret)

                self.critic_optim.zero_grad()
                critic_loss.backward()
                nn.utils.clip_grad_norm_(self.critic.parameters(), self.cfg.max_grad_norm)
                self.critic_optim.step()

                total_actor_loss += actor_loss.item()
                total_critic_loss += critic_loss.item()

        return total_actor_loss, total_critic_loss

    def collect_rollout(self, env: GridEnv, n_steps: int = 2400) -> Tuple[Experience, float]:
        """Collect n_steps of experience from env."""
        buffer = RolloutBuffer()
        obs = env.reset()
        episode_reward = 0.0
        episode_rewards = []

        for _ in range(n_steps):
            state_t = torch.FloatTensor(obs).unsqueeze(0).to(self.device)

            with torch.no_grad():
                action, log_prob = self.actor.get_action(state_t)
                value = self.critic(state_t)

            action_np = action.cpu().numpy().flatten()[0]
            next_obs, reward, done, info = env.step(action_np)

            buffer.store(
                obs, action_np, reward,
                log_prob.cpu().item(), value.cpu().item(), done
            )

            episode_reward += reward
            obs = next_obs

            if done:
                episode_rewards.append(episode_reward)
                episode_reward = 0.0
                obs = env.reset()

        avg_reward = np.mean(episode_rewards) if episode_rewards else episode_reward
        return buffer.get(), avg_reward

    def train(self, market: str = "ERCOT") -> Dict:
        """Full training loop with curriculum learning."""
        logger.info("=" * 60)
        logger.info(" PRIMEnergeia DRL Training Pipeline (PPO)")
        logger.info(f" Market: {market} | Episodes: {self.cfg.n_episodes}")
        logger.info(f" Device: {self.device}")
        logger.info("=" * 60)

        env_config = EnvConfig(market=market)
        best_reward = -float("inf")

        for episode in range(self.cfg.n_episodes):
            # Curriculum: increase disturbance severity over training
            stage = min(episode // (self.cfg.n_episodes // self.cfg.curriculum_stages),
                        self.cfg.curriculum_stages - 1)
            env_config.disturbance_severity = 0.2 + 0.2 * stage
            env = GridEnv(env_config)

            # Collect rollout
            experience, avg_reward = self.collect_rollout(env, n_steps=2400)

            # PPO update
            actor_loss, critic_loss = self.ppo_update(experience)

            # Logging
            log_entry = {
                "episode": episode,
                "avg_reward": float(avg_reward),
                "actor_loss": float(actor_loss),
                "critic_loss": float(critic_loss),
                "severity": float(env_config.disturbance_severity),
                "stage": stage,
            }
            self.training_log.append(log_entry)

            if episode % 10 == 0:
                logger.info(
                    f"  Ep {episode:4d} | Reward: {avg_reward:8.1f} | "
                    f"A_loss: {actor_loss:.4f} | C_loss: {critic_loss:.4f} | "
                    f"Severity: {env_config.disturbance_severity:.1f}"
                )

            # Save best model
            if avg_reward > best_reward:
                best_reward = avg_reward
                self.save_checkpoint("best", market)

            # Periodic checkpoint
            if episode % self.cfg.save_interval == 0 and episode > 0:
                self.save_checkpoint(f"ep{episode}", market)

            # Evaluation
            if episode % self.cfg.eval_interval == 0 and episode > 0:
                self.evaluate(market)

        # Final save
        self.save_checkpoint("final", market)
        self._save_training_log(market)

        logger.info(f"\n  Training complete. Best reward: {best_reward:.1f}")
        return {"best_reward": best_reward, "log": self.training_log}

    def evaluate(self, market: str = "ERCOT", n_episodes: int = 5) -> Dict:
        """Evaluate current policy on test scenarios."""
        env = GridEnv(EnvConfig(market=market, disturbance_severity=1.0))
        total_rewards = []
        total_violations = 0

        self.actor.eval()
        for ep in range(n_episodes):
            obs = env.reset(seed=1000 + ep)
            ep_reward = 0.0
            done = False
            while not done:
                state_t = torch.FloatTensor(obs).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    mu, _ = self.actor(state_t)
                    action = mu.cpu().numpy().flatten()[0]
                obs, reward, done, info = env.step(action)
                ep_reward += reward
                if abs(info["freq_deviation"]) > env.cfg.penalty_threshold_hz:
                    total_violations += 1
            total_rewards.append(ep_reward)
        self.actor.train()

        avg_reward = np.mean(total_rewards)
        logger.info(f"  [EVAL] Avg reward: {avg_reward:.1f} | Violations: {total_violations}")
        return {"avg_reward": float(avg_reward), "violations": total_violations}

    def save_checkpoint(self, tag: str, market: str):
        """Save model checkpoint."""
        path = os.path.join(self.cfg.model_dir, f"prime_drl_{market}_{tag}.pt")
        torch.save({
            "actor": self.actor.state_dict(),
            "critic": self.critic.state_dict(),
            "actor_optim": self.actor_optim.state_dict(),
            "critic_optim": self.critic_optim.state_dict(),
        }, path)
        logger.info(f"  Checkpoint saved: {path}")

    def load_checkpoint(self, path: str):
        """Load model checkpoint."""
        checkpoint = torch.load(path, map_location=self.device)
        self.actor.load_state_dict(checkpoint["actor"])
        self.critic.load_state_dict(checkpoint["critic"])
        self.actor_optim.load_state_dict(checkpoint["actor_optim"])
        self.critic_optim.load_state_dict(checkpoint["critic_optim"])
        logger.info(f"  Checkpoint loaded: {path}")

    def _save_training_log(self, market: str):
        """Save training metrics to JSON."""
        path = os.path.join(self.cfg.model_dir, f"training_log_{market}.json")
        with open(path, "w") as f:
            json.dump(self.training_log, f, indent=2)


# ─────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(name)s] %(message)s")

    parser = argparse.ArgumentParser(description="PRIMEnergeia DRL Trainer")
    parser.add_argument("--market", default="ERCOT", choices=["ERCOT", "SEN", "MIBEL", "NEM", "CAISO"])
    parser.add_argument("--episodes", type=int, default=500)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--resume", type=str, default=None, help="Checkpoint path to resume from")
    args = parser.parse_args()

    config = TrainingConfig(
        n_episodes=args.episodes,
        lr_actor=args.lr,
    )

    trainer = PPOTrainer(config)
    if args.resume:
        trainer.load_checkpoint(args.resume)

    trainer.train(market=args.market)
