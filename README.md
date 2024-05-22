
# ToS Scraper

## Overview
The ToS Scraper is a web application that allows users to scrape, store, and archive Terms of Service (ToS) documents from various websites. The application provides functionalities to submit URLs for scraping, view stored ToS data, and manage archived ToS versions.

## Features
- **Scrape ToS**: Users can submit a URL to scrape the ToS content from the specified website.
- **Store ToS**: The application stores the scraped ToS content, avoiding duplicates if the content has not changed.
- **Archive ToS**: When the ToS content changes, the previous version is archived for reference.
- **Notes and Annotations**: Users can add, update, and delete notes for specific ToS entries.
- **Search Functionality**: Users can search through archived and stored ToS entries by URL or content.

## Prerequisites
- Python 3.10(or above)
- Flask
- Selenium
- MySQL (or any other database you choose to use)

## Setup and Installation
1. **Clone the repository**:
   ```
   git clone https://github.com/Bhanu-teja-reddy/tos_crawler
   cd ToS-Scraper
   ```

2. **Install the dependencies**:
   ```
   pip install -r requirements.txt
   ```

3. **Set up the database**:
   - **Install MySQL**:
     - Make sure you have MySQL installed on your system. You can download and install it from the [official MySQL website](https://dev.mysql.com/downloads/mysql/).
   - **Create a Database**:
     - Open your MySQL command-line client or any MySQL management tool like phpMyAdmin.
     - Create a new database for the application. You can name it `tos_scraper` or any other name you prefer.
     ```sql
     CREATE DATABASE tos_scraper;
     ```
   - **Create Tables**:
     - Create the necessary tables for storing websites, terms of service, and archived terms of service.
     - Below is the SQL script to create the required tables:
     ```sql
     USE tos_scraper;

     CREATE TABLE websites (
         website_id INT AUTO_INCREMENT PRIMARY KEY,
         url VARCHAR(255) NOT NULL,
         last_scraped DATETIME
     );

     CREATE TABLE terms_of_service (
         tos_id INT AUTO_INCREMENT PRIMARY KEY,
         website_id INT,
         content TEXT,
         content_hash VARCHAR(64),
         date_recorded DATETIME,
         FOREIGN KEY (website_id) REFERENCES websites(website_id)
     );

     CREATE TABLE archive_tos (
         archive_id INT AUTO_INCREMENT PRIMARY KEY,
         tos_id INT,
         content TEXT,
         content_hash VARCHAR(64),
         date_recorded DATETIME,
         FOREIGN KEY (tos_id) REFERENCES terms_of_service(tos_id)
     );
  - **Update Connection Details in `app.py`**:
     - In your `app.py` file, you need to configure the database connection details. Ensure you have the correct database credentials.
     - Update the connection string with your MySQL username, password, and database name.
     
4. **Run the application**:
   ```
   python app.py
   ```

5. **Access the application**:
   - Open your web browser and navigate to `http://127.0.0.1:5000`.

## Usage
- **Submit URL**: Enter a URL to scrape the ToS content.
- **View Stored ToS**: Navigate to "Stored ToS Data" to view the stored ToS entries.
- **View Archived ToS**: Navigate to "Archive" to view archived ToS entries.
- **Manage Notes**: Add, update, or delete notes for specific ToS entries.
