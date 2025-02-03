import time
import json
import os
import logging
from datetime import datetime
import yfinance as yf
from twilio.rest import Client
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MarketMonitor:
    def __init__(self):
        # Load environment variables
        self.twilio_sid = os.getenv("TWILIO_SID")
        self.twilio_auth = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_phone = os.getenv("TWILIO_PHONE")
        self.user_phone = os.getenv("USER_PHONE")
        
        if not all([self.twilio_sid, self.twilio_auth, self.twilio_phone, self.user_phone]):
            raise EnvironmentError("Missing required environment variables")

        # Initialize Twilio client
        self.client = Client(self.twilio_sid, self.twilio_auth)
        
        # Assets to track with their symbols
        self.assets: Dict[str, str] = {
            "S&P 500": "^GSPC",
            "Bitcoin": "BTC-CAD",
            "Ethereum": "ETH-CAD",
            "Solana": "SOL-CAD",
        }
        
        # Configuration
        self.storage_path = os.getenv("STORAGE_PATH", "market_data.json")
        self.check_interval = int(os.getenv("CHECK_INTERVAL", "300"))  # 5 minutes default
        self.price_history_hours = int(os.getenv("PRICE_HISTORY_HOURS", "3"))
        self.max_retries = 3
        self.retry_delay = 60  # seconds
        
        # Load or initialize market data
        self.market_data = self._load_market_data()

    def _load_market_data(self) -> Dict:
        """Load market data from file or initialize if not exists."""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                logger.info("Loaded existing market data")
                return data
        except Exception as e:
            logger.error(f"Error loading market data: {e}")
        
        # Initialize new data structure
        return {asset: {
            "weekly_high": 0,
            "confirmed_drops": [],
            "recent_prices": [],
            "last_update": datetime.now().isoformat()
        } for asset in self.assets}

    def _save_market_data(self) -> None:
        """Save market data to file with error handling."""
        try:
            with open(self.storage_path, "w") as f:
                json.dump(self.market_data, f, indent=4)
            logger.info("Market data saved successfully")
        except Exception as e:
            logger.error(f"Error saving market data: {e}")

    def get_price(self, symbol: str) -> Optional[float]:
        """Fetch latest price with retries."""
        for attempt in range(self.max_retries):
            try:
                ticker = yf.Ticker(symbol)
                price = ticker.history(period="1d")['Close'].iloc[-1]
                return float(price)
            except Exception as e:
                logger.error(f"Error fetching price for {symbol} (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
        return None

    def send_alert(self, asset: str, drop_level: float, price: float) -> None:
        """Send alert with error handling."""
        message = (
            f"ALERT: {asset} dropped {drop_level}% from its weekly high!\n"
            f"Current price: ${price:.2f} CAD\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        try:
            self.client.messages.create(
                body=message,
                from_=self.twilio_phone,
                to=self.user_phone
            )
            logger.info(f"Alert sent successfully: {message}")
        except Exception as e:
            logger.error(f"Error sending alert: {e}")

    def update_asset_data(self, asset: str, current_price: float) -> None:
        """Update asset data and check for alerts."""
        data = self.market_data[asset]
        
        # Update recent prices
        max_history_points = int(self.price_history_hours * 12)  # 12 checks per hour
        data["recent_prices"].append(current_price)
        if len(data["recent_prices"]) > max_history_points:
            data["recent_prices"] = data["recent_prices"][-max_history_points:]
        
        # Update weekly high if current price is highest in recent history
        if current_price > data["weekly_high"] and current_price == max(data["recent_prices"]):
            data["weekly_high"] = current_price
            data["confirmed_drops"] = []  # Reset drop alerts
            logger.info(f"New weekly high for {asset}: ${current_price:.2f}")
        
        # Check for price drops
        self.check_price_drops(asset, current_price, data)
        
        # Update last check timestamp
        data["last_update"] = datetime.now().isoformat()

    def check_price_drops(self, asset: str, current_price: float, data: Dict) -> None:
        """Check for and alert on price drops."""
        drop_levels = [5, 10, 15, 20, 25]
        
        for drop in drop_levels:
            threshold_price = data["weekly_high"] * (1 - drop / 100)
            
            # Check if price stays below threshold for 3 consecutive checks
            if (len(data["recent_prices"]) >= 3 and
                all(p <= threshold_price for p in data["recent_prices"][-3:]) and
                drop not in data["confirmed_drops"]):
                
                self.send_alert(asset, drop, current_price)
                data["confirmed_drops"].append(drop)

    def test_twilio(self) -> bool:
        """Test Twilio connection by sending a test message."""
        try:
            self.client.messages.create(
                body="Market Monitor starting up - Test Message",
                from_=self.twilio_phone,
                to=self.user_phone
            )
            logger.info("Twilio test message sent successfully")
            return True
        except Exception as e:
            logger.error(f"Twilio test failed: {e}")
            return False

    def run(self) -> None:
        """Main monitoring loop."""
        logger.info("Starting market monitoring...")
        
        # Send test message on startup
        if not self.test_twilio():
            logger.error("Failed to send test message - check Twilio credentials")
            raise Exception("Twilio test failed")
        
        while True:
            try:
                for asset, symbol in self.assets.items():
                    current_price = self.get_price(symbol)
                    
                    if current_price is not None:
                        self.update_asset_data(asset, current_price)
                        logger.info(f"Updated {asset} price: ${current_price:.2f}")
                    else:
                        logger.warning(f"Skipping update for {asset} due to price fetch failure")
                
                self._save_market_data()
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
            
            time.sleep(self.check_interval)

if __name__ == "__main__":
    try:
        monitor = MarketMonitor()
        monitor.run()
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        raise