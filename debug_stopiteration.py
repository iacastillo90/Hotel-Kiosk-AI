"""
Script para debuggear el error de StopIteration.
Este script busca todos los lugares donde puede estar ocurriendo el error.
"""
import ast
import os
from pathlib import Path

def find_async_generators_with_return(directory):
    """Encuentra async generators que usan return"""
    results = []
    
    for py_file in Path(directory).rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
                
            for node in ast.walk(tree):
                # Buscar funciones async que devuelven AsyncGenerator
                if isinstance(node, ast.AsyncFunctionDef):
                    # Verificar si es un generator (tiene yield)
                    has_yield = any(isinstance(n, (ast.Yield, ast.YieldFrom)) 
                                   for n in ast.walk(node))
                    
                    # Verificar si tiene return con valor
                    for n in ast.walk(node):
                        if isinstance(n, ast.Return) and n.value is not None:
                            if has_yield:
                                results.append({
                                    'file': str(py_file),
                                    'function': node.name,
                                    'line': n.lineno,
                                    'type': 'return_in_generator'
                                })
                        elif isinstance(n, ast.Return) and n.value is None and has_yield:
                            # return sin valor también puede causar problemas
                            results.append({
                                'file': str(py_file),
                                'function': node.name,
                                'line': n.lineno,
                                'type': 'bare_return_in_generator'
                            })
                            
        except Exception as e:
            print(f"Error procesando {py_file}: {e}")
            
    return results

if __name__ == "__main__":
    print("🔍 Buscando async generators con return statements...\n")
    
    results = find_async_generators_with_return(".")
    
    if results:
        print(f"❌ Encontrados {len(results)} problemas potenciales:\n")
        for r in results:
            print(f"  📄 {r['file']}")
            print(f"     Función: {r['function']}")
            print(f"     Línea: {r['line']}")
            print(f"     Tipo: {r['type']}")
            print()
    else:
        print("✅ No se encontraron async generators con return statements")
