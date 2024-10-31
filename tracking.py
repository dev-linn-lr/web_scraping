import requests
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import time
from dotenv import load_dotenv
import os
from bs4 import BeautifulSoup
import csv
from playwright.sync_api import sync_playwright  # Import Playwright
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Function to get the full page source using Playwright
def get_full_page_source(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page_source = page.content()
        browser.close()
    return page_source

# Function to calculate the hash of the content
def calculate_hash(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()

# Function to get the website content
def get_website_content(url):
    response = requests.get(url)
    return response.text

# Function to send an email
def send_email(subject, body, to_emails):
    from_email = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = ", ".join(to_emails)
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(from_email, password)
    text = msg.as_string()
    server.sendmail(from_email, to_emails, text)
    server.quit()


def generate_html_table_rows(data):
    rows = ""
    for row in data:
        rows += f"<tr>"
        for cell in row:
            if data.index(row) % 2 == 0:
                rows += f"<td class='py-2 text-wrap w-1/3 break-all px-4 border-b border-gray-200 bg-gray-100'>{cell}</td>"
            else:
                rows += f"<td class='py-2 text-wrap w-1/3 break-all px-4 border-b border-gray-200'>{cell}</td>"
        rows += f"</tr>"
    return rows

# Function to scrape all information from the website
def scrape_website(url):
    page_source = get_full_page_source(url)
    soup = BeautifulSoup(page_source, 'html.parser')

    # Extract text content from main tags
    text_data = []
    for tag in ["a", "abbr", "address", "area", "article", "aside", "audio", "b", "base", "bdi", "bdo", "blockquote", "body", "br", "button", "canvas", "caption", "cite", "code", "col", "colgroup", "data", "datalist", "dd", "del", "details", "dfn", "dialog", "div", "dl", "dt", "em", "embed", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "head", "header", "hr", "html", "i", "iframe", "img", "input", "ins", "kbd", "label", "legend", "li", "link", "main", "map", "mark", "meta", "meter", "nav", "noscript", "object", "ol", "optgroup", "option", "output", "p", "param", "picture", "pre", "progress", "q", "rp", "rt", "s", "samp", "script", "section", "select", "small", "source", "span", "strong", "style", "sub", "sup", "table", "tbody", "td", "template", "textarea", "tfoot", "th", "thead", "time", "title", "tr", "track", "u", "ul", "var", "video", "wbr"]:
        for element in soup.find_all(tag):
            text_content = element.get_text(strip=True)
            if text_content:  # Avoid empty strings
                text_data.append(['テキスト', text_content, ""])

    # Extract all links
    link_data = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        link_text = link.get_text(strip=True)
        link_data.append(['リンク', link_text, href])

    # Extract all images
    image_data = []
    for img in soup.find_all('img', src=True):
        img_src = img['src']
        img_alt = img.get('alt', '代替テキストなし')
        image_data.append(['画像', img_alt, img_src])

    # Combine all extracted data
    all_data = text_data + link_data + image_data

    # Generate HTML table rows
    table_rows = generate_html_table_rows(all_data)

    # Insert the generated rows into the HTML template
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Scraped Data</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    </head>
    <body class="bg-gray-100 p-6">
        <div class="container mx-auto">
            <h1 class="text-2xl font-bold mb-4">Scraped Data</h1>
            <p class="text-2xl font-bold mb-4">Get time: {{ last_updated }}</p>
            <p class="text-2xl font-bold mb-4">Web address target: <a href="{{ url }}" target="_blank">{{ url }}</a></p>

            <table class="min-w-full bg-white">
                <thead>
                    <tr>
                        <th class="py-2 px-4 border-b-2 border-gray-300 text-left leading-tight">Type</th>
                        <th class="py-2 px-4 border-b-2 border-gray-300 text-left leading-tight">Content</th>
                        <th class="py-2 px-4 border-b-2 border-gray-300 text-left leading-tight">URL</th>
                    </tr>
                </thead>
                <tbody>
                    {{ table_rows }}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """.replace("{{ table_rows }}", table_rows).replace("{{ last_updated }}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")).replace("{{ url }}", url)

    # Save the HTML content to a file
    with open("index.html", "w", encoding="utf-8") as file:
        file.write(html_content)

# Function to check for updates
def check_for_update():
    print("更新を確認中")
    url = os.getenv("WEBSITE_URL")
    current_content = get_website_content(url)
    current_hash = calculate_hash(current_content)

    try:
        with open("website_hash.txt", "r") as file:
            previous_hash = file.read()
    except FileNotFoundError:
        previous_hash = ""
    print(f"previous_hash: {previous_hash}")
    print(f"current_hash: {current_hash}")
    if current_hash != previous_hash:
        target_emails = os.getenv("TARGET_EMAILS").split(",")
        print("更新されました")
        # send_email("ウェブサイトが更新されました", "ウェブサイトが更新されました。", target_emails)
        with open("website_hash.txt", "w") as file:
            file.write(current_hash)
        scrape_website(url)  # Call the scrape function when an update is detected
    else:
        print("更新なし")

# Schedule the task
# schedule.every().day.at("09:00").do(check_for_update)

# Keep the script running
while True:
    # schedule.run_pending()
    check_for_update()
    time.sleep(10)

