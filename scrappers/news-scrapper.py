from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from html import escape
from openpyxl import Workbook
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta





# Define search parameters
search_string = "war"
url_to_scrap = "https://www.aljazeera.com/"
number_of_months=0





# Function to download image
def download_image(image_url, filename, output_dir="outputs"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        response = requests.get(image_url)

        if response.status_code == 200:
            with open(os.path.join(output_dir, filename), 'wb') as f:
                f.write(response.content)
            print(f"Image downloaded successfully: {filename}")
        else:
            print(f"Failed to download image: {image_url}. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error downloading image: {e}")

# Function to extract articles from HTML content
def extract_articles(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    articles = soup.find_all("article", class_="gc")
    return articles

# Function to format date
def format_date(date_str):
    date_obj = datetime.strptime(date_str, "%d %b %Y")
    return date_obj

# Function to check if scraping should continue
def keep_scrapping(html_content):
    articles = extract_articles(html_content)
    try:
        last_article_date = articles[-1].find("span", class_="screen-reader-text").get_text(strip=True)
        last_article_formatted = last_article_date[len(last_article_date) - 11:]
        print(last_article_formatted)

        if add_days_to_date(datetime.now(), 30*(number_of_months+1)) > format_date(last_article_formatted):
            print("Continue scraping")
            return True
        else:
            print("Time limit reached")
            return False
    except Exception:
        return True

# Function to add days to date
def add_days_to_date(date_obj, days_to_add):
    new_date = date_obj + timedelta(days=days_to_add)
    return new_date

# Set up workbook
wb = Workbook()
ws = wb.active
ws.append(["Published Date", "Title", "Description", "Link", "Image URL"])

# Set up Selenium
driver = webdriver.Edge()
driver.maximize_window()


# Navigate to the website
driver.get(url_to_scrap)

# Click on the search button
search_btn = driver.find_element(By.CLASS_NAME, "site-header__search-trigger")
search_btn.click()

# Wait for the search input field to be visible
search_input = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, "search-bar__input")))

# Search for articles related to the search string
search_input.send_keys(search_string)
search_button = driver.find_element(By.CLASS_NAME, "css-sp7gd")
search_button.click()

# Select the "Date" option from the dropdown
select_dropdown = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "search-sort-option")))
select = Select(select_dropdown)
select.select_by_value('date')

# Wait for at least 5 articles to be loaded
try:
    articles = WebDriverWait(driver, 10).until(EC.visibility_of_all_elements_located((By.XPATH, "//article[contains(@class, 'gc')]")))
except TimeoutException:
    print("TimeoutException occurred. Saving scraped data so far.")

# Loop to scrape articles
html_content = driver.page_source
while keep_scrapping(html_content):
    try:
        show_more = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, "show-more-button")))
        show_more_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, "show-more-button")))
        driver.execute_script("arguments[0].click();", show_more_button)
        html_content = driver.page_source
    except TimeoutException:
        print("TimeoutException occurred. Saving scraped data so far.")
        break

# Extract and save article content
articles = extract_articles(html_content)
for article in articles:
    try:
        published_date = article.find("span", class_="screen-reader-text").get_text(strip=True)
        full_date = published_date[len(published_date) - 11:]
        print("Published Date:", full_date)

        title = escape(article.find("h3", class_="gc__title").get_text(strip=True))
        description = escape(article.find("div", class_="gc__excerpt").get_text(strip=True))
        link = article.find('a', class_='u-clickable-card__link').get('href')
        image_url = article.find("img", class_="article-card__image gc__image").get('src')

        # Remove the first 11 characters from the description
        trimmed_description = description[11:]

        # Join the first 15 words from the title and append '.jpg'
        image_title = ' '.join(title.split()[:15]) + ".jpg"

        # Download the image
        download_image(image_url, image_title)

        # Add data to the workbook
        ws.append([full_date, title, trimmed_description, link, image_url])

    except AttributeError:
        print("Error occurred while processing article.")
        continue

# Save workbook and quit driver
wb.save("articles.xlsx")
