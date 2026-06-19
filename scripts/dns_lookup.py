#!/usr/bin/env python3
import argparse
import sys

try:
    import dns.resolver
except ImportError:
    print("Error: Falta la librería 'dnspython'.")
    print("Instálala ejecutando: pip install dnspython")
    sys.exit(1)

def lookup_domain(domain):
    record_types = ['A', 'AAAA', 'CNAME', 'MX', 'NS', 'TXT', 'SOA']
    results = {}
    
    # Configurar el resolver con tiempos de espera razonables
    resolver = dns.resolver.Resolver()
    resolver.timeout = 5
    resolver.lifetime = 5
    
    print(f"Buscando registros DNS para: {domain}")
    print("=" * 50)
    
    try:
        # Hacer una primera consulta rápida para ver si existe el dominio (NXDOMAIN)
        resolver.resolve(domain, 'A')
    except dns.resolver.NXDOMAIN:
        print(f"Error: El dominio '{domain}' no existe (NXDOMAIN).")
        return
    except Exception:
        pass # Ignoramos errores aquí, puede que no tenga registro A pero sí otros

    for qtype in record_types:
        try:
            answers = resolver.resolve(domain, qtype)
            records = [rdata.to_text() for rdata in answers]
            results[qtype] = records
            print(f"[{qtype}] Registros encontrados ({len(records)}):")
            for record in records:
                print(f"  - {record}")
            print("-" * 50)
        except dns.resolver.NoAnswer:
            # El dominio existe, pero no tiene este tipo de registro
            pass
        except dns.resolver.NXDOMAIN:
            break
        except dns.exception.Timeout:
            print(f"[{qtype}] Error: Tiempo de espera agotado.")
            print("-" * 50)
        except Exception as e:
            # Otros errores como problemas de red o configuración DNS errónea
            pass
            
    if not results:
        print("No se encontraron registros comunes para este dominio.")

def main():
    parser = argparse.ArgumentParser(description="Consulta de registros DNS para un dominio o subdominio.")
    parser.add_argument("domain", help="El dominio o subdominio a consultar (ej: google.com)")
    
    args = parser.parse_args()
    lookup_domain(args.domain)

if __name__ == "__main__":
    main()
