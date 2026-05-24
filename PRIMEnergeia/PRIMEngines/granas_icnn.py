import torch
import torch.nn as nn
import torch.nn.functional as F

class NonNegativeLinear(nn.Linear):
    """
    A linear layer where weights are enforced to be non-negative.
    This is required for maintaining convexity with respect to the input z.
    """
    def forward(self, input):
        # Clamp weights to be strictly non-negative during the forward pass
        return F.linear(input, F.relu(self.weight), self.bias)

class GranasPICNN(nn.Module):
    """
    Partial Input Convex Neural Network (PICNN) for the Granas Framework.
    
    This model enforces convexity ONLY with respect to the economic input z (log pL), 
    while remaining highly flexible and non-convex with respect to covariates x.
    
    Structure based on Amos et al. (2017):
    u_0 = g_0(x)
    u_{i+1} = \sigma(W_i^{(z)} z + W_i^{(u)} u_i + g_{i+1}(x))
    where W_i^{(u)} are non-negative, and \sigma is convex and non-decreasing.
    """
    def __init__(self, covariate_dim, hidden_dims=[64, 64], z_dim=1):
        super(GranasPICNN, self).__init__()
        
        self.covariate_dim = covariate_dim
        self.z_dim = z_dim
        self.hidden_dims = hidden_dims
        self.num_layers = len(hidden_dims)
        
        # 1. Covariate processing layers (unconstrained)
        # These layers process the weather, topology, load history, etc.
        self.g_layers = nn.ModuleList()
        prev_dim = covariate_dim
        for h_dim in hidden_dims:
            self.g_layers.append(nn.Linear(prev_dim, h_dim))
            prev_dim = h_dim
        # Final projection to match the final output shape if needed
        self.g_final = nn.Linear(prev_dim, 1)

        # 2. Z-path layers (W^{(z)})
        # These project the isolated economic input z (log LMP) into the hidden state
        self.z_layers = nn.ModuleList()
        for h_dim in hidden_dims:
            self.z_layers.append(nn.Linear(z_dim, h_dim, bias=False))
        self.z_final = nn.Linear(z_dim, 1, bias=False)

        # 3. U-path layers (W^{(u)})
        # These project the previous convex hidden state to the next convex hidden state
        # MUST BE NON-NEGATIVE to preserve convexity
        self.u_layers = nn.ModuleList()
        for i in range(self.num_layers - 1):
            self.u_layers.append(NonNegativeLinear(hidden_dims[i], hidden_dims[i+1], bias=False))
        self.u_final = NonNegativeLinear(hidden_dims[-1], 1, bias=False)
        
        # Convex, non-decreasing activation
        self.activation = nn.Softplus() # Smoother than ReLU, strictly convex

    def forward(self, x, z):
        """
        x: Covariates tensor of shape (batch_size, covariate_dim)
        z: Log LMP tensor of shape (batch_size, z_dim)
        """
        # We need to maintain convexity in z.
        # If we want a downward sloping demand, we might model the negative utility,
        # or just ensure the relationship allows for decreasing functions via parameter limits.
        
        # Step 1: Process covariates to get biases for each convex layer
        g_outs = []
        curr_g = x
        for g_layer in self.g_layers:
            curr_g = F.relu(g_layer(curr_g))
            g_outs.append(curr_g)
        g_final_out = self.g_final(curr_g)

        # Step 2: Initialize convex hidden state (u_0)
        # First layer doesn't have a previous u state
        u = self.z_layers[0](z) + g_outs[0]
        u = self.activation(u)

        # Step 3: Iterate through hidden layers
        for i in range(1, self.num_layers):
            z_proj = self.z_layers[i](z)
            u_proj = self.u_layers[i-1](u)
            g_proj = g_outs[i]
            
            u = z_proj + u_proj + g_proj
            u = self.activation(u)
            
        # Step 4: Final Output
        # Represents log qL
        out = self.z_final(z) + self.u_final(u) + g_final_out
        
        return out
