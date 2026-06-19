
import argparse
import csv
import json
import os
import sys
from itertools import islice

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = 'https://openpagerank.com/api/v1.0/getPageRank'
HEADERS = {'API-OPR': os.getenv('OPEN_RANK_API_KEY', 'YOUR-API-KEY-HERE')}
BATCH_SIZE = 250


def get_openpagerank(domains):
	params = [('domains[]', d) for d in domains]
	resp = requests.get(API_URL, headers=HEADERS, params=params, timeout=30)
	resp.raise_for_status()
	return resp.json()


def collect_response_rows(api_results):
	rows = []
	for result in api_results:
		rows.extend(result.get('response', []))
	return rows


def write_csv(rows, output_stream):
	fieldnames = sorted({key for row in rows for key in row.keys()}) if rows else []
	writer = csv.DictWriter(output_stream, fieldnames=fieldnames)
	writer.writeheader()
	writer.writerows(rows)


def read_domains_from_csv(csv_path):
	with open(csv_path, newline='', encoding='utf-8') as f:
		reader = csv.DictReader(f)
		for row in reader:
			domain = (row.get('dominio') or '').strip()
			if domain:
				yield domain


def chunked(iterator, size):
	while True:
		chunk = list(islice(iterator, size))
		if not chunk:
			break
		yield chunk


def main():
	parser = argparse.ArgumentParser(description='Consulta OpenPageRank desde un CSV con la columna dominio.')
	parser.add_argument('csv_file', help='Ruta al archivo CSV de entrada')
	parser.add_argument('--batch-size', type=int, default=BATCH_SIZE, help='Cantidad de dominios por petición (default: 250)')
	parser.add_argument('--output-csv', help='Ruta del CSV de salida. Si no se indica, se imprime por stdout.')
	args = parser.parse_args()

	domains = read_domains_from_csv(args.csv_file)
	results = []
	for batch in chunked(domains, args.batch_size):
		results.append(get_openpagerank(batch))

	response_rows = collect_response_rows(results)
	if args.output_csv:
		with open(args.output_csv, 'w', newline='', encoding='utf-8') as f:
			write_csv(response_rows, f)
	else:
		write_csv(response_rows, sys.stdout)


if __name__ == '__main__':
	main()
		