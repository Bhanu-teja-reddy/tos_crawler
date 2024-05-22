from flask import Flask, render_template, request, jsonify
from selenium_scraper import get_tos_content  
from flask_mysqldb import MySQL
from datetime import datetime
import hashlib
import requests

app = Flask(__name__)

app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'mysql'
app.config['MYSQL_DB'] = 'tosdatabase'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/stored_tos', methods=['GET', 'POST'])
def stored_tos():
    search_query = ''
    cursor = mysql.connection.cursor()
    
    if request.method == 'POST':
        search_query = request.form.get('search', '')
        cursor.execute("""
            SELECT terms_of_service.tos_id, websites.url, terms_of_service.content, terms_of_service.date_recorded
            FROM terms_of_service
            JOIN websites ON terms_of_service.website_id = websites.website_id
            WHERE websites.url LIKE %s OR terms_of_service.content LIKE %s
            ORDER BY terms_of_service.date_recorded DESC
        """, ('%' + search_query + '%', '%' + search_query + '%'))
    else:
        cursor.execute("""
            SELECT terms_of_service.tos_id, websites.url, terms_of_service.content, terms_of_service.date_recorded
            FROM terms_of_service
            JOIN websites ON terms_of_service.website_id = websites.website_id
            ORDER BY terms_of_service.date_recorded DESC
        """)

    tos_entries = cursor.fetchall()
    cursor.close()
    return render_template('stored_tos.html', tos_entries=tos_entries, search_query=search_query)

@app.route('/archive_tos', methods=['GET', 'POST'])
def archive_tos():
    message = ''
    search_query = request.args.get('search', default='')
    archived_tos_entries = []

    if request.method == 'POST':
        tos_id = request.form.get('tos_id')
        content = request.form.get('content')
        
        if not tos_id or not content:
            message = 'No ToS ID or content provided'
        else:
            tos_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            cursor = mysql.connection.cursor()

         
            cursor.execute("SELECT content_hash FROM archive_tos WHERE content_hash = %s", (tos_hash,))
            if cursor.fetchone() is None:
                cursor.execute("""
                    INSERT INTO archive_tos (tos_id, content, content_hash, date_recorded)
                    VALUES (%s, %s, %s, NOW())
                """, (tos_id, content, tos_hash))
                mysql.connection.commit()
                message = 'Content archived successfully!'
            else:
                message = 'Content is already archived.'

            cursor.close()
    
    cursor = mysql.connection.cursor()


    sql_query = """
        SELECT at.archive_id, at.date_recorded, at.content_hash, ts.content as terms_content, w.url
        FROM archive_tos at
        JOIN terms_of_service ts ON at.tos_id = ts.tos_id
        JOIN websites w ON ts.website_id = w.website_id
        ORDER BY at.date_recorded DESC
    """

    if search_query: 
        sql_query += " WHERE w.url LIKE %s OR ts.content LIKE %s ORDER BY at.date_recorded DESC"
        search_like = f"%{search_query}%"
        cursor.execute(sql_query, (search_like, search_like))
    else:
        cursor.execute(sql_query)

    archived_tos_entries = cursor.fetchall()
    cursor.close()
    
    return render_template('archive_tos.html', archives=archived_tos_entries, message=message, search_query=search_query)

