# GOLDM 5-Hour Chart Data using Direct Sharekhan API Endpoint
# Direct REST API calls to https://api.sharekhan.com/skapi/services/historical/

import requests
import pandas as pd
import json
from datetime import datetime, timedelta
import time

class SharekhanDirectAPI:
    def __init__(self, api_key, secret_key, user_id):
        self.api_key = api_key
        self.secret_key = secret_key
        self.user_id = user_id
        self.base_url = "https://api.sharekhan.com/skapi/services"
        self.session = requests.Session()
        self.auth_token = None
        
    def login(self):
        """
        Authenticate with Sharekhan API and get auth token
        """
        login_url = f"{self.base_url}/auth/login"
        
        login_payload = {
            "userId": self.user_id,
            "apiKey": self.api_key,
            "secretKey": self.secret_key
        }
        
        try:
            response = self.session.post(login_url, json=login_payload)
            response.raise_for_status()
            
            auth_data = response.json()
            if auth_data.get('status') == 'success':
                self.auth_token = auth_data.get('data', {}).get('authToken')
                # Set auth token in session headers
                self.session.headers.update({
                    'Authorization': f'Bearer {self.auth_token}',
                    'Content-Type': 'application/json'
                })
                print("✓ Login successful")
                return True
            else:
                print(f"✗ Login failed: {auth_data.get('message', 'Unknown error')}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Login error: {e}")
            return False
    
    def get_goldm_historical_data(self, exchange="MCX", scripcode="GOLDM", interval="5H", 
                                  days_back=30, from_date=None, to_date=None):
        """
        Fetch GOLDM historical data using direct API endpoint
        
        Parameters:
        - exchange: Exchange code (MCX for commodities)
        - scripcode: Script code (GOLDM for Gold Mini)
        - interval: Time interval (1m, 5m, 15m, 1H, 5H, 1D, etc.)
        - days_back: Number of days to fetch (if from_date/to_date not provided)
        - from_date: Start date (YYYY-MM-DD format)
        - to_date: End date (YYYY-MM-DD format)
        """
        
        if not self.auth_token:
            print("✗ Please login first")
            return None
        
        # Build the endpoint URL
        endpoint_url = f"{self.base_url}/historical/{exchange}/{scripcode}/{interval}"
        
        # Calculate date range if not provided
        if not from_date or not to_date:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            from_date = start_date.strftime("%Y-%m-%d")
            to_date = end_date.strftime("%Y-%m-%d")
        
        # API parameters
        params = {
            "fromDate": from_date,
            "toDate": to_date
        }
        
        print(f"Fetching data from: {endpoint_url}")
        print(f"Date range: {from_date} to {to_date}")
        
        try:
            response = self.session.get(endpoint_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'success':
                historical_data = data.get('data', [])
                print(f"✓ Fetched {len(historical_data)} data points")
                return historical_data
            else:
                print(f"✗ API Error: {data.get('message', 'Unknown error')}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Request error: {e}")
            return None
    
    def logout(self):
        """
        Logout and cleanup session
        """
        if self.auth_token:
            logout_url = f"{self.base_url}/auth/logout"
            try:
                response = self.session.post(logout_url)
                if response.status_code == 200:
                    print("✓ Logged out successfully")
                else:
                    print("⚠ Logout response:", response.status_code)
            except:
                print("⚠ Logout request failed (continuing anyway)")
            
            self.auth_token = None
            self.session.headers.pop('Authorization', None)

def process_goldm_data(raw_data):
    """
    Process raw GOLDM data from Sharekhan API into pandas DataFrame
    """
    if not raw_data:
        print("No data to process")
        return None
    
    try:
        df = pd.DataFrame(raw_data)
        
        # Map API response fields to standard OHLCV format
        # Adjust these field names based on actual API response structure
        field_mapping = {
            'timestamp': 'datetime',
            'dateTime': 'datetime',
            'time': 'datetime',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'ltp': 'close',  # Last traded price as close
            'volume': 'volume',
            'vol': 'volume'
        }
        
        # Rename columns based on mapping
        for old_name, new_name in field_mapping.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        # Handle datetime conversion
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.set_index('datetime')
        
        # Ensure OHLCV columns are numeric
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Sort by datetime
        df = df.sort_index()
        
        # Remove any duplicate timestamps
        df = df[~df.index.duplicated(keep='last')]
        
        return df
        
    except Exception as e:
        print(f"Error processing data: {e}")
        return None

def get_goldm_scrip_codes():
    """
    Common GOLDM scrip codes for different expiries
    Note: These may change based on current active contracts
    """
    return {
        'GOLDM_CURRENT': 'GOLDM',  # Current month
        'GOLDM_NEXT': 'GOLDM1',   # Next month  
        'GOLDM_FAR': 'GOLDM2'     # Far month
    }

def analyze_goldm_data(df):
    """
    Analyze GOLDM 5-hour data and provide insights
    """
    if df is None or df.empty:
        return {"error": "No data to analyze"}
    
    analysis = {}
    
    # Basic data info
    analysis['data_summary'] = {
        'total_periods': len(df),
        'date_range': {
            'start': df.index.min().strftime('%Y-%m-%d %H:%M'),
            'end': df.index.max().strftime('%Y-%m-%d %H:%M')
        }
    }
    
    # Price analysis
    if 'close' in df.columns:
        latest_price = df['close'].iloc[-1]
        analysis['price_analysis'] = {
            'current_price': f"₹{latest_price:,.2f}",
            'highest_price': f"₹{df['high'].max():,.2f}",
            'lowest_price': f"₹{df['low'].min():,.2f}",
            'average_price': f"₹{df['close'].mean():,.2f}",
            'price_change': f"₹{(df['close'].iloc[-1] - df['close'].iloc[0]):,.2f}",
            'price_change_pct': f"{((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100:.2f}%"
        }
        
        # Volatility analysis
        df['price_change'] = df['close'].pct_change()
        analysis['volatility'] = {
            'std_deviation': f"{df['price_change'].std() * 100:.2f}%",
            'max_gain': f"{df['price_change'].max() * 100:.2f}%",
            'max_loss': f"{df['price_change'].min() * 100:.2f}%"
        }
    
    # Volume analysis
    if 'volume' in df.columns:
        analysis['volume_analysis'] = {
            'total_volume': f"{df['volume'].sum():,.0f}",
            'average_volume': f"{df['volume'].mean():,.0f}",
            'highest_volume': f"{df['volume'].max():,.0f}",
            'latest_volume': f"{df['volume'].iloc[-1]:,.0f}"
        }
    
    return analysis

def save_data_with_timestamp(df, base_filename="goldm_5hr_data"):
    """
    Save data with timestamp in filename
    """
    if df is None or df.empty:
        print("No data to save")
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{base_filename}_{timestamp}.csv"
    
    try:
        df.to_csv(filename)
        print(f"✓ Data saved to {filename}")
        return filename
    except Exception as e:
        print(f"✗ Error saving data: {e}")
        return None

def main():
    """
    Main function to demonstrate GOLDM data fetching with direct API
    """
    print("=== GOLDM 5-Hour Data Fetcher (Direct Sharekhan API) ===\n")
    
    # Initialize API client
    # Replace with your actual credentials
    api = SharekhanDirectAPI(
        api_key="GIaiFf8eFa1gOfdC2W4m6RUb9YOvVYIu",
        secret_key="JBXq5t3E1JEuoarPtQm1VHtT1tEsjOOd", 
        user_id="4036182"
    )
    
    try:
        # Login
        if not api.login():
            print("Failed to login. Please check your credentials.")
            return
        
        # Fetch GOLDM 5-hour data
        print("\nFetching GOLDM 5-hour historical data...")
        raw_data = api.get_goldm_historical_data(
            exchange="MCX",
            scripcode="GOLDM",
            interval="5H",
            days_back=45  # Get 45 days of data
        )
        
        if raw_data:
            # Process the data
            df = process_goldm_data(raw_data)
            
            if df is not None and not df.empty:
                print(f"\n✓ Successfully processed {len(df)} data points")
                
                # Show latest data
                print("\n=== Latest 5 Records ===")
                print(df.tail().to_string())
                
                # Analyze data
                print("\n=== Analysis Summary ===")
                analysis = analyze_goldm_data(df)
                print(json.dumps(analysis, indent=2))
                
                # Save data
                saved_file = save_data_with_timestamp(df)
                if saved_file:
                    print(f"\n✓ Data exported to: {saved_file}")
                
            else:
                print("✗ Failed to process the fetched data")
        else:
            print("✗ No data received from API")
    
    except Exception as e:
        print(f"✗ Error in main execution: {e}")
    
    finally:
        # Always logout
        api.logout()

# Alternative function for different intervals
def fetch_multiple_intervals(api, intervals=['1H', '5H', '1D']):
    """
    Fetch GOLDM data for multiple time intervals
    """
    all_data = {}
    
    for interval in intervals:
        print(f"\nFetching {interval} data...")
        raw_data = api.get_goldm_historical_data(
            interval=interval,
            days_back=30
        )
        
        if raw_data:
            df = process_goldm_data(raw_data)
            if df is not None and not df.empty:
                all_data[interval] = df
                print(f"✓ {interval}: {len(df)} data points")
        
        time.sleep(1)  # Rate limiting
    
    return all_data

# Example usage for specific contract months
def fetch_goldm_contracts():
    """
    Fetch data for different GOLDM contract months
    """
    contracts = get_goldm_scrip_codes()
    api = SharekhanDirectAPI(
        api_key="GIaiFf8eFa1gOfdC2W4m6RUb9YOvVYIu",
        secret_key="JBXq5t3E1JEuoarPtQm1VHtT1tEsjOOd",
        user_id="4036182"
    )
    
    if api.login():
        contract_data = {}
        
        for contract_name, scrip_code in contracts.items():
            print(f"\nFetching {contract_name} ({scrip_code})...")
            
            raw_data = api.get_goldm_historical_data(
                scripcode=scrip_code,
                interval="5H",
                days_back=30
            )
            
            if raw_data:
                df = process_goldm_data(raw_data)
                if df is not None and not df.empty:
                    contract_data[contract_name] = df
            
            time.sleep(1)  # Rate limiting
        
        api.logout()
        return contract_data

if __name__ == "__main__":
    print("⚠️  Please replace API credentials with your actual Sharekhan API details")
    print("⚠️  Uncomment main() call below to execute\n")
    
    # Uncomment to run:
    main()
    
    # Example API endpoint being used:
    print("Using Sharekhan API endpoint:")
    print("https://api.sharekhan.com/skapi/services/historical/{exchange}/{scripcode}/{interval}")
    print("\nExample for GOLDM 5H data:")
    print("https://api.sharekhan.com/skapi/services/historical/MCX/GOLDM/5H")