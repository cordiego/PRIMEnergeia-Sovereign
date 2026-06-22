import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO

class ExecutionEnv(gym.Env):
    """
    A reinforcement learning environment for optimal trade execution.
    The goal is to execute a target percentage of a portfolio within a time window,
    minimizing slippage and taking advantage of VWAP dips.
    """
    def __init__(self, data, target_shares, time_window=12):
        super(ExecutionEnv, self).__init__()
        self.data = data.reset_index(drop=True)
        self.target_shares = target_shares
        self.time_window = min(time_window, len(self.data))
        
        # Actions: Percentage of remaining order to execute now (0.0 to 1.0)
        self.action_space = spaces.Box(low=0.0, high=1.0, shape=(1,), dtype=np.float32)
        
        # State: [Price, VWAP, RSI, Remaining Shares, Time Left]
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(5,), dtype=np.float32)
        self.reset()
        
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        self.remaining_shares = self.target_shares
        self.executed_shares = 0
        self.total_cost = 0.0
        return self._get_obs(), {}
        
    def _get_obs(self):
        row = self.data.iloc[self.current_step]
        price = row['Close']
        vwap = row.get('VWAP', price)
        rsi = row.get('RSI', 50)
        time_left = self.time_window - self.current_step
        return np.array([price, vwap, rsi, self.remaining_shares, time_left], dtype=np.float32)
        
    def step(self, action):
        row = self.data.iloc[self.current_step]
        price = row['Close']
        vwap = row.get('VWAP', price)
        
        # Calculate execution amount
        pct_to_exec = action[0]
        if self.current_step == self.time_window - 1:
            # Force execute remainder on last step
            pct_to_exec = 1.0
            
        exec_amount = self.remaining_shares * pct_to_exec
        self.remaining_shares -= exec_amount
        self.executed_shares += exec_amount
        
        # Calculate cost and reward
        step_cost = exec_amount * price
        self.total_cost += step_cost
        
        # Reward is based on how much better than VWAP the execution was
        benchmark_cost = exec_amount * vwap
        reward = benchmark_cost - step_cost
        
        self.current_step += 1
        done = self.current_step >= self.time_window
        
        return self._get_obs(), reward, done, False, {}

def train_and_execute_rl(target_pct, current_price, intraday_data):
    """
    Trains a quick PPO model on the recent intraday data to determine optimal execution chunk.
    For production, this would load a pre-trained model.
    """
    if intraday_data is None or intraday_data.empty or target_pct <= 0:
        return target_pct, current_price # Fallback to naive MOC
        
    # Not enough data for RL
    if len(intraday_data) < 15:
        return target_pct, current_price
        
    # Normalize target (assume a fixed portfolio base, e.g., 1000 shares for percentages)
    target_shares = target_pct * 10
    
    env = ExecutionEnv(intraday_data, target_shares=target_shares)
    
    try:
        model = PPO("MlpPolicy", env, n_steps=64, batch_size=16, verbose=0)
        model.learn(total_timesteps=100) # Micro-training
        
        obs, _ = env.reset()
        action, _states = model.predict(obs, deterministic=True)
        
        recommended_pct_to_execute = action[0]
        # Translate back to absolute percentage
        actual_pct = target_pct * recommended_pct_to_execute
        return actual_pct, current_price
    except Exception as e:
        print(f"RL Execution failed: {e}")
        return target_pct, current_price # Fallback
