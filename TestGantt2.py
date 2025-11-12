import pandas as pd
import numpy as np

# Bestandsnamen
INPUT_FILE = "book1.xlsx"
OUTPUT_FILE = "Book1_CLEANED.xlsx"


# De gewenste kolomnamen, zoals in het 'Bus Planning' bestand.
# We gebruiken de namen die het meest lijken op de output van een planningstool.
TARGET_COLUMNS = [
    'bus',
    'start time',
    'end time',
    'activity',
    'line',
    'start location',
    'end location',
    'time (min)',
    'energy used (kWh)',
    'battery start (kWh)',
    'batterij end (kWh)'
]

def clean_and_convert_data(input_file, output_file, target_columns):
    """
    Laadt het Book1-bestand, past de kolommen aan en verwijdert ongewenste opmaakrijen.
    """
    print(f"Laden van bestand: {input_file}...")
    try:
        # Laden van de CSV
        df = pd.read_csv(input_file)
        
        # Oude kolomnamen (uit de snippet)
        original_cols = df.columns.tolist()
        
        # Controleer of het aantal kolommen overeenkomt of dichtbij is
        if len(original_cols) != len(target_columns):
            print(f"WAARSCHUWING: Kolomtelling komt niet overeen. Verwacht: {len(target_columns)}, Gevonden: {len(original_cols)}")
            print("Originele kolommen:", original_cols)
            print("Doelkolommen:", target_columns)
            
            # Voer handmatige mapping uit op basis van de snippet/uploaded data
            # Kolomnamen in Book1: ['bus', 'start time', 'end time', 'activity', 'line', 'start location', 'end location', 'time (min)', 'energy used (kWh)', 'battery start (kWh)', 'batterij end (kWh)']
            # Deze komen gelukkig al overeen met de gewenste namen, we hernoemen alleen voor de zekerheid als er kleine verschillen zijn.
            df.columns = target_columns[:len(original_cols)]

        else:
             # Hernoem alle kolommen naar de doelkolommen
            df.columns = target_columns


        # 1. Verwijder rijen die dienen als scheidingsteken (zoals '---' of lege rijen)
        # We controleren of de 'bus' kolom een geldig nummer bevat.
        # Rijen met '---' of lege waarden in 'bus' worden verwijderd.
        df_cleaned = df[pd.to_numeric(df['bus'], errors='coerce').notna()]
        
        # Log hoeveel rijen zijn verwijderd
        removed_rows = len(df) - len(df_cleaned)
        print(f"Aantal verwijderde opmaakrijen (bv. '---'): {removed_rows}")

        # 2. Verwijder of converteer dikgedrukte tekst (niet zichtbaar in CSV, maar kan hoofdletters zijn)
        # We zetten alle tekstkolommen in 'activity' en 'start/end location' naar kleine letters voor consistentie.
        # Dit helpt bij het groeperen en visualiseren van data.
        if 'activity' in df_cleaned.columns:
            df_cleaned['activity'] = df_cleaned['activity'].astype(str).str.lower().str.strip()
        if 'start location' in df_cleaned.columns:
            df_cleaned['start location'] = df_cleaned['start location'].astype(str).str.lower().str.strip()
        if 'end location' in df_cleaned.columns:
            df_cleaned['end location'] = df_cleaned['end location'].astype(str).str.lower().str.strip()


        # Sla het opgeschoonde bestand op
        df_cleaned.to_csv(output_file, index=False)
        
        print(f"\nSucces! Het opgeschoonde bestand is opgeslagen als: {output_file}")
        print("U kunt dit bestand nu gebruiken voor verdere analyse en het maken van de Gantt-grafiek.")
        
        return df_cleaned

    except FileNotFoundError:
        print(f"Fout: Bestand '{input_file}' niet gevonden. Zorg ervoor dat het bestand correct is geüpload.")
        return None
    except Exception as e:
        print(f"Er is een onverwachte fout opgetreden: {e}")
        return None

# Voer de opschoning uit
clean_and_convert_data(INPUT_FILE, OUTPUT_FILE, TARGET_COLUMNS)

