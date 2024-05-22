import os
from PyPDF2 import PdfReader
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
import re
import time

def init_driver(headless=True):
    """Initialize the Selenium WebDriver."""
    options = Options()
    options.headless = headless
    options.add_argument("--enable-javascript")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36")
    return webdriver.Chrome(options=options)

def find_terms_link(element):
    """Function to locate a terms of service link using various criteria."""
    text = element.get_attribute('innerText')
    href = element.get_attribute('href')
    terms_patterns = [
        'terms of service', 'terms and conditions', 'terms & conditions',
        'terms', 'terms of use', 'general terms and conditions', 'General Terms and Conditions'
    ]
    pattern = re.compile('|'.join(terms_patterns), re.IGNORECASE)
    return pattern.search(text) or pattern.search(href)

def is_terms_of_service_page(content):
    """Check if the current page is likely the Terms of Service page."""
    soup = BeautifulSoup(content, 'html.parser')
    headers = ['h1', 'h2', 'h3']
    for header in headers:
        if soup.find(header, string=lambda text: text and "terms of service" in text.lower()):
            return True
    return False

def download_and_extract_pdf(url):
    pdf_path = download_pdf(url)
    return extract_text_from_pdf(pdf_path)

def download_pdf(url):
    response = requests.get(url)
    pdf_directory = "pdf_files"
    os.makedirs(pdf_directory, exist_ok=True)
    pdf_path = os.path.join(pdf_directory, "tos.pdf")
    with open(pdf_path, "wb") as file:
        file.write(response.content)
    return pdf_path

def extract_text_from_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        print("Extracted text from PDF.")
        return text
    except Exception as e:
        print(f"Failed to extract text from PDF: {e}")
        return "Failed to extract text from PDF."

def navigate_to_tos(driver, url):
    driver.get(url)
    initial_page_source = driver.page_source
    
    if is_terms_of_service_page(initial_page_source):
        print("Already on the Terms of Service page.")
        return initial_page_source, False
    else:
        try:
            footer_links = driver.find_elements(By.CSS_SELECTOR, 'footer a')
            terms_link = next((link for link in footer_links if find_terms_link(link)), None)
            
            if not terms_link:
                all_links = driver.find_elements(By.TAG_NAME, 'a')
                terms_link = next((link for link in all_links if find_terms_link(link)), None)
            
            if terms_link:
                href = terms_link.get_attribute('href')
                if href and href.lower().endswith('.pdf'):
                    print("PDF link found. Downloading and extracting text.")
                    pdf_text = download_and_extract_pdf(href)
                    return pdf_text, True
                else:
                    terms_link.click()
                    WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.TAG_NAME, 'body')))
                    return driver.page_source, False
            else:
                print("No Terms of Service link found.")
                return None, False

        except TimeoutException:
            print("Timed out waiting for terms of service page to load.")
        except Exception as e:
            print(f"Error navigating to Terms of Service page: {e}")
        return None, False

def get_tos_content(url):
    driver = init_driver(headless=True)
    try:
        page_source, is_pdf = navigate_to_tos(driver, url)
        if is_pdf:
            return page_source  # Return the PDF text directly
        elif page_source:
            return get_text_from_tos_page(page_source)
        else:
            print("Failed to retrieve the Terms of Service page.")
            return None
    finally:
        driver.quit()

def get_text_from_tos_page(content):
    """Extract all text from the Terms of Service page after the 'Terms of Service' header."""
    soup = BeautifulSoup(content, 'html.parser')

    pattern = re.compile(r"terms of service", re.IGNORECASE)
    tos_header = soup.find(lambda tag: tag.name in ['h1', 'h2', 'h3'] and pattern.search(tag.get_text()))

    if tos_header:
        content = []
        element = tos_header.find_next()
        while element:
            if element.name in ['h1', 'h2', 'h3']:
                break 
            if element.get_text(strip=True):
                content.append(element.get_text(strip=True))
            element = element.find_next()
        return '\n'.join(content)
    else:
        return "Terms of Service section not found."

if __name__ == '__main__':
    url = 'https://www.spirit.com/legal'
    tos_text = get_tos_content(url)
    if tos_text:
        print(tos_text)
    else:
        print("No ToS content found.")
