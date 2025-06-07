import streamlit as st
import pandas as pd
import requests
import datetime
from base64 import b64encode

# eBay API credentials
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

# UI
st.title("eBay Product Listings")
st.write("Fetch latest eBay listings by category, type, and max price.")

# Category options with combined Tech Accessories
category_options = {
    "All Categories": None,
    "Cell Phones & Smartphones": "9355",
    "Tablets & eBook Readers": "171485",
    "Books": "267",
    "Consumer Electronics": "293",
    "Sporting Goods": "888",
    "Men's Clothing": "1059",
    "Men's Shoes": "93427",
    "DVD & Blu-ray": "617",
    "Tech Accessories": "9394"  # Combined category IDs
}
selected_category = st.selectbox("Category", options=list(category_options.keys()))

# Listing type dropdown
listing_type_filter = st.selectbox(
    "Filter by listing type",
    ["All", "Auction", "Fixed Price", "Best Offer"]
)

# Search input and filters
search_term = st.text_input("Search for:", "iPhone")
max_price = st.number_input("Maximum total price ($):", min_value=1, max_value=10000, value=150)
limit = st.slider("Number of listings to fetch:", min_value=1, max_value=100, value=25)

# Query exclusions based on category
if selected_category in ["Cell Phones & Smartphones", "Tablets & eBook Readers"]:
    query = f'"{search_term}" -(case,cover,keyboard,manual,guide,screen,protector,folio,box,accessory,cable,cord,charger,pen,for parts,not working)'
elif selected_category == "Tech Accessories":
    query = f'"{search_term}" -(broken,defective,not working,for parts)'
else:
    query = f'"{search_term}"'

# Build filters
filters = [
    f"price:[1..{max_price}]",
    "priceCurrency:USD",
    "conditions:{1000|1500|2000|2500|3000}"
]
if listing_type_filter == "Auction":
    filters.append("buyingOptions:{AUCTION}")
elif listing_type_filter == "Fixed Price":
    filters.append("buyingOptions:{FIXED_PRICE}")
elif listing_type_filter == "Best Offer":
    filters.append("buyingOptions:{BEST_OFFER}")

params = {
    "q": query,
    "filter": ",".join(filters),
    "limit": limit
}

# Add category ID(s)
category_ids = category_options[selected_category]
if category_ids:
    if isinstance(category_ids, list):
        params["category_ids"] = ",".join(category_ids)
    else:
        params["category_ids"] = category_ids

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# Button to search
if st.button("Search eBay"):
    response = requests.get("https://api.ebay.com/buy/browse/v1/item_summary/search", params=params, headers=headers)
    items = response.json().get("itemSummaries", [])

    results = []
    for item in items:
        title = item.get("title", "")
        price = float(item.get("price", {}).get("value", 0.0))
        shipping = float(item.get("shippingOptions", [{}])[0].get("shippingCost", {}).get("value", 0.0))
        total_cost = price + shipping
        link = item.get("itemWebUrl")
        buying_options = item.get("buyingOptions", [])
       
        # Filter out for parts not working (condition ID: 7000)
        condition_id = item.get("conditionId")
        if condition_id == "7000":
            continue


        end_time_str = item.get("itemEndDate")
        end_time = "N/A"
        if "AUCTION" in buying_options and end_time_str:
            try:
                utc_dt = datetime.datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                local_dt = utc_dt.astimezone()
                end_time = local_dt.strftime("%Y-%m-%d %I:%M %p %Z")
            except Exception:
                end_time = "Invalid date"

        bid_count = item.get("bidCount") if "AUCTION" in buying_options else None

        if total_cost <= max_price:
            results.append({
                "listing": title,
                "condition": item.get("condition"),
                "price": price,
                "shipping": shipping,
                "total": total_cost,
                "listing_type": ", ".join(buying_options),
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

        def format_currency(val):
            return f"${val:,.2f}"
        for col in ["price", "current_bid", "shipping", "total"]:
            if col in df.columns:
                df[col] = df[col].apply(format_currency)

        styled_df = df.style.set_properties(
            **{"text-align": "center", "white-space": "pre-wrap"}
        ).set_table_styles([
            {"selector": "th", "props": [("font-weight", "bold"), ("text-align", "center")]}
        ])

        st.dataframe(
            styled_df,
            column_config={
                "link": st.column_config.LinkColumn("Link", display_text="View Listing")
            },
            use_container_width=True
        )
    else:
        st.write("No listings found under that price.")
