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
    "Consumer Electronics": "293"                    # General electronics
}

st.title("eBay Product Listings")
st.write("This app fetches the latest eBay listings based on selected category and displays them in a table.")

# UI input from user

# Category dropdown
selected_category = st.selectbox("Category", options=list(category_options.keys()))

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


# Run only if user clicks
if st.button("Search eBay"):
    response = requests.get("https://api.ebay.com/buy/browse/v1/item_summary/search", params=params, headers=headers)
    items = response.json().get("itemSummaries", [])

    # Process results
    results = []
    for item in items:
        title = item.get("title", "")
        price = float(item.get("price", {}).get("value", 0))
        shipping = float(item.get("shippingOptions", [{}])[0].get("shippingCost", {}).get("value", 0.0))
        total_cost = price + shipping
        end_time = item.get("itemEndDate")
        #end_time_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00")) if end_time else None

        if total_cost <= max_price:
            results.append({
                "listing": title,
                "price": price,
                "condition": item.get("condition"),
                "shipping": shipping,
                "total": total_cost,
                "seller": item.get("seller", {}).get("username"),
                "seller_feedback": item.get("seller", {}).get("feedbackPercentage"),
                "seller_feedback_score": item.get("seller", {}).get("feedbackScore"),
                # "link": f"[View Listing]({item.get('itemWebUrl')})"
                "link": item.get("itemWebUrl")  # Direct link to the listing
                
            })

    # if results:
    #     df = pd.DataFrame(results)
    #     df = df.sort_values(by=["total"]).reset_index(drop=True)
    #     st.write(df)
    # else:
    #     st.write("No listings found under that price.")


    if results:
        style = """
<style>
    table {
        width: 100%;
        border-collapse: collapse;
    }
    th {
        position: sticky;
        top: 0;
        background-color: #f9f9f9;
        z-index: 1;
        text-align: center;
        padding: 8px;
    }
    td {
        text-align: center;
        padding: 8px;
    }
</style>
"""
        df = pd.DataFrame(results)
        df = df[~df['condition'].str.contains("for parts or not working", case=False, na=False)]
        df["link"] = df["link"].apply(lambda url: f'<a href="{url}" target="_blank">View Listing</a>')
        df = df.sort_values(by=["total"]).reset_index(drop=True)

        st.write("### eBay Listings")
        st.write(style + df.to_html(escape=False, index=False), unsafe_allow_html=True)
else:
        st.write("No listings found under that price.")



