import streamlit as st
import pandas as pd
import requests
import datetime
import json
from base64 import b64encode

# Set up eBay API credentials

CLIENT_ID = st.secrets["ebay"]["CLIENT_ID"]
CLIENT_SECRET = st.secrets["ebay"]["CLIENT_SECRET"]



# Encode credentials
credentials = b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

# Get OAuth2 token
token_url = "https://api.ebay.com/identity/v1/oauth2/token"
headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Authorization": f"Basic {credentials}"
}
data = {
    "grant_type": "client_credentials",
    "scope": "https://api.ebay.com/oauth/api_scope"
}

response = requests.post(token_url, headers=headers, data=data)
access_token = response.json().get("access_token")
#print("Access token:", access_token)

# Browse API endpoint
search_url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

# eBay category mapping
category_options = {
    "All Categories": None,
    "Cell Phones & Smartphones": "9355",             # Cell phones
    "Tablets & eBook Readers": "171485",             # Tablets
    "Books": "267",                                  # Books
    "Consumer Electronics": "293",                   # General electronics
    "Sporting Goods": "888",                         # Sporting goods
    "Men's Clothing": "1059",                        # Men's clothing
    "Men's Shoes": "93427",                          # Men's shoes
    "DVD & Blu-ray": "617"                           # DVD & Blu-ray
}

st.title("eBay Product Listings")
st.write("This app fetches the latest eBay listings based on selected category and displays them in a table.")

# UI input from user

# Category dropdown
selected_category = st.selectbox("Category", options=list(category_options.keys()))

# Dropdown filter
listing_type_filter = st.selectbox(
    "Filter by listing type",
    ["All", "Auction", "Fixed Price", "Best Offer"]
)

# Search term, max price, and limit inputs
search_term = st.text_input("Search for:", "iPhone")
max_price = st.number_input("Maximum total price ($):", min_value=1, max_value=10000, value=150)
limit = st.slider("Number of listings to fetch:", min_value=1, max_value=100, value=25)

# Construct query with exclusions
query = f'"{search_term}" -(case,cover,keyboard,manual,guide,screen,protector,folio,box,accessory,cable,cord,charger,pen,for parts,not working)'

# Search parameters
params = {
    "q": query,
    "filter": f"price:[50..{max_price}],priceCurrency:USD,conditions:{{NEW|USED|NEW_OTHER|MANUFACTURER_REFURBISHED|SELLER_REFURBISHED}}",
    "limit": limit
}

# Add category ID if not "All Categories"
category_id = category_options[selected_category]
if category_id:
    params["category_ids"] = category_id

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# Run search on button click
if st.button("Search eBay"):
    response = requests.get("https://api.ebay.com/buy/browse/v1/item_summary/search", params=params, headers=headers)
    items = response.json().get("itemSummaries", [])

    results = []
    for item in items:
        title = item.get("title", "")
        raw_price = item.get("price", {}).get("value")
        price = float(raw_price) if raw_price else 0.0
        shipping = float(item.get("shippingOptions", [{}])[0].get("shippingCost", {}).get("value", 0.0))
        total_cost = price + shipping
        link = item.get("itemWebUrl")
        buying_options = item.get("buyingOptions", [])

        
        # Apply dropdown filter
        if listing_type_filter == "Auction" and "AUCTION" not in buying_options:
            continue
        elif listing_type_filter == "Fixed Price" and "FIXED_PRICE" not in buying_options:
            continue
        elif listing_type_filter == "Best Offer" and "BEST_OFFER" not in buying_options:
            continue

        # Determine end time if it's an auction
        end_time_str = item.get("itemEndDate")
        end_time = "N/A"
        if "AUCTION" in buying_options and end_time_str:
            try:
                utc_dt = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                local_dt = utc_dt.astimezone()  # Convert to local time
                end_time = local_dt.strftime("%Y-%m-%d %I:%M %p %Z")
            except Exception:
                end_time = "Not in Auction"
        
        # Number of bids (only for auctions)
        bid_count = item.get("bidCount") if "AUCTION" in buying_options else None

        if total_cost <= max_price:
            results.append({
                "listing": title,
                "condition": item.get("condition"),
                "current_bid" if "AUCTION" in buying_options else "price": price,
                "shipping": shipping,
                "total": total_cost,
                "listing_type": item.get("buyingOptions", []),
                "bid_count": bid_count,
                "auction_end_time": end_time,
                "seller": item.get("seller", {}).get("username"),
                "seller_feedback": item.get("seller", {}).get("feedbackPercentage"),
                "seller_feedback_score": item.get("seller", {}).get("feedbackScore"),
                "link": link
            })

    
    if results:
        df = pd.DataFrame(results)
        df = df.sort_values(by="total").reset_index(drop=True)
        # Format currency
        def format_currency(val):
            return f"${val:,.2f}"
        df["price"] = df["price"].apply(format_currency)
        df["shipping"] = df["shipping"].apply(format_currency)
        df["total"] = df["total"].apply(format_currency)
            # Style the DataFrame
        styled_df = df.style.set_properties(
            **{
            "text-align": "center",  # center all cells
            "white-space": "pre-wrap"  # wrap text in 'listing'
            }
        ).set_table_styles(
        [
            {"selector": "th", "props": [("font-weight", "bold"), ("text-align", "center")]}
        ]
    )

        st.dataframe(
            styled_df,
            column_config={
                "link": st.column_config.LinkColumn("Link", display_text="View Listing")
            },
            use_container_width=True
        )
    else:
        st.write("No listings found under that price.")



