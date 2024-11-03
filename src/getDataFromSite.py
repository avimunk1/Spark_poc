import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import pandas as pd

def scrape_campaign_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Connection": "keep-alive"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to retrieve the webpage: {url}. Status code: {response.status_code}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    title_tag = soup.find("h1", class_="product_title entry-title")
    title = title_tag.get_text(strip=True) if title_tag else "Title not found"

    description_tag = soup.find("p", string=lambda text: text and "mortgage advisor" in text)
    description = description_tag.get_text(strip=True) if description_tag else "Description not found"

    content_div = soup.find("div", class_="large-12 columns nasa-content-panel")
    content = content_div.get_text(separator="\n", strip=True) if content_div else "Content not found"

    project_id_tag = soup.find("input", {"id": "spark_campaign_id"})
    project_id = project_id_tag["value"] if project_id_tag else "Project ID not found"

    return {
        "project_id": project_id,
        "title": title,
        "description": description,
        "content": content
    }

def process_sitemap(sitemap_url, output_path):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Connection": "keep-alive"
    }

    response = requests.get(sitemap_url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to retrieve the sitemap. Status code: {response.status_code}")
        return

    root = ET.fromstring(response.content)
    namespaces = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [url.find("ns:loc", namespaces).text for url in root.findall("ns:url", namespaces)]

    campaign_data_list = []
    for url in urls:
        campaign_data = scrape_campaign_data(url)
        if campaign_data:
            campaign_data_list.append(campaign_data)

    # Convert the list of dictionaries to a DataFrame and save as an Excel file
    df = pd.DataFrame(campaign_data_list)
    df.to_excel(output_path, index=False)
    print(f"Data successfully saved to {output_path}")

# Define the output path
output_path = "/Users/avimunk/PycharmProjects/spark_poc/files/export.xlsx"
process_sitemap("https://sparkil.org/product-sitemap.xml", output_path)
