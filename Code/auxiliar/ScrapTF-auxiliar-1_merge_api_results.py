import json
import os


base_path = "Downloads/" #Salvo em um diretório de interesse. Você pode, ao tentar replicar, salvar no mesmo diretório que o código, se quiser.

file_names = [
    os.path.join(base_path, 'pagina1.txt'),
    os.path.join(base_path, 'pagina2.txt'),
    os.path.join(base_path, 'pagina3.txt'),
    os.path.join(base_path, 'pagina4.txt'),
    os.path.join(base_path, 'pagina5.txt')
]

all_hits = []
base_json = None


for file_path in file_names:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if base_json is None:
                base_json = data
            if 'result' in data and 'hits' in data['result'] and 'hits' in data['result']['hits']:
                all_hits.extend(data['result']['hits']['hits'])
            else:
                print(f"Aviso: O arquivo {os.path.basename(file_path)} não contém a estrutura esperada 'result.hits.hits'.")

    except FileNotFoundError:
        print(f"Erro: O arquivo {file_path} não foi encontrado.")
    except json.JSONDecodeError:
        print(f"Erro: O arquivo {os.path.basename(file_path)} não contém um JSON válido.")
    except Exception as e:
        print(f"Ocorreu um erro ao processar o arquivo {os.path.basename(file_path)}: {e}")

if base_json and all_hits:
    base_json['result']['hits']['hits'] = all_hits
    base_json['result']['hits']['total']['value'] = len(all_hits)
    output_file = os.path.join(base_path, 'merged_result.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(base_json, f, ensure_ascii=False, indent=4)

    print(f"Merge concluído com sucesso! O resultado foi salvo em '{output_file}'.")
else:
    print("Não foi possível realizar o merge. Verifique os arquivos de entrada.")