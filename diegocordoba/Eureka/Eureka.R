# Load required libraries
library(quantmod)
library(PerformanceAnalytics)
library(quadprog)

# Define the stock tickers
tickers <- c("RMS.PA", "MC.PA", "AAPL", "KER.PA", "AMZN", "AVGO", "NVDA", 
             "AXP", "JPM", "AIR.PA", "NFLX", "CFR.SW")

# Download historical price data
getSymbols(tickers, src = "yahoo", from = "2018-01-01", to = "2023-12-31", auto.assign = TRUE)

# Extract adjusted close prices and combine into a single data frame
prices <- do.call(merge, lapply(tickers, function(ticker) Cl(get(ticker))))

# Calculate daily returns
returns <- na.omit(ROC(prices, type = "discrete"))

# Calculate mean returns and covariance matrix
mean_returns <- colMeans(returns)
cov_matrix <- cov(returns)

# Define the portfolio optimization function with bounds
optimize_portfolio <- function(mean_returns, cov_matrix, risk_free_rate = 0.02, min_weight = 0.05, max_weight = 0.20) {
  num_assets <- length(mean_returns)
  
  # Set up quadratic programming inputs
  Dmat <- 2 * cov_matrix  # Quadratic coefficients
  dvec <- rep(0, num_assets)  # Linear coefficients (zero for minimization)
  
  # Create constraints for weights
  # Sum of weights = 1
  Aeq <- matrix(1, nrow = 1, ncol = num_assets)
  beq <- 1
  
  # Bounds for weights (min and max constraints)
  Ain <- rbind(diag(num_assets), -diag(num_assets))  # Identity matrices for bounds
  bin <- c(rep(max_weight, num_assets), rep(-min_weight, num_assets))
  
  # Combine equality and inequality constraints
  Amat <- t(rbind(Aeq, Ain))
  bvec <- c(beq, bin)
  meq <- 1  # Number of equality constraints
  
  # Solve for optimized portfolio
  result <- solve.QP(Dmat, dvec, Amat, bvec, meq)
  weights <- result$solution
  
  # Calculate portfolio return and volatility
  portfolio_return <- sum(weights * mean_returns)
  portfolio_volatility <- sqrt(t(weights) %*% cov_matrix %*% weights)
  sharpe_ratio <- (portfolio_return - risk_free_rate) / portfolio_volatility
  
  list(weights = weights, return = portfolio_return, 
       volatility = portfolio_volatility, sharpe_ratio = sharpe_ratio)
}

# Optimize the portfolio
optimized <- optimize_portfolio(mean_returns, cov_matrix)

# Display the results
cat("Optimized Portfolio Weights:\n")
names(optimized$weights) <- colnames(returns)
print(round(optimized$weights, 4))

cat("\nPortfolio Expected Return:", round(optimized$return * 100, 2), "%\n")
cat("Portfolio Volatility:", round(optimized$volatility * 100, 2), "%\n")
cat("Portfolio Sharpe Ratio:", round(optimized$sharpe_ratio, 2), "\n")

