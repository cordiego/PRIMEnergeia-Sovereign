#############################################
# EUREKA I — STATE VECTOR MEASUREMENT SCRIPT #
#############################################

# ---- Libraries ----
library(quantmod)
library(PerformanceAnalytics)
library(TTR)
library(dplyr)

# ---- Configuration ----
tickers <- c("AGQ", "SGOV")

target_vol <- 0.705       # 13.2% annual target volatility
max_dd_limit <- -0.20      # -20% max drawdown tolerance
trading_days <- 252

output_path <- "state_vector.csv"

# ---- Data Ingestion ----
getSymbols(tickers, src = "yahoo", auto.assign = TRUE)

prices <- na.omit(
  do.call(
    merge,
    lapply(tickers, function(t) Ad(get(t)))
  )
)

colnames(prices) <- tickers

# ---- Returns ----
returns <- na.omit(Return.calculate(prices))

# Equal-weight portfolio (measurement only)
weights <- rep(1 / length(tickers), length(tickers))
port_ret <- Return.portfolio(returns, weights = weights)

# ---- Metric Functions ----
realized_vol <- function(x, n) {
  runSD(x, n = n) * sqrt(trading_days)
}

max_drawdown <- function(x) {
  cum <- cumprod(1 + x)
  dd <- cum / cummax(cum) - 1
  min(dd, na.rm = TRUE)
}

vrp_proxy <- function(x, n = 20) {
  rv <- runSD(x, n)^2 * trading_days
  iv <- EMA(rv, n = n)
  iv - rv
}

# ---- State Vector (STRICT TYPES) ----
state <- data.frame(
  date = as.Date(index(port_ret)[nrow(port_ret)]),
  
  realized_vol_20 = as.numeric(
    realized_vol(port_ret, 20)[nrow(port_ret)]
  ),
  
  realized_vol_60 = as.numeric(
    realized_vol(port_ret, 60)[nrow(port_ret)]
  ),
  
  target_vol = target_vol,
  
  max_drawdown = max_drawdown(port_ret),
  
  vrp_20 = as.numeric(
    vrp_proxy(port_ret, 20)[nrow(port_ret)]
  ),
  
  exposure = sum(abs(weights)),
  
  leverage = 1.0,           # update only if externally leveraged
  
  liquidity_buffer = 1.0    # placeholder (cash / T-bill sleeve)
)

# ---- Persist State History (TYPE-SAFE) ----
if (file.exists(output_path)) {
  history <- read.csv(output_path, stringsAsFactors = FALSE)
  history$date <- as.Date(history$date)
  history <- bind_rows(history, state)
} else {
  history <- state
}

write.csv(history, output_path, row.names = FALSE)

cat("Eureka I state vector updated successfully.\n")
