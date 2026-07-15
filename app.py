import asyncio
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, render_template
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options

app = Flask(__name__)

def search_eurlex(query):
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=options)
    try:
        driver.get("https://eur-lex.europa.eu/homepage.html?locale=en")

        advanced_search_link = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Advanced search')]"))
        )
        advanced_search_link.click()

        textarea = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "andConditionsMapping_0"))
        )
        textarea.send_keys(query)

        try:
            text_checkbox = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "checkbox_AND_0_1"))
            )
            if text_checkbox.is_selected():
                text_checkbox.click()
        except:
            pass

        try:
            excl_cons_leg_checkbox = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "excConsLeg"))
            )
            if not excl_cons_leg_checkbox.is_selected():
                excl_cons_leg_checkbox.click()
        except:
            pass

        try:
            excl_corr_checkbox = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "excCorr"))
            )
            if not excl_corr_checkbox.is_selected():
                excl_corr_checkbox.click()
        except:
            pass

        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "topSearch"))
        )
        search_button.click()

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.SearchResult"))
        )

        return {"source": "EUR-Lex", "url": driver.current_url}
    except Exception as e:
        return {"error": f"EUR-Lex: {str(e)}"}
    finally:
        driver.quit()

def search_nlex(query):
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=options)
    try:
        driver.get("https://n-lex.europa.eu/n-lex/aggregated-search")

        all_countries_checkbox = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "edit-country-all"))
        )
        all_countries_checkbox.click()

        try:
            text_checkbox = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "text-position"))
            )
            if text_checkbox.is_selected():
                text_checkbox.click()
        except:
            pass

        search_box = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "edit-words-field"))
        )
        search_box.send_keys(query)
        search_box.send_keys(Keys.RETURN)

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "AggrResultsTable"))
        )

        return {"source": "N-Lex", "url": driver.current_url}
    except Exception as e:
        return {"error": f"N-Lex: {str(e)}"}
    finally:
        driver.quit()

def search_legislationline(query):
    import urllib.parse
    encoded_query = urllib.parse.quote(f"text:{query},lang:en")
    url = f"https://legislationline.org/search?q={encoded_query}"
    return {"source": "Legislationline", "url": url}


async def run_in_executor(executor, func, query):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, query)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
async def search():
    query = request.form.get('query')
    if not query:
        return jsonify({"error": "No query provided"}), 400

    with ThreadPoolExecutor(max_workers=3) as executor:
        eurlex_task = run_in_executor(executor, search_eurlex, query)
        nlex_task = run_in_executor(executor, search_nlex, query)
        legislationline_task = run_in_executor(executor, search_legislationline, query)

        results = await asyncio.gather(eurlex_task, nlex_task, legislationline_task, return_exceptions=True)

    final_results = []
    for result in results:
        if isinstance(result, dict) and "url" in result:
            final_results.append({"source": result["source"], "url": result["url"]})

    if final_results:
        return jsonify({"results": final_results})

    error_messages = " ".join([res["error"] for res in results if isinstance(res, dict) and "error" in res])
    return jsonify({"error": error_messages or "No results found."})

if __name__ == "__main__":
    app.run(debug=True, port=3000)