@app.route('/submit_url', methods=['POST'])
def submit_url():
    url = request.form['url']
    tos_id = request.form.get('tos_id')
    message = 'No Terms of Service processed.'
    tos_text = get_tos_content(url)
    current_time = datetime.now()
    cursor = mysql.connection.cursor()

    # Check if the website already exists in the database
    cursor.execute("SELECT website_id FROM websites WHERE url = %s", (url,))
    website_row = cursor.fetchone()

    if website_row:
        website_id = website_row['website_id']
    else:
        # Insert the new website into the database
        cursor.execute("INSERT INTO websites (url, last_scraped) VALUES (%s, %s)", (url, current_time))
        website_id = cursor.lastrowid

    # Update the last scraped time for the website
    cursor.execute("UPDATE websites SET last_scraped = %s WHERE website_id = %s", (current_time, website_id))
    mysql.connection.commit()

    if tos_text:
        tos_hash = hashlib.sha256(tos_text.encode('utf-8')).hexdigest()

        if tos_id:
            cursor.execute("SELECT content, content_hash FROM terms_of_service WHERE tos_id = %s", (tos_id,))
            existing = cursor.fetchone()
            if existing and existing['content_hash'] != tos_hash:
                # Archive the previous version
                cursor.execute("INSERT INTO archive_tos (tos_id, content, content_hash, date_recorded) VALUES (%s, %s, %s, %s)",
                               (tos_id, existing['content'], existing['content_hash'], current_time))
                mysql.connection.commit()
                # Update the ToS entry with the new content
                cursor.execute("UPDATE terms_of_service SET content = %s, content_hash = %s, date_recorded = %s WHERE tos_id = %s",
                               (tos_text, tos_hash, current_time, tos_id))
                mysql.connection.commit()
                message = 'Terms of Service content has changed and the previous version was archived.'
            else:
                message = 'No changes detected in Terms of Service.'
        else:
            # Check if the same content already exists in the database for this website
            cursor.execute("SELECT content_hash FROM terms_of_service WHERE website_id = %s AND content_hash = %s", 
                           (website_id, tos_hash))
            existing_hash = cursor.fetchone()
            if existing_hash:
                message = 'This ToS content already exists in the stored data.'
            else:
                # Insert the new ToS entry into the database
                cursor.execute("INSERT INTO terms_of_service (website_id, content, content_hash, date_recorded) VALUES (%s, %s, %s, %s)",
                               (website_id, tos_text, tos_hash, current_time))
                mysql.connection.commit()
                message = 'New Terms of Service saved successfully!'
    else:
        message = 'Failed to retrieve Terms of Service from the URL provided.'

    cursor.close()
    return render_template('scrape_result.html', url=url, content=tos_text if tos_text else '', time_scraped=current_time, message=message)




@app.route('/tos_details/<int:tos_id>', methods=['GET', 'POST'])
def tos_details(tos_id):
    cursor = mysql.connection.cursor()
    message = ""

    if request.method == 'POST':
        action = request.form.get('action')
        note = request.form.get('note', '')

        if action == 'update':
            cursor.execute("UPDATE terms_of_service SET notes = %s WHERE tos_id = %s", (note, tos_id))
            message = "Note updated successfully!"
        elif action == 'delete':
            cursor.execute("UPDATE terms_of_service SET notes = NULL WHERE tos_id = %s", (tos_id,))
            message = "Note deleted successfully!"
        mysql.connection.commit()

    cursor.execute("""
        SELECT ts.tos_id, ts.content, ts.date_recorded, w.url, ts.notes
        FROM terms_of_service ts
        JOIN websites w ON ts.website_id = w.website_id
        WHERE ts.tos_id = %s
    """, (tos_id,))
    entry = cursor.fetchone()
    cursor.close()

    if entry:
        return render_template('tos_details.html', entry=entry, message=message)
    else:
        return "ToS entry not found.", 404

    
@app.route('/archive_details/<int:archive_id>')
def archive_details(archive_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT at.archive_id, at.date_recorded, at.content_hash, at.content, w.url
        FROM archive_tos at
        JOIN terms_of_service ts ON at.tos_id = ts.tos_id
        JOIN websites w ON ts.website_id = w.website_id
        WHERE at.archive_id = %s
    """, (archive_id,))
    entry = cursor.fetchone()
    cursor.close()
    
    if entry:
        return render_template('archive_details.html', entry=entry)
    else:
        return "Archived ToS entry not found.", 404



def can_scrape_site(url):
    """ Check if scraping a website is allowed based on its robots.txt. """
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    robots_url = f"{base_url}/robots.txt"
    try:
        response = requests.get(robots_url)
        response.raise_for_status()
        lines = response.text.splitlines()
        for line in lines:
            if line.startswith('User-agent: *'):
                for rule in lines[lines.index(line):]:
                    if rule.startswith('Disallow: '):
                        disallowed_path = rule.split(' ')[1].strip()
                        if disallowed_path == '/' or url.startswith(f"{base_url}{disallowed_path}"):
                            return False
        return True
    except requests.RequestException:
        return False
    
if __name__ == '__main__':
    app.run(debug=True)
