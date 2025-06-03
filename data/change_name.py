import os
import json

# Ruta al directorio de los archivos
base_path = os.path.expanduser('~/BREI/GuessDle/data')

# Funciones de alias
def harry_potter_alias(name):
    alias_map = {
        "Mr Crabbe": "Vincent Crabbe",
        "Mr Goyle": "Gregory Goyle",
        "Mrs Norris": "Sra. Norris",
        "Lily Potter": "Lily Evans",
        "Mrs Figg": "Arabella Figg",
        "Nearly Headless Nick": "Nicholas de Mimsy-Porpington",
        "Alicia Spinet": "Alicia Spinnet",
        "Mr Borgin": "Borgin",
        "Moaning Myrtle": "Myrtle Warren",
        "Ernest Prang": "Ernie Prang",
        "Barty Crouch": "Bartemius Crouch Sr.",
        "The Grey Lady": "Helena Ravenclaw",
        "Albus Severus Potter": "Albus Potter",
        "Milicent Bullstroude": "Millicent Bulstrode",
        "Barty Crouch Junior": "Bartemius Crouch Jr.",
        "Madam Hooch": "Rolanda Hooch"
    }
    return alias_map.get(name, name)

def one_piece_alias(name):
    alias_map = {
        "Edward Weeble": "Edward Weevil",
        "Ben Beckmann": "Benn Beckman",
        "Yassop": "Yasopp",
        "Don Quijote Doflamingo": "Donquixote Doflamingo",
        "Akainu (Sakazuki)": "Sakazuki",
        "Kizaru (Borsalino)": "Kizaru",
        "Fujitora (Issho)": "Issho",
        "Ryokugyu (Aramaki)": "Aramaki",
        "Kobby": "Koby",
        "Johny": "Johnny",
        "Iceberg": "Iceburg",
        "Oden Kozuki": "Kozuki Oden",
        "Ryuma Shimotsuki": "Shimotsuki Ryuma",
        "Judge Vinsmoke": "Vinsmoke Judge",
        "Reiju Vinsmoke": "Vinsmoke Reiju",
        "Ichiji Vinsmoke": "Vinsmoke Ichiji",
        "Niji Vinsmoke": "Vinsmoke Niji",
        "Yonji Vinsmoke": "Vinsmoke Yonji",
        "Aokiji (Kuzan)": "Kuzan",
        "Cesar Clown": "Caesar Clown",
        "Karazu": "Karasu",
        "Kaashii": "Kashi"
    }
    return alias_map.get(name, name)

# Procesamiento de archivos
def process_file(file_name, key_name, alias_function):
    file_path = os.path.join(base_path, file_name)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error al leer {file_name}: {e}")
        return

    if not isinstance(data, list):
        print(f"{file_name} no contiene un array en la raíz, omitiendo.")
        return

    modified = False
    for obj in data:
        if isinstance(obj, dict) and key_name in obj:
            original = obj[key_name]
            new_value = alias_function(original)
            if original != new_value:
                obj[key_name] = new_value
                modified = True

    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Actualizado: {file_name}")
    else:
        print(f"No hubo cambios necesarios en: {file_name}")

# Ejecutar para los dos archivos
process_file('harry-potter.json', 'name', harry_potter_alias)
process_file('one-piece.json', 'nombre', one_piece_alias)
