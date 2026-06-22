import pandas as pd
import numpy as np

class GranasDataPipeline:
    """
    Identification-first data pipeline for the Granas framework.
    Enforces minimum statistical conditions before a single observation touches the neural net.
    """
    def __init__(self, 
                 min_weeks=52, 
                 min_distinct_prices=3, 
                 min_price_changes=5, 
                 min_log_price_range=0.15):
        self.min_weeks = min_weeks
        self.min_distinct_prices = min_distinct_prices
        self.min_price_changes = min_price_changes
        self.min_log_price_range = min_log_price_range

    def filter_nodes(self, df: pd.DataFrame, node_col='node_id', time_col='timestamp', price_col='lmp'):
        """
        Filters out nodes that do not meet the minimum statistical conditions for elasticity estimation.
        
        Args:
            df: DataFrame containing nodal price history.
            node_col: Name of the node identifier column.
            time_col: Name of the timestamp column.
            price_col: Name of the locational marginal price (LMP) column.
            
        Returns:
            Filtered DataFrame containing only valid nodes, and a list of valid node IDs.
        """
        valid_nodes = []
        
        # Group by node to check statistical conditions
        for node, group in df.groupby(node_col):
            # 1. Temporal History (e.g., 52 weeks)
            time_span = group[time_col].max() - group[time_col].min()
            if time_span.days < (self.min_weeks * 7):
                continue
                
            # 2. Distinct Prices
            # Depending on precision, we might round prices first to find "meaningful" distinct clusters
            rounded_prices = group[price_col].round(2)
            if rounded_prices.nunique() < self.min_distinct_prices:
                continue
                
            # 3. Price Changes
            # Count how many times the price actually changed from the previous interval
            price_diffs = rounded_prices.diff().dropna()
            num_changes = (price_diffs != 0).sum()
            if num_changes < self.min_price_changes:
                continue
                
            # 4. Log-Price Range
            # Avoid log(0) issues by clamping strictly positive prices
            positive_prices = group[group[price_col] > 0][price_col]
            if positive_prices.empty:
                continue
                
            log_prices = np.log(positive_prices)
            log_range = log_prices.max() - log_prices.min()
            if log_range < self.min_log_price_range:
                continue
                
            # If all conditions met, this node is valid for the ICNN
            valid_nodes.append(node)
            
        filtered_df = df[df[node_col].isin(valid_nodes)].copy()
        return filtered_df, valid_nodes

    def remove_confounders(self, df: pd.DataFrame, dispatch_col='qL', dr_flag_col='is_dr_event'):
        """
        Removes confounding events (e.g., explicit Demand Response dispatches or out-of-market actions)
        that distort the baseline price-quantity relationship.
        """
        if dr_flag_col in df.columns:
            # Filter out intervals where a DR event was active
            clean_df = df[df[dr_flag_col] == False].copy()
            return clean_df
        return df

    def prepare_tensors(self, df: pd.DataFrame, x_cols, z_col='log_pL', y_col='log_qL'):
        """
        Converts the filtered dataframe into PyTorch-ready tensors.
        x_cols: List of covariate column names (weather, time, topology)
        """
        import torch
        
        # Ensure log columns exist
        if z_col not in df.columns:
            df[z_col] = np.log(df['lmp'].clip(lower=0.01)) # Prevent log(0)
            
        if y_col not in df.columns:
            df[y_col] = np.log(df['quantity'].clip(lower=0.01))
            
        X = torch.tensor(df[x_cols].values, dtype=torch.float32)
        Z = torch.tensor(df[[z_col]].values, dtype=torch.float32)
        Y = torch.tensor(df[[y_col]].values, dtype=torch.float32)
        
        return X, Z, Y
