#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin

prefixes = ("bo", "com.bo", "edu.bo", "gob.bo", "int.bo", "org.bo", "net.bo", "mil.bo", "tv.bo", "web.bo", "academia.bo", "agro.bo", "arte.bo", "blog.bo", "bolivia.bo", "ciencia.bo", "cooperativa.bo", "democracia.bo", "deporte.bo", "ecologia.bo", "economia.bo", "empresa.bo", "indigena.bo",
            "industria.bo", "info.bo", "medicina.bo", "movimiento.bo", "musica.bo", "natural.bo", "nombre.bo", "noticias.bo", "patria.bo", "politica.bo", "profesional.bo", "plurinacional.bo", "pueblo.bo", "revista.bo", "salud.bo", "tecnologia.bo", "tksat.bo", "transporte.bo", "wiki.bo", "ai.bo")


def get_domain_details(session, detail_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:149.0) Gecko/20100101 Firefox/149.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': 'https://nic.bo/dominio_buscar.php',
    }
    response = session.get(detail_url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table')
    if not table:
        return {}

    details = {}
    current_category = "General"

    for row in table.find_all('tr'):
        cells = [td.text.strip() for td in row.find_all(['td', 'th'])]
        if not cells:
            continue

        if len(cells) == 1:
            current_category = cells[0]
            details[current_category] = {}
        elif len(cells) >= 2:
            key = cells[0].rstrip(' :')
            value = cells[1]
            if current_category not in details:
                details[current_category] = {}
            details[current_category][key] = value

    return details


def get_whois_bo(dominio, subdominio=".bo", session=None):
    url_search = 'https://nic.bo/dominio_buscar.php#buscar'
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:149.0) Gecko/20100101 Firefox/149.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://nic.bo',
        'Referer': 'https://nic.bo/',
    }
    data = {
        'dominio': dominio,
        'subdominio': subdominio,
        'enviar': ''
    }

    if session is None:
        session = requests.Session()
        
    response = session.post(url_search, headers=headers, data=data)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'html.parser')

    # Extraemos la primera tabla, que corresponde al xpath:
    # /html/body/section[1]/div/div/div[2]/div/table
    table = soup.find('table')
    if not table:
        return {"error": "No se encontró la tabla de resultados"}

    results = []

    for row in table.find_all('tr'):
        cells = row.find_all(['td', 'th'])
        if len(cells) >= 2:
            domain_name = cells[0].text.strip()
            status = cells[1].text.strip()

            # Ignoramos la fila de cabecera
            if domain_name == 'Nombre de dominio':
                continue

            link_tag = row.find('a')

            result_item = {
                "dominio": domain_name,
                "estado": status,
            }

            # Si hay enlaces, extraemos la URL para sacar más datos
            if link_tag and 'href' in link_tag.attrs:
                href = link_tag['href']
                if "revisar_contacto.php" in href:
                    detail_url = urljoin('https://nic.bo/', href)
                    detail_data = get_domain_details(session, detail_url)
                    result_item["detalles"] = detail_data

            if len(cells) >= 3:
                result_item["precio"] = cells[2].text.strip()

            results.append(result_item)

    return results


def get_all_subdomains(dominio, session=None):
    """
    Usa el arreglo de consultar '.ia.bo' y '.bo' para obtener todos los subdominios posibles
    para un dominio dado sin duplicados.
    """
    if session is None:
        session = requests.Session()
        
    data_ia = get_whois_bo(dominio, '.ia.bo', session)
    data_bo = get_whois_bo(dominio, '.bo', session)
    
    # Manejar posibles errores
    if isinstance(data_ia, dict) and "error" in data_ia:
        data_ia = []
    if isinstance(data_bo, dict) and "error" in data_bo:
        data_bo = []
        
    all_data = data_ia + data_bo
    
    # Eliminar duplicados usando el nombre del dominio como llave
    seen = set()
    unique_data = []
    for item in all_data:
        if item["dominio"] not in seen:
            seen.add(item["dominio"])
            unique_data.append(item)
            
    return unique_data


def scan_multiple_domains(dominios):
    """
    Consulta multiples dominios y extrae todos sus subdominios posibles.
    """
    all_results = []
    # Reutilizar la sesión mejora el rendimiento para múltiples peticiones
    session = requests.Session() 
    
    for dominio in dominios:
        dom_results = get_all_subdomains(dominio, session)
        all_results.extend(dom_results)
        
    return all_results


import argparse
from toolkit_utils import fail, now_iso, get_targets, print_csv, flatten_json

def main():
    parser = argparse.ArgumentParser(description="Consulta de dominios en nic.bo")
    parser.add_argument("--target", nargs='+')
    parser.add_argument("--file", help="Archivo con lista de targets")
    args = parser.parse_args()

    targets = get_targets(args)
    if not targets:
        fail("Debes proveer al menos un target (--target o --file)")

    results = []
    session = requests.Session()
    
    for t in targets:
        dominio_raiz = t.replace(".bo", "").split(".")[0]
        try:
            dom_results = get_all_subdomains(dominio_raiz, session)
            if not dom_results:
                payload = {
                    "timestamp": now_iso(),
                    "action": "whois_bo",
                    "target": t,
                    "ok": False,
                    "status": 404,
                    "error": "No se encontraron resultados en nic.bo"
                }
                results.append(payload)
            else:
                for item in dom_results:
                    payload = {
                        "timestamp": now_iso(),
                        "action": "whois_bo",
                        "target": t,
                        "ok": True,
                        "status": 200,
                        "error": ""
                    }
                    flat = flatten_json(item, prefix="whois_")
                    payload.update(flat)
                    results.append(payload)
        except Exception as e:
            payload = {
                "timestamp": now_iso(),
                "action": "whois_bo",
                "target": t,
                "ok": False,
                "status": 500,
                "error": str(e)
            }
            results.append(payload)

    print_csv(results)

if __name__ == "__main__":
    main()
